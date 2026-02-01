"""
Base Scene Handler interface.

Defines the contract for scene-specific game logic handlers.
Each scene can have a handler that processes actions, pin references,
and other scene-specific interactions.

Architecture:
- Scene config (e.g., life_raft.py) = data/structure definition
- Scene handler (this interface) = gameplay mechanics
- World Director = pacing and narrative decisions
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from post_speak_hooks import PostSpeakContext
    from scene_context import SceneContext


@dataclass
class ActionResult:
    """Result of a game action."""

    success: bool
    state_changes: dict[str, float] = field(default_factory=dict)
    message: str | None = None
    sfx: str | None = None
    milestone: str | None = None
    trigger_ending: str | None = None  # 'hero_ending', 'safe_ending', etc.


@dataclass
class PinReactionResult:
    """Result of examining an evidence pin."""

    pin_id: int
    name: str
    reaction_prompt: str  # Instructions for NPC response
    state_changes: dict[str, Any] = field(default_factory=dict)


class SceneHandler(ABC):
    """
    Abstract base class for scene-specific game logic.

    Scenes that need custom logic beyond standard dialogue should
    implement this interface. The handler processes:
    - Button actions (with state modifications)
    - Evidence/pin references (for investigation scenes)
    - Custom scene events

    Handlers do NOT handle:
    - NPC dialogue generation (that's the ChatSession's job)
    - UI rendering (that's the frontend's job)
    - Global settings (those come from config)
    """

    @property
    @abstractmethod
    def scene_id(self) -> str:
        """Return the scene ID this handler is for."""
        pass

    async def process_action(
        self,
        action: str,
        scene_state: dict[str, Any],
        ctx: SceneContext | None = None,
    ) -> ActionResult:
        """
        Process a button action and return state changes.

        Default implementation returns empty result.
        Override in subclasses that have button-based gameplay.

        Args:
            action: Button label (e.g., 'O2 VALVE')
            scene_state: Current scene state dict
            ctx: Optional SceneContext for query/RAG access (backwards compatible)

        Returns:
            ActionResult with state changes to apply
        """
        return ActionResult(success=True, state_changes={})

    def get_pin_reaction(self, pin_id: str) -> PinReactionResult | None:
        """
        Get reaction data for an evidence pin reference.

        Default implementation returns None (no pin support).
        Override in investigation scenes.

        Args:
            pin_id: The pin ID (e.g., "pin_map", "pin_receipt")

        Returns:
            PinReactionResult with NPC reaction prompt, or None
        """
        return None

    def get_action_description(self, action: str) -> str:
        """
        Get a human-readable description of an action for UI display.

        Args:
            action: Button label

        Returns:
            Description string for system notifications
        """
        return f"{action} activated"

    def on_scene_start(self, scene_state: dict[str, Any]) -> None:
        """
        Called when the scene starts. Override for initialization logic.
        """
        pass

    def on_scene_end(self, scene_state: dict[str, Any]) -> None:
        """
        Called when the scene ends. Override for cleanup logic.
        """
        pass

    async def post_speak(self, ctx: PostSpeakContext) -> None:
        """
        Called after NPC dialogue is sent, during TTS playback.

        Override in subclasses to add custom post-response logic:
        - Pre-compute state for next turn
        - Trigger events based on NPC dialogue
        - Update internal handler state

        Args:
            ctx: PostSpeakContext with dialogue info and state access

        Note:
            This method has a timeout (default 2s). Keep it fast.
        """
        pass
