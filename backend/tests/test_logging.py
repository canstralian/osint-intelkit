"""Tests for logging configuration."""

import logging

import structlog


class TestLoggingConfiguration:
    """Test structured logging setup."""

    def test_configure_logging_returns_logger(self):
        """Test that configure_logging returns a logger instance."""
        from app.logging_config import configure_logging

        logger = configure_logging()
        assert logger is not None

    def test_structlog_configuration(self):
        """Test that structlog is properly configured."""
        log = structlog.get_logger()
        assert log is not None

    def test_log_levels(self):
        """Test that logging levels work correctly."""
        from app.logging_config import configure_logging

        logger = configure_logging()
        # Should not raise exceptions
        logger.debug("test_debug")
        logger.info("test_info")
        logger.warning("test_warning")
        logger.error("test_error")


class TestErrorHandling:
    """Test error envelope middleware."""

    def test_error_envelope_middleware_exists(self):
        """Test that error middleware is defined."""
        from app.errors import ErrorEnvelopeMiddleware

        assert ErrorEnvelopeMiddleware is not None
