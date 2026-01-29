"""Graph query endpoints for relationship analysis."""
from fastapi import APIRouter, HTTPException, Query
import logging

from ..db.neo4j import (
    get_domain_graph,
    find_related_domains,
    get_graph_statistics
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{domain}")
async def get_graph(
    domain: str,
    depth: int = Query(2, ge=1, le=5, description="Graph traversal depth")
):
    """
    Retrieve graph neighborhood for a domain.

    Returns nodes and relationships showing how the domain connects
    to other entities (IPs, certificates, organizations, etc.)

    Args:
        domain: Domain name
        depth: Traversal depth (1-5)

    Returns:
        Graph data with nodes and relationships
    """
    try:
        graph_data = await get_domain_graph(domain, depth)

        return {
            "domain": domain,
            "depth": depth,
            "node_count": len(graph_data.get("nodes", [])),
            "relationship_count": len(graph_data.get("relationships", [])),
            "graph": graph_data
        }

    except Exception as e:
        logger.error(f"Error retrieving graph for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{domain}/related")
async def get_related(
    domain: str,
    min_connections: int = Query(2, ge=1, description="Minimum shared connections")
):
    """
    Find domains related through shared infrastructure.

    Discovers domains that share IPs, certificates, or other infrastructure
    with the target domain.

    Args:
        domain: Domain name
        min_connections: Minimum number of shared connections

    Returns:
        List of related domains with connection counts
    """
    try:
        related = await find_related_domains(domain, min_connections)

        return {
            "domain": domain,
            "related_count": len(related),
            "related_domains": related,
            "min_connections": min_connections
        }

    except Exception as e:
        logger.error(f"Error finding related domains for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats():
    """
    Get graph database statistics.

    Returns:
        Statistics about entities and relationships
    """
    try:
        stats = await get_graph_statistics()
        return stats

    except Exception as e:
        logger.error(f"Error retrieving graph statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve graph statistics")
