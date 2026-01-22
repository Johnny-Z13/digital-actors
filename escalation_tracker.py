"""
Escalation Tracker - Anti-Repetition System

Tracks warnings and repeated situations to vary NPC responses systematically.
Prevents the same warning from being given the same way multiple times.

Key Features:
- Tracks warning counts per topic
- Provides escalating response variations
- Eventually "gives up" on repeated warnings (realistic behavior)
- Scene-specific escalation strategies
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EscalationLevel:
    """Represents a single escalation level with response guidance."""
    level: int
    tone: str  # e.g., "concerned", "frustrated", "resigned"
    intensity: float  # 0.0 to 1.0
    instruction: str  # Guidance for LLM
    give_up: bool = False  # True if NPC should stop warning


class EscalationTracker:
    """
    Tracks warnings per topic to provide varied, escalating responses.

    Prevents NPCs from repeating the exact same warning multiple times.
    After max escalations, NPC "gives up" - realistic behavior.

    Usage:
        tracker = EscalationTracker()
        response = tracker.get_escalated_response('crank_warning')
        # First time: "Easy on the crank..."
        # Second time: "You're pushing it too hard..."
        # Third time: "You're not listening..."
        # Fourth time: [silence] (give up)
    """

    # Escalation strategies for common warning types
    ESCALATION_STRATEGIES = {
        'crank_warning': [
            EscalationLevel(1, "concerned", 0.4, "Warn gently about the crank. 'Easy on the crank. Quarter turns.'"),
            EscalationLevel(2, "firm", 0.6, "Be more direct. 'You're pushing it too hard.'"),
            EscalationLevel(3, "frustrated", 0.8, "Show frustration. 'You're not listening.'"),
            EscalationLevel(4, "resigned", 0.3, "Give up warning. Just react to consequences.", give_up=True),
        ],
        'o2_warning': [
            EscalationLevel(1, "alert", 0.5, "Note the oxygen level. 'Watch the O2.'"),
            EscalationLevel(2, "worried", 0.7, "Show more concern. 'Oxygen's dropping.'"),
            EscalationLevel(3, "urgent", 0.9, "Be urgent. 'We're losing air.'"),
            EscalationLevel(4, "desperate", 0.95, "Last warning. 'I can't keep warning you.'"),
            EscalationLevel(5, "resigned", 0.5, "Stop warning, focus on survival.", give_up=True),
        ],
        'radiation_warning': [
            EscalationLevel(1, "concerned", 0.5, "Note radiation exposure. 'Radiation's climbing.'"),
            EscalationLevel(2, "worried", 0.7, "Express physical discomfort. '[coughing] Getting worse.'"),
            EscalationLevel(3, "distressed", 0.85, "Show physical effects. '[voice weakening] Can feel it.'"),
            EscalationLevel(4, "resigned", 0.6, "Accept fate, focus on what matters.", give_up=True),
        ],
        'interruption': [
            EscalationLevel(1, "patient", 0.3, "Acknowledge interruption. 'Let me finish.'"),
            EscalationLevel(2, "firm", 0.5, "Be more direct. 'You need to listen.'"),
            EscalationLevel(3, "frustrated", 0.7, "Show frustration. 'Stop interrupting!'"),
            EscalationLevel(4, "cold", 0.6, "Withdraw slightly. Shorter responses.", give_up=True),
        ],
        'button_mashing': [
            EscalationLevel(1, "concerned", 0.4, "Warn about rapid actions. 'Slow down.'"),
            EscalationLevel(2, "stern", 0.6, "Be firm. 'Stop. Think before you act.'"),
            EscalationLevel(3, "frustrated", 0.8, "Express frustration. 'You're making it worse!'"),
            EscalationLevel(4, "resigned", 0.4, "Give up. 'Fine. Do what you want.'", give_up=True),
        ],
        'wrong_action': [
            EscalationLevel(1, "helpful", 0.4, "Correct gently. 'Not that one. Try...'"),
            EscalationLevel(2, "patient", 0.5, "Guide more explicitly. 'Listen carefully...'"),
            EscalationLevel(3, "direct", 0.7, "Be very direct. Give exact instructions."),
            EscalationLevel(4, "resigned", 0.5, "Accept they'll fail. 'I've told you what to do.'", give_up=True),
        ],
        'idle_prompt': [
            EscalationLevel(1, "gentle", 0.3, "Prompt softly. 'Still there?'"),
            EscalationLevel(2, "concerned", 0.5, "Show concern. 'Talk to me.'"),
            EscalationLevel(3, "worried", 0.7, "Express worry. 'I need to hear your voice.'"),
            EscalationLevel(4, "resigned", 0.4, "Accept silence. Continue monologue.", give_up=True),
        ],
        # Generic fallback
        'default': [
            EscalationLevel(1, "neutral", 0.4, "Address the issue calmly."),
            EscalationLevel(2, "firm", 0.6, "Be more direct."),
            EscalationLevel(3, "resigned", 0.4, "Accept the situation.", give_up=True),
        ],
    }

    def __init__(self):
        """Initialize the escalation tracker."""
        self.warnings_given: dict[str, int] = {}
        self.last_warning_time: dict[str, float] = {}

        logger.info("[EscalationTracker] Initialized")

    def get_escalation_level(self, topic: str) -> EscalationLevel:
        """
        Get the current escalation level for a topic.

        Args:
            topic: Warning topic (e.g., 'crank_warning', 'o2_warning')

        Returns:
            EscalationLevel with response guidance
        """
        count = self.warnings_given.get(topic, 0)
        strategy = self.ESCALATION_STRATEGIES.get(topic, self.ESCALATION_STRATEGIES['default'])

        # Get the appropriate level (clamped to max)
        level_index = min(count, len(strategy) - 1)
        return strategy[level_index]

    def record_warning(self, topic: str) -> EscalationLevel:
        """
        Record that a warning was given and return the escalation guidance.

        Args:
            topic: Warning topic

        Returns:
            EscalationLevel for how to express this warning
        """
        # Increment count
        if topic not in self.warnings_given:
            self.warnings_given[topic] = 0
        self.warnings_given[topic] += 1

        level = self.get_escalation_level(topic)

        logger.info(
            "[EscalationTracker] %s: level %d (%s), give_up=%s",
            topic,
            level.level,
            level.tone,
            level.give_up
        )

        return level

    def should_warn(self, topic: str) -> bool:
        """
        Check if we should still warn about this topic.

        Returns False if we've reached the "give up" level.

        Args:
            topic: Warning topic

        Returns:
            True if should warn, False if should give up
        """
        level = self.get_escalation_level(topic)
        return not level.give_up

    def get_warning_instruction(self, topic: str, base_content: str = "") -> str:
        """
        Get LLM instruction for an escalated warning.

        Args:
            topic: Warning topic
            base_content: Optional base warning content

        Returns:
            Instruction string for LLM prompt
        """
        level = self.record_warning(topic)

        if level.give_up:
            return (
                f"\n\nESCALATION NOTE: You've warned about {topic} {self.warnings_given[topic]} times. "
                f"STOP repeating this warning. Either give up, accept the situation, or focus on something else. "
                f"Tone: {level.tone}."
            )

        return (
            f"\n\nESCALATION NOTE: This is warning #{self.warnings_given[topic]} about {topic}. "
            f"Tone: {level.tone}. Intensity: {level.intensity:.0%}. "
            f"Guidance: {level.instruction}"
        )

    def get_response_variation(self, topic: str) -> Optional[str]:
        """
        Get a pre-written response variation for common warnings.

        Returns None if no pre-written response available (use LLM instead).

        Args:
            topic: Warning topic

        Returns:
            Pre-written response or None
        """
        # Pre-written response variations for rapid feedback
        variations = {
            'crank_warning': [
                "Easy on the crank. Quarter turns.",
                "You're pushing it too hard.",
                "You're not listening.",
                None,  # Give up - use silence or LLM
            ],
            'o2_warning': [
                "Watch the O2.",
                "Oxygen's dropping.",
                "We're losing air.",
                "I can't keep warning you.",
                None,  # Give up
            ],
        }

        if topic not in variations:
            return None

        count = self.warnings_given.get(topic, 0)
        topic_variations = variations[topic]

        if count < len(topic_variations):
            return topic_variations[count]

        return None

    def reset(self) -> None:
        """Reset all tracking (e.g., for new scene)."""
        self.warnings_given.clear()
        self.last_warning_time.clear()
        logger.info("[EscalationTracker] Reset")

    def reset_topic(self, topic: str) -> None:
        """Reset tracking for a specific topic."""
        if topic in self.warnings_given:
            del self.warnings_given[topic]
        if topic in self.last_warning_time:
            del self.last_warning_time[topic]
        logger.debug("[EscalationTracker] Reset topic: %s", topic)

    def get_status(self) -> dict[str, Any]:
        """Get current status for debugging."""
        return {
            'warnings_given': dict(self.warnings_given),
            'topics_at_give_up': [
                topic for topic in self.warnings_given
                if not self.should_warn(topic)
            ]
        }


# Global instance
_escalation_tracker: Optional[EscalationTracker] = None


def get_escalation_tracker() -> EscalationTracker:
    """Get the global EscalationTracker instance."""
    global _escalation_tracker
    if _escalation_tracker is None:
        _escalation_tracker = EscalationTracker()
    return _escalation_tracker
