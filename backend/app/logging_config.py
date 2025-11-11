import logging
import os
import sys

import structlog
from pythonjsonlogger import jsonlogger


def configure_logging():
    """Configure structured logging with JSON output for production."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_mode = os.getenv("LOG_JSON", "1") == "1"

    handlers = []
    if json_mode:
        handler = logging.StreamHandler(sys.stdout)
        fmt = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(threadName)s"
        )
        handler.setFormatter(fmt)
        handlers.append(handler)
    else:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(level=log_level, handlers=handlers)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.dict_tracebacks,
            # redactor for known sensitive fields
            lambda logger, method, event_dict: {
                k: ("<redacted>" if k in {"api_key", "apikey", "authorization"} else v)
                for k, v in event_dict.items()
            },
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()
