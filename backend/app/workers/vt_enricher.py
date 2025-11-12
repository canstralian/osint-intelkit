"""
VirusTotal enricher with resilient error handling, backoff, and cache fallback.

IMPORTANT:
- Requires valid VirusTotal API key
- Respects rate limits with exponential backoff
- Use only for authorized defensive security purposes
"""
import os
import aiohttp
from datetime import datetime
from typing import Optional, Dict
from ..db.postgres import add_enrichment, last_enrichment

log = structlog.get_logger()
VT_API_KEY = os.getenv("API_KEY_VT")
VT_BASE = "https://www.virustotal.com/api/v3"
HEADERS = {"x-apikey": VT_API_KEY} if VT_API_KEY else {}


class VTQuota(Exception):
    """Rate limit / quota exceeded."""
    pass


class VTError(Exception):
    """General VT API error."""
    pass


async def _fetch(session: aiohttp.ClientSession, url: str):
    """Internal fetch with error classification."""
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        if resp.status == 429:
            raise VTQuota("rate_limited")
        if resp.status >= 500:
            raise VTError(f"server_error_{resp.status}")
        if resp.status == 404:
            # Domain not found in VT - not an error per se
            return None
        if resp.status != 200:
            text = await resp.text()
            raise VTError(f"bad_status_{resp.status}_{text[:120]}")
        return await resp.json()


    # Enforce rate limit
    if _vt_request_count >= VT_RATE_LIMIT:
        wait_time = 60 - (current_time - _last_vt_request).seconds
        if wait_time > 0:
            logger.info("vt_rate_limit_reached", wait_seconds=wait_time, rate_limit=VT_RATE_LIMIT)
            await asyncio.sleep(wait_time)
            _vt_request_count = 0
            _last_vt_request = datetime.utcnow()
@retry(
    retry=retry_if_exception_type((VTQuota, VTError)),
    wait=wait_exponential_jitter(initial=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def vt_call(session, domain):
    """Call VT API with exponential backoff and jitter."""
    url = f"{VT_BASE}/domains/{domain}"
    return await _fetch(session, url)


async def vt_enrich_domain(domain: str, cache_ttl_minutes: int = 1440) -> Optional[Dict]:
    """
    Enrich a domain with VirusTotal data.

    Features:
    - Cache checking with configurable TTL
    - Exponential backoff with jitter on errors
    - Graceful fallback to cached data on rate limiting
    - Comprehensive error logging

    Args:
        domain: Domain name to enrich
        cache_ttl_minutes: Cache TTL in minutes (default: 1440 = 24 hours)

    Returns:
        Enrichment data dict or None on failure
    """
    if not VT_API_KEY or VT_API_KEY == "your_virustotal_api_key_here":
        log.warning("vt_api_key_missing", domain=domain)
        await add_enrichment(domain, "virustotal", "failed", error="api_key_missing")
        return None

    # Check cache: use last good if recent
    prev = await last_enrichment(domain, "virustotal")
    if prev and prev.get("status") in ("success", "cached"):
        # Simple TTL check
        if prev.get("created_at") and datetime.utcnow() - prev["created_at"] < timedelta(minutes=cache_ttl_minutes):
            log.info("vt_cache_hit", domain=domain)
            await add_enrichment(domain, "virustotal", "cached", data=prev.get("data"))
            return prev.get("data")

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            payload = await vt_call(session, domain)

            # Handle 404 (domain not found)
            if payload is None:
                log.info("vt_domain_not_found", domain=domain)
                await add_enrichment(domain, "virustotal", "success", data={"found": False})
                return {"found": False}

            attrs = payload.get("data", {}).get("attributes", {}) if payload else {}

            # Extract relevant fields
            reduced = {
                "found": True,
                "reputation": attrs.get("reputation"),
                "last_analysis_stats": attrs.get("last_analysis_stats"),
                "categories": attrs.get("categories"),
                "harmless_votes": attrs.get("total_votes", {}).get("harmless"),
                "malicious_votes": attrs.get("total_votes", {}).get("malicious"),
                "last_analysis_date": attrs.get("last_analysis_date"),
                "tags": attrs.get("tags", []),
            }

            await add_enrichment(domain, "virustotal", "success", data=reduced)
            log.info("vt_success", domain=domain, reputation=reduced.get("reputation"))

            # Polite pause to avoid bursts on free tier
            await asyncio.sleep(0.5)
            return reduced

        except VTQuota as e:
            log.warning("vt_rate_limited", domain=domain, error=str(e))
            if prev and prev.get("status") == "success":
                await add_enrichment(domain, "virustotal", "cached", data=prev.get("data"), error="rate_limited")
                return prev.get("data")
            await add_enrichment(domain, "virustotal", "failed", error="rate_limited_no_cache")
            return None

        except Exception as e:
            log.exception("vt_failed", domain=domain, error=str(e))
            if prev and prev.get("status") == "success":
                await add_enrichment(
                    domain, "virustotal", "cached", data=prev.get("data"), error="error_fallback_cache"
                )
                return prev.get("data")
            await add_enrichment(domain, "virustotal", "failed", error=str(e)[:200])
            return None


async def vt_enrich_ip(ip: str) -> Optional[Dict]:
    """
    Fetch threat intelligence for an IP address from VirusTotal.

    Args:
        ip: IP address to enrich

    Returns:
        Enrichment data or None if error
    """
    if not VT_API_KEY or VT_API_KEY == "your_virustotal_api_key_here":
        log.warning("vt_api_key_missing")
        return None

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            url = f"{VT_BASE}/ip_addresses/{ip}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    attributes = data.get("data", {}).get("attributes", {})

                    enrichment_data = {
                        "reputation": attributes.get("reputation"),
                        "last_analysis_stats": attributes.get("last_analysis_stats", {}),
                        "country": attributes.get("country"),
                        "asn": attributes.get("asn"),
                        "as_owner": attributes.get("as_owner"),
                        "network": attributes.get("network"),
                    }

                    log.info("vt_ip_success", ip=ip)
                    return enrichment_data
                else:
                    log.warning("vt_ip_failed", ip=ip, status=response.status)
                    return None

    except Exception as e:
        log.error("vt_ip_error", ip=ip, error=str(e))
        return None
