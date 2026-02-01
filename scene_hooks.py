"""
Standardized Scene Hooks - Data-Driven Post-Speak Processing.

Provides a declarative, configuration-based hook system that works
identically across all scenes. Scene authors define hooks in scene
config rather than writing custom handler code.

Usage in scene definition:
    hooks=[
        SceneHook(
            name="slip_detected",
            query="Speaker accidentally revealed they were present",
            latch=True,
            on_true={"state": {"contradictions": "+1"}, "event": "slip_detected"}
        ),
    ]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from post_speak_hooks import PostSpeakContext, PostSpeakHook, register_hook

logger = logging.getLogger(__name__)


@dataclass
class SceneHookAction:
    """
    Action to take when a hook condition is met.

    Attributes:
        state_updates: Dict of state changes. Values can be:
            - Absolute: {"trust": 50}
            - Delta with "+": {"contradictions": "+1"}
            - Delta with "-": {"trust": "-10"}
        event: Optional event name to trigger
        milestone: Optional milestone to record
    """

    state_updates: dict[str, Any] = field(default_factory=dict)
    event: str | None = None
    milestone: str | None = None


@dataclass
class SceneHookConfig:
    """
    Configuration for a single scene hook.

    Attributes:
        name: Unique identifier for this hook
        query: Natural language condition to evaluate against NPC response
        latch: If True, once triggered it won't re-trigger
        on_true: Action to take when query evaluates to True
        on_false: Optional action when query evaluates to False
        enabled: Whether this hook is active
    """

    name: str
    query: str
    latch: bool = False
    on_true: SceneHookAction = field(default_factory=SceneHookAction)
    on_false: SceneHookAction | None = None
    enabled: bool = True


class StandardSceneHook(PostSpeakHook):
    """
    Generic, data-driven post-speak hook.

    Reads hook configurations from scene and evaluates them uniformly.
    No custom code needed per scene - just declare hooks in config.
    """

    def __init__(self, scene_id: str, hooks: list[SceneHookConfig]):
        self._scene_id = scene_id
        self._hooks = hooks
        self._triggered: set[str] = set()  # Latched hooks that have fired

    @property
    def scene_id(self) -> str:
        return self._scene_id

    async def execute(self, ctx: PostSpeakContext) -> None:
        """Execute all configured hooks for this scene."""
        for hook in self._hooks:
            if not hook.enabled:
                continue

            # Skip latched hooks that already fired
            if hook.latch and hook.name in self._triggered:
                continue

            # Evaluate the query
            try:
                result = await ctx.query(
                    ctx.llm_response,
                    hook.query,
                    latch=False,  # We handle latching ourselves
                )
            except Exception as e:
                logger.warning("Hook %s query failed: %s", hook.name, e)
                continue

            # Apply appropriate action
            action = hook.on_true if result else hook.on_false
            if action:
                self._apply_action(ctx, action, hook.name)

            # Mark as triggered if latched and true
            if result and hook.latch:
                self._triggered.add(hook.name)
                logger.debug("Hook %s latched (won't fire again)", hook.name)

    def _apply_action(
        self,
        ctx: PostSpeakContext,
        action: SceneHookAction,
        hook_name: str,
    ) -> None:
        """Apply a hook action to the context."""
        # Apply state updates
        for key, value in action.state_updates.items():
            if isinstance(value, str):
                # Handle delta syntax: "+1", "-10"
                if value.startswith("+"):
                    delta = float(value[1:])
                    current = ctx.scene_state.get(key, 0)
                    ctx.update_state(key, current + delta)
                elif value.startswith("-"):
                    delta = float(value[1:])
                    current = ctx.scene_state.get(key, 0)
                    ctx.update_state(key, current - delta)
                else:
                    # Try to parse as number, else use as string
                    try:
                        ctx.update_state(key, float(value))
                    except ValueError:
                        ctx.update_state(key, value)
            else:
                ctx.update_state(key, value)

        # Trigger event
        if action.event:
            ctx.trigger_event(action.event)

        logger.debug(
            "Hook %s applied: state=%s, event=%s", hook_name, action.state_updates, action.event
        )

    def reset(self) -> None:
        """Reset latched hooks (e.g., on scene restart)."""
        self._triggered.clear()


# =============================================================================
# Hook Registry - Automatically creates hooks from scene config
# =============================================================================

_registered_scenes: set[str] = set()


def register_scene_hooks(scene_id: str, hooks_config: list[dict[str, Any]]) -> None:
    """
    Register hooks for a scene from configuration.

    Called automatically when a scene with hooks is loaded.

    Args:
        scene_id: Scene identifier
        hooks_config: List of hook configuration dicts
    """
    if scene_id in _registered_scenes:
        return  # Already registered

    if not hooks_config:
        return

    # Convert config dicts to SceneHookConfig objects
    hooks = []
    for cfg in hooks_config:
        on_true_cfg = cfg.get("on_true", {})
        on_true = SceneHookAction(
            state_updates=on_true_cfg.get("state", {}),
            event=on_true_cfg.get("event"),
            milestone=on_true_cfg.get("milestone"),
        )

        on_false = None
        if "on_false" in cfg:
            on_false_cfg = cfg["on_false"]
            on_false = SceneHookAction(
                state_updates=on_false_cfg.get("state", {}),
                event=on_false_cfg.get("event"),
                milestone=on_false_cfg.get("milestone"),
            )

        hooks.append(
            SceneHookConfig(
                name=cfg.get("name", f"hook_{len(hooks)}"),
                query=cfg["query"],
                latch=cfg.get("latch", False),
                on_true=on_true,
                on_false=on_false,
                enabled=cfg.get("enabled", True),
            )
        )

    # Create and register the hook
    hook = StandardSceneHook(scene_id, hooks)
    register_hook(hook)
    _registered_scenes.add(scene_id)

    logger.info("Registered %d hooks for scene: %s", len(hooks), scene_id)


def create_standard_hooks(
    slip_detection: bool = False,
    emotional_tracking: bool = False,
    name_mentions: list[str] | None = None,
    location_mentions: list[str] | None = None,
    custom_hooks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Factory function to create standard hook configurations.

    Provides common hook patterns that can be mixed and matched.

    Args:
        slip_detection: Add hooks for detecting verbal slips/contradictions
        emotional_tracking: Add hooks for tracking emotional moments
        name_mentions: List of character names to track when mentioned
        location_mentions: List of locations to track when mentioned
        custom_hooks: Additional custom hook configurations

    Returns:
        List of hook configuration dicts ready for scene definition
    """
    hooks: list[dict[str, Any]] = []

    # Slip detection - catches "when I..." type reveals
    if slip_detection:
        hooks.append(
            {
                "name": "presence_slip",
                "query": "Speaker accidentally revealed they were present at the scene or event, such as saying 'when I' then correcting themselves",
                "latch": True,
                "on_true": {
                    "state": {"contradictions": "+1"},
                    "event": "slip_detected",
                },
            }
        )
        hooks.append(
            {
                "name": "obvious_lie",
                "query": "Speaker gave an obviously weak excuse or contradicted something they said earlier",
                "latch": False,
                "on_true": {
                    "state": {"contradictions": "+1"},
                },
            }
        )

    # Emotional tracking
    if emotional_tracking:
        hooks.append(
            {
                "name": "emotional_moment",
                "query": "Speaker showed strong emotion like voice breaking, crying, long pauses, or confessing something painful",
                "latch": False,
                "on_true": {
                    "state": {"emotional_bond": "+5"},
                    "event": "emotional_moment",
                },
            }
        )
        hooks.append(
            {
                "name": "vulnerability_shown",
                "query": "Speaker revealed something personal or vulnerable about themselves",
                "latch": False,
                "on_true": {
                    "state": {"emotional_bond": "+3"},
                },
            }
        )

    # Name mention tracking
    if name_mentions:
        for name in name_mentions:
            hooks.append(
                {
                    "name": f"mentioned_{name.lower().replace(' ', '_')}",
                    "query": f"Speaker mentioned someone named {name}",
                    "latch": True,
                    "on_true": {
                        "state": {f"{name.lower().replace(' ', '_')}_mentioned": True},
                        "event": "clue_unlocked",
                    },
                }
            )

    # Location mention tracking
    if location_mentions:
        for location in location_mentions:
            hooks.append(
                {
                    "name": f"mentioned_{location.lower().replace(' ', '_')}",
                    "query": f"Speaker mentioned {location} or a place matching that description",
                    "latch": True,
                    "on_true": {
                        "state": {f"{location.lower().replace(' ', '_')}_mentioned": True},
                    },
                }
            )

    # Add any custom hooks
    if custom_hooks:
        hooks.extend(custom_hooks)

    return hooks
