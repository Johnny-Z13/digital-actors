"""
Scene Handlers Registry.

Provides a unified interface for getting scene-specific handlers.
Handlers encapsulate scene-specific game logic (button actions, pin reactions, etc.)
separate from the generic chat session and scene configuration.

Usage:
    from scenes.handlers import get_scene_handler

    handler = get_scene_handler('life_raft')
    if handler:
        result = handler.process_action('O2 VALVE', scene_state)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scenes.handlers.base import ActionResult, PinReactionResult, SceneHandler

# Handler registry - maps scene_id to handler getter function
_HANDLER_REGISTRY: dict[str, callable] = {}


def register_handler(scene_id: str, getter_fn: callable) -> None:
    """Register a handler getter function for a scene."""
    _HANDLER_REGISTRY[scene_id] = getter_fn


def get_scene_handler(scene_id: str) -> SceneHandler | None:
    """
    Get the handler for a specific scene.

    Args:
        scene_id: The scene identifier (e.g., 'life_raft', 'iconic_detectives')

    Returns:
        SceneHandler instance if one exists for this scene, else None
    """
    getter = _HANDLER_REGISTRY.get(scene_id)
    if getter:
        return getter()
    return None


def get_all_handler_scene_ids() -> list[str]:
    """Get list of all scene IDs that have handlers."""
    return list(_HANDLER_REGISTRY.keys())


# Register built-in handlers
def _register_builtin_handlers() -> None:
    """Register all built-in scene handlers."""
    # Submarine handler
    from scenes.handlers.submarine_handler import get_handler as get_submarine_handler

    register_handler("submarine", get_submarine_handler)

    # Life Raft handler
    from scenes.handlers.life_raft_handler import get_handler as get_life_raft_handler

    register_handler("life_raft", get_life_raft_handler)

    # Iconic Detectives handler
    from scenes.handlers.iconic_detectives_handler import get_handler as get_detectives_handler

    register_handler("iconic_detectives", get_detectives_handler)


# Auto-register on import
_register_builtin_handlers()


__all__ = [
    "ActionResult",
    "PinReactionResult",
    "SceneHandler",
    "get_all_handler_scene_ids",
    "get_scene_handler",
    "register_handler",
]
