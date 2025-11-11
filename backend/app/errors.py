import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger()


class ErrorEnvelopeMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware for FastAPI.
    Catches unhandled exceptions and returns structured error responses.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            log.exception("unhandled_error", path=str(request.url))
            return JSONResponse(
                status_code=500,
                content={"error": {"message": "internal_error", "detail": str(exc)[:200]}},
            )
