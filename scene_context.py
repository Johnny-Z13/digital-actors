"""
Scene Context - Unified API for scene authors.

Bundles query system, RAG facts, state management, and events
into a clean interface for scene handlers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from query_system import QuerySystem
    from rag_facts import RAGFactsEngine

logger = logging.getLogger(__name__)


@dataclass
class SceneContext:
    """
    Unified context API for scene handlers.

    Provides a clean interface for scene authors to:
    - Query conditions using LLM
    - Retrieve relevant facts via RAG
    - Read and update scene state
    - Trigger events

    Example:
        async def process_action(self, action, scene_state, ctx=None):
            if ctx and action == "OVERRIDE":
                # Check if player earned trust
                if await ctx.query(
                    ctx.dialogue_history,
                    "Player has built rapport",
                    latch=True
                ):
                    return ActionResult(success=True, ...)
    """

    scene_id: str
    session_id: str = ""
    query_system: QuerySystem | None = None
    rag_engine: RAGFactsEngine | None = None
    scene_state: dict[str, Any] = field(default_factory=dict)
    dialogue_history: str = ""

    # Internal: callbacks for state/event handling
    _state_updates: dict[str, Any] = field(default_factory=dict)
    _triggered_events: list[str] = field(default_factory=list)

    async def query(
        self,
        text: str,
        condition: str,
        latch: bool = False,
        context: str = "",
    ) -> bool:
        """
        Evaluate a condition using LLM.

        Uses Claude Haiku for fast evaluation with caching.

        Args:
            text: Text to evaluate against (e.g., dialogue history)
            condition: Natural language condition to check
            latch: If True, once True it stays True for session
            context: Additional context for evaluation

        Returns:
            bool: Whether the condition is met

        Example:
            if await ctx.query(
                ctx.dialogue_history,
                "Player has mentioned their family",
                latch=True
            ):
                ctx.update_state("family_mentioned", True)
        """
        if self.query_system is None:
            logger.warning("Query attempted but QuerySystem not available")
            return False

        return await self.query_system.query(
            input_text=text,
            query_text=condition,
            latch=latch,
            context=context,
            session_id=self.session_id,
        )

    def get_relevant_facts(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[str]:
        """
        Retrieve facts relevant to a query.

        Uses sentence embeddings when available, keyword fallback otherwise.

        Args:
            query: Query string to match against
            top_k: Maximum number of facts to return

        Returns:
            List of relevant fact strings

        Example:
            facts = ctx.get_relevant_facts("reactor cooling system")
            # Returns: ["The reactor uses VM-5 pressurized water design...", ...]
        """
        if self.rag_engine is None:
            logger.debug("RAG retrieval attempted but engine not available")
            return []

        result = self.rag_engine.retrieve(
            query=query,
            scene_id=self.scene_id,
            top_k=top_k,
        )
        return result.facts

    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get a scene state value.

        Args:
            key: State variable name
            default: Value to return if key not found

        Returns:
            Current value or default
        """
        return self.scene_state.get(key, default)

    def update_state(self, key: str, value: Any) -> None:
        """
        Queue a state update.

        Updates are collected and applied by the caller after
        action processing completes.

        For numeric values, this sets the absolute value.
        Use ActionResult.state_changes for deltas.

        Args:
            key: State variable name
            value: New value
        """
        self._state_updates[key] = value
        logger.debug("Queued state update: %s = %s", key, value)

    def trigger_event(self, event_name: str) -> None:
        """
        Trigger a named event.

        Events are collected and dispatched by the caller after
        action processing completes.

        Common events:
        - "alarm_sound" - Play alarm SFX
        - "music_change" - Change background music
        - "flash_warning" - Flash UI warning

        Args:
            event_name: Event identifier
        """
        if event_name not in self._triggered_events:
            self._triggered_events.append(event_name)
            logger.debug("Triggered event: %s", event_name)

    def get_state_updates(self) -> dict[str, Any]:
        """Get all queued state updates."""
        return self._state_updates.copy()

    def get_triggered_events(self) -> list[str]:
        """Get all triggered events."""
        return self._triggered_events.copy()

    def clear_pending(self) -> None:
        """Clear pending state updates and events."""
        self._state_updates.clear()
        self._triggered_events.clear()


def create_scene_context(
    scene_id: str,
    session_id: str = "",
    query_system: QuerySystem | None = None,
    rag_engine: RAGFactsEngine | None = None,
    scene_state: dict[str, Any] | None = None,
    dialogue_history: str = "",
) -> SceneContext:
    """
    Factory function to create a SceneContext.

    Args:
        scene_id: Scene identifier
        session_id: Session identifier for latch isolation
        query_system: QuerySystem instance
        rag_engine: RAGFactsEngine instance
        scene_state: Current scene state dict
        dialogue_history: Accumulated dialogue

    Returns:
        Configured SceneContext instance
    """
    return SceneContext(
        scene_id=scene_id,
        session_id=session_id,
        query_system=query_system,
        rag_engine=rag_engine,
        scene_state=scene_state or {},
        dialogue_history=dialogue_history,
    )
