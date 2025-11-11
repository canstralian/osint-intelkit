"""
Prefect flow orchestration for scheduled OSINT collection and enrichment.

This module defines Prefect flows that coordinate:
- Domain collection from seed lists
- Passive intelligence gathering
- VirusTotal enrichment
- Graph database updates

Scheduling options:
- Interval-based (every N hours)
- Cron-based schedules
- Event-driven triggers
"""
import asyncio
import logging
import os
from typing import List
from datetime import timedelta, datetime

from prefect import flow, task
from prefect.tasks import task_input_hash

from app.db.postgres import save_domain
from app.workers.vt_enricher import vt_enrich_domain
from app.workers.collector import collect_domain, collect_subdomains_passive
from app.db.neo4j import link_domain

logger = logging.getLogger(__name__)

# Seed domains for scheduled collection
# IMPORTANT: Only include authorized targets
# Can be overridden via OSINT_SEED_DOMAINS environment variable (comma-separated)
DEFAULT_SEED_DOMAINS = [
    "example.com",  # Replace with authorized targets
]

def get_seed_domains() -> List[str]:
    """
    Get seed domains from environment variable or default list.

    Returns:
        List of authorized domain names to collect
    """
    env_domains = os.getenv("OSINT_SEED_DOMAINS", "").strip()
    if env_domains:
        domains = [d.strip() for d in env_domains.split(",") if d.strip()]
        logger.info(f"Using {len(domains)} seed domains from environment")
        return domains
    else:
        logger.info(f"Using {len(DEFAULT_SEED_DOMAINS)} default seed domains")
        return DEFAULT_SEED_DOMAINS

@task(
    name="collect-seed-domains",
    description="Collect intelligence on seed domains",
    retries=2,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1)
)
async def collect_seed_domains(domains: List[str]) -> List[str]:
    """
    Task: Collect domain intelligence from seed list.

    Args:
        domains: List of domain names to collect

    Returns:
        List of successfully collected domains
    """
    logger.info(f"[Prefect Task] Collecting {len(domains)} seed domains")

    collected = []
    for domain in domains:
        try:
            result = await collect_domain(domain, source="scheduled_seed")
            if result.get("status") == "success":
                collected.append(domain)
                await link_domain(domain)
        except Exception as e:
            logger.error(f"[Prefect Task] Failed to collect {domain}: {e}")

    logger.info(f"[Prefect Task] Successfully collected {len(collected)}/{len(domains)} domains")
    return collected

@task(
    name="vt-enrich-domains",
    description="Enrich domains with VirusTotal intelligence",
    retries=3,
    retry_delay_seconds=120
)
async def vt_enrich_all(domains: List[str]) -> List[dict]:
    """
    Task: Enrich all domains with VirusTotal threat intelligence.

    Args:
        domains: List of domain names

    Returns:
        List of enrichment results
    """
    logger.info(f"[Prefect Task] Enriching {len(domains)} domains with VirusTotal")

    results = []
    for domain in domains:
        try:
            enrichment = await vt_enrich_domain(domain)
            if enrichment:
                results.append({
                    "domain": domain,
                    "status": "success",
                    "data": enrichment
                })
            else:
                results.append({
                    "domain": domain,
                    "status": "no_data"
                })

            # Rate limiting pause between requests
            await asyncio.sleep(15)  # 4 req/min = 15s between requests

        except Exception as e:
            logger.error(f"[Prefect Task] Failed to enrich {domain}: {e}")
            results.append({
                "domain": domain,
                "status": "error",
                "error": str(e)
            })

    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(f"[Prefect Task] Successfully enriched {success_count}/{len(domains)} domains")

    return results

