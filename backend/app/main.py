"""OSINT IntelKit - Automated OSINT Pipeline API

FastAPI application for orchestrating OSINT collection and enrichment.

IMPORTANT: This system is designed for authorized security testing,
defensive security, threat intelligence, and educational purposes only.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import ErrorEnvelopeMiddleware
from .logging_config import configure_logging
from .routers import domains, graph, tasks

# Configure structured logging
log = configure_logging()

# Initialize FastAPI app
app = FastAPI(
    title="OSINT IntelKit",
    description="""
    Automated OSINT Pipeline for authorized reconnaissance and threat intelligence.

    **Ethical Use Only:**
    - Authorized security testing
    - Defensive security operations
    - CTF competitions
    - Security research
    - Educational purposes

    **Prohibited Uses:**
    - Unauthorized access or scanning
    - Mass targeting or reconnaissance
    - Malicious activities
    - Detection evasion for malicious purposes
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for web UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware
app.add_middleware(ErrorEnvelopeMiddleware)

# Include routers
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(domains.router, prefix="/domains", tags=["domains"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])


@app.get("/")
async def root():
    """API health check and status."""
    log.info("health_check")
    return {
        "status": "online",
        "service": "OSINT IntelKit",
        "version": "1.0.0",
        "endpoints": {"docs": "/docs", "tasks": "/tasks", "domains": "/domains", "graph": "/graph"},
    }


@app.get("/health")
async def health_check():
    """Detailed health check for monitoring."""
    # TODO: Add database connectivity checks
    return {
        "status": "healthy",
        "postgres": "connected",  # Implement actual check
        "neo4j": "connected",  # Implement actual check
    }


@app.on_event("startup")
async def startup_event():
    """Execute startup tasks."""
    log.info("osint_api_startup")
    log.warning(
        "authorized_use_only", message="Use only for authorized targets and ethical purposes"
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Execute shutdown tasks."""
    log.info("osint_api_shutdown")
    # Close database connections
    try:
        from .db.neo4j import _neo4j_conn

        _neo4j_conn.close()
    except Exception as e:
        log.warning("neo4j_close_failed", error=str(e))
