"""
Structured logging configuration for OSINT IntelKit.

Configures JSON-formatted logging with security-aware sanitization.
"""
import os
import sys
import logging
import structlog
from typing import Any
from pythonjsonlogger import jsonlogger

from ..middleware.security import sanitize_log_data


def configure_structured_logging():
    """
    Configure structured logging with JSON output and sanitization.

    Features:
    - JSON-formatted logs for easy parsing
    - Automatic log sanitization (removes API keys, passwords, etc.)
    - Context variable support (correlation IDs)
    - Standard library logging compatibility
    - Colored output in development mode
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    environment = os.getenv("ENVIRONMENT", "production")

    # Determine if we should use pretty console output (development) or JSON (production)
    use_json = environment.lower() == "production" or os.getenv("LOG_FORMAT", "json").lower() == "json"

    # Configure structlog
    if use_json:
        # Production: JSON output
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_app_context,
            sanitize_processor,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Development: Pretty console output
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_app_context,
            sanitize_processor,
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )

    # Add JSON formatter to standard library root logger if in production
    if use_json:
        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setFormatter(CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        ))
        logging.root.handlers = [json_handler]
        logging.root.setLevel(getattr(logging, log_level))


def add_app_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Add application-specific context to log events.

    Adds:
    - Application name
    - Environment
    - Service name
    """
    event_dict["app"] = "osint-intelkit"
    event_dict["environment"] = os.getenv("ENVIRONMENT", "production")
    event_dict["service"] = os.getenv("SERVICE_NAME", "api")

    return event_dict


def sanitize_processor(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Sanitize sensitive data from log events.

    Removes:
    - API keys
    - Passwords
    - Tokens
    - Partially masks emails
    """
    # Don't sanitize certain safe fields
    safe_fields = {
        "timestamp", "level", "logger", "event", "app",
        "environment", "service", "correlation_id",
        "method", "path", "status_code"
    }

    sanitized_event = {}
    for key, value in event_dict.items():
        if key in safe_fields:
            sanitized_event[key] = value
        elif isinstance(value, dict):
            sanitized_event[key] = sanitize_log_data(value)
        elif isinstance(value, str):
            # Check if the string looks like an API key or token
            if len(value) > 20 and any(char.isalnum() for char in value):
                # If it's a long alphanumeric string in a suspicious context
                key_lower = key.lower()
                if any(keyword in key_lower for keyword in ["key", "token", "secret", "password", "auth"]):
                    sanitized_event[key] = "***REDACTED***"
                else:
                    sanitized_event[key] = value
            else:
                sanitized_event[key] = value
        else:
            sanitized_event[key] = value

    return sanitized_event


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for standard library logging.

    Adds additional context and sanitization.
    """

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict):
        """Add custom fields to JSON log record."""
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["app"] = "osint-intelkit"
        log_record["environment"] = os.getenv("ENVIRONMENT", "production")

        # Sanitize the log record
        for key, value in list(log_record.items()):
            if isinstance(value, dict):
                log_record[key] = sanitize_log_data(value)
            elif isinstance(value, str) and any(
                keyword in key.lower()
                for keyword in ["key", "token", "secret", "password", "auth"]
            ):
                if len(value) > 5:
                    log_record[key] = "***REDACTED***"


def get_logger(name: str):
    """
    Get a configured structlog logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
