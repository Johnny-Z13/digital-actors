"""
Example demonstrating structured JSON logging.

Run this script to see JSON logging in action with different configurations.
"""

import os
from logging_config import setup_logging, StructuredLoggerAdapter
import logging

def demonstrate_json_logging():
    """Show JSON logging output."""
    print("=" * 60)
    print("DEMONSTRATION: JSON Logging (Production Format)")
    print("=" * 60)

    # Setup JSON logging
    setup_logging(use_json=True, log_level="INFO")

    # Create a logger
    logger = logging.getLogger("example")

    # Create structured logger with session context
    session_logger = StructuredLoggerAdapter(logger, {
        'session_id': 'demo_session_123',
        'character': 'clippy',
        'scene': 'welcome'
    })

    # Log various events
    print("\n1. Session created event:")
    session_logger.info_event("session_created", "Generated session token",
                               session_token_preview="abc123")

    print("\n2. Dialogue generated event with timing:")
    session_logger.info_event("dialogue_generated", "Generated dialogue response",
                               message_preview="Hello, I'm Clippy!",
                               response_preview="How can I help you?",
                               llm_response_time_ms=450,
                               total_response_time_ms=520,
                               sequence_id=1)

    print("\n3. Error event:")
    session_logger.error_event("llm_api_error", "LLM API call failed",
                                error="Connection timeout",
                                error_type="TimeoutError",
                                retry_count=3)

    print("\n4. WebSocket event:")
    session_logger.info_event("websocket_connected", "Client connected")


def demonstrate_readable_logging():
    """Show readable logging output."""
    print("\n\n" + "=" * 60)
    print("DEMONSTRATION: Readable Logging (Development Format)")
    print("=" * 60 + "\n")

    # Setup readable logging
    setup_logging(use_json=False, log_level="DEBUG")

    # Create a logger
    logger = logging.getLogger("example_dev")

    # Create structured logger
    session_logger = StructuredLoggerAdapter(logger, {
        'session_id': 'dev_session_456',
        'character': 'eliza',
        'scene': 'introduction'
    })

    # Log various events
    session_logger.debug_event("debug_event", "Debugging information",
                                variable_x=42, variable_y="test")

    session_logger.info_event("info_event", "Information message",
                               user_action="button_click")

    session_logger.warning_event("warning_event", "Warning message",
                                  deprecated_feature="old_api")

    session_logger.error_event("error_event", "Error occurred",
                                error="Something went wrong")


def demonstrate_environment_variable():
    """Show how environment variables control logging format."""
    print("\n\n" + "=" * 60)
    print("DEMONSTRATION: Environment Variable Control")
    print("=" * 60)

    print("\nSetting ENV=development (readable format):")
    os.environ["ENV"] = "development"
    setup_logging()  # Auto-detects from environment

    logger = logging.getLogger("env_test")
    logger.info("This should be in readable format")

    print("\nSetting ENV=production (JSON format):")
    os.environ["ENV"] = "production"
    os.environ["LOG_FORMAT_JSON"] = "true"
    setup_logging()  # Auto-detects from environment

    logger = logging.getLogger("env_test_prod")
    adapter = StructuredLoggerAdapter(logger, {'env': 'production'})
    adapter.info_event("production_event", "Production log in JSON format")


if __name__ == "__main__":
    # Run all demonstrations
    demonstrate_json_logging()
    demonstrate_readable_logging()
    demonstrate_environment_variable()

    print("\n\n" + "=" * 60)
    print("Demonstration Complete!")
    print("=" * 60)
    print("\nTo use JSON logging in production, set:")
    print("  ENV=production")
    print("  LOG_FORMAT_JSON=true")
    print("\nTo use readable logging in development, set:")
    print("  ENV=development")
    print("=" * 60)
