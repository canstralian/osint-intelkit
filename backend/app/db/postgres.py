"""PostgreSQL database connection and operations."""
import asyncpg
import os
import json
import structlog
from datetime import datetime
from typing import Optional, Dict, List, Any
from ..security import pseudo_id

log = structlog.get_logger()


async def get_conn():
    """Establish connection to PostgreSQL database."""
    return await asyncpg.connect(os.getenv("POSTGRES_URL"))


async def save_domain(domain: str, source: str, metadata: Optional[Dict] = None) -> int:
    """
    Save a domain to the database with provenance tracking and pseudonymous ID.

    Args:
        domain: Domain name to save
        source: Source of the domain (e.g., 'seed', 'crt.sh', 'manual')
        metadata: Optional metadata dictionary

    Returns:
        Domain ID
    """
    pid = pseudo_id(domain)
    conn = await get_conn()
    try:
        # Upsert domain and update last_seen timestamp
        result = await conn.fetchrow("""
            INSERT INTO domains (name, pseudo_id, source, metadata, first_seen, last_seen)
            VALUES ($1, $2, $3, $4, $5, $5)
            ON CONFLICT (name)
            DO UPDATE SET
                last_seen = EXCLUDED.last_seen,
                metadata = domains.metadata || EXCLUDED.metadata
            RETURNING id
        """, domain, pid, source, json.dumps(metadata or {}), datetime.utcnow())

        # Log to audit trail
        await log_audit(conn, "domain_saved", "domain", domain, source)
        log.info("domain_saved", domain=domain, pseudo_id=pid, source=source)

        return result['id']
    finally:
        await conn.close()


async def last_enrichment(domain: str, source: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent enrichment for a domain from a specific source.
    Used for cache checking.

    Args:
        domain: Domain name
        source: Enrichment source

    Returns:
        Enrichment record or None
    """
    conn = await get_conn()
    try:
        row = await conn.fetchrow("""
            SELECT e.data, e.status, e.created_at
            FROM enrichments e
            JOIN domains d ON d.id = e.domain_id
            WHERE d.name = $1 AND e.source = $2
            ORDER BY e.created_at DESC
            LIMIT 1
        """, domain, source)
        return dict(row) if row else None
    finally:
        await conn.close()


async def add_enrichment(domain: str, source: str, status: str, data: Optional[Dict] = None,
                         error: Optional[str] = None, confidence: float = 0.0) -> None:
    """
    Add enrichment data for a domain with status tracking.

    Args:
        domain: Domain name
        source: Enrichment source (e.g., 'virustotal', 'shodan')
        status: Enrichment status ('pending', 'success', 'failed', 'cached')
        data: Enrichment data dictionary (optional)
        error: Error message if failed (optional)
        confidence: Confidence score (0.0 to 1.0)
    """
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO enrichments (domain_id, source, status, data, error, confidence_score, created_at)
            SELECT id, $2, $3, $4, $5, $6, $7 FROM domains WHERE name=$1
        """, domain, source, status, json.dumps(data) if data else None, error, confidence, datetime.utcnow())

        await log_audit(conn, "enrichment_added", "domain", domain, f"source={source}")
        log.info("enrichment_recorded", domain=domain, source=source, status=status)

    finally:
        await conn.close()


async def get_domain_enrichments(domain: str) -> List[Dict[str, Any]]:
    """
    Retrieve all enrichments for a domain.

    Args:
        domain: Domain name

    Returns:
        List of enrichment records
    """
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT e.source, e.status, e.data, e.error, e.confidence_score, e.created_at
            FROM enrichments e
            JOIN domains d ON d.id = e.domain_id
            WHERE d.name = $1
            ORDER BY e.created_at DESC
        """, domain)

        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_domains_by_source(source: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get domains from a specific source.

    Args:
        source: Source identifier
        limit: Maximum number of results

    Returns:
        List of domain records
    """
    conn = await get_conn()
    try:
        rows = await conn.fetch("""
            SELECT id, name, source, first_seen, last_seen, metadata
            FROM domains
            WHERE source = $1
            ORDER BY last_seen DESC
            LIMIT $2
        """, source, limit)

        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def log_audit(conn: asyncpg.Connection, operation: str, entity_type: str,
                    entity_value: str, user_context: str, metadata: Optional[Dict] = None) -> None:
    """
    Log an operation to the audit trail.

    Args:
        conn: Database connection
        operation: Operation name
        entity_type: Type of entity (e.g., 'domain', 'ip')
        entity_value: Value of the entity
        user_context: User or system context
        metadata: Optional metadata
    """
    if os.getenv("ENABLE_AUDIT_LOG", "true").lower() == "true":
        await conn.execute("""
            INSERT INTO audit_log (operation, entity_type, entity_value, user_context, metadata, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, operation, entity_type, entity_value, user_context,
                           json.dumps(metadata or {}), datetime.utcnow())


async def record_api_usage(api_name: str, endpoint: str,
                           rate_limit_remaining: Optional[int] = None,
                           reset_time: Optional[datetime] = None) -> None:
    """
    Record API usage for rate limiting tracking.

    Args:
        api_name: Name of the API
        endpoint: API endpoint called
        rate_limit_remaining: Remaining requests in current window
        reset_time: Time when rate limit resets
    """
    conn = await get_conn()
    try:
        await conn.execute("""
            INSERT INTO api_usage (api_name, endpoint, request_count, last_request,
                                 rate_limit_remaining, reset_time)
            VALUES ($1, $2, 1, $3, $4, $5)
            ON CONFLICT (api_name, endpoint)
            DO UPDATE SET
                request_count = api_usage.request_count + 1,
                last_request = EXCLUDED.last_request,
                rate_limit_remaining = EXCLUDED.rate_limit_remaining,
                reset_time = EXCLUDED.reset_time
        """, api_name, endpoint, datetime.utcnow(), rate_limit_remaining, reset_time)
    finally:
        await conn.close()
