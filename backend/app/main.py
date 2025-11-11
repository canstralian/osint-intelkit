"""
OSINT IntelKit - Automated OSINT Pipeline API

FastAPI application for orchestrating OSINT collection and enrichment.

IMPORTANT: This system is designed for authorized security testing,
defensive security, threat intelligence, and educational purposes only.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

from .routers import tasks, domains, graph

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    redoc_url="/redoc"
)

# CORS middleware for web UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(domains.router, prefix="/domains", tags=["domains"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])

@app.get("/")
async def root():
    """API health check and status."""
    return {
        "status": "online",
        "service": "OSINT IntelKit",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "tasks": "/tasks",
            "domains": "/domains",
            "graph": "/graph"
        }
    }

@app.get("/health")
async def health_check():
    """Detailed health check for monitoring."""
    # TODO: Add database connectivity checks
    return {
        "status": "healthy",
        "postgres": "connected",  # Implement actual check
        "neo4j": "connected",      # Implement actual check
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc)
        }
    )

@app.on_event("startup")
async def startup_event():
    """Execute startup tasks."""
    logger.info("OSINT IntelKit API starting up")
    logger.warning("IMPORTANT: Use only for authorized targets and ethical purposes")

@app.on_event("shutdown")
async def shutdown_event():
    """Execute shutdown tasks."""
    logger.info("OSINT IntelKit API shutting down")
    # Close database connections
    from .db.neo4j import _neo4j_conn
    _neo4j_conn.close()
