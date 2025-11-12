"""
Request correlation ID middleware.

Adds unique correlation IDs to each request for distributed tracing and log correlation.
"""
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

# Context variable for storing correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests and responses.

    Features:
    - Generates unique correlation ID for each request
    - Extracts existing correlation ID from X-Correlation-ID header if present
    - Adds correlation ID to response headers
    - Makes correlation ID available in context for logging
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and inject correlation ID."""
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in context variable for access in logging
        correlation_id_var.set(correlation_id)

        # Bind correlation ID to structured logging context
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )

        # Process request
        try:
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            # Log request completion
            logger.info(
                "request_completed",
                status_code=response.status_code,
                correlation_id=correlation_id
            )

            return response

        except Exception as e:
            logger.error(
                "request_failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise
        finally:
            # Clear context variables
            structlog.contextvars.clear_contextvars()


def get_correlation_id() -> str:
    """Get the current request's correlation ID."""
    return correlation_id_var.get()
