"""Prefect flow orchestration for scheduled OSINT collection and enrichment.

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
import os
from datetime import datetime, timedelta

from prefect import flow, task
from prefect.tasks import task_input_hash

from app.db.neo4j import link_domain
from app.db.postgres import save_domain

# Configure structured logging for Prefect flows
from app.logging_config import configure_logging
from app.security import DomainIn
from app.workers.collector import collect_domain, collect_subdomains_passive
from app.workers.vt_enricher import vt_enrich_domain

log = configure_logging()

# Seed domains for scheduled collection
# IMPORTANT: Only include authorized targets
# Can be overridden via OSINT_SEED_DOMAINS environment variable (comma-separated)
DEFAULT_SEED_DOMAINS = [
    "example.com",  # Replace with authorized targets
]


def get_seed_domains() -> list[str]:
    """Get seed domains from environment variable or default list.
    Validates and normalizes all domains.

    Returns:
        List of authorized domain names to collect
    """
    env_domains = os.getenv("OSINT_SEED_DOMAINS", "").strip()
    if env_domains:
        raw_domains = [d.strip() for d in env_domains.split(",") if d.strip()]
    else:
        raw_domains = DEFAULT_SEED_DOMAINS

    # Validate and normalize domains
    validated_domains = []
    for domain in raw_domains:
        try:
            validated = DomainIn(domain=domain).domain
            validated_domains.append(validated)
        except Exception as e:
            log.warning("seed_domain_invalid", domain=domain, error=str(e))

    log.info(
        "seed_domains_loaded",
        count=len(validated_domains),
        source="env" if env_domains else "default",
    )
    return validated_domains


@task(
    name="collect-seed-domains",
    description="Collect intelligence on seed domains",
    retries=2,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
async def collect_seed_domains(domains: list[str]) -> list[str]:
    """Task: Collect domain intelligence from seed list.

    Args:
        domains: List of domain names to collect

    Returns:
        List of successfully collected domains
    """
    log.info("prefect_collect_seed_start", domain_count=len(domains))

    collected = []
    for domain in domains:
        try:
            result = await collect_domain(domain, source="scheduled_seed")
            if result.get("status") == "success":
                collected.append(domain)
                await link_domain(domain)
        except Exception as e:
            log.error("prefect_collect_seed_failed", domain=domain, error=str(e))

    log.info("prefect_collect_seed_complete", collected=len(collected), total=len(domains))
    return collected


@task(
    name="vt-enrich-domains",
    description="Enrich domains with VirusTotal intelligence",
    retries=3,
    retry_delay_seconds=120,
)
async def vt_enrich_all(domains: list[str]) -> list[dict]:
    """Task: Enrich all domains with VirusTotal threat intelligence.

    Args:
        domains: List of domain names

    Returns:
        List of enrichment results
    """
    log.info("prefect_vt_enrich_start", domain_count=len(domains))

    results = []
    for domain in domains:
        try:
            enrichment = await vt_enrich_domain(domain)
            if enrichment:
                results.append({"domain": domain, "status": "success", "data": enrichment})
            else:
                results.append({"domain": domain, "status": "no_data"})

            # Rate limiting pause between requests
            await asyncio.sleep(15)  # 4 req/min = 15s between requests

        except Exception as e:
            log.error("prefect_vt_enrich_failed", domain=domain, error=str(e))
            results.append({"domain": domain, "status": "error", "error": str(e)})

    success_count = sum(1 for r in results if r["status"] == "success")
    log.info("prefect_vt_enrich_complete", success=success_count, total=len(domains))

    return results


@task(
    name="collect-subdomains",
    description="Collect subdomains from passive sources",
    retries=2,
    retry_delay_seconds=60,
)
async def collect_subdomains_task(domains: list[str]) -> dict:
    """Task: Collect subdomains for all seed domains.

    Args:
        domains: List of parent domains

    Returns:
        Dictionary mapping domains to their subdomains
    """
    log.info("prefect_subdomain_collect_start", domain_count=len(domains))

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
            log.error("prefect_subdomain_collect_failed", domain=domain, error=str(e))
            subdomain_map[domain] = []

    total_subdomains = sum(len(subs) for subs in subdomain_map.values())
    log.info("prefect_subdomain_collect_complete", total_subdomains=total_subdomains)

    return subdomain_map


@flow(
    name="vt-osint-flow",
    description="Scheduled OSINT collection and VirusTotal enrichment flow",
    log_prints=True,
    timeout_seconds=7200,  # 2 hours max
)
def scheduled_vt_osint(domains: list[str] = None):
    """Main Prefect flow: Orchestrates domain collection and enrichment.

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
    log.info("prefect_flow_start", start_time=start_time.isoformat(), domain_count=len(domains))

    # Run async tasks
    asyncio.run(run_flow_async(domains))

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    log.info("prefect_flow_complete", end_time=end_time.isoformat(), duration_seconds=duration)


async def run_flow_async(domains: list[str]):
    """Async execution wrapper for Prefect flow.

    Args:
        domains: List of domains to process
    """
    # Step 1: Collect seed domains
    collected_domains = await collect_seed_domains.fn(domains)

    if not collected_domains:
        log.warning("prefect_flow_no_domains")
        return

    # Step 2: Discover subdomains (passive only)
    subdomain_map = await collect_subdomains_task.fn(collected_domains)

    # Step 3: Enrich all domains (seeds + discovered subdomains)
    all_domains = set(collected_domains)
    for subs in subdomain_map.values():
        all_domains.update(subs[:50])  # Limit subdomains to avoid quota exhaustion

    enrichment_results = await vt_enrich_all.fn(list(all_domains))

    # Log summary
    total_subdomains = sum(len(s) for s in subdomain_map.values())
    log.info(
        "prefect_flow_summary",
        collected_domains=len(collected_domains),
        discovered_subdomains=total_subdomains,
        enriched_domains=len(enrichment_results),
    )


# Alternative: Scheduled deployment
def deploy_scheduled():
    """Deploy the flow with a schedule.

    This creates a Prefect deployment that runs the flow automatically.
    """
    from prefect.deployments import Deployment
    from prefect.server.schemas.schedules import IntervalSchedule

    deployment = Deployment.build_from_flow(
        flow=scheduled_vt_osint,
        name="osint-pipeline-6h",
        schedule=IntervalSchedule(interval=timedelta(hours=6)),
        work_queue_name="osint",
        tags=["osint", "virustotal", "scheduled"],
    )

    deployment.apply()
    log.info("prefect_deployment_created", interval_hours=6)


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
