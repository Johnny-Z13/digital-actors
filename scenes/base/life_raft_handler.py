"""
Life Raft Scene Handler.

Handles button actions and state modifications for the submarine survival scene.
"""

from __future__ import annotations

import logging
from typing import Any

from scenes.handlers.base import ActionResult, SceneHandler

logger = logging.getLogger(__name__)


# O2 Transfer constants
O2_TRANSFER_AMOUNT = 15.0  # How much O2 transfers per valve use
O2_TRANSFER_CAPTAIN_COST = 20.0  # Captain loses more than player gains (sacrifice)
O2_TRANSFER_EMPATHY_BONUS = 5.0  # Accepting transfer shows trust
O2_TRANSFER_COMMITMENT_BONUS = 3.0  # Taking action shows commitment
O2_TRANSFER_MAX = 5  # Maximum transfers allowed

# Comms action constants
COMMS_PRESENCE_BONUS = 10.0  # Opening comms shows presence
COMMS_EMPATHY_BONUS = 2.0  # Reaching out shows care

# Pod prep constants
POD_PREP_COMMITMENT_BONUS = 15.0  # Preparing pod shows commitment

# Detach constants (safe ending)
DETACH_REQUIRED_PHASE = 4  # Must be in phase 4+ to detach

# Risky maneuver constants
RISKY_REQUIRED_EMPATHY = 60.0
RISKY_REQUIRED_COMMITMENT = 70.0
RISKY_REQUIRED_PRESENCE = 50.0