@task(
    name="collect-subdomains",
    description="Collect subdomains from passive sources",
    retries=2,
    retry_delay_seconds=60
)
async def collect_subdomains_task(domains: List[str]) -> dict:
    """
    Task: Collect subdomains for all seed domains.

    Args:
        domains: List of parent domains

    Returns:
        Dictionary mapping domains to their subdomains
    """
    logger.info(f"[Prefect Task] Collecting subdomains for {len(domains)} domains")

    subdomain_map = {}
    for domain in domains:
        try:
            result = await collect_subdomains_passive(domain)
            subdomain_map[domain] = result.get("subdomains", [])

            # Save discovered subdomains
            for subdomain in subdomain_map[domain][:100]:  # Limit to avoid overload
                await save_domain(subdomain, source="subdomain_enumeration")
                await link_domain(subdomain)

        except Exception as e:
            logger.error(f"[Prefect Task] Failed subdomain collection for {domain}: {e}")
            subdomain_map[domain] = []

    total_subdomains = sum(len(subs) for subs in subdomain_map.values())
    logger.info(f"[Prefect Task] Discovered {total_subdomains} total subdomains")

    return subdomain_map

@flow(
    name="vt-osint-flow",
    description="Scheduled OSINT collection and VirusTotal enrichment flow",
    log_prints=True,
    timeout_seconds=7200  # 2 hours max
)
def scheduled_vt_osint(domains: List[str] = None):
    """
    Main Prefect flow: Orchestrates domain collection and enrichment.

    This flow:
    1. Collects intelligence on seed domains
    2. Discovers subdomains from passive sources
    3. Enriches all domains with VirusTotal intelligence
    4. Updates graph database with relationships

    Args:
        domains: Optional list of domains (defaults to seed domains from config)

    Usage:
        # Run once:
        scheduled_vt_osint()

        # Schedule with Prefect:
        scheduled_vt_osint.serve(
            name="osint-pipeline",
            interval=timedelta(hours=6)
        )
    """
    if domains is None:
        domains = get_seed_domains()

    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"[Flow] OSINT Collection Flow Started")
    logger.info(f"[Flow] Start Time: {start_time.isoformat()}")
    logger.info(f"[Flow] Target Domains: {len(domains)}")
    logger.info("=" * 60)

    # Run async tasks
    asyncio.run(run_flow_async(domains))

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info(f"[Flow] OSINT Collection Flow Completed")
    logger.info(f"[Flow] End Time: {end_time.isoformat()}")
    logger.info(f"[Flow] Duration: {duration:.2f} seconds")
    logger.info("=" * 60)

async def run_flow_async(domains: List[str]):
    """
    Async execution wrapper for Prefect flow.

    Args:
        domains: List of domains to process
    """
    # Step 1: Collect seed domains
    collected_domains = await collect_seed_domains.fn(domains)

    if not collected_domains:
        logger.warning("[Flow] No domains collected, skipping enrichment")
        return

    # Step 2: Discover subdomains (passive only)
    subdomain_map = await collect_subdomains_task.fn(collected_domains)

    # Step 3: Enrich all domains (seeds + discovered subdomains)
    all_domains = set(collected_domains)
    for subs in subdomain_map.values():
        all_domains.update(subs[:50])  # Limit subdomains to avoid quota exhaustion

    enrichment_results = await vt_enrich_all.fn(list(all_domains))

    # Log summary
    logger.info(f"[Flow Summary]")
    logger.info(f"  Collected domains: {len(collected_domains)}")
    logger.info(f"  Discovered subdomains: {sum(len(s) for s in subdomain_map.values())}")
    logger.info(f"  Enriched domains: {len(enrichment_results)}")

# Alternative: Scheduled deployment
def deploy_scheduled():
    """
    Deploy the flow with a schedule.

    This creates a Prefect deployment that runs the flow automatically.
    """
    from prefect.deployments import Deployment
    from prefect.server.schemas.schedules import IntervalSchedule

    deployment = Deployment.build_from_flow(
        flow=scheduled_vt_osint,
        name="osint-pipeline-6h",
        schedule=IntervalSchedule(interval=timedelta(hours=6)),
        work_queue_name="osint",
        tags=["osint", "virustotal", "scheduled"]
    )

    deployment.apply()
    logger.info("Deployment created: OSINT pipeline will run every 6 hours")

# Entry point for direct execution
if __name__ == "__main__":
    import sys

    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "deploy":
            deploy_scheduled()
        elif sys.argv[1] == "run":
            scheduled_vt_osint()
        else:
            print("Usage: python -m app.flows.vt_flow [run|deploy]")
    else:
        # Default: run once
        scheduled_vt_osint()
