"""
Fast Rules-Based Director Decision Layer

Provides instant decisions for common situations without needing LLM consultation.
This layer runs BEFORE the LLM-based World Director, handling predictable scenarios
that don't require AI reasoning.

Key Benefits:
- ~500ms → ~5ms decision time for rule-matched scenarios
- Consistent, predictable behavior for critical events
- Reduces LLM API costs and latency
- Handles time-sensitive situations (oxygen critical, phase transitions)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RuleAction(Enum):
    """Actions that rules can trigger."""

    CONTINUE = "continue"  # Let natural dialogue flow
    ADVANCE_PHASE = "advance_phase"  # Time to move to next phase
    TRIGGER_URGENCY = "trigger_urgency"  # Make NPC show urgency
    PROMPT_PLAYER = "prompt_player"  # Player has been idle
    GIVE_HINT = "give_hint"  # Help struggling player
    SPAWN_CRISIS = "spawn_crisis"  # Create emergency event
    CONSULT_LLM = "consult_llm"  # No rule matched, ask LLM


@dataclass
class RuleDecision:
    """Result of a rules-based evaluation."""

    action: RuleAction
    data: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    confidence: float = 1.0  # How certain we are (1.0 = rule matched exactly)


class DirectorRules:
    """
    Fast rules-based decision layer for the World Director.

    Evaluates common situations using simple rules before falling back
    to the LLM-based director for complex decisions.

    Usage:
        rules = DirectorRules()
        decision = rules.evaluate(scene_state, player_context)
        if decision.action != RuleAction.CONSULT_LLM:
            # Handle decision without LLM
        else:
            # Fall back to LLM director
    """

    def __init__(self):
        """Initialize the rules engine with default thresholds."""
        # Scene timing thresholds (seconds)
        self.phase_transition_times = {
            1: 75,  # Phase 1 → 2 after 1:15
            2: 150,  # Phase 2 → 3 after 2:30
            3: 210,  # Phase 3 → 4 after 3:30
        }

        # Resource thresholds
        self.oxygen_critical_threshold = 15
        self.oxygen_urgent_threshold = 30
        self.radiation_critical_threshold = 90
        self.radiation_urgent_threshold = 75

        # Player behavior thresholds
        self.player_idle_threshold = 30  # seconds
        self.player_struggling_threshold = 3  # failed attempts

        # Cooldowns for actions (prevent spam)
        self.cooldowns: dict[str, float] = {}

        # Default cooldown durations
        self._default_cooldowns = {
            "phase_transition": 60,
            "oxygen_warning": 30,
            "urgency_trigger": 45,
            "player_prompt": 20,
            "hint_given": 25,
            "emotional_beat": 45,
        }

        # Scene-specific cooldown overrides
        # Different scenes have different pacing needs
        self._scene_cooldowns = {
            "submarine": {
                "oxygen_warning": 30,  # Don't warn about O2 more than every 30s
                "phase_transition": 60,  # Min time between phase changes
                "emotional_beat": 45,  # Space out emotional moments
                "player_prompt": 20,  # Don't nag player too often
                "urgency_trigger": 30,  # Can trigger urgency more often (high tension)
                "hint_given": 20,  # More frequent hints (complex scenario)
            },
            "crown_court": {
                "oxygen_warning": 60,  # N/A but keep for consistency
                "phase_transition": 90,  # Slower pacing for courtroom drama
                "emotional_beat": 60,  # More space for dramatic beats
                "player_prompt": 30,  # More patience in formal setting
                "urgency_trigger": 60,  # Less frequent urgency (formal setting)
                "hint_given": 30,  # Less hand-holding
            },
            "default": {
                "phase_transition": 60,
                "oxygen_warning": 30,
                "urgency_trigger": 45,
                "player_prompt": 20,
                "hint_given": 25,
                "emotional_beat": 45,
            },
        }

        # Start with default cooldowns
        self.cooldown_durations = self._default_cooldowns.copy()

        logger.info("[DirectorRules] Initialized fast rules-based decision layer")

    def set_scene_cooldowns(self, scene_id: str) -> None:
        """
        Set cooldown durations based on the current scene.

        Args:
            scene_id: Current scene identifier
        """
        # Determine which cooldown profile to use
        scene_key = "default"
        if "submarine" in scene_id.lower():
            scene_key = "submarine"
        elif "court" in scene_id.lower():
            scene_key = "crown_court"

        # Apply scene-specific cooldowns
        self.cooldown_durations = self._scene_cooldowns.get(
            scene_key, self._default_cooldowns
        ).copy()
        logger.info("[DirectorRules] Applied %s cooldown profile", scene_key)

    def evaluate(
        self,
        scene_state: dict[str, Any],
        elapsed_time: float = 0.0,
        player_idle_seconds: float = 0.0,
        player_failed_attempts: int = 0,
        scene_id: str = "",
    ) -> RuleDecision:
        """
        Evaluate the current situation using fast rules.

        Args:
            scene_state: Current scene state variables
            elapsed_time: Seconds since scene started
            player_idle_seconds: Seconds since player last acted
            player_failed_attempts: Number of failed attempts this scene
            scene_id: Current scene identifier

        Returns:
            RuleDecision with action and data, or CONSULT_LLM if no rule matched
        """
        current_phase = scene_state.get("phase", 1)
        oxygen = scene_state.get("oxygen", 100)
        radiation = scene_state.get("radiation", 0)
        time_remaining = scene_state.get("time_remaining", 300)

        # RULE 1: Time-based phase transitions (highest priority)
        phase_decision = self._check_phase_transition(current_phase, elapsed_time, time_remaining)
        if phase_decision:
            return phase_decision

        # RULE 2: Critical resource thresholds
        resource_decision = self._check_resource_critical(oxygen, radiation, scene_id)
        if resource_decision:
            return resource_decision

        # RULE 3: Player idle too long
        idle_decision = self._check_player_idle(player_idle_seconds)
        if idle_decision:
            return idle_decision

        # RULE 4: Player struggling
        struggle_decision = self._check_player_struggling(player_failed_attempts, oxygen)
        if struggle_decision:
            return struggle_decision

        # RULE 5: Urgent resource warnings (non-critical but concerning)
        urgent_decision = self._check_resource_urgent(oxygen, radiation, scene_id)
        if urgent_decision:
            return urgent_decision

        # No rule matched - consult LLM
        return RuleDecision(
            action=RuleAction.CONSULT_LLM, reason="No fast rule matched - deferring to LLM director"
        )

    def _check_phase_transition(
        self, current_phase: int, elapsed_time: float, time_remaining: float
    ) -> RuleDecision | None:
        """Check if it's time to advance to the next phase."""
        if not self._check_cooldown("phase_transition"):
            return None

        # Check time-based transition
        if current_phase in self.phase_transition_times:
            threshold = self.phase_transition_times[current_phase]
            if elapsed_time >= threshold:
                self._set_cooldown("phase_transition")
                return RuleDecision(
                    action=RuleAction.ADVANCE_PHASE,
                    data={
                        "from_phase": current_phase,
                        "to_phase": current_phase + 1,
                        "trigger": "time_elapsed",
                    },
                    reason=f"Phase {current_phase}→{current_phase + 1}: {elapsed_time:.0f}s elapsed",
                )

        # Check time_remaining based transition (Pressure Point uses countdown)
        if time_remaining > 0:
            phase_thresholds = {1: 405, 2: 330, 3: 270}  # Matches web_server.py
            if current_phase in phase_thresholds:
                if time_remaining < phase_thresholds[current_phase]:
                    self._set_cooldown("phase_transition")
                    return RuleDecision(
                        action=RuleAction.ADVANCE_PHASE,
                        data={
                            "from_phase": current_phase,
                            "to_phase": current_phase + 1,
                            "trigger": "time_remaining",
                        },
                        reason=f"Phase {current_phase}→{current_phase + 1}: {time_remaining:.0f}s remaining",
                    )

        return None

    def _check_resource_critical(
        self, oxygen: float, radiation: float, scene_id: str
    ) -> RuleDecision | None:
        """Check for critical resource levels requiring immediate action."""
        # Submarine-specific: Oxygen critical
        if "submarine" in scene_id.lower() and oxygen <= self.oxygen_critical_threshold:
            if self._check_cooldown("oxygen_warning"):
                self._set_cooldown("oxygen_warning")
                return RuleDecision(
                    action=RuleAction.SPAWN_CRISIS,
                    data={
                        "event_type": "crisis",
                        "resource": "oxygen",
                        "level": oxygen,
                        "event_description": "Oxygen critically low - emergency situation",
                    },
                    reason=f"CRITICAL: Oxygen at {oxygen}% - below {self.oxygen_critical_threshold}%",
                )

        # Radiation critical
        if radiation >= self.radiation_critical_threshold:
            if self._check_cooldown("urgency_trigger"):
                self._set_cooldown("urgency_trigger")
                return RuleDecision(
                    action=RuleAction.TRIGGER_URGENCY,
                    data={
                        "behavior_change": "more_worried",
                        "reason": f"radiation_critical_{radiation}",
                    },
                    reason=f"CRITICAL: Radiation at {radiation}% - above {self.radiation_critical_threshold}%",
                )

        return None

    def _check_resource_urgent(
        self, oxygen: float, radiation: float, scene_id: str
    ) -> RuleDecision | None:
        """Check for urgent (but not critical) resource warnings."""
        # Oxygen urgent
        if "submarine" in scene_id.lower() and oxygen <= self.oxygen_urgent_threshold:
            if oxygen > self.oxygen_critical_threshold:  # Not critical yet
                if self._check_cooldown("oxygen_warning"):
                    self._set_cooldown("oxygen_warning")
                    return RuleDecision(
                        action=RuleAction.TRIGGER_URGENCY,
                        data={"behavior_change": "more_urgent", "reason": f"oxygen_low_{oxygen}"},
                        reason=f"URGENT: Oxygen at {oxygen}% - approaching critical",
                    )

        # Radiation urgent
        if (
            radiation >= self.radiation_urgent_threshold
            and radiation < self.radiation_critical_threshold
        ):
            if self._check_cooldown("urgency_trigger"):
                self._set_cooldown("urgency_trigger")
                return RuleDecision(
                    action=RuleAction.TRIGGER_URGENCY,
                    data={
                        "behavior_change": "more_worried",
                        "reason": f"radiation_high_{radiation}",
                    },
                    reason=f"URGENT: Radiation at {radiation}% - dangerous levels",
                )

        return None

    def _check_player_idle(self, player_idle_seconds: float) -> RuleDecision | None:
        """Check if player has been idle too long."""
        if player_idle_seconds >= self.player_idle_threshold:
            if self._check_cooldown("player_prompt"):
                self._set_cooldown("player_prompt")
                return RuleDecision(
                    action=RuleAction.PROMPT_PLAYER,
                    data={"idle_seconds": player_idle_seconds, "hint_type": "subtle"},
                    reason=f"Player idle for {player_idle_seconds:.0f}s - prompting",
                )
        return None

    def _check_player_struggling(self, failed_attempts: int, oxygen: float) -> RuleDecision | None:
        """Check if player is struggling and needs help."""
        if failed_attempts >= self.player_struggling_threshold:
            if self._check_cooldown("hint_given"):
                self._set_cooldown("hint_given")
                # More direct hint if oxygen is low
                hint_type = "direct" if oxygen < 50 else "subtle"
                return RuleDecision(
                    action=RuleAction.GIVE_HINT,
                    data={
                        "hint_type": hint_type,
                        "failed_attempts": failed_attempts,
                        "hint_content": "what to do next",
                    },
                    reason=f"Player struggling: {failed_attempts} failures - giving {hint_type} hint",
                )
        return None

    def _check_cooldown(self, action_type: str) -> bool:
        """Check if an action type is off cooldown."""
        if action_type not in self.cooldowns:
            return True
        return time.time() >= self.cooldowns[action_type]

    def _set_cooldown(self, action_type: str) -> None:
        """Set cooldown for an action type."""
        duration = self.cooldown_durations.get(action_type, 30)
        self.cooldowns[action_type] = time.time() + duration
        logger.debug("[DirectorRules] Set cooldown for %s: %ds", action_type, duration)

    def reset_cooldowns(self) -> None:
        """Reset all cooldowns (e.g., on scene restart)."""
        self.cooldowns.clear()
        logger.info("[DirectorRules] Cooldowns reset")

    def get_status(self) -> dict[str, Any]:
        """Get current rules engine status for debugging."""
        now = time.time()
        return {
            "cooldowns": {
                action: max(0, self.cooldowns.get(action, 0) - now)
                for action in self.cooldown_durations
            },
            "thresholds": {
                "oxygen_critical": self.oxygen_critical_threshold,
                "oxygen_urgent": self.oxygen_urgent_threshold,
                "radiation_critical": self.radiation_critical_threshold,
                "player_idle": self.player_idle_threshold,
            },
        }


# Global instance for convenience
_director_rules: DirectorRules | None = None


def get_director_rules() -> DirectorRules:
    """Get the global DirectorRules instance."""
    global _director_rules
    if _director_rules is None:
        _director_rules = DirectorRules()
    return _director_rules