class LifeRaftHandler(SceneHandler):
    """
    Handler for the Life Raft submarine survival scene.

    Processes button actions and returns state modifications.
    """

    @property
    def scene_id(self) -> str:
        return "life_raft"

    def __init__(self):
        self.action_handlers = {
            "O2 VALVE": self._handle_o2_valve,
            "COMMS": self._handle_comms,
            "PREP POD": self._handle_pod_prep,
            "DETACH": self._handle_detach,
            "RISKY SAVE": self._handle_risky_save,
        }

    async def process_action(
        self,
        action: str,
        scene_state: dict[str, Any],
        ctx: Any = None,
    ) -> ActionResult:
        """
        Process a button action and return state changes.

        Args:
            action: Button label (e.g., 'O2 VALVE')
            scene_state: Current scene state dict
            ctx: Optional SceneContext (unused, for interface compatibility)

        Returns:
            ActionResult with state changes to apply
        """
        handler = self.action_handlers.get(action)
        if not handler:
            logger.warning("[LifeRaft] Unknown action: %s", action)
            return ActionResult(
                success=False, state_changes={}, message=f"Unknown action: {action}"
            )

        return handler(scene_state)

    def get_action_description(self, action: str) -> str:
        """Get human-readable description of an action."""
        descriptions = {
            "O2 VALVE": "Oxygen transfer initiated",
            "COMMS": "Communication channel opened",
            "PREP POD": "Escape pod preparation initiated",
            "DETACH": "DETACHMENT SEQUENCE INITIATED",
            "RISKY SAVE": "RISKY MANEUVER INITIATED",
        }
        return descriptions.get(action, f"{action} activated")

    def _handle_o2_valve(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle O2 VALVE button - transfer oxygen from captain to player.

        Captain sacrifices some of his oxygen to keep you alive.
        """
        transfers = state.get("o2_transfers", 0)
        captain_o2 = state.get("captain_oxygen", 0)
        player_o2 = state.get("player_oxygen", 0)

        # Check if transfer is possible
        if transfers >= O2_TRANSFER_MAX:
            return ActionResult(
                success=False,
                state_changes={},
                message="O2 valve exhausted - no more transfers possible",
            )

        if captain_o2 < O2_TRANSFER_CAPTAIN_COST:
            return ActionResult(
                success=False, state_changes={}, message="Captain's oxygen too low to transfer"
            )

        # Calculate new values
        new_player_o2 = min(100.0, player_o2 + O2_TRANSFER_AMOUNT)
        actual_gain = new_player_o2 - player_o2

        state_changes = {
            "player_oxygen": actual_gain,  # Delta to add
            "captain_oxygen": -O2_TRANSFER_CAPTAIN_COST,  # Delta to subtract
            "o2_transfers": 1,  # Increment counter
            "empathy_score": O2_TRANSFER_EMPATHY_BONUS,  # Accepting help shows trust
            "commitment_score": O2_TRANSFER_COMMITMENT_BONUS,  # Taking action
        }

        logger.info(
            "[LifeRaft] O2 Transfer: player +%.1f, captain -%.1f",
            actual_gain,
            O2_TRANSFER_CAPTAIN_COST,
        )

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="o2_hiss",
            milestone="o2_valve_used",
            message=f"O2 transferred: +{actual_gain:.0f}% oxygen",
        )

    def _handle_comms(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle COMMS button - open communication channel.

        Shows presence and engagement with the captain.
        """
        state_changes = {
            "presence_score": COMMS_PRESENCE_BONUS,
            "empathy_score": COMMS_EMPATHY_BONUS,
        }

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="radio_static",
            message="Communication channel opened",
        )

    def _handle_pod_prep(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle PREP POD button - prepare escape pod for deployment.

        Shows commitment to the escape plan.
        """
        phase = state.get("phase", 1)

        # Only available in later phases
        if phase < 4:
            return ActionResult(
                success=False, state_changes={}, message="Pod prep not available yet"
            )

        state_changes = {
            "commitment_score": POD_PREP_COMMITMENT_BONUS,
        }

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="pod_prep",
            message="Escape pod preparation initiated",
        )

    def _handle_detach(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle DETACH button - trigger safe escape (captain's sacrifice).

        This ends the scene with the 'safe_ending' - player survives,
        captain dies.
        """
        phase = state.get("phase", 1)

        if phase < DETACH_REQUIRED_PHASE:
            return ActionResult(
                success=False,
                state_changes={},
                message="Detachment not available - situation not critical enough",
            )

        state_changes = {
            "detachment_triggered": 1,  # Set to true
        }

        logger.info("[LifeRaft] DETACH triggered - safe ending initiated")

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="detach_sequence",
            trigger_ending="safe_ending",
            message="Detachment sequence initiated",
        )

    def _handle_risky_save(self, state: dict[str, Any]) -> ActionResult:
        """
        Handle RISKY SAVE button - attempt the 1-in-10 maneuver.

        Success depends on empathy + commitment + presence scores.
        High scores = hero ending (both survive)
        Low scores = tragic failure (both die)
        """
        phase = state.get("phase", 1)

        if phase < 5:
            return ActionResult(
                success=False, state_changes={}, message="Risky maneuver not available yet"
            )

        empathy = state.get("empathy_score", 0)
        commitment = state.get("commitment_score", 0)
        presence = state.get("presence_score", 0)

        state_changes = {
            "risky_triggered": 1,  # Set to true - ending determined by success criteria
        }

        # Log the attempt
        will_succeed = (
            empathy >= RISKY_REQUIRED_EMPATHY
            and commitment >= RISKY_REQUIRED_COMMITMENT
            and presence >= RISKY_REQUIRED_PRESENCE
        )

        logger.info(
            "[LifeRaft] RISKY SAVE triggered - empathy=%.0f, commitment=%.0f, presence=%.0f -> %s",
            empathy,
            commitment,
            presence,
            "SUCCESS" if will_succeed else "FAILURE",
        )

        return ActionResult(
            success=True,
            state_changes=state_changes,
            sfx="hull_groan",
            trigger_ending="hero_ending" if will_succeed else "risky_failure",
            message="Risky maneuver initiated...",
        )


# Singleton instance
_handler: LifeRaftHandler | None = None


def get_handler() -> LifeRaftHandler:
    """Get or create the Life Raft handler."""
    global _handler
    if _handler is None:
        _handler = LifeRaftHandler()
    return _handler
