"""
Session Orchestrator Module

Coordinates all session components (connection, dialogue, state, response handling).
This is the main entry point that replaces the monolithic ChatSession class.

This orchestrator delegates responsibilities to:
- ResponseHandler: TTS and response delivery
- GameStateManager: State tracking and game logic
- DialogueEngine: Prompt building and LLM calls
- Connection management: Message routing and WebSocket handling
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from typing import TYPE_CHECKING, Any

from llm_prompt_core.types import SceneData
from logging_config import StructuredLoggerAdapter
from player_memory import PlayerMemory
from query_system import get_query_system
from rag_facts import get_rag_engine
from response_queue import ResponsePriority
from scene_hooks import register_scene_hooks
from sessions.dialogue_engine import DialogueEngine
from sessions.game_state_manager import GameStateManager
from sessions.response_handler import ResponseHandler
from tts_elevenlabs import get_tts_manager
from world_director import WorldDirector

if TYPE_CHECKING:
    from aiohttp import web

logger = logging.getLogger(__name__)

# Global session tracking
ACTIVE_SESSIONS = {}


class SessionOrchestrator:
    """
    Coordinates all components of a chat session.

    This replaces the monolithic ChatSession class by delegating to focused components.
    """

    def __init__(
        self,
        ws: web.WebSocketResponse,
        character_id: str = "clippy",
        scene_id: str = "welcome",
        player_id: str | None = None,
        characters_registry: dict[str, Any] = None,
        scenes_registry: dict[str, Any] = None,
        scene_character_map: dict[str, str] = None,
    ) -> None:
        """
        Initialize the session orchestrator.

        Args:
            ws: WebSocket connection
            character_id: Initial character ID
            scene_id: Initial scene ID
            player_id: Optional player ID for memory tracking
            characters_registry: Character configuration registry
            scenes_registry: Scene configuration registry
            scene_character_map: Scene to character mapping
        """
        self.ws = ws
        self.session_id = secrets.token_urlsafe(32)

        # Auto-select: scene determines character (locked pairing)
        if scene_character_map and scene_id in scene_character_map:
            expected_char = scene_character_map[scene_id]
            if character_id != expected_char:
                character_id = expected_char

        self.character_id = character_id
        self.scene_id = scene_id

        # Create structured logger with session context
        self.logger = StructuredLoggerAdapter(
            logger,
            {
                "session_id": self.session_id,
                "character": self.character_id,
                "scene": self.scene_id,
            },
        )
        self.logger.info_event(
            "session_created", "Generated session token", session_token_preview=self.session_id[:8]
        )

        # Load configurations
        self.character_config = characters_registry.get(character_id, characters_registry["custom"])
        self.scene_config = scenes_registry.get(scene_id, scenes_registry["introduction"])

        # Player memory system
        self.player_id = player_id or f"player_{id(ws)}"
        self.player_memory = PlayerMemory(self.player_id)
        self.logger.info_event(
            "player_memory_loaded", "Loaded player memory", player_id=self.player_id
        )

        # World Director (dungeon master)
        self.world_director = WorldDirector()
        self.director_npc_modifier = ""
        self.pending_director_guidance: dict[str, Any] | None = None

        # Query System (LLM-based condition evaluation)
        from constants import LLM_MAX_TOKENS_QUERY, LLM_TEMPERATURE_QUERY
        from llm_prompt_core.models.anthropic import ClaudeHaikuModel

        query_model = ClaudeHaikuModel(
            temperature=LLM_TEMPERATURE_QUERY,
            max_tokens=LLM_MAX_TOKENS_QUERY,
        )
        self.query_system = get_query_system(model=query_model)
        self.logger.info_event("query_system_initialized", "Query System initialized")

        # RAG Facts Engine
        self.rag_engine = get_rag_engine()
        scene_facts = self.scene_config.get("facts", [])
        if scene_facts:
            self.rag_engine.set_facts(scene_id, scene_facts)
            self.logger.info_event(
                "rag_facts_indexed", "Indexed RAG facts for scene", facts_count=len(scene_facts)
            )

        # Register scene hooks
        scene_hooks = self.scene_config.get("hooks", [])
        if scene_hooks:
            register_scene_hooks(scene_id, scene_hooks)

        # Create scene data for dialogue
        self.scene_data = self._create_scene_data()

        # Initialize components
        tts_manager = get_tts_manager()

        self.response_handler = ResponseHandler(
            ws=ws,
            tts_manager=tts_manager,
            character_config=self.character_config,
            logger_adapter=self.logger,
        )

        self.game_state_manager = GameStateManager(
            ws=ws,
            scene_config=self.scene_config,
            scene_id=scene_id,
            logger_adapter=self.logger,
            player_memory=self.player_memory,
        )

        self.dialogue_engine = DialogueEngine(
            character_config=self.character_config,
            scene_config=self.scene_config,
            scene_data=self.scene_data,
            scene_id=scene_id,
            player_memory=self.player_memory,
            rag_engine=self.rag_engine,
            logger_adapter=self.logger,
        )

        # Set response handler context
        self.response_handler.set_context(
            character_id=character_id,
            scene_id=scene_id,
            scene_phase=self.game_state_manager.scene_state.get("phase"),
        )

        # Track if NPC is currently responding
        self.npc_responding = False
        self.opening_speech_playing = False

        # Response sequence tracking
        self.response_sequence = 0
        self.current_response_id = 0

        # Background task tracking
        self._background_tasks: set[asyncio.Task] = set()

        # Start tracking this scene attempt
        self.player_memory.start_scene(
            scene_id=self.scene_id,
            character_id=self.character_id,
            initial_state=self.game_state_manager.scene_state.copy(),
        )

        # Apply difficulty adjustments from World Director
        difficulty = self.world_director.get_difficulty_adjustment(
            self.player_memory, self.scene_id
        )
        if "oxygen_bonus" in difficulty and "oxygen" in self.game_state_manager.scene_state:
            self.game_state_manager.scene_state["oxygen"] += difficulty["oxygen_bonus"]
            logger.info(
                "Director adjusted oxygen: %+d (player skill-based)", difficulty["oxygen_bonus"]
            )

        self.difficulty_settings = difficulty

    def _create_scene_data(self) -> SceneData:
        """Create a SceneData object from character and scene configs."""
        return SceneData(
            scene_name=self.scene_id,
            scene_description=self.scene_config["description"],
            previous_scenes_description="",
            steer_back_instructions="Stay in character and keep responses conversational.",
            scene_supplement="",
            back_story=self.character_config["back_story"],
            dialogue_instruction_prefix=self.character_config["instruction_prefix"],
            summary_instruction_prefix="You are summarizing dialogue.",
            merge_instruction_prefix="You are merging summaries.",
            opening_speech=self.scene_config["opening_speech"],
            queries=[],
            actors=[self.character_config["name"], "Player"],
        )

    def _create_tracked_task(self, coro, name: str = "unknown") -> asyncio.Task:
        """
        Create a tracked background task that won't silently fail.

        Args:
            coro: Coroutine to run as background task
            name: Descriptive name for logging

        Returns:
            The created Task object
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)

        def _task_done_callback(t: asyncio.Task) -> None:
            self._background_tasks.discard(t)
            try:
                t.result()
            except asyncio.CancelledError:
                logger.debug(f"[SessionOrchestrator] Background task '{name}' was cancelled")
            except Exception as e:
                logger.error(
                    f"[SessionOrchestrator] Background task '{name}' failed with error: {e}",
                    exc_info=True,
                )

        task.add_done_callback(_task_done_callback)
        logger.debug(f"[SessionOrchestrator] Created tracked task: {name}")
        return task

    async def _cleanup_background_tasks(self) -> None:
        """Cancel all background tasks and wait for them to complete."""
        if not self._background_tasks:
            return

        logger.info(f"[SessionOrchestrator] Cancelling {len(self._background_tasks)} background tasks...")

        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
        logger.info("[SessionOrchestrator] All background tasks cleaned up")

    def start_state_update_loop(self) -> None:
        """Start the state update loop if scene has dynamic state variables."""
        self.game_state_manager.start_state_update_loop(self._create_tracked_task)

    def stop_state_update_loop(self) -> None:
        """Stop the state update loop."""
        self.game_state_manager.stop_state_update_loop()

    @staticmethod
    def validate_session(session_id: str | None) -> bool:
        """
        Validate that a session ID is valid and active.

        Args:
            session_id: The session ID to validate

        Returns:
            True if the session is valid and active, False otherwise
        """
        if not session_id:
            return False
        return session_id in ACTIVE_SESSIONS

    # Delegate to components
    async def send_character_response(self, content: str, **kwargs) -> None:
        """Send a character response (delegates to ResponseHandler)."""
        # Update context before sending
        self.response_handler.set_context(
            character_id=self.character_id,
            scene_id=self.scene_id,
            scene_phase=self.game_state_manager.scene_state.get("phase"),
        )
        await self.response_handler.send_character_response(content, **kwargs)

    async def send_character_response_immediate(self, content: str, **kwargs) -> None:
        """Send an immediate critical response (delegates to ResponseHandler)."""
        await self.response_handler.send_character_response_immediate(content, **kwargs)

    # Expose necessary attributes for compatibility
    @property
    def scene_state(self) -> dict[str, Any]:
        """Get current scene state."""
        return self.game_state_manager.scene_state

    @property
    def game_over(self) -> bool:
        """Check if game is over."""
        return self.game_state_manager.game_over

    @property
    def dialogue_history(self) -> str:
        """Get dialogue history."""
        return self.dialogue_engine.dialogue_history

    def check_game_over_conditions(self) -> None:
        """Check game over conditions."""
        self.game_state_manager.check_game_over_conditions()
