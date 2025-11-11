"""Task orchestration endpoints for OSINT collection and enrichment."""

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..security import DomainIn
from ..workers.collector import collect_domain
from ..workers.vt_enricher import vt_enrich_domain

log = structlog.get_logger()

router = APIRouter()


class CollectionRequest(BaseModel):
    """Request model for domain collection."""

    domain: str = Field(..., description="Domain name to collect intelligence on")
    source: str = Field(default="api", description="Source identifier for provenance")
    enrich: bool = Field(default=True, description="Whether to run enrichment after collection")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate and normalize domain input."""
        return DomainIn(domain=v).domain


class EnrichmentRequest(BaseModel):
    """Request model for domain enrichment."""

    domain: str = Field(..., description="Domain name to enrich")
    sources: list[str] = Field(default=["virustotal"], description="Enrichment sources to use")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate and normalize domain input."""
        return DomainIn(domain=v).domain


class BulkCollectionRequest(BaseModel):
    """Request model for bulk domain collection."""

    domains: list[str] = Field(..., description="List of domains to collect")
    source: str = Field(default="bulk_api", description="Source identifier")
    enrich: bool = Field(default=True, description="Whether to run enrichment")

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, v):
        """Validate and normalize all domain inputs."""
        return [DomainIn(domain=d).domain for d in v]


@router.post("/collect")
async def start_collection(request: CollectionRequest, background_tasks: BackgroundTasks):
    """Start OSINT collection for a domain.

    This endpoint initiates passive collection of publicly available information
    about a domain. Use only for authorized targets.

    Args:
        request: Collection request parameters
        background_tasks: FastAPI background tasks

    Returns:
        Task status and domain information
    """
    log.info(
        "collection_request", domain=request.domain, source=request.source, enrich=request.enrich
    )

    # Add collection task to background
    background_tasks.add_task(collect_domain, request.domain, request.source)

    # Optionally enrich after collection
    if request.enrich:
        background_tasks.add_task(vt_enrich_domain, request.domain)

    return {
        "status": "started",
        "domain": request.domain,
        "source": request.source,
        "enrichment_enabled": request.enrich,
        "message": f"Collection started for {request.domain}",
    }


@router.post("/enrich")
async def start_enrichment(request: EnrichmentRequest, background_tasks: BackgroundTasks):
    """Start enrichment for a domain using threat intelligence sources.

    Args:
        request: Enrichment request parameters
        background_tasks: FastAPI background tasks

    Returns:
        Enrichment task status
    """
    log.info("enrichment_request", domain=request.domain, sources=request.sources)

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
        "message": f"Enrichment started for {request.domain}",
    }


@router.post("/collect/bulk")
async def bulk_collection(request: BulkCollectionRequest, background_tasks: BackgroundTasks):
    """Start OSINT collection for multiple domains.

    IMPORTANT: Use rate limiting and ensure all targets are authorized.

    Args:
        request: Bulk collection request
        background_tasks: FastAPI background tasks

    Returns:
        Bulk task status
    """
    if len(request.domains) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 domains per bulk request. Use multiple requests for larger sets.",
        )

    log.info(
        "bulk_collection_request",
        domain_count=len(request.domains),
        source=request.source,
        enrich=request.enrich,
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
        "message": f"Bulk collection started for {len(request.domains)} domains",
    }


@router.get("/status")
async def get_task_status():
    """Get status of running tasks.

    Returns:
        Task queue status and statistics
    """
    # TODO: Implement actual task tracking
    return {"status": "operational", "active_tasks": 0, "completed_tasks": 0, "failed_tasks": 0}
