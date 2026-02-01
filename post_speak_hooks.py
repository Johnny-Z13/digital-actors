"""
Post-Speak Hooks for scene-specific post-response processing.

Provides a hook system that runs after NPC dialogue is sent,
during TTS playback. Useful for pre-computation and event triggers.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from query_system import QuerySystem

logger = logging.getLogger(__name__)

# Default timeout for hook execution (seconds)
DEFAULT_HOOK_TIMEOUT = 2.0


@dataclass
class PostSpeakContext:
    """
    Context passed to post-speak hooks.

    Provides access to dialogue state and utilities for hooks to
    update scene state or trigger events.
    """

    llm_response: str
    dialogue_history: str
    scene_state: dict[str, Any]
    scene_id: str
    session_id: str = ""
    query_system: QuerySystem | None = None

    # Internal: callbacks for state/event handling
    _state_updates: dict[str, Any] = field(default_factory=dict)
    _triggered_events: list[str] = field(default_factory=list)

    def update_state(self, key: str, value: Any) -> None:
        """
        Queue a state update.

        Updates are collected and applied after all hooks complete.

        Args:
            key: State variable name
            value: New value (or delta for numeric values)
        """
        self._state_updates[key] = value
        logger.debug("Post-speak queued state update: %s = %s", key, value)

    def trigger_event(self, event_name: str) -> None:
        """
        Trigger a named event.

        Events are collected and dispatched after all hooks complete.

        Args:
            event_name: Event identifier (e.g., "alarm_sound", "music_change")
        """
        if event_name not in self._triggered_events:
            self._triggered_events.append(event_name)
            logger.debug("Post-speak triggered event: %s", event_name)

    async def query(
        self,
        text: str,
        condition: str,
        latch: bool = False,
    ) -> bool:
        """
        Convenience method to evaluate a condition.

        Args:
            text: Text to evaluate against
            condition: Condition to check
            latch: If True, result latches to True once triggered

        Returns:
            Whether condition is met
        """
        if self.query_system is None:
            logger.warning("Query attempted but QuerySystem not available")
            return False

        return await self.query_system.query(
            input_text=text,
            query_text=condition,
            latch=latch,
            session_id=self.session_id,
        )

    def get_state_updates(self) -> dict[str, Any]:
        """Get all queued state updates."""
        return self._state_updates.copy()

    def get_triggered_events(self) -> list[str]:
        """Get all triggered events."""
        return self._triggered_events.copy()


class PostSpeakHook(ABC):
    """
    Abstract base class for scene-specific post-speak hooks.

    Subclass and implement execute() to add custom logic that
    runs after NPC dialogue is sent.
    """

    @property
    @abstractmethod
    def scene_id(self) -> str:
        """Return the scene ID this hook applies to."""
        pass

    @abstractmethod
    async def execute(self, ctx: PostSpeakContext) -> None:
        """
        Execute the post-speak hook.

        Called after NPC text is sent to client, during TTS playback.
        Use ctx.update_state() and ctx.trigger_event() to affect game state.

        Args:
            ctx: Context with dialogue info and state access

        Note:
            This method has a timeout (default 2s). If it takes longer,
            it will be cancelled and a warning logged.
        """
        pass


# Global registry of hooks by scene_id
_hook_registry: dict[str, list[PostSpeakHook]] = {}


def register_hook(hook: PostSpeakHook) -> None:
    """
    Register a post-speak hook.

    Args:
        hook: Hook instance to register
    """
    scene_id = hook.scene_id
    if scene_id not in _hook_registry:
        _hook_registry[scene_id] = []

    _hook_registry[scene_id].append(hook)
    logger.info("Registered post-speak hook for scene: %s", scene_id)


def unregister_hook(hook: PostSpeakHook) -> None:
    """
    Unregister a post-speak hook.

    Args:
        hook: Hook instance to unregister
    """
    scene_id = hook.scene_id
    if scene_id in _hook_registry:
        try:
            _hook_registry[scene_id].remove(hook)
            logger.info("Unregistered post-speak hook for scene: %s", scene_id)
        except ValueError:
            pass  # Hook not in list


def get_hooks(scene_id: str) -> list[PostSpeakHook]:
    """
    Get all registered hooks for a scene.

    Args:
        scene_id: Scene identifier

    Returns:
        List of registered hooks (may be empty)
    """
    return _hook_registry.get(scene_id, [])


async def execute_hooks(
    ctx: PostSpeakContext,
    timeout: float = DEFAULT_HOOK_TIMEOUT,
) -> PostSpeakContext:
    """
    Execute all registered hooks for a scene.

    Runs hooks sequentially with timeout protection.
    Collects all state updates and events from all hooks.

    Args:
        ctx: Context with dialogue info
        timeout: Max time per hook in seconds

    Returns:
        Updated context with collected state updates and events
    """
    hooks = get_hooks(ctx.scene_id)

    if not hooks:
        return ctx

    logger.debug("Executing %d post-speak hooks for scene: %s", len(hooks), ctx.scene_id)

    for hook in hooks:
        try:
            await asyncio.wait_for(
                hook.execute(ctx),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning(
                "Post-speak hook timed out after %.1fs: %s.%s",
                timeout,
                ctx.scene_id,
                hook.__class__.__name__,
            )
        except Exception as e:
            logger.error(
                "Post-speak hook failed: %s.%s - %s",
                ctx.scene_id,
                hook.__class__.__name__,
                e,
            )

    return ctx


def clear_hooks(scene_id: str | None = None) -> None:
    """
    Clear registered hooks.

    Args:
        scene_id: Specific scene to clear (None = clear all)
    """
    if scene_id:
        _hook_registry.pop(scene_id, None)
        logger.debug("Cleared hooks for scene: %s", scene_id)
    else:
        _hook_registry.clear()
        logger.debug("Cleared all post-speak hooks")
