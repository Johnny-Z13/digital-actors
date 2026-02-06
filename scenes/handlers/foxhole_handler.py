"""
Foxhole Scene Handler

Handles button actions and game logic for the Foxhole submarine crisis scenario.
Implements grief spiral mechanics and phase transitions.
"""

from scenes.handlers.base import ActionResult, SceneHandler


class FoxholeHandler(SceneHandler):
    """Handler for Foxhole scene button interactions"""

    @property
    def scene_id(self) -> str:
        return "foxhole"

    async def process_action(self, action: str, scene_state: dict, ctx=None) -> ActionResult:
        """
        Process player actions in the Foxhole scene.

        Args:
            action: The action ID (button clicked)
            scene_state: Current scene state dictionary
            ctx: Scene context object (optional)

        Returns:
            ActionResult with success status and state changes
        """
        phase = scene_state.get("phase", 1)

        # PHASE 1: Power restoration
        if action == "restore_power":
            return ActionResult(
                success=True,
                state_changes={
                    "power_level": 100,
                    "power_restored": 1,
                    "trust_level": "+15",
                },
                message="Power systems coming online. Emergency lighting restored.",
            )

        # PHASE 2: Trajectory stabilization
        elif action == "stabilize_helm":
            current_stability = scene_state.get("trajectory_stability", 0)
            if current_stability < 100:
                return ActionResult(
                    success=True,
                    state_changes={
                        "trajectory_stability": "+35",
                        "trust_level": "+10",
                        "emotional_connection": "+5",
                    },
                    message="Helm responding. Adjusting pitch...",
                )
            else:
                # Already stabilized
                if scene_state.get("trajectory_stabilized", 0) == 0:
                    return ActionResult(
                        success=True,
                        state_changes={"trajectory_stabilized": 1},
                        message="Trajectory stabilized. We're climbing.",
                    )
                else:
                    return ActionResult(
                        success=True,
                        state_changes={},
                        message="Course is steady.",
                    )

        # PHASE 3-4: Check crew logs
        elif action == "check_logs":
            # First press: Discover someone entered machinery bay
            if scene_state.get("occupancy_verified", 0) == 0:
                return ActionResult(
                    success=True,
                    state_changes={"occupancy_verified": 1},
                    message="Crew log accessed. Last entry shows engineer entered machinery bay. Name field: [DATA CORRUPTED]. Need to check bay door logs.",
                )
            else:
                # Subsequent presses: More details
                return ActionResult(
                    success=True,
                    state_changes={},
                    message="Entry time: 14:32. Status: In progress. No exit logged.",
                )

        # PHASE 3-4: Drain corridor
        elif action == "drain_entrance":
            return ActionResult(
                success=True,
                state_changes={"corridor_drained": 1},
                message="Drainage pumps activated. Water level dropping. Access to machinery bay door clear.",
            )

        # PHASE 4: Try to open bay door (will always fail - locked from inside)
        elif action == "open_bay_door":
            attempt_count = scene_state.get("bay_door_attempts", 0)
            if attempt_count == 0:
                return ActionResult(
                    success=False,
                    state_changes={"bay_door_attempts": 1},
                    message="Door control panel accessed. Entry log visible: 'LAST ENTRY - ALEX KOVICH (ENGINEER) - 14:32 - DOOR LOCKED FROM INSIDE'",
                )
            else:
                return ActionResult(
                    success=False,
                    state_changes={},
                    message="Door remains locked. Override not possible from this side.",
                )

        # PHASE 5-6: Flood machinery bay (final action)
        elif action == "flood_machinery_bay":
            # Can only be done after grief spiral is complete
            grief_complete = scene_state.get("grief_spiral_complete", 0)
            if grief_complete == 1:
                return ActionResult(
                    success=True,
                    state_changes={
                        "machinery_bay_flooded": 1,
                        "trajectory_stability": 100,  # Vessel stabilizes
                    },
                    message="[SYSTEM] Flood valves opening. Machinery bay flooding. Ballast compensating. Vessel ascending.",
                )
            else:
                # Player trying to act before James is ready
                return ActionResult(
                    success=False,
                    state_changes={},
                    message="[SYSTEM] Manual override requires remote authorization. Awaiting confirmation from Lt. Commander Kovich.",
                )

        # Unknown action
        return ActionResult(
            success=False, state_changes={}, message=f"Action '{action}' not recognized."
        )


# Singleton instance
_handler: FoxholeHandler | None = None


def get_handler() -> FoxholeHandler:
    """Get or create the Foxhole handler."""
    global _handler
    if _handler is None:
        _handler = FoxholeHandler()
    return _handler


# Export for scene handler registration
__all__ = ["FoxholeHandler", "get_handler"]
