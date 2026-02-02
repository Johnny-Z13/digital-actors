"""
Submarine Scene Handler.

Handles button actions and state modifications for the Pressure Point submarine scene.
"""

from __future__ import annotations

import logging
from typing import Any

from scenes.handlers.base import ActionResult, SceneHandler

logger = logging.getLogger(__name__)


# Power system constants
POWER_BUTTON_BOOST = 20.0  # Power button adds 20% when activated
CRANK_POWER_PER_TURN = 5.0  # Each quarter turn adds 5% power
CRANK_WARNING_THRESHOLD = 2  # Warn after 2 cranks in quick succession
CRANK_COOLDOWN_SECONDS = 8  # Reset crank counter after 8 seconds

# Power limits
POWER_MIN = 0.0
POWER_MAX = 100.0


class SubmarineHandler(SceneHandler):
    """
    Handler for the Submarine (Pressure Point) scene.

    Processes button actions and returns state modifications.
    """

    @property
    def scene_id(self) -> str:
        return "submarine"

    def __init__(self):
        self.action_handlers = {
            "POWER": self._handle_power_button,
            "CRANK": self._handle_crank,
            "O2 VALVE": self._handle_o2_valve,
            "VENT": self._handle_vent,
            "BALLAST": self._handle_ballast,
            "FLOOD MED BAY": self._handle_flood_med_bay,
        }

        # Track last crank time for cooldown
        self.last_crank_time = 0
        self.recent_cranks = 0

    async def process_action(
        self,
        action: str,
        scene_state: dict[str, Any],
        ctx: Any = None,
    ) -> ActionResult:
        """
        Process a button action and return state changes.

        Args:
            action: Button label (e.g., 'POWER', 'CRANK')
            scene_state: Current scene state dict
            ctx: Optional SceneContext

        Returns:
            ActionResult with state changes to apply
        """
        handler = self.action_handlers.get(action)
        if not handler:
            logger.warning("[Submarine] Unknown action: %s", action)
            return ActionResult(
                success=False, state_changes={}, message=f"Unknown action: {action}"
            )

        return handler(scene_state)

    def get_action_description(self, action: str) -> str:
        """Get human-readable description of an action."""
        descriptions = {
            "POWER": "Power relay activated",
            "CRANK": "Generator cranked (quarter turn)",
            "O2 VALVE": "Oxygen valve adjusted",
            "VENT": "Emergency vent activated",
            "BALLAST": "Ballast adjusted",
            "FLOOD MED BAY": "MED BAY FLOOD INITIATED",
        }
        return descriptions.get(action, f"{action} activated")

    def _handle_power_button(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle POWER button - activate backup power relay.

        Provides a significant power boost to emergency systems.
        """
        current_power = state.get("power_level", 15.0)

        # Add power boost
        new_power = min(POWER_MAX, current_power + POWER_BUTTON_BOOST)
        power_gained = new_power - current_power

        state_changes = {
            "power_level": power_gained,  # Delta to add
            "systems_repaired": 1,  # Increment systems counter
        }

        logger.info(
            "[Submarine] POWER button: +%.1f%% power (%.1f%% -> %.1f%%)",
            power_gained,
            current_power,
            new_power,
        )

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="power_on",
            milestone="power_restored",
            message=f"Backup power activated: +{power_gained:.0f}% power",
        )

    def _handle_crank(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle CRANK button - manually generate emergency power.

        Each press = one quarter turn. Generates 5% power per turn.
        James will warn if player cranks too aggressively.
        """
        import time
        current_time = time.time()
        current_power = state.get("power_level", 15.0)

        # Check if this is a rapid crank (within cooldown period)
        time_since_last = current_time - self.last_crank_time
        if time_since_last < CRANK_COOLDOWN_SECONDS:
            self.recent_cranks += 1
        else:
            self.recent_cranks = 1  # Reset counter if cooldown expired

        self.last_crank_time = current_time

        # Add power from cranking
        new_power = min(POWER_MAX, current_power + CRANK_POWER_PER_TURN)
        power_gained = new_power - current_power

        state_changes = {
            "power_level": power_gained,  # Delta to add
        }

        # Check if player is over-cranking
        over_cranking = self.recent_cranks > CRANK_WARNING_THRESHOLD
        if over_cranking:
            message = f"Generator cranked: +{power_gained:.0f}% (CAUTION: Rapid cranking!)"
            milestone = "over_cranking_detected"
        else:
            message = f"Generator cranked (quarter turn): +{power_gained:.0f}% power"
            milestone = "crank_used"

        logger.info(
            "[Submarine] CRANK: +%.1f%% power (%.1f%% -> %.1f%%), recent_cranks=%d",
            power_gained,
            current_power,
            new_power,
            self.recent_cranks,
        )

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="generator_crank",
            milestone=milestone,
            message=message,
        )

    def _handle_o2_valve(self, state: dict[str, Any]) -> ActionResult:
        """Handle O2 VALVE button - adjust oxygen flow between compartments."""
        state_changes = {
            "systems_repaired": 1,
        }

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="valve_turn",
            milestone="o2_valve_used",
            message="Oxygen valve adjusted",
        )

    def _handle_vent(self, state: dict[str, Any]) -> ActionResult:
        """Handle VENT button - emergency pressure release."""
        state_changes = {
            "systems_repaired": 1,
        }

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="vent_hiss",
            milestone="vent_used",
            message="Emergency vent activated",
        )

    def _handle_ballast(self, state: dict[str, Any]) -> ActionResult:
        """Handle BALLAST button - adjust submarine buoyancy."""
        current_depth = state.get("hull_pressure", 2400.0)

        # Ballast reduces depth slightly
        depth_reduction = 50.0
        new_depth = max(0, current_depth - depth_reduction)

        state_changes = {
            "hull_pressure": -(current_depth - new_depth),  # Delta (negative to reduce)
            "systems_repaired": 1,
        }

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="ballast_blow",
            milestone="ballast_used",
            message=f"Ballast adjusted: depth reduced by {depth_reduction:.0f}ft",
        )

    def _handle_flood_med_bay(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle FLOOD MED BAY button - emergency ascent (kills Adrian).

        This is the impossible choice button. Only available in Phase 3+.
        """
        phase = state.get("phase", 1)

        if phase < 3:
            return ActionResult(
                success=False,
                state_changes={},
                message="Med bay flood not available yet",
            )

        state_changes = {
            "med_bay_flooded": 1,  # Boolean flag
        }

        logger.info("[Submarine] MED BAY FLOOD triggered - impossible choice made")

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="flood_alarm",
            trigger_ending="sacrifice_ending",
            message="MED BAY FLOOD SEQUENCE INITIATED",
        )


# Singleton instance
_handler: SubmarineHandler | None = None


def get_handler() -> SubmarineHandler:
    """Get or create the Submarine handler."""
    global _handler
    if _handler is None:
        _handler = SubmarineHandler()
    return _handler
