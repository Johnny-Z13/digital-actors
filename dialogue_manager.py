"""
Dialogue Manager - Rolling Summarization System

Manages dialogue history efficiently by keeping recent turns verbatim
and summarizing older turns. This reduces token usage while preserving
important context for natural conversation flow.

Key Features:
- Keeps last N turns verbatim for immediate context
- Periodically summarizes older turns to reduce token bloat
- Tracks key information (names, facts, emotional moments)
- Provides context-optimized output for LLM prompts
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DialogueTurn:
    """Represents a single turn in the conversation."""

    speaker: str  # "player", "npc", "system"
    text: str
    turn_number: int
    timestamp: float = 0.0
    emotion: str | None = None
    topics: list[str] = field(default_factory=list)


@dataclass
class DialogueSummary:
    """Summarized older dialogue turns."""

    summary_text: str
    turn_range: tuple[int, int]  # (first_turn, last_turn)
    key_facts: list[str] = field(default_factory=list)  # Important information mentioned


class DialogueManager:
    """
    Manages dialogue history with rolling summarization.

    Keeps recent turns (last 6-8) verbatim for immediate context,
    and summarizes older turns to reduce token usage.

    Usage:
        manager = DialogueManager()
        manager.add_turn("player", "My name is Alex.")
        manager.add_turn("npc", "Nice to meet you, Alex.")
        context = manager.get_context_for_prompt()
    """

    def __init__(
        self,
        recent_turns_to_keep: int = 6,
        summarize_threshold: int = 12,
        summary_callback: Callable[[str], Awaitable[str]] | None = None,
    ):
        """
        Initialize the dialogue manager.

        Args:
            recent_turns_to_keep: Number of recent turns to keep verbatim
            summarize_threshold: Number of turns before triggering summarization
            summary_callback: Async function to summarize text (uses LLM)
        """
        self.recent_turns_to_keep = recent_turns_to_keep
        self.summarize_threshold = summarize_threshold
        self.summary_callback = summary_callback

        # Turn storage
        self.full_history: list[DialogueTurn] = []
        self.rolling_summary: DialogueSummary | None = None

        # Key information tracking
        self.key_facts: list[str] = []
        self.player_name: str | None = None
        self.npc_name: str | None = None

        # Turn counter
        self.turn_count = 0

        logger.info(
            "[DialogueManager] Initialized (keep=%d, threshold=%d)",
            recent_turns_to_keep,
            summarize_threshold,
        )

    def add_turn(
        self,
        speaker: str,
        text: str,
        emotion: str | None = None,
        topics: list[str] | None = None,
        timestamp: float = 0.0,
    ) -> None:
        """
        Add a new turn to the dialogue history.

        Args:
            speaker: "player", "npc", or "system"
            text: The dialogue text
            emotion: Optional emotional context
            topics: Optional list of topics mentioned
            timestamp: Optional timestamp
        """
        self.turn_count += 1

        turn = DialogueTurn(
            speaker=speaker,
            text=text[:500],  # Truncate very long turns
            turn_number=self.turn_count,
            timestamp=timestamp,
            emotion=emotion,
            topics=topics or [],
        )

        self.full_history.append(turn)

        # Extract key information
        self._extract_key_info(turn)

        logger.debug(
            "[DialogueManager] Added turn %d: %s ('%s...')", self.turn_count, speaker, text[:50]
        )

    def _extract_key_info(self, turn: DialogueTurn) -> None:
        """Extract important information from a turn."""
        text_lower = turn.text.lower()

        # Detect name mentions
        if turn.speaker == "player":
            # Player introducing themselves
            name_indicators = ["my name is", "i'm ", "i am ", "call me "]
            for indicator in name_indicators:
                if indicator in text_lower:
                    # Extract the name (word after the indicator)
                    try:
                        idx = text_lower.index(indicator) + len(indicator)
                        words = turn.text[idx:].split()
                        if words:
                            potential_name = words[0].strip(".,!?")
                            if len(potential_name) > 1 and potential_name[0].isupper():
                                self.player_name = potential_name
                                self.key_facts.append(f"Player's name is {self.player_name}")
                                logger.info(
                                    "[DialogueManager] Extracted player name: %s", self.player_name
                                )
                    except (ValueError, IndexError):
                        pass

    def get_context_for_prompt(self) -> str:
        """
        Get optimized dialogue context for LLM prompts.

        Returns summary + recent turns, reducing token usage while
        preserving important context.

        Returns:
            Formatted context string
        """
        # Get recent turns (verbatim)
        recent = self.full_history[-self.recent_turns_to_keep :]
        recent_text = "\n".join([f"[{t.speaker.upper()}]: {t.text}" for t in recent])

        # Build context
        parts = []

        # Add key facts first
        if self.key_facts:
            parts.append("Key information from dialogue:\n- " + "\n- ".join(self.key_facts[-5:]))

        # Add rolling summary if available
        if self.rolling_summary:
            parts.append(f"Summary of earlier dialogue:\n{self.rolling_summary.summary_text}")

        # Add recent turns
        parts.append(f"Recent dialogue:\n{recent_text}")

        return "\n\n".join(parts)

    async def maybe_update_summary(self) -> None:
        """
        Periodically summarize older turns to reduce token usage.

        Only summarizes when history exceeds threshold.
        """
        if len(self.full_history) < self.summarize_threshold:
            return

        if not self.summary_callback:
            logger.debug("[DialogueManager] No summary callback configured, skipping")
            return

        # Get turns to summarize (older than recent)
        old_turns = self.full_history[: -self.recent_turns_to_keep]
        if not old_turns:
            return

        # Only summarize if we have enough old turns
        if len(old_turns) < 6:
            return

        # Prepare text for summarization
        old_text = "\n".join([f"[{t.speaker.upper()}]: {t.text}" for t in old_turns])

        # Build prompt for summarization
        summarize_prompt = f"""Summarize this dialogue in 2-3 sentences. Focus on:
