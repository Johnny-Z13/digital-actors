"""
Logging configuration for structured JSON logging.

Provides utilities for setting up JSON logging with contextual data and
different formats for development vs production environments.
"""

import logging
import os
import sys
from typing import Any, Optional

from pythonjsonlogger import jsonlogger

from constants import LOG_FORMAT_JSON, LOG_LEVEL_DEVELOPMENT, LOG_LEVEL_PRODUCTION


class ContextualJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that includes contextual information.

    Automatically adds fields from extra parameters and ensures
    consistent timestamp and log level formatting.
    """

    def __init__(self, *args, rename_fields: Optional[dict] = None, **kwargs):
        """Initialize formatter with optional field renaming."""
        super().__init__(*args, **kwargs)
        self.rename_fields = rename_fields or {}

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Ensure timestamp is always included
        if not log_record.get('timestamp'):
            log_record['timestamp'] = self.formatTime(record, self.datefmt)

        # Ensure level is always included
        if not log_record.get('level'):
            log_record['level'] = record.levelname

        # Ensure logger name is included
        if not log_record.get('logger'):
            log_record['logger'] = record.name

        # Apply field renaming if configured
        if self.rename_fields:
            for old_name, new_name in self.rename_fields.items():
                if old_name in log_record:
                    log_record[new_name] = log_record.pop(old_name)


def setup_logging(use_json: Optional[bool] = None, log_level: Optional[str] = None) -> None:
    """
    Configure application logging with JSON or readable format.

    Args:
        use_json: If True, use JSON format. If False, use readable format.
                  If None, uses LOG_FORMAT_JSON from constants.
        log_level: Logging level (e.g., "INFO", "DEBUG").
                   If None, auto-detects based on environment.
    """
    # Determine format and log level
    if use_json is None:
        # Check environment variable or use constant
        use_json = os.getenv("LOG_FORMAT_JSON", str(LOG_FORMAT_JSON)).lower() in ("true", "1", "yes")

    if log_level is None:
        # Use production level by default, development if ENV is set
        env = os.getenv("ENV", "production").lower()
        log_level = LOG_LEVEL_DEVELOPMENT if env in ("dev", "development") else LOG_LEVEL_PRODUCTION

    # Remove all existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create new handler
    handler = logging.StreamHandler(sys.stdout)

    if use_json:
        # JSON format for production/structured logging
        formatter = ContextualJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s',
            rename_fields={
                'timestamp': '@timestamp',
                'level': 'severity',
            }
        )
    else:
        # Readable format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))


def get_structured_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for structured logging.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance ready for structured logging
    """
    return logging.getLogger(name)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds contextual information to all log messages.

    Usage:
        logger = StructuredLoggerAdapter(logging.getLogger(__name__), {
            'session_id': session.id,
            'character': character.name
        })
        logger.info("Message sent", extra={'response_time_ms': 123})
    """

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Process log message and add context."""
        # Merge adapter context with message-specific extra data
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs

    def log_event(
        self,
        level: int,
        event_type: str,
        message: str,
        **context: Any
    ) -> None:
        """
        Log a structured event with type and context.

        Args:
            level: Logging level (e.g., logging.INFO)
            event_type: Type of event (e.g., "dialogue_generated", "websocket_connected")
            message: Human-readable message
            **context: Additional contextual key-value pairs
        """
        context['event_type'] = event_type
        self.log(level, message, extra=context)

    def info_event(self, event_type: str, message: str, **context: Any) -> None:
        """Log an INFO level event."""
        self.log_event(logging.INFO, event_type, message, **context)

    def error_event(self, event_type: str, message: str, **context: Any) -> None:
        """Log an ERROR level event."""
        self.log_event(logging.ERROR, event_type, message, **context)

    def warning_event(self, event_type: str, message: str, **context: Any) -> None:
        """Log a WARNING level event."""
        self.log_event(logging.WARNING, event_type, message, **context)

    def debug_event(self, event_type: str, message: str, **context: Any) -> None:
        """Log a DEBUG level event."""
        self.log_event(logging.DEBUG, event_type, message, **context)
