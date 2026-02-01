"""
Game State Manager Module

Manages scene state, state updates, game over conditions, and scene logic.
Tracks state variables, handles countdown loops, and evaluates win/lose conditions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aiohttp import web
    from player_memory import PlayerMemory

logger = logging.getLogger(__name__)


class GameStateManager:
    """Manages scene state, state updates, and game over conditions."""

    def __init__(
        self,
        ws: web.WebSocketResponse,
        scene_config: dict[str, Any],
        scene_id: str,
        logger_adapter: Any,
        player_memory: PlayerMemory,
    ) -> None:
        """
        Initialize the game state manager.

        Args:
            ws: WebSocket connection for sending state updates
            scene_config: Scene configuration dict
            scene_id: Scene identifier
            logger_adapter: Structured logger adapter for this session
            player_memory: Player memory system for tracking progress
        """
        self.ws = ws
        self.scene_config = scene_config
        self.scene_id = scene_id
        self.logger = logger_adapter
        self.player_memory = player_memory

        # Initialize scene state from config
        self.scene_state = {
            var["name"]: var["initial_value"]
            for var in self.scene_config.get("state_variables", [])
        }

        # Game over tracking
        self.game_over = False
        self.game_outcome = None
        self.james_dying_speech_sent = False
        self.death_sequence_active = False

        # Oxygen/state update countdown task
        self.state_update_task = None

        # Button press tracking
        self.button_press_counts = {}
        self.button_cooldowns = {}

        # Scene controls for validation
        self.scene_controls = {ctrl["id"]: ctrl for ctrl in self.scene_config.get("controls", [])}
        self.button_press_caps = self._build_button_caps_from_controls()

    def _build_button_caps_from_controls(self) -> dict:
        """
        Build button press caps from scene control configuration.

        Uses control.max_presses if defined, otherwise defaults to unlimited.
        Returns dict mapping control label -> max_presses.
        """
        caps = {}
        for ctrl in self.scene_controls.values():
            label = ctrl.get("label", "")
            max_presses = ctrl.get("max_presses")
            if max_presses is not None:
                caps[label] = max_presses
        return caps

    def get_control_cooldown(self, control_label: str) -> float:
        """Get cooldown seconds for a control, or 0 if no cooldown."""
        for ctrl in self.scene_controls.values():
            if ctrl.get("label") == control_label:
                return ctrl.get("cooldown_seconds") or 0.0
        return 0.0

    def start_state_update_loop(self, background_task_creator: Any) -> None:
        """
        Start the state update task if this scene has state variables with update_rate.

        Args:
            background_task_creator: Callable that creates tracked background tasks
        """
        has_dynamic_state = any(
            var.get("update_rate", 0.0) != 0 for var in self.scene_config.get("state_variables", [])
        )
        if has_dynamic_state and self.state_update_task is None:
            self.state_update_task = background_task_creator(
                self._state_update_loop(), name="state_update_loop"
            )
            logger.info("Started state update task")

    def stop_state_update_loop(self) -> None:
        """Stop the state update task if running."""
        if self.state_update_task:
            self.state_update_task.cancel()
            self.state_update_task = None
            logger.info("Stopped state update task")

    async def _state_update_loop(self) -> None:
        """Background task that updates all state variables with non-zero update_rate every second."""
        try:
            while not self.game_over:
                await asyncio.sleep(1)

                if self.game_over:
                    break

                # Update all state variables with non-zero update_rate
                state_updated = False
                for var in self.scene_config.get("state_variables", []):
                    var_name = var["name"]
                    update_rate = var.get("update_rate", 0.0)

                    if update_rate != 0 and var_name in self.scene_state:
                        min_value = var.get("min_value", 0)
                        max_value = var.get("max_value", float("inf"))

                        # Update the state variable
                        new_value = self.scene_state[var_name] + update_rate
                        self.scene_state[var_name] = max(min_value, min(max_value, new_value))
                        state_updated = True

                        # Update phase based on time remaining (for specific scenes)
                        if var_name == "time_remaining" and "phase" in self.scene_state:
                            self._update_phase_based_on_time()

                        # Scene-specific emotional bond mechanic for submarine
                        if (
                            var_name == "time_remaining"
                            and self.scene_id == "submarine"
                            and "emotional_bond" in self.scene_state
                        ):
                            bond_increase = 0.1
                            current_bond = self.scene_state["emotional_bond"]
                            self.scene_state["emotional_bond"] = min(
                                100.0, current_bond + bond_increase
                            )

                        # Log periodic updates for important variables
                        if var_name in ["oxygen", "radiation", "time_remaining"]:
                            current_value = self.scene_state[var_name]
                            if var_name == "radiation" and int(current_value) % 10 == 0:
                                logger.info("Radiation level: %.0f%%", current_value)
                            elif var_name == "time_remaining" and int(current_value) % 60 == 0:
                                logger.info("Time remaining: %.0f seconds", current_value)
                            elif var_name == "oxygen" and int(current_value) % 30 == 0:
                                logger.info("Oxygen level: %.0f", current_value)

                # Send state update to client if any variable was updated
                if state_updated:
                    try:
                        await self.ws.send_json({"type": "state_update", "state": self.scene_state})
                    except Exception:
                        break  # Connection closed

                    # Check special death triggers (scene-specific)
                    await self._check_special_death_triggers()

                    # Check for game over
                    self.check_game_over_conditions()
                    if self.game_over:
                        # Notify caller that game over was triggered
                        # (caller will handle trigger_game_over)
                        break
        except asyncio.CancelledError:
            pass  # Task was cancelled, that's fine

    async def _check_special_death_triggers(self) -> None:
        """Check for special death triggers (e.g., James death at 93% radiation)."""
        # This is a placeholder - the actual implementation will need access to
        # the dialogue engine to trigger James's death speech
        # For now, just track the flag
        if "radiation" in self.scene_state and not self.james_dying_speech_sent:
            if self.scene_state["radiation"] >= 93.0:
                self.james_dying_speech_sent = True
                logger.info("[GAME_STATE] James death trigger reached (93% radiation)")

    def _update_phase_based_on_time(self) -> None:
        """Update the phase state variable based on time_remaining (scene-specific logic)."""
        # Only update phase based on time for submarine scene
        if self.scene_id != "submarine":
            return

        time_remaining = self.scene_state.get("time_remaining", 0)
        current_phase = self.scene_state.get("phase", 1)

        # Phase thresholds based on Pressure Point screenplay
        new_phase = current_phase
        if time_remaining >= 405:
            new_phase = 1
        elif time_remaining >= 330:
            new_phase = 2
        elif time_remaining >= 270:
            new_phase = 3
        else:
            new_phase = 4

        # Log phase transitions
        if new_phase != current_phase:
            self.scene_state["phase"] = new_phase
            logger.info(
                "[PHASE TRANSITION] Entering Phase %d at %.0fs remaining", new_phase, time_remaining
            )

    def check_game_over_conditions(self) -> None:
        """Check if any win/lose conditions are met."""
        if self.game_over:
            return  # Already game over

        # Get success and failure criteria from scene config
        success_criteria = self.scene_config.get("success_criteria", [])
        failure_criteria = self.scene_config.get("failure_criteria", [])

        # Check failure conditions first (death takes priority)
        for criterion in failure_criteria:
            if self.evaluate_condition(criterion["condition"]):
                self.game_over = True
                self.game_outcome = {
                    "type": "failure",
                    "id": criterion["id"],
                    "message": criterion["message"],
                    "description": criterion.get("description", ""),
                }
                return

        # Check success conditions
        for criterion in success_criteria:
            if self.evaluate_condition(criterion["condition"]):
                self.game_over = True
                self.game_outcome = {
                    "type": "success",
                    "id": criterion["id"],
                    "message": criterion["message"],
                    "description": criterion.get("description", ""),
                }
                return

    def evaluate_condition(self, condition_str: str) -> bool:
        """Evaluate a condition string using scene state."""
        try:
            # Create a safe evaluation environment with just the state
            state = self.scene_state
            return eval(condition_str, {"__builtins__": {}}, {"state": state})
        except Exception as e:
            logger.warning("Error evaluating condition '%s': %s", condition_str, e)
            return False

    def update_state(self, updates: dict[str, Any]) -> None:
        """
        Update scene state with new values.

        Args:
            updates: Dictionary of state variable names and their new values
        """
        for key, value in updates.items():
            if key in self.scene_state:
                self.scene_state[key] = value
                logger.debug("[STATE] Updated %s = %s", key, value)

    def get_state(self) -> dict[str, Any]:
        """Get current scene state."""
        return self.scene_state.copy()

    def reset_state(self) -> None:
        """Reset scene state to initial values."""
        self.scene_state = {
            var["name"]: var["initial_value"]
            for var in self.scene_config.get("state_variables", [])
        }
        self.game_over = False
        self.game_outcome = None
        self.death_sequence_active = False
        self.james_dying_speech_sent = False
        self.button_press_counts = {}
        self.button_cooldowns = {}
