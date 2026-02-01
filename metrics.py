"""
Prometheus metrics instrumentation for Digital Actors.

This module provides metrics tracking for:
- Request count by scene/character
- Response time distribution
- LLM API latency
- TTS processing time
- Error rate by type
- Active session count
- Database query time

Usage:
    from metrics import (
        track_request,
        track_llm_call,
        track_tts_call,
        track_error,
        active_sessions_gauge,
    )

    # Track a request
    with track_request(scene="welcome", character="clippy", status="success"):
        # ... handle request ...
        pass

    # Track LLM call
    with track_llm_call(provider="anthropic", model="claude-haiku"):
        # ... call LLM ...
        pass

    # Track TTS call
    with track_tts_call():
        # ... synthesize speech ...
        pass

    # Track error
    track_error("validation_error")

    # Update active sessions
    active_sessions_gauge.set(5)
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator

from prometheus_client import Counter, Gauge, Histogram

if TYPE_CHECKING:
    from typing import Literal

# === COUNTERS ===

# Total number of requests by scene, character, and status
requests_total = Counter(
    "digital_actors_requests_total",
    "Total number of requests processed",
    ["scene", "character", "status"],
)

# Total number of errors by type
errors_total = Counter(
    "digital_actors_errors_total",
    "Total number of errors encountered",
    ["error_type"],
)

# === HISTOGRAMS ===

# Response time distribution (seconds) by scene and character
response_time_seconds = Histogram(
    "digital_actors_response_time_seconds",
    "Time taken to process a complete request",
    ["scene", "character"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

# LLM API latency (seconds) by provider and model
llm_latency_seconds = Histogram(
    "digital_actors_llm_latency_seconds",
    "Time taken for LLM API calls",
    ["provider", "model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

# TTS processing time (seconds)
tts_latency_seconds = Histogram(
    "digital_actors_tts_latency_seconds",
    "Time taken for TTS processing",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")),
)

# Database query time (seconds) by operation
db_query_time_seconds = Histogram(
    "digital_actors_db_query_time_seconds",
    "Time taken for database queries",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, float("inf")),
)

# === GAUGES ===

# Current number of active sessions
active_sessions_gauge = Gauge(
    "digital_actors_active_sessions",
    "Current number of active chat sessions",
)

# === CONTEXT MANAGERS ===


@contextmanager
def track_request(
    scene: str,
    character: str,
    status: Literal["success", "error"] = "success",
) -> Generator[None, None, None]:
    """
    Context manager to track request metrics.

    Args:
        scene: The scene ID
        character: The character ID
        status: Request status (success or error)

    Example:
        with track_request("welcome", "clippy", "success"):
            # ... handle request ...
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        response_time_seconds.labels(scene=scene, character=character).observe(duration)
        requests_total.labels(scene=scene, character=character, status=status).inc()


@contextmanager
def track_llm_call(
    provider: str,
    model: str,
) -> Generator[None, None, None]:
    """
    Context manager to track LLM API call metrics.

    Args:
        provider: The LLM provider (e.g., "anthropic", "openai", "google")
        model: The model name (e.g., "claude-haiku", "gpt-4")

    Example:
        with track_llm_call("anthropic", "claude-haiku"):
            # ... call LLM API ...
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        llm_latency_seconds.labels(provider=provider, model=model).observe(duration)


@contextmanager
def track_tts_call() -> Generator[None, None, None]:
    """
    Context manager to track TTS processing metrics.

    Example:
        with track_tts_call():
            # ... synthesize speech ...
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        tts_latency_seconds.observe(duration)


@contextmanager
def track_db_query(operation: str) -> Generator[None, None, None]:
    """
    Context manager to track database query metrics.

    Args:
        operation: The database operation (e.g., "insert", "select", "update", "delete")

    Example:
        with track_db_query("select"):
            # ... execute database query ...
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        db_query_time_seconds.labels(operation=operation).observe(duration)


def track_error(error_type: str) -> None:
    """
    Track an error occurrence.

    Args:
        error_type: The type of error (e.g., "validation_error", "llm_timeout", "tts_error")

    Example:
        track_error("validation_error")
    """
    errors_total.labels(error_type=error_type).inc()


def update_active_sessions(count: int) -> None:
    """
    Update the active sessions gauge.

    Args:
        count: The current number of active sessions

    Example:
        update_active_sessions(5)
    """
    active_sessions_gauge.set(count)
