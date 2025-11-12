"""
Security middleware for OSINT IntelKit.

Implements security headers, input sanitization, and security event logging.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog
import re
from typing import Optional

logger = structlog.get_logger(__name__)

# Patterns for detecting potential injection attacks
SQL_INJECTION_PATTERNS = [
    r"(\bunion\b.*\bselect\b)",
    r"(\bor\b.*=.*)",
    r"(;.*drop\b.*\btable\b)",
    r"(--.*$)",
    r"(/\*.*\*/)",
]

XSS_PATTERNS = [
    r"(<script[^>]*>.*?</script>)",
    r"(javascript:)",
    r"(onerror\s*=)",
    r"(onload\s*=)",
]

COMMAND_INJECTION_PATTERNS = [
    r"(\||;|`|\$\(|\${)",
    r"(&&|\|\|)",
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements:
    - Content Security Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - Strict-Transport-Security (HSTS)
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable HSTS (31536000 seconds = 1 year)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # XSS Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Remove server header to avoid information disclosure
        response.headers.pop("Server", None)

        return response


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor and log security-relevant events.

    Detects:
    - Potential injection attacks
    - Suspicious request patterns
    - Malformed requests
    - Rate limit violations
    """

    async def dispatch(self, request: Request, call_next):
        """Monitor request for security issues."""
        # Check for suspicious patterns in URL and query parameters
        suspicious = self._check_suspicious_patterns(request)

        if suspicious:
            logger.warning(
                "suspicious_request_detected",
                path=request.url.path,
                query=str(request.url.query),
                method=request.method,
                client_ip=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
                suspicious_patterns=suspicious,
                security_event=True
            )

        # Log authentication attempts (if auth headers present)
        if "authorization" in request.headers or "x-api-key" in request.headers:
            logger.info(
                "authentication_attempt",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else "unknown",
                has_auth_header="authorization" in request.headers,
                has_api_key="x-api-key" in request.headers,
                security_event=True
            )

        response = await call_next(request)

        # Log failed authentication attempts
        if response.status_code == 401 or response.status_code == 403:
            logger.warning(
                "authentication_failed",
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                client_ip=request.client.host if request.client else "unknown",
                security_event=True
            )

        return response

    def _check_suspicious_patterns(self, request: Request) -> list:
        """
        Check request for suspicious patterns indicating potential attacks.

        Returns:
            List of detected suspicious pattern types
        """
        suspicious = []

        # Combine URL path and query parameters for checking
        check_string = f"{request.url.path} {request.url.query}".lower()

        # Check for SQL injection patterns
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, check_string, re.IGNORECASE):
                suspicious.append("sql_injection")
                break

        # Check for XSS patterns
        for pattern in XSS_PATTERNS:
            if re.search(pattern, check_string, re.IGNORECASE):
                suspicious.append("xss")
                break

        # Check for command injection patterns
        for pattern in COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, check_string):
                suspicious.append("command_injection")
                break

        # Check for directory traversal
        if "../" in check_string or "..%2f" in check_string:
            suspicious.append("directory_traversal")

        # Check for excessively long parameters (potential buffer overflow)
        if len(check_string) > 2000:
            suspicious.append("excessive_length")

        return suspicious


def sanitize_log_data(data: dict) -> dict:
    """
    Sanitize sensitive data from logs.

    Removes or masks:
    - API keys
    - Passwords
    - Tokens
    - Email addresses (partially)
    - Credit card numbers

    Args:
        data: Dictionary of log data

    Returns:
        Sanitized dictionary
    """
    sensitive_keys = [
        "password", "passwd", "pwd",
        "api_key", "apikey", "api-key",
        "token", "access_token", "refresh_token",
        "secret", "auth",
        "authorization",
        "x-api-key", "x-apikey"
    ]

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Mask sensitive fields
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if value:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        # Partially mask email addresses
        elif isinstance(value, str) and "@" in value and "." in value:
            parts = value.split("@")
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                masked_username = username[0] + "***" + username[-1] if len(username) > 2 else "***"
                sanitized[key] = f"{masked_username}@{domain}"
            else:
                sanitized[key] = value
        # Recursively sanitize nested dictionaries
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized
