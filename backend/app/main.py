"""
OSINT IntelKit - Automated OSINT Pipeline API

FastAPI application for orchestrating OSINT collection and enrichment.

IMPORTANT: This system is designed for authorized security testing,
defensive security, threat intelligence, and educational purposes only.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import tasks, domains, graph
from .logging_config import configure_logging
from .errors import ErrorEnvelopeMiddleware

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
    redoc_url="/redoc"
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(429, rate_limit_exceeded_handler)

# Security middleware (order matters - first added is outermost)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SecurityMonitoringMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# CORS middleware - Configure allowed origins in production
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
if allowed_origins == ["*"]:
    logger.warning(
        "cors_insecure_configuration",
        message="CORS is configured to allow all origins. Set CORS_ORIGINS environment variable in production.",
        security_event=True
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
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
        "endpoints": {
            "docs": "/docs",
            "tasks": "/tasks",
            "domains": "/domains",
            "graph": "/graph"
        }
    }


@app.get("/health")
async def health_check():
    """
    Detailed health check for monitoring.

    Checks:
    - API service status
    - PostgreSQL connectivity
    - Neo4j connectivity
    """
    health_status = {
        "status": "healthy",
        "checks": {}
    }

    # Check PostgreSQL
    try:
        from .db.postgres import get_conn
        conn = await get_conn()
        await conn.execute("SELECT 1")
        await conn.close()
        health_status["checks"]["postgres"] = {"status": "healthy", "message": "Connected"}
        logger.debug("postgres_health_check", status="healthy")
    except Exception as e:
        health_status["checks"]["postgres"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
        logger.error("postgres_health_check_failed", error=str(e), security_event=True)

    # Check Neo4j
    try:
        from .db.neo4j import get_driver
        driver = get_driver()
        with driver.session() as session:
            session.run("RETURN 1")
        health_status["checks"]["neo4j"] = {"status": "healthy", "message": "Connected"}
        logger.debug("neo4j_health_check", status="healthy")
    except Exception as e:
        health_status["checks"]["neo4j"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
        logger.error("neo4j_health_check_failed", error=str(e), security_event=True)

    # Log health check result
    if health_status["status"] != "healthy":
        logger.warning("health_check_degraded", checks=health_status["checks"])

    return health_status

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
        security_event=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

@app.on_event("startup")
async def startup_event():
    """Execute startup tasks."""
    log.info("osint_api_startup")
    log.warning("authorized_use_only", message="Use only for authorized targets and ethical purposes")


@app.on_event("shutdown")
async def shutdown_event():
    """Execute shutdown tasks."""
    logger.info("application_shutdown", service="OSINT IntelKit")

    # Close database connections
    try:
        from .db.neo4j import _neo4j_conn
        _neo4j_conn.close()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.error("error_closing_connections", error=str(e))
    except Exception as e:
        log.warning("neo4j_close_failed", error=str(e))
