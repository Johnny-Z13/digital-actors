"""
Response Queue System for NPC Dialogue Management.

This module provides a centralized queue system to prevent dialogue flooding
by ensuring NPC responses are delivered one at a time with proper prioritization
and intelligent cancellation of stale/superseded responses.

Key Features:
- Priority-based response ordering (CRITICAL > URGENT > NORMAL > BACKGROUND)
- Automatic cancellation of superseded low-priority responses
- Consolidation of redundant background chatter
- Minimum timing gap between responses for readability
- Thread-safe async processing

Author: Digital Actors Team
Date: 2026-01-21
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Callable, Any, Awaitable

logger = logging.getLogger(__name__)


class ResponsePriority(IntEnum):
    """
    Priority levels for NPC responses, ordered from highest to lowest.

    Lower numeric values = higher priority.
    Higher priority responses can supersede lower priority ones.
    """

    CRITICAL = 0    # Death speeches, game over - never cancelled, blocks all others
    URGENT = 1      # Major story beats (Phase 3 revelation, flooding decision)
    NORMAL = 2      # Player-triggered responses (messages, button presses)
    BACKGROUND = 3  # Director events, hints, waiting responses - easily cancelled


@dataclass
class ResponseItem:
    """
    Represents a single queued NPC response.

    Attributes:
        content: The dialogue text to speak
        priority: Priority level determining processing order and cancellation
        sequence_id: Unique identifier for tracking and cancellation
        emotion_context: Optional emotion hint for TTS (e.g., "panicked", "calm")
        cancellable: Whether this response can be cancelled by higher priority items
        source: Description of what generated this response (for debugging)
        timestamp: When this response was created (auto-generated)
    """
    content: str
    priority: ResponsePriority
    sequence_id: int
    emotion_context: Optional[str] = None
    cancellable: bool = True
    source: str = "unknown"
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    def __repr__(self) -> str:
        """Human-readable representation for logging."""
        return (
            f"ResponseItem(priority={self.priority.name}, "
            f"seq={self.sequence_id}, source={self.source}, "
            f"content={self.content[:50]}...)"
        )


class ResponseQueue:
    """
    Centralized queue for managing NPC dialogue responses.

    This queue ensures NPCs speak one thought at a time, with intelligent
    prioritization and cancellation to prevent dialogue flooding.

    Thread Safety:
        All public methods are async and use internal locks for thread safety.

    Usage:
        queue = ResponseQueue(send_callback)
        await queue.enqueue(ResponseItem(...))
        # Queue automatically processes items in background
    """

    def __init__(
        self,
        send_callback: Callable[[str, Optional[str]], Awaitable[None]],
        min_gap_seconds: float = 2.0
    ) -> None:
        """
        Initialize the response queue.

        Args:
            send_callback: Async function to actually send responses to client.
                          Signature: async def send(content: str, emotion: str | None) -> None
            min_gap_seconds: Minimum time gap between responses (seconds).
                           Prevents rapid-fire dialogue.
        """
        self._queue: list[ResponseItem] = []
        self._send_callback = send_callback
        self._min_gap_seconds = min_gap_seconds

        # Processing state
        self._is_processing = False
        self._lock = asyncio.Lock()  # Protects queue modifications
        self._last_send_time: float = 0.0

        # Sequence tracking
        self._global_sequence = 0

        logger.info(
            "[ResponseQueue] Initialized with min_gap=%.1fs",
            min_gap_seconds
        )

    async def enqueue(
        self,
        item: ResponseItem,
        supersede_lower_priority: bool = True
    ) -> None:
        """
        Add a response to the queue with priority handling.

        This method intelligently manages the queue by:
        1. Removing superseded low-priority items
        2. Consolidating redundant background chatter
        3. Maintaining priority order

        Args:
            item: The response item to enqueue
            supersede_lower_priority: If True, cancel queued items with lower priority

        Thread Safety:
            Uses internal lock to ensure thread-safe queue modifications.
        """
        async with self._lock:
            logger.debug(
                "[ResponseQueue] Enqueuing: %s (current queue size: %d)",
                item,
                len(self._queue)
            )

            # Rule 1: Supersede lower priority items (if enabled)
            if supersede_lower_priority and item.priority <= ResponsePriority.NORMAL:
                original_size = len(self._queue)
                self._queue = [
                    r for r in self._queue
                    if r.priority <= item.priority or not r.cancellable
                ]
                removed = original_size - len(self._queue)
                if removed > 0:
                    logger.info(
                        "[ResponseQueue] Superseded %d lower-priority items with %s",
                        removed,
                        item.priority.name
                    )

            # Rule 2: Consolidate background responses
            # Keep only the newest BACKGROUND item to prevent chatter buildup
            if item.priority == ResponsePriority.BACKGROUND:
                self._queue = [
                    r for r in self._queue
                    if r.priority != ResponsePriority.BACKGROUND
                ]
                logger.debug("[ResponseQueue] Consolidated background responses")

            # Rule 3: Add item to queue in priority order
            self._queue.append(item)
            self._queue.sort(key=lambda r: (r.priority, r.sequence_id))

            logger.info(
                "[ResponseQueue] Queued %s response from '%s' (queue size: %d)",
                item.priority.name,
                item.source,
                len(self._queue)
            )

        # Start processing if not already running
        if not self._is_processing:
            asyncio.create_task(self._process_queue())

    async def cancel_by_sequence(self, sequence_id: int) -> int:
        """
        Cancel all queued responses with a specific sequence ID.

        This is useful when a response generation is cancelled mid-flight
        (e.g., player interrupted with new action).

        Args:
            sequence_id: The sequence ID to cancel

        Returns:
            Number of responses cancelled
        """
        async with self._lock:
            original_size = len(self._queue)
            self._queue = [
                r for r in self._queue
                if r.sequence_id != sequence_id or not r.cancellable
            ]
            cancelled = original_size - len(self._queue)

            if cancelled > 0:
                logger.info(
                    "[ResponseQueue] Cancelled %d responses with sequence_id=%d",
                    cancelled,
                    sequence_id
                )

            return cancelled

    async def clear_background_responses(self) -> int:
        """
        Remove all queued BACKGROUND priority responses.

        Useful when player takes major action that makes background
        chatter irrelevant.

        Returns:
            Number of responses removed
        """
        async with self._lock:
            original_size = len(self._queue)
            self._queue = [
                r for r in self._queue
                if r.priority != ResponsePriority.BACKGROUND or not r.cancellable
            ]
            removed = original_size - len(self._queue)

            if removed > 0:
                logger.info(
                    "[ResponseQueue] Cleared %d background responses",
                    removed
                )

            return removed

    def get_next_sequence_id(self) -> int:
        """
        Get the next sequence ID for response tracking.

        Returns:
            Monotonically increasing sequence ID
        """
        self._global_sequence += 1
        return self._global_sequence

    async def _process_queue(self) -> None:
        """
        Background task that processes queued responses one at a time.

        This ensures:
        - Only one response is being sent at a time
        - Minimum gap between responses is maintained
        - Priority order is respected
        - Cancellable items can be removed before sending

        Runs continuously while queue has items.
        """
        if self._is_processing:
            logger.debug("[ResponseQueue] Already processing, skipping duplicate task")
            return

        self._is_processing = True
        logger.debug("[ResponseQueue] Started queue processing")

        try:
            while True:
                # Get next item (thread-safe)
                async with self._lock:
                    if not self._queue:
                        break  # Queue empty, exit

                    item = self._queue.pop(0)
                    logger.debug(
                        "[ResponseQueue] Processing: %s (remaining: %d)",
                        item,
                        len(self._queue)
                    )

                # Enforce minimum gap between responses
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - self._last_send_time

                if time_since_last < self._min_gap_seconds:
                    gap_needed = self._min_gap_seconds - time_since_last
                    logger.debug(
                        "[ResponseQueue] Waiting %.1fs before next response",
                        gap_needed
                    )
                    await asyncio.sleep(gap_needed)

                # Send the response
                logger.info(
                    "[ResponseQueue] Sending %s response: '%s...'",
                    item.priority.name,
                    item.content[:50]
                )

                try:
                    await self._send_callback(item.content, item.emotion_context)
                    self._last_send_time = asyncio.get_event_loop().time()
                except Exception as e:
                    logger.error(
                        "[ResponseQueue] Error sending response: %s",
                        e,
                        exc_info=True
                    )

        finally:
            self._is_processing = False
            logger.debug("[ResponseQueue] Stopped queue processing")

    def get_queue_status(self) -> dict[str, Any]:
        """
        Get current queue status for debugging/monitoring.

        Returns:
            Dictionary with queue statistics
        """
        return {
            "size": len(self._queue),
            "is_processing": self._is_processing,
            "items": [
                {
                    "priority": item.priority.name,
                    "sequence": item.sequence_id,
                    "source": item.source,
                    "preview": item.content[:50] + "..."
                }
                for item in self._queue
            ]
        }
