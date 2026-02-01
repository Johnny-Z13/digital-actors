"""
Tests for structured JSON logging configuration and output.

Verifies that logging produces valid JSON with expected fields.
"""

import json
import logging
from io import StringIO

import pytest

from logging_config import (
    ContextualJsonFormatter,
    StructuredLoggerAdapter,
    setup_logging,
)


class TestStructuredLogging:
    """Test suite for structured JSON logging."""

    def test_setup_logging_json_format(self):
        """Test that setup_logging configures JSON format correctly."""
        # Setup JSON logging
        setup_logging(use_json=True, log_level="INFO")

        # Get a logger and capture output
        logger = logging.getLogger("test_logger")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        # Log a message
        logger.info("Test message")

        # Get output and parse as JSON
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        # Verify JSON structure
        assert "message" in log_data
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data
        assert "level" in log_data
        assert log_data["level"] == "INFO"
        assert "logger" in log_data
        assert log_data["logger"] == "test_logger"

    def test_setup_logging_readable_format(self):
        """Test that setup_logging can use readable format for development."""
        # Setup readable logging
        setup_logging(use_json=False, log_level="DEBUG")

        # Get a logger and capture output
        logger = logging.getLogger("test_readable")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)

        # Log a message
        logger.debug("Debug message")

        # Verify output is NOT JSON (should be readable text)
        output = stream.getvalue().strip()
        assert "Debug message" in output
        assert "test_readable" in output
        # Shouldn't be valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)

    def test_contextual_json_formatter_adds_fields(self):
        """Test that ContextualJsonFormatter adds custom fields."""
        formatter = ContextualJsonFormatter(
            '%(timestamp)s %(level)s %(message)s',
            rename_fields={'timestamp': '@timestamp', 'level': 'severity'}
        )

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Format the record
        output = formatter.format(record)
        log_data = json.loads(output)

        # Verify renamed fields
        assert "@timestamp" in log_data
        assert "severity" in log_data
        assert log_data["severity"] == "INFO"

    def test_structured_logger_adapter_context(self):
        """Test that StructuredLoggerAdapter adds context to logs."""
        logger = logging.getLogger("test_adapter")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter('%(message)s')
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        # Create adapter with context
        adapter = StructuredLoggerAdapter(logger, {
            'session_id': 'abc123',
            'character': 'test_char',
            'scene': 'test_scene'
        })

        # Log with adapter
        adapter.info("Test with context")

        # Parse output
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        # Verify context is included
        assert log_data["session_id"] == "abc123"
        assert log_data["character"] == "test_char"
        assert log_data["scene"] == "test_scene"

    def test_structured_logger_adapter_event_methods(self):
        """Test structured event logging methods."""
        logger = logging.getLogger("test_events")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter('%(message)s')
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)

        adapter = StructuredLoggerAdapter(logger, {'session_id': 'test123'})

        # Test info_event
        adapter.info_event("test_event", "Event message", response_time_ms=123)
        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["event_type"] == "test_event"
        assert log_data["message"] == "Event message"
        assert log_data["response_time_ms"] == 123
        assert log_data["session_id"] == "test123"

    def test_structured_logger_adapter_merges_extra(self):
        """Test that adapter merges context with message-specific extra data."""
        logger = logging.getLogger("test_merge")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter('%(message)s')
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        adapter = StructuredLoggerAdapter(logger, {'session_id': 'xyz789'})

        # Log with additional extra data
        adapter.info("Merge test", extra={'user_id': 'user456', 'action': 'click'})

        output = stream.getvalue().strip()
        log_data = json.loads(output)

        # Verify both context and extra are present
        assert log_data["session_id"] == "xyz789"  # From adapter context
        assert log_data["user_id"] == "user456"    # From extra
        assert log_data["action"] == "click"       # From extra

    def test_log_levels_respected(self):
        """Test that log levels are properly respected."""
        logger = logging.getLogger("test_levels")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter('%(message)s')
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.WARNING)  # Set to WARNING level

        adapter = StructuredLoggerAdapter(logger, {})

        # Debug and info should be ignored
        adapter.debug_event("debug_event", "Should not appear")
        adapter.info_event("info_event", "Should not appear")

        # Warning and error should appear
        adapter.warning_event("warning_event", "Warning message")
        adapter.error_event("error_event", "Error message")

        output = stream.getvalue().strip()
        lines = output.split('\n')

        # Should only have 2 lines (warning and error)
        assert len(lines) == 2

        warning_data = json.loads(lines[0])
        error_data = json.loads(lines[1])

        assert warning_data["event_type"] == "warning_event"
        assert warning_data["level"] == "WARNING"
        assert error_data["event_type"] == "error_event"
        assert error_data["level"] == "ERROR"

    def test_json_output_format_for_production(self):
        """Test complete JSON structure for production logging."""
        logger = logging.getLogger("test_production")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s',
            rename_fields={'timestamp': '@timestamp', 'level': 'severity'}
        )
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        adapter = StructuredLoggerAdapter(logger, {
            'session_id': 'prod_session',
            'character': 'clippy',
            'scene': 'welcome'
        })

        # Simulate production log event
        adapter.info_event(
            "dialogue_generated",
            "Generated dialogue response",
            response_time_ms=450,
            llm_response_time_ms=380,
            message_preview="Hello, how can I help?"
        )

        output = stream.getvalue().strip()
        log_data = json.loads(output)

        # Verify all expected fields
        assert log_data["@timestamp"]  # Renamed from timestamp
        assert log_data["severity"] == "INFO"  # Renamed from level
        assert log_data["logger"] == "test_production"
        assert log_data["message"] == "Generated dialogue response"
        assert log_data["event_type"] == "dialogue_generated"
        assert log_data["session_id"] == "prod_session"
        assert log_data["character"] == "clippy"
        assert log_data["scene"] == "welcome"
        assert log_data["response_time_ms"] == 450
        assert log_data["llm_response_time_ms"] == 380
        assert log_data["message_preview"] == "Hello, how can I help?"


