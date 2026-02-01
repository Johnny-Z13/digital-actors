"""
Response Handler Module

Manages TTS, audio generation, and response delivery for chat sessions.
Handles the response queue system to prevent dialogue flooding.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from response_queue import ResponseItem, ResponsePriority, ResponseQueue
from tts_elevenlabs import synthesize_npc_speech

if TYPE_CHECKING:
    from aiohttp import web

logger = logging.getLogger(__name__)


class ResponseHandler:
    """Handles response delivery, TTS generation, and audio streaming."""

    def __init__(
        self,
        ws: web.WebSocketResponse,
        tts_manager: Any,
        character_config: dict[str, Any],
        logger_adapter: Any,
    ) -> None:
        """
        Initialize the response handler.

        Args:
            ws: WebSocket connection for sending responses
            tts_manager: TTS manager instance
            character_config: Character configuration dict
            logger_adapter: Structured logger adapter for this session
        """
        self.ws = ws
        self.tts_manager = tts_manager
        self.character_config = character_config
        self.logger = logger_adapter
        self.tts_mode = "expressive"
        self.game_over = False
        self.opening_speech_playing = False
        self.death_sequence_active = False

        # Initialize response queue
        self.response_queue = ResponseQueue(
            send_callback=self._send_character_response_direct,
            min_gap_seconds=2.0,
        )
        logger.info("Response Queue initialized")

    async def _send_character_response_direct(
        self,
        content: str,
        emotion_context: str | None = None,
        is_death_speech: bool = False,
    ) -> None:
        """
        INTERNAL: Directly send a character response to the client (bypasses queue).

        This method is called by the ResponseQueue to actually transmit responses.
        Do NOT call this directly unless you have a very good reason.

        TEXT-FIRST OPTIMIZATION: Sends text immediately for perceived low-latency,
        then sends audio as a follow-up message. Frontend displays text while waiting
        for audio to arrive.

        Args:
            content: The dialogue text
            emotion_context: Optional emotional context for TTS (e.g., "panicked", "calm")
            is_death_speech: If True, this is a final death speech and should be allowed
                            even when death_sequence_active is True.
        """
        start_time = time.time()

        # === GLOBAL DEATH BLOCK (applies to ALL actors) ===
        if self.death_sequence_active and not is_death_speech:
            self.logger.info_event(
                "death_block",
                "Blocked post-death response",
                content_preview=content[:50],
                death_sequence_active=True,
            )
            return

        # Generate unique response ID for matching text with audio
        response_id = f"resp_{id(content)}_{asyncio.get_event_loop().time()}"

        # STEP 1: Send text IMMEDIATELY (don't wait for TTS)
        text_response = {
            "type": "character_response_text",
            "character_name": self.character_config["name"],
            "content": content,
            "response_id": response_id,
            "suggested_questions": [],  # Will be populated by caller if needed
        }
        await self.ws.send_json(text_response)
        text_sent_time = time.time()
        self.logger.debug_event(
            "text_response_sent",
            "Sent text response",
            content_preview=content[:50],
            response_time_ms=int((text_sent_time - start_time) * 1000),
        )

        # STEP 2: Generate TTS audio asynchronously
        if self.tts_manager.is_enabled():
            try:
                # Get character_id and scene info from context (will be injected)
                character_id = getattr(self, "character_id", "clippy")
                scene_id = getattr(self, "scene_id", "welcome")
                scene_phase = getattr(self, "scene_phase", None)

                audio_base64 = await synthesize_npc_speech(
                    content,
                    character_id,
                    emotion_context,
                    scene_phase,
                    scene_id,
                    self.tts_mode,
                )

                # STEP 3: Send audio as follow-up message
                if audio_base64:
                    audio_response = {
                        "type": "character_response_audio",
                        "response_id": response_id,
                        "audio": audio_base64,
                        "audio_format": "mp3",
                    }
                    await self.ws.send_json(audio_response)
                    total_time = time.time()
                    self.logger.info_event(
                        "audio_response_sent",
                        "TTS audio sent",
                        audio_size=len(audio_base64),
                        tts_time_ms=int((total_time - text_sent_time) * 1000),
                        total_response_time_ms=int((total_time - start_time) * 1000),
                    )
                else:
                    self.logger.warning_event("tts_no_audio", "TTS returned no audio")
            except Exception as e:
                self.logger.warning_event("tts_failed", "TTS generation failed", error=str(e))
        else:
            self.logger.debug("TTS not enabled")

    async def send_character_response(
        self,
        content: str,
        priority: ResponsePriority = ResponsePriority.NORMAL,
        emotion_context: str | None = None,
        sequence_id: int | None = None,
        source: str = "unknown",
        cancellable: bool = True,
        suggested_questions: list[str] | None = None,
    ) -> None:
        """
        Queue a character response for delivery (goes through ResponseQueue).

        This is the standard way to send NPC dialogue. Responses are queued
        and delivered one at a time with proper prioritization to prevent flooding.

        Args:
            content: The dialogue text
            priority: Priority level (default: NORMAL)
            emotion_context: Optional emotional context for TTS
            sequence_id: Optional sequence ID for cancellation tracking
            source: Description of what generated this response (for debugging)
            cancellable: Whether this response can be cancelled by higher priority items
            suggested_questions: Optional list of suggested questions for the player
        """
        if sequence_id is None:
            sequence_id = await self.response_queue.get_next_sequence_id()

        item = ResponseItem(
            content=content,
            priority=priority,
            sequence_id=sequence_id,
            emotion_context=emotion_context,
            cancellable=cancellable,
            source=source,
        )

        await self.response_queue.enqueue(item)
        self.logger.debug_event(
            "response_queued",
            f"Queued {priority.name} response",
            priority=priority.name,
            content_preview=content[:50],
            source=source,
            sequence_id=sequence_id,
        )

    async def send_character_response_immediate(
        self,
        content: str,
        emotion_context: str | None = None,
    ) -> None:
        """
        Send a CRITICAL character response immediately (bypasses queue).

        Use ONLY for:
        - Death speeches
        - Game over messages
        - Other critical narrative moments that must not be delayed

        For normal dialogue, use send_character_response() instead.

        Args:
            content: The dialogue text
            emotion_context: Optional emotional context for TTS
        """
        self.logger.info_event(
            "immediate_response",
            "Sending IMMEDIATE response (bypassing queue)",
            content_preview=content[:50],
        )

        # Queue it with CRITICAL priority and don't allow cancellation
        sequence_id = await self.response_queue.get_next_sequence_id()
        item = ResponseItem(
            content=content,
            priority=ResponsePriority.CRITICAL,
            sequence_id=sequence_id,
            emotion_context=emotion_context,
            cancellable=False,
            source="immediate_critical",
        )

        await self.response_queue.enqueue(item, supersede_lower_priority=False)

    async def dispatch_event(self, event_name: str) -> None:
        """Dispatch an event triggered by post-speak hooks."""
        logger.info("[EVENT] Dispatching: %s", event_name)
        try:
            await self.ws.send_json(
                {
                    "type": "scene_event",
                    "event": event_name,
                }
            )
        except Exception as e:
            logger.warning("[EVENT] Failed to dispatch %s: %s", event_name, e)

    def set_context(self, character_id: str, scene_id: str, scene_phase: int | None = None) -> None:
        """
        Set contextual information for TTS generation.

        Args:
            character_id: Character ID for voice selection
            scene_id: Scene ID for context-aware TTS
            scene_phase: Optional scene phase for progression-aware TTS
        """
        self.character_id = character_id
        self.scene_id = scene_id
        self.scene_phase = scene_phase
