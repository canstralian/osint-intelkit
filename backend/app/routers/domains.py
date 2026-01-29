"""Domain data retrieval endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query

from ..db.postgres import get_domain_enrichments, get_domains_by_source

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{domain}/enrichments")
async def get_enrichments(domain: str):
    """Retrieve all enrichment data for a domain.

    Args:
        domain: Domain name

    Returns:
        List of enrichments with metadata
    """
    try:
        enrichments = await get_domain_enrichments(domain)

        if not enrichments:
            return {
                "domain": domain,
                "enrichments": [],
                "message": "No enrichments found for this domain",
            }

        return {"domain": domain, "count": len(enrichments), "enrichments": enrichments}

    except Exception as e:
        logger.error(f"Error retrieving enrichments for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_domains(
    source: str | None = Query(None, description="Filter by source"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
):
    """List domains in the database.

    Args:
        source: Optional source filter
        limit: Maximum number of results

    Returns:
        List of domains
    """
    try:
        if source:
            domains = await get_domains_by_source(source, limit)
        else:
            # Get all domains (implement in postgres.py if needed)
            domains = await get_domains_by_source("", limit)  # Placeholder

        return {"count": len(domains), "domains": domains, "limit": limit}

    except Exception as e:
        logger.error(f"Error listing domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{domain}/summary")
async def get_domain_summary(domain: str):
    """Get a comprehensive summary of a domain's intelligence data.

    Args:
        domain: Domain name

    Returns:
        Summary of all collected intelligence
    """
    try:
        enrichments = await get_domain_enrichments(domain)

        # Aggregate data by source
        summary = {
            "domain": domain,
            "enrichment_sources": [],
            "total_enrichments": len(enrichments),
            "latest_enrichment": None,
        }

        sources = {}
        latest_timestamp = None

        for enrichment in enrichments:
            source = enrichment["source"]
            if source not in sources:
                sources[source] = {
                    "source": source,
                    "count": 0,
                    "latest_data": None,
                    "avg_confidence": 0.0,
                }

            sources[source]["count"] += 1
            sources[source]["latest_data"] = enrichment["data"]

            # Track latest enrichment overall
            if not latest_timestamp or enrichment["created_at"] > latest_timestamp:
                latest_timestamp = enrichment["created_at"]
                summary["latest_enrichment"] = enrichment

        summary["enrichment_sources"] = list(sources.values())

        return summary

    except Exception as e:
        logger.error(f"Error getting summary for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
