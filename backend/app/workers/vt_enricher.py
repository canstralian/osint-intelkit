"""
VirusTotal enrichment worker.

Enriches domain data using VirusTotal's API for threat intelligence.

IMPORTANT:
- Requires valid VirusTotal API key
- Respects rate limits (4 req/min for free tier)
- Use only for authorized defensive security purposes
"""
import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Dict

from ..db.postgres import add_enrichment, record_api_usage
from ..config.logging import get_logger

logger = get_logger(__name__)

# VirusTotal API configuration
VT_API_KEY = os.getenv("API_KEY_VT")
VT_BASE_URL = "https://www.virustotal.com/api/v3"
VT_RATE_LIMIT = int(os.getenv("VT_RATE_LIMIT", "4"))  # requests per minute

# Rate limiting state
_last_vt_request = None
_vt_request_count = 0

async def rate_limit_vt():
    """
    Enforce VirusTotal API rate limits.

    Free tier: 4 requests per minute
    Premium: Higher limits (configure via environment)
    """
    global _last_vt_request, _vt_request_count

    current_time = datetime.utcnow()

    # Reset counter every minute
    if _last_vt_request is None or (current_time - _last_vt_request).seconds >= 60:
        _vt_request_count = 0
        _last_vt_request = current_time

    # Enforce rate limit
    if _vt_request_count >= VT_RATE_LIMIT:
        wait_time = 60 - (current_time - _last_vt_request).seconds
        if wait_time > 0:
            logger.info("vt_rate_limit_reached", wait_seconds=wait_time, rate_limit=VT_RATE_LIMIT)
            await asyncio.sleep(wait_time)
            _vt_request_count = 0
            _last_vt_request = datetime.utcnow()

    _vt_request_count += 1

async def vt_enrich_domain(domain: str) -> Optional[Dict]:
    """
    Fetch threat intelligence for a domain from VirusTotal.

    Retrieves:
    - Reputation score
    - Detection statistics
    - Categories and tags
    - Historical analysis data

    Args:
        domain: Domain name to enrich

    Returns:
        Enrichment data or None if error

    Rate limiting:
        Automatically enforced (4 req/min for free tier)
    """
    if not VT_API_KEY or VT_API_KEY == "your_virustotal_api_key_here":
        logger.warning("vt_api_key_missing", message="No valid API key configured, skipping enrichment")
        return None

    logger.info("vt_enrichment_started", domain=domain, security_event=True)

    try:
        # Enforce rate limiting
        await rate_limit_vt()

        headers = {"x-apikey": VT_API_KEY}
        url = f"{VT_BASE_URL}/domains/{domain}"

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                # Record API usage
                rate_limit_remaining = response.headers.get("X-Ratelimit-Remaining")
                await record_api_usage(
                    "virustotal",
                    f"/domains/{domain}",
                    rate_limit_remaining=int(rate_limit_remaining) if rate_limit_remaining else None
                )

                if response.status == 200:
                    data = await response.json()

                    # Extract relevant fields
                    attributes = data.get("data", {}).get("attributes", {})

                    enrichment_data = {
                        "reputation": attributes.get("reputation"),
                        "last_analysis_stats": attributes.get("last_analysis_stats", {}),
                        "last_analysis_date": attributes.get("last_analysis_date"),
                        "categories": attributes.get("categories", {}),
                        "total_votes": attributes.get("total_votes", {}),
                        "popularity_ranks": attributes.get("popularity_ranks", {}),
                        "last_dns_records": attributes.get("last_dns_records", [])[:10],
                        "whois": attributes.get("whois"),
                        "tags": attributes.get("tags", []),
                    }

                    # Calculate confidence score based on detection ratio
                    stats = enrichment_data.get("last_analysis_stats", {})
                    total = sum(stats.values()) if stats else 0
                    malicious = stats.get("malicious", 0)
                    confidence = (malicious / total) if total > 0 else 0.0

                    # Save enrichment to database
                    await add_enrichment(domain, "virustotal", enrichment_data, confidence)

                    logger.info(
                        "vt_enrichment_success",
                        domain=domain,
                        reputation=enrichment_data['reputation'],
                        malicious_detections=malicious,
                        total_detections=total,
                        confidence=confidence,
                        security_event=True
                    )

                    return enrichment_data

                elif response.status == 404:
                    logger.info("vt_domain_not_found", domain=domain)
                    return None

                elif response.status == 429:
                    logger.warning("vt_rate_limit_exceeded", domain=domain, security_event=True)
                    await asyncio.sleep(60)  # Wait before retry
                    return None

                else:
                    error_data = await response.text()
                    logger.error(
                        "vt_http_error",
                        domain=domain,
                        status_code=response.status,
                        error_response=error_data[:200],  # Limit error message length
                        security_event=True
                    )
                    return None

    except asyncio.TimeoutError:
        logger.error("vt_timeout", domain=domain, security_event=True)
        return None

    except Exception as e:
        logger.error("vt_enrichment_error", domain=domain, error=str(e), exc_info=True, security_event=True)
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
        logger.warning("[VT] No valid API key configured")
        return None

    try:
        await rate_limit_vt()

        headers = {"x-apikey": VT_API_KEY}
        url = f"{VT_BASE_URL}/ip_addresses/{ip}"

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                await record_api_usage("virustotal", f"/ip_addresses/{ip}")

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

                    logger.info(f"[VT] Enriched IP {ip}")
                    return enrichment_data

                else:
                    logger.warning(f"[VT] HTTP {response.status} for IP {ip}")
                    return None

    except Exception as e:
        logger.error(f"[VT] Error enriching IP {ip}: {e}")
        return None

# Worker main loop for standalone execution
async def worker_main():
    """Main enrichment worker loop."""
    logger.info("[VT Enricher Worker] Starting up")

    while True:
        try:
            # Placeholder: Get domains from enrichment queue
            # domain = await get_next_domain_for_enrichment()

            await asyncio.sleep(60)

        except KeyboardInterrupt:
            logger.info("[VT Enricher Worker] Shutting down")
            break
        except Exception as e:
            logger.error(f"[VT Enricher Worker] Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(worker_main())