class TestLoggingIntegration:
    """Integration tests for logging in realistic scenarios."""

    def test_websocket_connection_logging(self):
        """Test logging for websocket connection scenario."""
        logger = logging.getLogger("websocket_test")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter('%(message)s')
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        session_adapter = StructuredLoggerAdapter(logger, {
            'session_id': 'ws_session_123',
            'character': 'eliza',
            'scene': 'introduction'
        })

        # Simulate connection sequence
        session_adapter.info_event("websocket_connected", "Client connected")
        session_adapter.info_event("session_registered", "Registered session for authentication")
        session_adapter.info_event("session_token_sent", "Sent session token to client")

        output = stream.getvalue().strip()
        lines = output.split('\n')

        # Verify all events logged
        assert len(lines) == 3

        for line in lines:
            log_data = json.loads(line)
            assert log_data["session_id"] == "ws_session_123"
            assert log_data["character"] == "eliza"
            assert log_data["scene"] == "introduction"
            assert "event_type" in log_data

    def test_error_logging_with_exception_details(self):
        """Test error logging with exception information."""
        logger = logging.getLogger("error_test")
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = ContextualJsonFormatter('%(message)s')
        handler.setFormatter(formatter)
        logger.handlers = [handler]
        logger.setLevel(logging.ERROR)

        adapter = StructuredLoggerAdapter(logger, {'session_id': 'error_session'})

        # Log error with exception details
        try:
            raise ValueError("Test error")
        except ValueError as e:
            adapter.error_event(
                "llm_api_error",
                "LLM API call failed",
                error=str(e),
                error_type=type(e).__name__
            )

        output = stream.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["event_type"] == "llm_api_error"
        assert log_data["error"] == "Test error"
        assert log_data["error_type"] == "ValueError"
        assert log_data["level"] == "ERROR"
