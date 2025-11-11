"""Task orchestration endpoints for OSINT collection and enrichment."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import re

from ..workers.collector import collect_domain
from ..workers.vt_enricher import vt_enrich_domain
from ..config.logging import get_logger
from ..middleware.rate_limit import limiter

logger = get_logger(__name__)

router = APIRouter()

# Domain validation regex
DOMAIN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
)

class CollectionRequest(BaseModel):
    """Request model for domain collection."""
    domain: str = Field(..., description="Domain name to collect intelligence on", max_length=253)
    source: str = Field(default="api", description="Source identifier for provenance", max_length=100)
    enrich: bool = Field(default=True, description="Whether to run enrichment after collection")

    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain name format and security."""
        v = v.lower().strip()

        # Check for valid domain format
        if not DOMAIN_REGEX.match(v):
            raise ValueError('Invalid domain name format')

        # Security: Prevent potential injection attacks
        if any(char in v for char in ['<', '>', '"', "'", '\\', ';', '|', '&', '$', '`']):
            raise ValueError('Domain contains invalid characters')

        # Prevent private/internal domains (optional security measure)
        if v.endswith(('.local', '.internal', '.localhost')):
            raise ValueError('Private/internal domains are not allowed')

        return v

    @validator('source')
    def validate_source(cls, v):
        """Validate source string."""
        v = v.strip()

        # Alphanumeric, underscore, hyphen only
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('Source must contain only alphanumeric characters, underscores, and hyphens')

        return v

class EnrichmentRequest(BaseModel):
    """Request model for domain enrichment."""
    domain: str = Field(..., description="Domain name to enrich", max_length=253)
    sources: List[str] = Field(default=["virustotal"], description="Enrichment sources to use")

    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain name format and security."""
        v = v.lower().strip()

        if not DOMAIN_REGEX.match(v):
            raise ValueError('Invalid domain name format')

        if any(char in v for char in ['<', '>', '"', "'", '\\', ';', '|', '&', '$', '`']):
            raise ValueError('Domain contains invalid characters')

        if v.endswith(('.local', '.internal', '.localhost')):
            raise ValueError('Private/internal domains are not allowed')

        return v

    @validator('sources')
    def validate_sources(cls, v):
        """Validate enrichment sources."""
        allowed_sources = ['virustotal', 'shodan', 'censys', 'securitytrails']

        for source in v:
            source_clean = source.lower().strip()
            if source_clean not in allowed_sources:
                raise ValueError(f'Unknown enrichment source: {source}. Allowed: {", ".join(allowed_sources)}')

        return [s.lower().strip() for s in v]

class BulkCollectionRequest(BaseModel):
    """Request model for bulk domain collection."""
    domains: List[str] = Field(..., description="List of domains to collect", max_items=100, min_items=1)
    source: str = Field(default="bulk_api", description="Source identifier", max_length=100)
    enrich: bool = Field(default=True, description="Whether to run enrichment")

    @validator('domains')
    def validate_domains(cls, v):
        """Validate all domains in bulk request."""
        validated = []

        for domain in v:
            domain = domain.lower().strip()

            if not DOMAIN_REGEX.match(domain):
                raise ValueError(f'Invalid domain format: {domain}')

            if any(char in domain for char in ['<', '>', '"', "'", '\\', ';', '|', '&', '$', '`']):
                raise ValueError(f'Domain contains invalid characters: {domain}')

            if domain.endswith(('.local', '.internal', '.localhost')):
                raise ValueError(f'Private/internal domain not allowed: {domain}')

            validated.append(domain)

        # Remove duplicates
        return list(set(validated))

    @validator('source')
    def validate_source(cls, v):
        """Validate source string."""
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('Source must contain only alphanumeric characters, underscores, and hyphens')
        return v

@router.post("/collect")
@limiter.limit("10/minute")
async def start_collection(request: CollectionRequest, background_tasks: BackgroundTasks):
    """
    Start OSINT collection for a domain.

    This endpoint initiates passive collection of publicly available information
    about a domain. Use only for authorized targets.

    Rate limit: 10 requests per minute

    Args:
        request: Collection request parameters
        background_tasks: FastAPI background tasks

    Returns:
        Task status and domain information
    """
    logger.info(
        "collection_started",
        domain=request.domain,
        source=request.source,
        enrich=request.enrich,
        security_event=True
    )

    # Add collection task to background
    background_tasks.add_task(collect_domain, request.domain, request.source)

    # Optionally enrich after collection
    if request.enrich:
        background_tasks.add_task(vt_enrich_domain, request.domain)
        logger.info(
            "enrichment_queued",
            domain=request.domain,
            source="virustotal"
        )

    return {
        "status": "started",
        "domain": request.domain,
        "source": request.source,
        "enrichment_enabled": request.enrich,
        "message": f"Collection started for {request.domain}"
    }

@router.post("/enrich")
@limiter.limit("10/minute")
async def start_enrichment(request: EnrichmentRequest, background_tasks: BackgroundTasks):
    """
    Start enrichment for a domain using threat intelligence sources.

    Rate limit: 10 requests per minute

    Args:
        request: Enrichment request parameters
        background_tasks: FastAPI background tasks

    Returns:
        Enrichment task status
    """
    logger.info(
        "enrichment_started",
        domain=request.domain,
        sources=request.sources,
        security_event=True
    )

    # Add enrichment tasks based on requested sources
    if "virustotal" in request.sources:
        background_tasks.add_task(vt_enrich_domain, request.domain)

    # Add more enrichment sources here as they're implemented
    # if "shodan" in request.sources:
    #     background_tasks.add_task(shodan_enrich_domain, request.domain)

    return {
        "status": "started",
        "domain": request.domain,
        "sources": request.sources,
        "message": f"Enrichment started for {request.domain}"
    }

@router.post("/collect/bulk")
@limiter.limit("2/minute")
async def bulk_collection(request: BulkCollectionRequest, background_tasks: BackgroundTasks):
    """
    Start OSINT collection for multiple domains.

    IMPORTANT: Use rate limiting and ensure all targets are authorized.

    Rate limit: 2 requests per minute (strict due to bulk nature)
    Maximum: 100 domains per request

    Args:
        request: Bulk collection request
        background_tasks: FastAPI background tasks

    Returns:
        Bulk task status
    """
    logger.warning(
        "bulk_collection_started",
        domain_count=len(request.domains),
        source=request.source,
        enrich=request.enrich,
        domains_sample=request.domains[:5],  # Log first 5 for audit
        security_event=True
    )

    for domain in request.domains:
        background_tasks.add_task(collect_domain, domain, request.source)
        if request.enrich:
            background_tasks.add_task(vt_enrich_domain, domain)

    return {
        "status": "started",
        "domain_count": len(request.domains),
        "source": request.source,
        "enrichment_enabled": request.enrich,
        "message": f"Bulk collection started for {len(request.domains)} domains"
    }

@router.get("/status")
async def get_task_status():
    """
    Get status of running tasks.

    Returns:
        Task queue status and statistics
    """
    logger.debug("task_status_check")

    # TODO: Implement actual task tracking with Redis or database
    return {
        "status": "operational",
        "active_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "message": "Task tracking not yet implemented - check Prefect UI for flow status"
    }
