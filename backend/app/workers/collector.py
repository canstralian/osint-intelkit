"""
Domain collection worker - passive OSINT gathering.

This module performs passive collection of publicly available information
about domains. All operations are non-intrusive and use public data sources.
"""
import asyncio
import aiohttp
import structlog
from typing import Optional, Dict
from datetime import datetime

from ..db.postgres import save_domain
from ..db.neo4j import link_domain
from .vt_enricher import vt_enrich_domain

log = structlog.get_logger()

async def collect_domain(domain: str, source: str = "collector") -> Dict:
    """
    Passive domain collection - gathers publicly available information.

    This function performs PASSIVE collection only:
    - Certificate transparency logs
    - Public DNS records
    - WHOIS information (public registries)
    - No active scanning or intrusive probing

    Args:
        domain: Domain name to collect intelligence on
        source: Source identifier for provenance tracking

    Returns:
        Dictionary with collection results

    IMPORTANT: Only use for authorized targets
    """
    log.info("collector_start", domain=domain, source=source)

    try:
        # Save domain to PostgreSQL with provenance
        domain_id = await save_domain(domain, source, metadata={
            "collection_timestamp": datetime.utcnow().isoformat(),
            "collection_method": "passive"
        })

        # Create or update domain node in Neo4j graph
        await link_domain(domain, metadata={
            "source": source,
            "collected_at": datetime.utcnow().isoformat()
        })

        log.info("collector_recorded", domain=domain)

        # Kick one enrichment here; bulk runs come from Prefect
        await vt_enrich_domain(domain)

        return {
            "status": "success",
            "domain": domain,
            "domain_id": domain_id,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        log.exception("collector_error", domain=domain, error=str(e))
        return {
            "status": "error",
            "domain": domain,
            "error": str(e)
        }

async def collect_from_crtsh(domain: str) -> Optional[Dict]:
    """
    Query Certificate Transparency logs via crt.sh.

    This is a passive, non-intrusive source that uses public CT logs.

    Args:
        domain: Domain name

    Returns:
        Certificate transparency data
    """
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    log.info("crtsh_success", domain=domain, cert_count=len(data))
                    return {
                        "source": "crt.sh",
                        "certificate_count": len(data),
                        "certificates": data[:100]  # Limit to avoid large payloads
                    }
                else:
                    log.warning("crtsh_http_error", domain=domain, status=response.status)
                    return None

    except asyncio.TimeoutError:
        log.warning("crtsh_timeout", domain=domain)
        return None
    except Exception as e:
        log.error("crtsh_error", domain=domain, error=str(e))
        return None

async def collect_subdomains_passive(domain: str) -> Dict:
    """
    Collect subdomains from passive sources only.

    Uses:
    - Certificate transparency logs
    - Public DNS datasets
    - Search engine results (within rate limits)

    Does NOT perform:
    - Active DNS bruteforcing
    - Network scanning
    - Intrusive enumeration

    Args:
        domain: Domain name

    Returns:
        Subdomain collection results
    """
    log.info("passive_subdomain_start", domain=domain)

    subdomains = set()

    # Collect from certificate transparency
    ct_data = await collect_from_crtsh(domain)
    if ct_data and "certificates" in ct_data:
        for cert in ct_data["certificates"]:
            # Extract domain names from certificate
            name_value = cert.get("name_value", "")
            for name in name_value.split("\n"):
                name = name.strip()
                if name and domain in name:
                    subdomains.add(name)

    log.info("passive_subdomain_complete", domain=domain, subdomain_count=len(subdomains))

    return {
        "domain": domain,
        "subdomain_count": len(subdomains),
        "subdomains": list(subdomains)[:500],  # Limit results
        "sources": ["certificate_transparency"]
    }

# Main worker loop (for standalone execution)
async def worker_main():
    """
    Main worker loop for continuous operation.

    This can be run as a separate service that processes domains
    from a queue or database.
    """
    log.info("collector_worker_start")

    # Example: Process a queue of domains
    # In production, integrate with message queue (RabbitMQ, Redis, etc.)

    while True:
        try:
            # Placeholder: Get domains from queue
            # domain = await get_next_domain_from_queue()

            await asyncio.sleep(60)  # Wait between iterations

        except KeyboardInterrupt:
            log.info("collector_worker_shutdown")
            break
        except Exception as e:
            log.error("collector_worker_error", error=str(e))
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(worker_main())