1. Key information revealed (names, facts, relationships)
2. Emotional moments or shifts
3. Important decisions or actions

Dialogue:
{old_text}

Summary:"""

        try:
            summary_text = await self.summary_callback(summarize_prompt)

            self.rolling_summary = DialogueSummary(
                summary_text=summary_text,
                turn_range=(old_turns[0].turn_number, old_turns[-1].turn_number),
                key_facts=self.key_facts.copy(),
            )

            # Remove summarized turns (keep recent)
            self.full_history = self.full_history[-self.recent_turns_to_keep :]

            logger.info(
                "[DialogueManager] Created summary for turns %d-%d",
                self.rolling_summary.turn_range[0],
                self.rolling_summary.turn_range[1],
            )

        except Exception as e:
            logger.warning("[DialogueManager] Summary generation failed: %s", e)

    def get_dialogue_history_string(self, max_turns: int | None = None) -> str:
        """
        Get raw dialogue history as a string.

        Args:
            max_turns: Maximum number of recent turns to include

        Returns:
            Formatted dialogue string
        """
        turns = self.full_history
        if max_turns:
            turns = turns[-max_turns:]

        return "\n".join([f"[{t.speaker.upper()}]: {t.text}" for t in turns])

    def reset(self) -> None:
        """Reset dialogue history for new conversation."""
        self.full_history.clear()
        self.rolling_summary = None
        self.key_facts.clear()
        self.player_name = None
        self.turn_count = 0
        logger.info("[DialogueManager] Reset")

    def get_status(self) -> dict[str, Any]:
        """Get current status for debugging."""
        return {
            "turn_count": self.turn_count,
            "history_length": len(self.full_history),
            "has_summary": self.rolling_summary is not None,
            "player_name": self.player_name,
            "key_facts_count": len(self.key_facts),
        }
