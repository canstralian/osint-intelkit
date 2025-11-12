"""
Rate limiting for OSINT IntelKit API.

Implements request rate limiting to prevent abuse and ensure fair usage.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import os
import structlog

logger = structlog.get_logger(__name__)

# Rate limit configuration from environment
DEFAULT_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "100/minute")
STRICT_RATE_LIMIT = os.getenv("API_STRICT_RATE_LIMIT", "10/minute")


def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.

    Priority:
    1. API key from X-API-Key header
    2. Authorization header
    3. Client IP address

    Returns:
        Unique identifier string
    """
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use hash of API key to avoid logging sensitive data
        import hashlib
        return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

    # Check for authorization header
    auth = request.headers.get("Authorization")
    if auth:
        import hashlib
        return f"auth:{hashlib.sha256(auth.encode()).hexdigest()[:16]}"

    # Fall back to IP address
    return get_remote_address(request)


# Initialize rate limiter
limiter = Limiter(
    key_func=get_identifier,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri=os.getenv("REDIS_URL", "memory://"),
    strategy="fixed-window",
    headers_enabled=True,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Logs security event and returns informative error response.
    """
    identifier = get_identifier(request)

    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        method=request.method,
        identifier=identifier,
        limit=str(exc.detail),
        client_ip=request.client.host if request.client else "unknown",
        security_event=True
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": "60 seconds"
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": str(exc.detail)
        }
    )
