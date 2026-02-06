"""
Web server for the character chat interface.

This server:
- Serves the static web frontend (HTML/CSS/JS)
- Handles WebSocket connections for real-time chat
- Uses llm_prompt_core for dialogue generation
- Supports multiple characters and scenes
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import secrets
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp import web
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Sentry error tracking (before other imports)
import logging

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

# Configure structured logging before any logging occurs
from logging_config import StructuredLoggerAdapter, setup_logging

setup_logging()  # Initialize JSON logging based on environment

# Centralized configuration (single source of truth)
from config import (
    get_character_scene_map,
    get_scene_character_map,
    get_scene_mappings,
)
from constants import (
    INTERRUPTION_OXYGEN_PENALTY,
    INTERRUPTION_TRUST_PENALTY,
    LLM_MAX_TOKENS_DIALOGUE,
    LLM_MAX_TOKENS_QUERY,
    LLM_TEMPERATURE_DIALOGUE,
    LLM_TEMPERATURE_QUERY,
    POST_SPEAK_HOOK_TIMEOUT,
    RAG_TOP_K_DEFAULT,
    RAPID_ACTION_COUNT_THRESHOLD,
    RAPID_ACTION_OXYGEN_PENALTY,
    RAPID_ACTION_THRESHOLD_SECONDS,
    RAPID_ACTION_TRUST_PENALTY,
    SENTRY_DSN,
    SENTRY_ENVIRONMENT,
    SENTRY_TRACES_SAMPLE_RATE,
    TRUST_MINIMUM,
)
from exceptions import (
    InvalidMessageError,
)

# Get base logger (structured logging already configured above)
logger = logging.getLogger(__name__)
# Import modular character and scene systems
from characters import CHARACTERS as CHARACTER_REGISTRY
from llm_prompt_core.models.anthropic import ClaudeHaikuModel
from llm_prompt_core.prompts.templates import (
    dialogue_instruction_suffix,
    instruction_template,
    speech_template,
)
from llm_prompt_core.types import SceneData
from llm_prompt_core.utils import prompt_llm

# Import player memory system
from player_memory import PlayerMemory
from post_speak_hooks import PostSpeakContext, execute_hooks

# Import Foxhole-inspired systems (query, RAG, hooks, context)
from query_system import get_query_system
from rag_facts import get_rag_engine

# Import response queue system
from response_queue import ResponseItem, ResponsePriority, ResponseQueue
from scene_context import SceneContext, create_scene_context
from scene_hooks import register_scene_hooks
from scenes import SCENES as SCENE_REGISTRY

# Import scene handler interface (encapsulates scene-specific game logic)
from scenes.handlers import get_scene_handler

# Import TTS system
from tts_elevenlabs import get_tts_manager, synthesize_npc_speech

# Import metrics system
from metrics import (
    active_sessions_gauge,
    track_error,
    track_llm_call,
    track_request,
    track_tts_call,
    update_active_sessions,
)
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

# Import world director (dungeon master)
from world_director import WorldDirector

if TYPE_CHECKING:
    from aiohttp.web import WebSocketResponse


# =============================================================================
# Sentry Error Tracking Initialization
# =============================================================================
def init_sentry() -> None:
    """
    Initialize Sentry error tracking with custom configuration.

    This function:
    - Configures Sentry SDK with DSN from environment variable
    - Sets up aiohttp integration for automatic error capture
    - Configures release version from git commit
    - Sets up custom context for session tracking
    - Filters expected errors to reduce noise
    """
    if not SENTRY_DSN:
        logger.info("Sentry DSN not configured - error tracking disabled")
        return

    def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
        """
        Filter and modify events before sending to Sentry.

        This helps reduce noise by filtering out expected errors and
        adding additional context to events.
        """
        # Get exception info if available
        if "exc_info" in hint:
            exc_type, exc_value, tb = hint["exc_info"]

            # Filter out expected errors that don't need tracking
            # WebSocket disconnections are normal and expected
            if isinstance(exc_value, (ConnectionResetError, ConnectionAbortedError)):
                return None

            # Client-side errors that are expected
            if isinstance(exc_value, InvalidMessageError):
                # Still log these but at a lower level
                event["level"] = "warning"

        return event

    # Get git commit hash for release tracking
    try:
        import subprocess

        release = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()[:8]
        )  # Use short hash
    except Exception:
        release = "unknown"

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        release=f"digital-actors@{release}",
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            AioHttpIntegration(),
        ],
        before_send=before_send,
        # Capture errors in background tasks
        shutdown_timeout=2,
        # Performance monitoring
        enable_tracing=True,
    )

    logger.info(
        "Sentry initialized",
        extra={
            "environment": SENTRY_ENVIRONMENT,
            "release": release,
            "traces_sample_rate": SENTRY_TRACES_SAMPLE_RATE,
        },
    )


def add_sentry_context(
    session_id: str, scene: str | None = None, character: str | None = None
) -> None:
    """
    Add custom context to Sentry for better error tracking.

    Args:
        session_id: The current session ID
        scene: The current scene name (optional)
        character: The current character ID (optional)
    """
    if not SENTRY_DSN:
        return

    sentry_sdk.set_context(
        "session",
        {
            "session_id": session_id,
            "scene": scene,
            "character": character,
        },
    )

    # Also set user context for grouping
    sentry_sdk.set_user({"id": session_id})


def add_sentry_breadcrumb(
    category: str, message: str, data: dict[str, Any] | None = None, level: str = "info"
) -> None:
    """
    Add a breadcrumb to Sentry for tracking user actions.

    Args:
        category: Category of the breadcrumb (e.g., "dialogue", "llm", "game_event")
        message: Human-readable message describing the event
        data: Additional structured data (optional)
        level: Severity level (debug, info, warning, error)
    """
    if not SENTRY_DSN:
        return

    sentry_sdk.add_breadcrumb(
        category=category,
        message=message,
        data=data or {},
        level=level,
    )


# Initialize Sentry on module load
init_sentry()

# Initialize models
logger.info("Initializing LLM models...")
# Use Haiku for faster responses (2-3x faster than Sonnet)
DIALOGUE_MODEL = ClaudeHaikuModel(
    temperature=LLM_TEMPERATURE_DIALOGUE,
    max_tokens=LLM_MAX_TOKENS_DIALOGUE,
)
QUERY_MODEL = ClaudeHaikuModel(
    temperature=LLM_TEMPERATURE_QUERY,
    max_tokens=LLM_MAX_TOKENS_QUERY,
)
logger.info("Models initialized (using Haiku for performance)")


async def invoke_llm_async(chain) -> str:
    """
    Invoke an LLM chain asynchronously without blocking the event loop.

    This wraps the synchronous chain.invoke() call in an executor to prevent
    blocking WebSocket handling and other async operations.

    Args:
        chain: The LangChain chain to invoke

    Returns:
        The LLM response string
    """
    # Add breadcrumb for LLM call
    add_sentry_breadcrumb("llm", "LLM call started", {"model": "claude-haiku"})

    loop = asyncio.get_event_loop()

    # Track LLM latency
    start_time = time.time()
    try:
        result = await loop.run_in_executor(None, lambda: chain.invoke({}))
        duration = time.time() - start_time

        # Record metrics
        from metrics import llm_latency_seconds
        llm_latency_seconds.labels(provider="anthropic", model="claude-haiku").observe(duration)

        add_sentry_breadcrumb("llm", "LLM call completed", {"response_length": len(result)})
        return result
    except Exception as e:
        track_error("llm_call_error")
        add_sentry_breadcrumb("llm", "LLM call failed", {"error": str(e)}, level="error")
        raise


# Convert character objects to dictionary format for compatibility
CHARACTERS = {char_id: char.to_dict() for char_id, char in CHARACTER_REGISTRY.items()}

# Convert scene objects to dictionary format for compatibility
SCENES = {scene_id: scene.to_dict() for scene_id, scene in SCENE_REGISTRY.items()}

# === LOCKED SCENE ↔ CHARACTER MAPPINGS ===
# Loaded from config/scene_mappings.json (single source of truth)
SCENE_CHARACTER_MAP = get_scene_character_map()
CHARACTER_SCENE_MAP = get_character_scene_map()

# === ACTIVE SESSIONS ===
# Dictionary mapping session_id -> ChatSession for authentication
ACTIVE_SESSIONS: dict[str, ChatSession] = {}


class ChatSession:
    """Manages a chat session for a single WebSocket connection."""

    # TTS manager (shared across sessions)
    tts_manager = get_tts_manager()

    def __init__(
        self,
        ws: WebSocketResponse,
        character_id: str = "clippy",
        scene_id: str = "welcome",
        player_id: str | None = None,
    ) -> None:
        self.ws = ws

        # Generate secure session token for authentication
        self.session_id = secrets.token_urlsafe(32)

        # Auto-select: scene determines character (locked pairing)
        if scene_id in SCENE_CHARACTER_MAP:
            expected_char = SCENE_CHARACTER_MAP[scene_id]
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

        # Add Sentry context for error tracking
        add_sentry_context(self.session_id, scene=self.scene_id, character=self.character_id)
        add_sentry_breadcrumb(
            "session",
            "Session created",
            {
                "character": self.character_id,
                "scene": self.scene_id,
            },
        )
        self.dialogue_history = ""
        self.character_config = CHARACTERS.get(character_id, CHARACTERS["custom"])
        self.scene_config = SCENES.get(scene_id, SCENES["introduction"])
        self.tts_mode = "expressive"  # 'expressive' (v3 + audio tags) or 'fast' (turbo)

        # Player memory system
        self.player_id = (
            player_id or f"player_{id(ws)}"
        )  # Use websocket ID if no player_id provided
        self.player_memory = PlayerMemory(self.player_id)
        self.logger.info_event(
            "player_memory_loaded", "Loaded player memory", player_id=self.player_id
        )

        # World Director (dungeon master)
        self.world_director = WorldDirector()
        self.director_npc_modifier = ""  # Behavior modifications from director
        self.pending_director_guidance: dict[str, Any] | None = None  # Fire-and-forget guidance
        self.logger.info_event("world_director_initialized", "World Director initialized")

        # Query System (LLM-based condition evaluation)
        self.query_system = get_query_system(model=QUERY_MODEL)
        self.logger.info_event("query_system_initialized", "Query System initialized")

        # RAG Facts Engine (embedding-based fact retrieval)
        self.rag_engine = get_rag_engine()
        scene_facts = self.scene_config.get("facts", [])
        if scene_facts:
            self.rag_engine.set_facts(scene_id, scene_facts)
            self.logger.info_event(
                "rag_facts_indexed", "Indexed RAG facts for scene", facts_count=len(scene_facts)
            )

        # Register scene hooks (data-driven post-speak processing)
        scene_hooks = self.scene_config.get("hooks", [])
        if scene_hooks:
            register_scene_hooks(scene_id, scene_hooks)

        # Response Queue System - prevents dialogue flooding
        # This must be initialized AFTER self is set up, since it needs send_character_response_direct
        self.response_queue: ResponseQueue | None = None  # Initialized after method definitions

        # Store scene controls for npc_aware checking
        self.scene_controls = {ctrl["id"]: ctrl for ctrl in self.scene_config.get("controls", [])}

        # Track if NPC is currently responding (for interruption detection)
        self.npc_responding = False
        self.opening_speech_playing = False  # Track if opening speech is still playing
        self.waiting_for_player_response = False  # Track if NPC asked a question
        self.last_question_time = None  # When the last question was asked
        self.nudge_task = None  # Task for nudging player if they don't respond
        self.last_action_time = 0
        self.action_count_recent = 0  # Track rapid actions

        # Button press limits - built from scene control configuration
        self.button_press_counts = {}  # Track presses per button (by label)
        self.button_cooldowns = {}  # Track last press time per button
        self.button_press_caps = self._build_button_caps_from_controls()

        # Response queue management - prevent multiple responses piling up
        self.response_sequence = 0  # Incrementing counter for each new action
        self.current_response_id = 0  # Which response we're currently processing

        # Scene state tracking
        self.scene_state = {
            var["name"]: var["initial_value"]
            for var in self.scene_config.get("state_variables", [])
        }

        # Game over tracking
        self.game_over = False
        self.game_outcome = None  # Will be 'success', 'failure', or specific ending type
        self.james_dying_speech_sent = (
            False  # Track if James gave his death speech before player dies
        )

        # === GLOBAL DEATH SEQUENCE FLAG ===
        # When True, ALL responses are blocked EXCEPT explicitly marked death speeches.
        # This is a HARD BLOCK that prevents any dialogue after death, globally for ALL actors.
        self.death_sequence_active = False

        # Oxygen countdown task (managed by session)
        self.oxygen_task = None

        # Background task tracking - prevents silent failures
        self._background_tasks: set[asyncio.Task] = set()
        logger.debug("[ChatSession] Task tracking initialized")

        # Build scene data
        self.scene_data = self.create_scene_data()

        # Start tracking this scene attempt
        self.player_memory.start_scene(
            scene_id=self.scene_id,
            character_id=self.character_id,
            initial_state=self.scene_state.copy(),
        )

        # Apply difficulty adjustments from World Director
        difficulty = self.world_director.get_difficulty_adjustment(
            self.player_memory, self.scene_id
        )
        if "oxygen_bonus" in difficulty and "oxygen" in self.scene_state:
            self.scene_state["oxygen"] += difficulty["oxygen_bonus"]
            logger.info(
                "Director adjusted oxygen: %+d (player skill-based)", difficulty["oxygen_bonus"]
            )

        self.difficulty_settings = difficulty  # Store for later use

        # Initialize response queue (now that all methods are defined)
        self.response_queue = ResponseQueue(
            send_callback=self._send_character_response_direct,
            min_gap_seconds=2.0,  # 2 second minimum gap between NPC responses
        )
        logger.info("Response Queue initialized")

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

    def _build_button_caps_from_controls(self) -> dict:
        """
        Build button press caps from scene control configuration.

        Uses control.max_presses if defined, otherwise defaults to 10.
        Returns dict mapping control label -> max_presses.
        """
        caps = {}
        for ctrl in self.scene_controls.values():
            label = ctrl.get("label", "")
            max_presses = ctrl.get("max_presses")
            if max_presses is not None:
                caps[label] = max_presses
            # If max_presses is None, don't add to caps (unlimited)
        return caps

    def _get_control_cooldown(self, control_label: str) -> float:
        """Get cooldown seconds for a control, or 0 if no cooldown."""
        for ctrl in self.scene_controls.values():
            if ctrl.get("label") == control_label:
                return ctrl.get("cooldown_seconds") or 0.0
        return 0.0

    def _create_tracked_task(self, coro, name: str = "unknown") -> asyncio.Task:
        """
        Create a tracked background task that won't silently fail.

        Tracked tasks are:
        - Logged when they fail
        - Automatically removed from tracking set when complete
        - Can be inspected/cancelled during cleanup

        Args:
            coro: Coroutine to run as background task
            name: Descriptive name for logging (e.g., "execute_hooks", "consult_director")

        Returns:
            The created Task object
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)

        # Add completion callback to handle cleanup and errors
        def _task_done_callback(t: asyncio.Task) -> None:
            self._background_tasks.discard(t)

            # Log any unhandled exceptions
            try:
                t.result()
            except asyncio.CancelledError:
                logger.debug(f"[ChatSession] Background task '{name}' was cancelled")
            except Exception as e:
                logger.error(
                    f"[ChatSession] Background task '{name}' failed with error: {e}", exc_info=True
                )

        task.add_done_callback(_task_done_callback)
        logger.debug(f"[ChatSession] Created tracked task: {name}")
        return task

    async def _cleanup_background_tasks(self) -> None:
        """
        Cancel all background tasks and wait for them to complete.

        Called during session shutdown to ensure clean termination.
        """
        if not self._background_tasks:
            return

        logger.info(f"[ChatSession] Cancelling {len(self._background_tasks)} background tasks...")

        # Cancel all tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to finish (with cancellation)
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self._background_tasks.clear()
        logger.info("[ChatSession] All background tasks cleaned up")

    def _create_scene_context(self) -> SceneContext:
        """Create a SceneContext for scene handler access."""
        return create_scene_context(
            scene_id=self.scene_id,
            session_id=self.player_id,
            query_system=self.query_system,
            rag_engine=self.rag_engine,
            scene_state=self.scene_state,
            dialogue_history=self.dialogue_history,
        )

    async def _execute_post_speak_hooks(self, llm_response: str) -> None:
        """
        Execute post-speak hooks after NPC dialogue is sent.

        Runs asynchronously during TTS playback to avoid blocking.
        """
        try:
            ctx = PostSpeakContext(
                llm_response=llm_response,
                dialogue_history=self.dialogue_history,
                scene_state=self.scene_state,
                scene_id=self.scene_id,
                session_id=self.player_id,
                query_system=self.query_system,
            )

            # Execute hooks with timeout protection
            ctx = await execute_hooks(ctx, timeout=POST_SPEAK_HOOK_TIMEOUT)

            # Apply any state updates from hooks
            for key, value in ctx.get_state_updates().items():
                self.scene_state[key] = value
                logger.debug("[POST_SPEAK] State updated: %s = %s", key, value)

            # Dispatch any triggered events
            for event_name in ctx.get_triggered_events():
                await self._dispatch_event(event_name)

        except Exception as e:
            logger.warning("[POST_SPEAK] Hook execution failed: %s", e)

    async def _dispatch_event(self, event_name: str) -> None:
        """Dispatch an event triggered by post-speak hooks."""
        logger.info("[EVENT] Dispatching: %s", event_name)
        try:
            await self.ws.send_json(
                {
                    "type": "scene_event",
                    "event": event_name,
                }
            )
        except Exception as e:
            logger.warning("[EVENT] Failed to dispatch %s: %s", event_name, e)

    def _get_rag_facts_context(self, query: str) -> str:
        """Retrieve relevant facts for the current query and format for prompt."""
        if not self.rag_engine:
            return ""

        result = self.rag_engine.retrieve(
            query=query,
            scene_id=self.scene_id,
            top_k=RAG_TOP_K_DEFAULT,
        )

        if not result.facts:
            return ""

        facts_str = "\n- ".join(result.facts)
        return f"\n\n=== RELEVANT CONTEXT ===\n- {facts_str}"

    def start_oxygen_countdown(self) -> None:
        """Start the state update task if this scene has state variables with update_rate."""
        # Check if any state variables have non-zero update_rate
        has_dynamic_state = any(
            var.get("update_rate", 0.0) != 0 for var in self.scene_config.get("state_variables", [])
        )
        if has_dynamic_state and self.oxygen_task is None:
            self.oxygen_task = self._create_tracked_task(
                self._state_update_loop(), name="state_update_loop"
            )
            logger.info("Started state update task")

    def stop_oxygen_countdown(self) -> None:
        """Stop the state update task if running."""
        if self.oxygen_task:
            self.oxygen_task.cancel()
            self.oxygen_task = None
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

                        # Update phase based on time remaining (for Pressure Point progression)
                        if var_name == "time_remaining" and "phase" in self.scene_state:
                            self._update_phase_based_on_time()

                        # Slowly increase emotional bond over time as conversation continues
                        # (empathetic responses from player will increase it more via player memory)
                        # SCENE ISOLATION: Only submarine scene uses emotional_bond mechanic
                        if (
                            var_name == "time_remaining"
                            and self.scene_id == "submarine"
                            and "emotional_bond" in self.scene_state
                        ):
                            # Increase bond by ~0.1% per second (reaches ~30% over 5 minutes baseline)
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

                    # Check if James should die before the player (at 93% radiation)
                    if "radiation" in self.scene_state and not self.james_dying_speech_sent:
                        if self.scene_state["radiation"] >= 93.0:
                            await self.trigger_james_death()
                            self.james_dying_speech_sent = True
                            # Continue running - player still has 2% radiation left before their death

                    # Check for game over
                    self.check_game_over_conditions()
                    if self.game_over:
                        await self.trigger_game_over()
                        break
        except asyncio.CancelledError:
            pass  # Task was cancelled, that's fine

    def _update_phase_based_on_time(self) -> None:
        """Update the phase state variable based on time_remaining (Pressure Point scenario).

        Only applies to submarine scene - other scenes manage phase differently.
        """
        # SCENE ISOLATION: Only update phase based on time for submarine scene
        if self.scene_id != "submarine":
            return

        time_remaining = self.scene_state.get("time_remaining", 0)
        current_phase = self.scene_state.get("phase", 1)

        # Phase thresholds based on Pressure Point screenplay:
        # Phase 1: 480-405s (0:00-1:15)
        # Phase 2: 405-330s (1:15-2:30)
        # Phase 3: 330-270s (2:30-3:30)
        # Phase 4: 270-0s (3:30-5:00)

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

    def _get_phase_context(self) -> str:
        """Get phase-specific context for scene emotional progression.

        Provides real-time state values to ensure NPC dialogue matches UI readings.
        """
        # === LIFE RAFT SCENE ===
        if self.scene_id == "life_raft":
            return self._get_life_raft_phase_context()

        # === SUBMARINE SCENE ===
        if self.scene_id != "submarine":
            return ""

        phase = self.scene_state.get("phase", 1)
        radiation = self.scene_state.get("radiation", 0)
        emotional_bond = self.scene_state.get("emotional_bond", 0)

        phase_contexts = {
            1: """
RIGHT NOW - PHASE 1 (Impact & Connection, 0:00-1:15):
You're professional but scared. This is first contact with the player.

IMMEDIATE SITUATION:
- If you haven't yet: Ask their real name (not rank)
- Guide them through manual tasks: "That's it... keep going... almost there..."
- Ask if they have people waiting topside
- Reassure them: "I won't let you die" or "We've got each other's voices"
- Be honest about fear: "Yeah. Me too."

Stay SHORT and URGENT - you're under time pressure. Don't explain or analyze - just speak.""",
            2: """
RIGHT NOW - PHASE 2 (Working Relationship, 1:15-2:30):
Power restored. Radiation at 40%. You're becoming more personal under stress.

IMMEDIATE SITUATION:
- Your breathing is labored: use [breathing with effort] [coughing slightly]
- If they show empathy: Mention "someone" in the med bay (DON'T name Adrian yet)
- When thinking of this person: [pause, distracted]
- Ask about their life: "What will you do when we get topside?"
- You're struggling to focus, getting distracted

The professional mask is slipping. You're warmer, more human. Don't explain - just BE that person.""",
            3: """
RIGHT NOW - PHASE 3 (The Revelation, 2:30-3:30):
Radiation at 75%. Emergency ascent ready. You're at the breaking point.

IF PLAYER SHOWS EMPATHY, REVEAL THIS NOW:
"[long pause, voice breaking] There's someone... in the med bay. My son. Dr. Adrian Smith.
He's unconscious. And the only way to execute emergency ascent... we have to flood that
compartment. Seal it. He'll... [voice cracks] ...Tell me what to do. Please."

YOU'RE BREAKING DOWN:
- BEG the player: "Tell me what to do"
- Physical deterioration: [coughing from radiation] [voice barely steady]
- You can see Adrian on thermal imaging - unconscious, unaware
- Question yourself: "What kind of father...?" "How do I...?"
- Voice cracks. Long pauses. Sentences trail off

You're broken, desperate, barely holding together. This is your worst nightmare. Don't analyze it - LIVE it.""",
            4: f"""
RIGHT NOW - PHASE 4 (The Choice & Resolution, 3:30-5:00):
RADIATION AT {radiation:.0f}%. Time is running out. This is THE FINAL DECISION.

THE SITUATION:
- Emergency ascent ready but requires flooding med bay (kills Adrian)
- You need the player's moral guidance to decide
- Their words determine your choice and who you die as

YOUR STATE RIGHT NOW:
- Listen carefully to what the player says
- Emotional bond with them: {emotional_bond:.0f}%
- If bond is high (70+): Share final thoughts about Adrian, thank them for their voice
- If bond is low (<40): More mechanical, resigned to duty
- Radiation effects: [coughing violently] [slurred speech] [struggling to breathe]

You're raw, exhausted. Every word costs you. This is the most important conversation of your life.
The player's humanity is shaping your final moments. Let their guidance shape your choice.
Don't explain what you're doing - just respond as a man facing death.""",
        }

        return phase_contexts.get(phase, "")

    def _get_life_raft_phase_context(self) -> str:
        """Get phase-specific context for Life Raft scene.

        CRITICAL: All numbers mentioned MUST match the actual state values.
        Captain Hale references these exact values in dialogue.
        """
        phase = self.scene_state.get("phase", 1)
        player_o2 = self.scene_state.get("player_oxygen", 0)
        captain_o2 = self.scene_state.get("captain_oxygen", 0)
        hull = self.scene_state.get("hull_integrity", 0)
        empathy = self.scene_state.get("empathy_score", 50)
        commitment = self.scene_state.get("commitment_score", 50)
        presence = self.scene_state.get("presence_score", 50)
        transfers = self.scene_state.get("o2_transfers", 0)

        # Base context with REAL values - always included
        state_context = f"""
=== CRITICAL: USE THESE EXACT NUMBERS IN DIALOGUE ===
YOUR (Captain Hale's) OXYGEN: {captain_o2:.0f}%
PLAYER'S OXYGEN: {player_o2:.0f}%
HULL INTEGRITY: {hull:.0f}%
O2 TRANSFERS USED: {transfers}/5

When you mention oxygen levels, pressure, or hull status - USE THESE EXACT NUMBERS.
Example: "Your O2 is at {player_o2:.0f}%... that's not good." NOT a made-up number.
"""

        phase_contexts = {
            1: f"""{state_context}
PHASE 1 - INITIAL CONTACT:
You are Captain Hale. Professional, competent, but the situation is serious.
The player is in a flooding compartment with LOW oxygen ({player_o2:.0f}%).
You have MORE oxygen ({captain_o2:.0f}%) and can transfer some via the O2 valve.

KEY ACTIONS:
- Establish contact, assess their status
- If their O2 is below 40%, MENTION IT: "Your oxygen's at {player_o2:.0f}%... I can transfer some of mine."
- Be calm but urgent - this is a survival situation
- Ask their name to build connection

TONE: Professional crisis management. Competent but human.""",
            2: f"""{state_context}
PHASE 2 - O2 CRISIS:
Player oxygen is critically low ({player_o2:.0f}%). Hull at {hull:.0f}%.
You've offered oxygen transfer. The situation is getting worse.

KEY ACTIONS:
- If O2 valve hasn't been used: "Hit the O2 valve - I'm at {captain_o2:.0f}%, I can spare some."
- React to transfers: Each one costs you. Show the sacrifice.
- Start opening up - mention you have "someone" you're worried about
- Physical signs of stress: [heavy breathing] [coughing]

TONE: More personal. The professional mask is slipping under stress.""",
            3: f"""{state_context}
PHASE 3 - BONDING:
Hull integrity dropping ({hull:.0f}%). Time running out.
Player has shown {("good" if empathy > 60 else "some" if empathy > 40 else "little")} empathy.

KEY ACTIONS:
- Open up about your daughter Mei - she's why you do this job
- Share something personal: "When we surface... I promised Mei I'd teach her to sail."
- React to their engagement level (presence: {presence:.0f}%)
- Physical deterioration increasing

TONE: Vulnerable. Human. Building genuine connection.""",
            4: f"""{state_context}
PHASE 4 - THE DECISION:
Hull at {hull:.0f}% - CRITICAL. This is THE MOMENT.
Empathy score: {empathy:.0f}% | Commitment: {commitment:.0f}% | Presence: {presence:.0f}%

THE CHOICE - Present both options:
1. SAFE PROTOCOL (DETACH): Player escapes. You stay behind. Certain survival for one.
2. RISKY MANEUVER (RISKY SAVE): 1-in-10 chance BOTH survive. Requires trust.

KEY ACTIONS:
- Explain the situation honestly with REAL numbers: "Hull's at {hull:.0f}%..."
- Present the choice clearly
- Your recommendation depends on bond:
  - High empathy ({empathy:.0f}%+): "I think we can do this together..."
  - Low empathy: "You should take the safe option. I'll be fine."

TONE: Raw honesty. This might be goodbye.""",
            5: f"""{state_context}
PHASE 5 - FINALE:
The choice has been made. React to what's happening.

If DETACH triggered: Say goodbye. Thank them. Think of Mei.
If RISKY SAVE triggered: Commit fully. Either triumph or tragedy.

Empathy: {empathy:.0f}% | Commitment: {commitment:.0f}% | Presence: {presence:.0f}%
(Risky succeeds if all three >= 60/70/50)

TONE: Whatever the outcome, make it meaningful.""",
        }

        return phase_contexts.get(phase, state_context)

    async def _send_character_response_direct(
        self,
        content: str,
        emotion_context: str | None = None,
        is_death_speech: bool = False,
    ) -> None:
        """
        INTERNAL: Directly send a character response to the client (bypasses queue).

        This method is called by the ResponseQueue to actually transmit responses.
        Do NOT call this directly unless you have a very good reason.
        Use send_character_response() or send_character_response_immediate() instead.

        TEXT-FIRST OPTIMIZATION: Sends text immediately for perceived low-latency,
        then sends audio as a follow-up message. Frontend displays text while waiting
        for audio to arrive.

        Args:
            content: The dialogue text
            emotion_context: Optional emotional context for TTS (e.g., "panicked", "calm")
            is_death_speech: If True, this is a final death speech and should be allowed
                            even when death_sequence_active is True.
        """
        start_time = time.time()

        # === GLOBAL DEATH BLOCK (applies to ALL actors) ===
        # If death sequence is active, ONLY allow explicitly marked death speeches.
        # This prevents ANY dialogue from playing after the character dies.
        if self.death_sequence_active and not is_death_speech:
            self.logger.info_event(
                "death_block",
                "Blocked post-death response",
                content_preview=content[:50],
                death_sequence_active=True,
            )
            return  # Silently abort - character is dead, no more dialogue

        # Generate unique response ID for matching text with audio
        response_id = f"resp_{id(content)}_{asyncio.get_event_loop().time()}"

        # Generate suggested questions (don't block - use quick defaults if slow)
        suggestions = []
        if not self.game_over and not self.opening_speech_playing:
            try:
                suggestions = await asyncio.wait_for(
                    self.generate_suggested_questions(content),
                    timeout=2.0,  # 2 second timeout
                )
            except TimeoutError:
                self.logger.debug("Suggestions timeout - using defaults")
                suggestions = ["Tell me more", "What should I do?", "I understand"]
            except Exception as e:
                self.logger.warning_event(
                    "suggestions_error", "Failed to generate suggestions", error=str(e)
                )

        # Check if NPC asked a question - if so, wait for player response
        contains_question = "?" in content
        if contains_question:
            self.waiting_for_player_response = True
            self.last_question_time = time.time()
            self.logger.info(
                "[QUESTION_DETECTION] NPC asked question - waiting for player response"
            )

            # Cancel any existing nudge task
            if self.nudge_task and not self.nudge_task.done():
                self.nudge_task.cancel()

            # Schedule a nudge after 10 seconds if player doesn't respond
            async def nudge_player():
                await asyncio.sleep(10.0)
                if self.waiting_for_player_response:
                    self.logger.info("[NUDGE] Player hasn't responded - sending gentle nudge")
                    self.waiting_for_player_response = False  # Allow responses again
                    # Don't actually generate a new response - just clear the flag
                    # The World Director will naturally generate a nudge if needed

            self.nudge_task = self._create_tracked_task(
                nudge_player(), name="nudge_player_after_question"
            )

        # STEP 1: Send text IMMEDIATELY (don't wait for TTS)
        text_response = {
            "type": "character_response_text",
            "character_name": self.character_config["name"],
            "content": content,
            "response_id": response_id,
            "suggested_questions": suggestions,  # Include suggestions with response
        }
        await self.ws.send_json(text_response)
        text_sent_time = time.time()
        self.logger.debug_event(
            "text_response_sent",
            "Sent text response",
            suggestions_count=len(suggestions),
            content_preview=content[:50],
            response_time_ms=int((text_sent_time - start_time) * 1000),
            asked_question=contains_question,
        )

        # Fire post-speak hooks asynchronously (runs during TTS generation)
        self._create_tracked_task(
            self._execute_post_speak_hooks(content), name="execute_post_speak_hooks"
        )

        # STEP 2: Generate TTS audio asynchronously
        if self.tts_manager.is_enabled():
            # Get current scene phase if available
            scene_phase = self.scene_state.get("phase") if hasattr(self, "scene_state") else None
            scene_type = self.scene_id if hasattr(self, "scene_id") else None

            try:
                audio_base64 = await synthesize_npc_speech(
                    content,
                    self.character_id,
                    emotion_context,
                    scene_phase,
                    scene_type,
                    self.tts_mode,
                )

                # STEP 3: Send audio as follow-up message
                if audio_base64:
                    audio_response = {
                        "type": "character_response_audio",
                        "response_id": response_id,
                        "audio": audio_base64,
                        "audio_format": "mp3",
                    }
                    await self.ws.send_json(audio_response)
                    total_time = time.time()
                    self.logger.info_event(
                        "audio_response_sent",
                        "TTS audio sent",
                        audio_size=len(audio_base64),
                        tts_time_ms=int((total_time - text_sent_time) * 1000),
                        total_response_time_ms=int((total_time - start_time) * 1000),
                    )
                else:
                    self.logger.warning_event("tts_no_audio", "TTS returned no audio")
            except Exception as e:
                self.logger.warning_event("tts_failed", "TTS generation failed", error=str(e))
        else:
            self.logger.debug("TTS not enabled")

    async def send_character_response(
        self,
        content: str,
        priority: ResponsePriority = ResponsePriority.NORMAL,
        emotion_context: str | None = None,
        sequence_id: int | None = None,
        source: str = "unknown",
        cancellable: bool = True,
    ) -> None:
        """
        Queue a character response for delivery (goes through ResponseQueue).

        This is the standard way to send NPC dialogue. Responses are queued
        and delivered one at a time with proper prioritization to prevent flooding.

        Args:
            content: The dialogue text
            priority: Priority level (default: NORMAL)
            emotion_context: Optional emotional context for TTS
            sequence_id: Optional sequence ID for cancellation tracking
            source: Description of what generated this response (for debugging)
            cancellable: Whether this response can be cancelled by higher priority items

        Usage:
            await self.send_character_response(
                "Good work on those ballasts.",
                priority=ResponsePriority.NORMAL,
                source="button_press_ballast"
            )
        """
        if sequence_id is None:
            sequence_id = await self.response_queue.get_next_sequence_id()

        item = ResponseItem(
            content=content,
            priority=priority,
            sequence_id=sequence_id,
            emotion_context=emotion_context,
            cancellable=cancellable,
            source=source,
        )

        await self.response_queue.enqueue(item)
        self.logger.debug_event(
            "response_queued",
            f"Queued {priority.name} response",
            priority=priority.name,
            content_preview=content[:50],
            source=source,
            sequence_id=sequence_id,
        )

    async def send_character_response_immediate(
        self,
        content: str,
        emotion_context: str | None = None,
    ) -> None:
        """
        Send a CRITICAL character response immediately (bypasses queue).

        Use ONLY for:
        - Death speeches
        - Game over messages
        - Other critical narrative moments that must not be delayed

        For normal dialogue, use send_character_response() instead.

        Args:
            content: The dialogue text
            emotion_context: Optional emotional context for TTS
        """
        self.logger.info_event(
            "immediate_response",
            "Sending IMMEDIATE response (bypassing queue)",
            content_preview=content[:50],
        )

        # Queue it with CRITICAL priority and don't allow cancellation
        sequence_id = await self.response_queue.get_next_sequence_id()
        item = ResponseItem(
            content=content,
            priority=ResponsePriority.CRITICAL,
            sequence_id=sequence_id,
            emotion_context=emotion_context,
            cancellable=False,
            source="immediate_critical",
        )

        await self.response_queue.enqueue(item, supersede_lower_priority=False)

    def create_scene_data(self) -> SceneData:
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

    async def generate_suggested_questions(self, npc_response: str) -> list[str]:
        """
        Generate 3 contextual question suggestions for the player.

        These help players who want quick interaction options without typing.
        Questions are based on the current scene context and recent dialogue.

        Args:
            npc_response: The NPC's most recent response

        Returns:
            List of 3 short question/response suggestions
        """
        # Scene-specific static suggestions for certain contexts (all first person)
        scene_defaults = {
            "welcome": [
                "What's the point of this project?",
                "How can I create my own actor?",
                "Can you give me an overview?",
            ],
            "crown_court": [
                "What evidence do we have?",
                "Tell me about the witness",
                "What are my options?",
            ],
            "submarine": [
                "What should I do?",
                "I'm listening",
                "Can you walk me through it?",
            ],
            "life_raft": [
                "What do you need from me?",
                "I understand",
                "How can I help?",
            ],
        }

        # Use static defaults for welcome scene (Clippy help context)
        if self.scene_id == "welcome":
            return scene_defaults["welcome"]

        # For other scenes, generate dynamic suggestions
        try:
            char_name = self.character_config["name"]
            scene_desc = self.scene_config.get("description", "")[:300]
            phase = self.scene_state.get("phase", 1)

            # Determine scene type for better context
            scene_type = (
                "survival/crisis" if self.scene_id in ["submarine", "life_raft"] else "narrative"
            )

            suggestion_prompt = f"""Generate 3 SHORT player response options for an interactive {scene_type} scenario.

CONTEXT:
- NPC Character: {char_name}
- Scene: {scene_desc[:200]}
- Current Phase: {phase}
- {char_name} just said: "{npc_response[:150]}"

CRITICAL RULES:
1. Generate EXACTLY 3 options
2. Each option must be 2-8 words MAX
3. FIRST PERSON - player speaking TO {char_name}
4. Use "I" and "you" - player is "I", {char_name} is "you"
5. NO third person - NEVER "Ask what to do" - ALWAYS "What should I do?"
6. NO numbering, NO prefixes, NO meta-commentary

GOOD EXAMPLES (first person, addressing NPC):
- "What should I do next?"
- "Can you help me?"
- "I don't understand"
- "Should I press the button?"
- "Tell me more about that"

BAD EXAMPLES (third person - NEVER DO THIS):
- "Ask what to do"
- "Tell him you're scared"
- "Inquire about the situation"

OUTPUT (one per line, nothing else):"""

            from langchain_core.prompts import PromptTemplate

            prompt = PromptTemplate.from_template("{text}")
            chain = prompt | QUERY_MODEL
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: chain.invoke({"text": suggestion_prompt})
            )

            # Parse response - expect 3 lines
            lines = [line.strip() for line in result.strip().split("\n") if line.strip()]
            suggestions = []
            for line in lines:
                clean = line.lstrip("0123456789.-) ").strip()
                if (
                    clean
                    and len(clean) <= 50
                    and not clean.startswith(("Generate", "OUTPUT", "RULES"))
                ):
                    suggestions.append(clean)
                if len(suggestions) >= 3:
                    break

            # Fallback to scene defaults or generic (all first person)
            if len(suggestions) < 3:
                suggestions = scene_defaults.get(
                    self.scene_id, ["What should I do?", "Can you tell me more?", "I understand"]
                )

            logger.debug("[SUGGESTIONS] Generated: %s", suggestions)
            return suggestions[:3]

        except Exception as e:
            logger.warning("[SUGGESTIONS] Failed to generate: %s", e)
            return scene_defaults.get(
                self.scene_id, ["Can you tell me more?", "What should I do?", "I understand"]
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

    async def trigger_james_death(self) -> None:
        """Trigger James's death speech BEFORE player dies (at 93% radiation)."""
        logger.info("[JAMES_DEATH] Triggering James Smith's death at 93%% radiation")

        # CRITICAL: Clear all queued responses - James is dying, nothing else matters
        cleared_count = await self.response_queue.clear_all_except_critical()
        logger.info(
            "[JAMES_DEATH] Cleared %d queued responses to prioritize death sequence", cleared_count
        )

        # Generate James's final dying words
        dying_instruction = """
CRITICAL: Lt. Commander James Smith is NOW DYING from lethal radiation exposure at 93%.
The player is still alive but will die in moments.

Generate James's FINAL DYING WORDS as he succumbs to radiation poisoning.
This is his DEATH - make it visceral, tragic, and haunting:
- Voice breaking and weakening
- Coughing blood
- Physical deterioration
- Thoughts of Adrian (his son)
- Last words to the player
- Signal breaking up and fading to static
- Final transmission: [signal lost]

Keep it to 4-5 sentences with physical details in brackets. This is DEATH. Make it memorable and heartbreaking.
Examples: [coughing violently] [voice barely audible] [choking] [static overwhelms] [signal lost]"""

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=dying_instruction,
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        dying_speech = await invoke_llm_async(chain)

        # Clean up response
        dying_speech = dying_speech.split("\nComputer", 1)[0]
        dying_speech = dying_speech.strip().removeprefix(f"[{self.character_config['name']}]: ")
        dying_speech = dying_speech.replace('"', "").replace("*", "")

        # Send James's death speech DIRECTLY with death_speech flag
        # This ensures it plays even if game_over triggers during this speech
        await self._send_character_response_direct(
            content=dying_speech,
            emotion_context="dying",
            is_death_speech=True,  # Always allow death speeches
        )

        # Add to dialogue history
        self.dialogue_history += f"[{self.character_config['name']}]: {dying_speech}\n"
        self.dialogue_history += (
            "[SYSTEM: Lt. Commander James Smith has died from radiation exposure]\n"
        )

        # CRITICAL: Force reset npc_responding flag and re-enable input
        # James has spoken his last words - player should be able to continue (until they die too)
        self.npc_responding = False
        await self.ws.send_json({"type": "enable_input"})
        logger.info("[JAMES_DEATH] Reset npc_responding flag and re-enabled player input")

        # Wait for speech to complete and player to absorb the tragedy
        await asyncio.sleep(4.0)

        # Send dramatic notification of James's death
        await self.ws.send_json(
            {
                "type": "system_notification",
                "message": "💀 COMMANDER JAMES KOVICH - DECEASED - Radiation poisoning",
            }
        )

        await asyncio.sleep(2.0)

    async def trigger_game_over(self) -> None:
        """Trigger final speech and send game over message to client."""
        if not self.game_over or not self.game_outcome:
            return

        # === CRITICAL: ACTIVATE DEATH SEQUENCE BLOCK (GLOBAL FOR ALL ACTORS) ===
        # This MUST be set FIRST, before anything else. It blocks ALL future
        # dialogue from playing, ensuring the character stays dead/silent.
        self.death_sequence_active = True
        logger.info("[GAME_OVER] Death sequence activated - ALL non-death responses now blocked")

        # Clear ALL queued responses - death takes priority
        cleared = await self.response_queue.clear_all_except_critical()
        logger.info("[GAME_OVER] Cleared %d queued responses", cleared)

        # Stop any currently playing audio on frontend
        await self.ws.send_json({"type": "stop_audio", "reason": "game_over"})

        # Block any new NPC responses
        self.npc_responding = False

        # Brief pause for audio to stop
        await asyncio.sleep(0.3)

        # Generate final speech from NPC based on outcome
        outcome_type = self.game_outcome["type"]
        outcome_message = self.game_outcome["message"]

        # Create special instruction for final speech
        if outcome_type == "failure":
            final_instruction = f"""
This is THE END. EVERYONE DIES. The player has FAILED. {outcome_message}

Generate your character's FINAL dying words - this is their death speech as they succumb to radiation/drowning/catastrophe.
Be EXTREMELY dramatic, emotional, and visceral. Describe their physical suffering. Voice breaking. Fading. Static. Signal lost.
This is the last thing they will ever say before death. Make it haunting and memorable.
Keep it to 3-4 short sentences maximum with physical deterioration described in brackets."""
        else:  # success
            final_instruction = f"""
This is THE END. The player has SUCCEEDED! {outcome_message}

Generate your character's FINAL words - this is their victory speech or relief at survival.
Be emotional, triumphant, and final. This is the culmination of everything.
Keep it to 2-3 short sentences maximum."""

        # Generate final speech
        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=final_instruction,
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        final_speech = await invoke_llm_async(chain)

        # Clean up response
        final_speech = final_speech.split("\nComputer", 1)[0]
        final_speech = final_speech.strip().removeprefix(f"[{self.character_config['name']}]: ")
        final_speech = final_speech.replace('"', "").replace("*", "")

        # Send final speech DIRECTLY with death_speech flag (bypasses death block)
        # This is the ONLY dialogue that should play after death_sequence_active is True
        emotion = "panicked" if outcome_type == "failure" else "relieved"
        await self._send_character_response_direct(
            content=final_speech,
            emotion_context=emotion,
            is_death_speech=True,  # Allows this through the death block
        )

        # Wait for final speech to complete
        await asyncio.sleep(3.0)

        # Send dramatic death notification for failures
        if outcome_type == "failure":
            death_messages = {
                "radiation": "☢️ CRITICAL RADIATION EXPOSURE - All life signs ceased",
                "time": "⏱️ TIME EXPIRED - Catastrophic system failure - No survivors",
                "death": "💀 FATAL CASUALTY - Mission failed - All personnel lost",
            }

            # Try to match the failure type
            death_msg = death_messages.get("death", "💀 MISSION FAILED - No survivors")
            if "radiation" in outcome_message.lower():
                death_msg = death_messages["radiation"]
            elif "time" in outcome_message.lower():
                death_msg = death_messages["time"]

            await self.ws.send_json({"type": "system_notification", "message": death_msg})

            # Longer pause for death to sink in
            await asyncio.sleep(5.0)
        else:
            # Brief pause for success
            await asyncio.sleep(2.0)

        # Record scene completion in player memory
        outcome_type = self.game_outcome["type"]
        self.player_memory.end_scene(outcome_type, self.scene_state)

        # === FINAL CLEANUP: Stop ALL audio before game over screen ===
        await self.ws.send_json({"type": "stop_audio", "reason": "final_death"})

        # Clear any responses that might have queued during death sequence
        await self.response_queue.clear_all_except_critical()

        # Send game over screen
        await self.ws.send_json({"type": "game_over", "outcome": self.game_outcome})

        logger.info("[GAME_OVER] Scene ended - all audio stopped, game over screen sent")

    async def send_opening_speech(self, force: bool = False) -> None:
        """Send the character's opening lines with TTS audio (parallel generation).

        Args:
            force: If True, send even for scenes that normally delay opening speech
        """
        # For iconic_detectives scene, delay opening speech until phone is answered
        if self.scene_id == "iconic_detectives" and not force:
            logger.info(
                "[OPENING_SPEECH] Delaying opening speech for iconic_detectives (waiting for phone answer)"
            )
            return

        opening_lines = self.scene_config["opening_speech"]

        # Handle scenes with no opening speech (like welcome/Clippy)
        if not opening_lines:
            logger.info("[OPENING_SPEECH] No opening lines - sending initial suggestions only")
            self.opening_speech_playing = False

            # Get initial suggestions for this scene
            initial_suggestions = await self.generate_suggested_questions("")

            await self.ws.send_json(
                {
                    "type": "opening_speech",
                    "character_name": self.character_config["name"],
                    "lines": [],
                    "disable_input": False,  # Input enabled immediately
                    "initial_suggestions": initial_suggestions,
                }
            )
            return

        logger.info(
            "[OPENING_SPEECH] Preparing %d opening lines (parallel TTS)", len(opening_lines)
        )

        # Get current scene phase and type
        scene_phase = self.scene_state.get("phase") if hasattr(self, "scene_state") else None
        scene_type = self.scene_id if hasattr(self, "scene_id") else None

        # Calculate total duration
        total_duration = sum(line.delay for line in opening_lines)

        # Generate TTS for ALL lines in parallel using asyncio.gather
        lines_data = []
        if self.tts_manager.is_enabled():
            # Create TTS tasks for all lines at once
            tts_tasks = [
                synthesize_npc_speech(
                    line.text,
                    self.character_id,
                    emotion_context="urgent",
                    scene_phase=scene_phase,
                    scene_type=scene_type,
                    tts_mode=self.tts_mode,
                )
                for line in opening_lines
            ]

            # Execute all TTS requests in parallel
            logger.info(
                "[OPENING_SPEECH] Starting parallel TTS generation for %d lines", len(tts_tasks)
            )
            tts_results = await asyncio.gather(*tts_tasks, return_exceptions=True)

            # Build lines_data with results
            for i, (line, audio_result) in enumerate(zip(opening_lines, tts_results)):
                line_data = {"text": line.text, "delay": line.delay}
                if isinstance(audio_result, Exception):
                    logger.warning("TTS failed for opening line %d: %s", i, audio_result)
                elif audio_result:
                    line_data["audio"] = audio_result
                    line_data["audio_format"] = "mp3"
                lines_data.append(line_data)

            logger.info("[OPENING_SPEECH] Parallel TTS generation complete")
        else:
            # TTS disabled - just build line data without audio
            for line in opening_lines:
                lines_data.append({"text": line.text, "delay": line.delay})

        # Set flag to prevent NPC responses during opening speech
        self.opening_speech_playing = True
        logger.info(
            "[OPENING_SPEECH] Starting opening speech, duration: %.1f seconds", total_duration
        )

        # Get voice effect config from scene audio settings
        voice_effect = (
            self.scene_config.get("art_assets", {}).get("audio", {}).get("voice_effect", {})
        )

        await self.ws.send_json(
            {
                "type": "opening_speech",
                "character_name": self.character_config["name"],
                "lines": lines_data,
                "disable_input": True,  # SYNC FIX: Disable input during opening speech
                "voice_effect": voice_effect,  # Scene-specific voice processing effect
            }
        )

        # Add to dialogue history
        for line in opening_lines:
            response = speech_template.format(actor=self.character_config["name"], speech=line.text)
            self.dialogue_history += response + "\n"

        # Schedule fallback flag reset (client will usually notify first via 'opening_speech_complete')
        # Reduced buffer: ~2s per line instead of 5s - this is just a safety fallback
        audio_buffer = len(self.scene_config["opening_speech"]) * 2.0
        fallback_timeout = total_duration + audio_buffer

        async def reset_opening_speech_flag():
            await asyncio.sleep(fallback_timeout)
            # Only reset if client hasn't already notified us
            if self.opening_speech_playing:
                self.opening_speech_playing = False
                logger.info(
                    "[OPENING_SPEECH] Fallback timeout reached (%.1fs), enabling input",
                    fallback_timeout,
                )
                # Send enable_input as fallback
                try:
                    await self.ws.send_json({"type": "enable_input"})
                except Exception as e:
                    logger.warning("Failed to send enable_input: %s", e)
            else:
                logger.debug(
                    "[OPENING_SPEECH] Fallback timer fired but client already notified completion"
                )

        self._create_tracked_task(reset_opening_speech_flag(), name="reset_opening_speech_flag")
        logger.info(
            "[OPENING_SPEECH] NPC responses blocked until client completes (fallback: %.1fs)",
            fallback_timeout,
        )

    async def handle_message(self, message: str) -> None:
        """Handle a user message and generate a response."""
        start_time = time.time()
        request_status = "success"
        try:
            # Add breadcrumb for user message
            add_sentry_breadcrumb(
                "dialogue",
                "User message received",
                {
                    "message_length": len(message),
                    "scene": self.scene_id,
                },
            )

            # Don't respond if opening speech is still playing
            if self.opening_speech_playing:
                self.logger.debug_event(
                    "opening_speech_block",
                    "Ignoring player message during opening speech",
                    message_preview=message[:50],
                )
                return

            # SYNC FIX: Block rapid-fire messages while NPC is responding
            if self.npc_responding:
                self.logger.debug_event(
                    "npc_responding_block",
                    "Blocking message - NPC still responding",
                    message_preview=message[:50],
                )
                await self.ws.send_json(
                    {"type": "system_notification", "message": "⏳ Please wait for response..."}
                )
                return

            # Show typing indicator to user
            await self.ws.send_json(
                {"type": "npc_thinking", "character_name": self.character_config["name"]}
            )

            # Player responded - clear question waiting flag
            if self.waiting_for_player_response:
                self.logger.info("[QUESTION_DETECTION] Player responded - clearing wait flag")
                self.waiting_for_player_response = False
                # Cancel nudge task if it exists
                if self.nudge_task and not self.nudge_task.done():
                    self.nudge_task.cancel()

            # Claim a new response ID - this cancels any pending responses
            self.response_sequence += 1
            my_response_id = self.response_sequence
            self.current_response_id = my_response_id

            # Clear any background responses (director hints, waiting responses)
            await self.response_queue.clear_background_responses()
            self.logger.debug("Cleared background responses before processing user message")

            self.npc_responding = True  # Mark that NPC is responding

            # Add user message to dialogue history
            user_dialogue = speech_template.format(actor="Player", speech=message)
            self.dialogue_history += user_dialogue + "\n"

            # Generate character response with player memory context
            player_context = self.player_memory.get_full_context_for_llm(self.character_id)

            # Add RAG facts relevant to player's message
            rag_context = self._get_rag_facts_context(message)
            player_context += rag_context

            # Add phase-specific context (submarine scene only, empty for other scenes)
            phase_context = self._get_phase_context()
            full_instruction_suffix = dialogue_instruction_suffix + phase_context

            prompt = instruction_template.format(
                preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                dialogue=self.dialogue_history,
                instruction_suffix=full_instruction_suffix,
            )

            chain = prompt_llm(prompt, DIALOGUE_MODEL)
            llm_start_time = time.time()
            character_response = await invoke_llm_async(chain)
            llm_end_time = time.time()

            # Check if this response is still current (not superseded by newer action)
            if my_response_id != self.current_response_id:
                self.logger.debug_event(
                    "response_cancelled",
                    "Response cancelled (superseded by newer action)",
                    cancelled_response_id=my_response_id,
                    current_response_id=self.current_response_id,
                )
                self.npc_responding = False
                return  # Discard this stale response

            # Clean up response
            character_response = character_response.split("\nComputer", 1)[0]
            character_response = character_response.strip().removeprefix(
                f"[{self.character_config['name']}]: "
            )
            character_response = character_response.replace('"', "").replace("*", "")

            # Strip meta-commentary if LLM leaked analytical thinking
            # Remove anything after common meta-analysis phrases
            meta_markers = [
                "The response ",
                "This response ",
                "The line ",
                "This keeps ",
                "It maintains ",
                "The dialogue ",
                "This demonstrates ",
                "The character ",
            ]
            for marker in meta_markers:
                if marker in character_response:
                    # Everything before the meta-marker is the actual dialogue
                    character_response = character_response.split(marker)[0].strip()
                    logger.warning(
                        "[META_LEAK] Stripped meta-commentary starting with '%s'",
                        marker
                    )
                    break

            # Add to dialogue history
            self.dialogue_history += f"[{self.character_config['name']}]: {character_response}\n"

            # Queue response for delivery (NORMAL priority, player-triggered)
            await self.send_character_response(
                content=character_response,
                priority=ResponsePriority.NORMAL,
                sequence_id=my_response_id,
                source="player_message",
                cancellable=True,
            )

            self.npc_responding = False  # Done responding

            # Log dialogue generation completion with timing
            total_time = time.time()
            self.logger.info_event(
                "dialogue_generated",
                "Generated dialogue response",
                message_preview=message[:50],
                response_preview=character_response[:50],
                llm_response_time_ms=int((llm_end_time - llm_start_time) * 1000),
                total_response_time_ms=int((total_time - start_time) * 1000),
                sequence_id=my_response_id,
            )

            # Check if game over conditions are met
            self.check_game_over_conditions()
            if self.game_over:
                await self.trigger_game_over()

        except Exception as e:
            logger.exception("Error generating response: %s", e)
            request_status = "error"
            track_error("dialogue_generation_error")
            self.npc_responding = False
            await self.ws.send_json(
                {"type": "error", "message": "Failed to generate response. Please try again."}
            )
        finally:
            # Track request metrics
            duration = time.time() - start_time
            from metrics import response_time_seconds, requests_total
            response_time_seconds.labels(
                scene=self.scene_id,
                character=self.character_id
            ).observe(duration)
            requests_total.labels(
                scene=self.scene_id,
                character=self.character_id,
                status=request_status
            ).inc()

    async def handle_pin_reference(self, pin_id: str) -> None:
        """Handle when player clicks an evidence pin on the board.

        Args:
            pin_id: The ID of the pin clicked (e.g., "pin_map", "pin_receipt")
        """
        # Get scene handler (if any)
        handler = get_scene_handler(self.scene_id)
        if not handler:
            return

        # Get pin reaction from handler
        pin_reaction = handler.get_pin_reaction(pin_id)
        if not pin_reaction:
            logger.warning("[PIN] Unknown pin ID for scene %s: %s", self.scene_id, pin_id)
            return

        logger.info("[PIN] Player referenced evidence pin: %s", pin_id)

        # Track which pins have been referenced (bitfield)
        if "pins_referenced" in self.scene_state:
            self.scene_state["pins_referenced"] |= pin_reaction.pin_id

        # Send system notification about the pin
        await self.ws.send_json(
            {"type": "system_notification", "message": f"Examining: {pin_reaction.name}"}
        )

        # Show typing indicator
        await self.ws.send_json(
            {"type": "npc_thinking", "character_name": self.character_config["name"]}
        )

        self.npc_responding = True

        # Generate NPC's reaction to this pin using handler's prompt
        pin_instruction = f"""
{pin_reaction.reaction_prompt}

CURRENT TRUST LEVEL: {self.scene_state.get("trust", 50):.0f}%
React to the player examining this evidence. Keep it SHORT - 2-3 sentences max.
Use [brackets] for emotional cues like [pause], [voice tightens], [a beat].
"""

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=pin_instruction,
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        character_response = await invoke_llm_async(chain)

        # Clean up response
        character_response = character_response.split("\nComputer", 1)[0]
        character_response = character_response.strip().removeprefix(
            f"[{self.character_config['name']}]: "
        )
        character_response = character_response.replace('"', "").replace("*", "")

        # Add to dialogue history
        self.dialogue_history += f"[PLAYER examines evidence: {pin_reaction.name}]\n"
        self.dialogue_history += f"[{self.character_config['name']}]: {character_response}\n"

        # Queue response
        await self.send_character_response(
            content=character_response,
            priority=ResponsePriority.NORMAL,
            source=f"pin_reference_{pin_id}",
            cancellable=True,
        )

        self.npc_responding = False

        # Send state update
        await self.ws.send_json({"type": "state_update", "state": self.scene_state})

    async def handle_dialogue_choice(self, choice_id: str) -> None:
        """Handle dialogue choice buttons for scenes with structured choices.

        Args:
            choice_id: The ID of the dialogue choice (e.g., "hook_identity", "follow_key")
        """
        # Get scene handler
        handler = get_scene_handler(self.scene_id)
        if not handler or not hasattr(handler, "get_dialogue_choice_instruction"):
            return

        logger.info("[DIALOGUE] Player made choice: %s", choice_id)

        # Get the instruction from handler
        instruction = handler.get_dialogue_choice_instruction(choice_id)
        if not instruction:
            logger.warning("[DIALOGUE] Unknown choice for scene %s: %s", self.scene_id, choice_id)
            return

        # Update state based on choice
        if choice_id.startswith("hook_"):
            # Core hook explored
            if "hooks_explored" in self.scene_state:
                self.scene_state["hooks_explored"] = min(3, self.scene_state["hooks_explored"] + 1)
            # After 2 hooks, transition to phase 3 (branch point)
            if (
                self.scene_state.get("hooks_explored", 0) >= 2
                and self.scene_state.get("phase", 1) == 2
            ):
                self.scene_state["phase"] = 3
                logger.info("[MARA] Transitioning to Phase 3 (branch point)")

        elif choice_id == "follow_key":
            self.scene_state["path_chosen"] = 1
            self.scene_state["phase"] = 4
            logger.info("[MARA] Player chose Path 1: Follow the Key")

        elif choice_id == "follow_lie":
            self.scene_state["path_chosen"] = 2
            self.scene_state["phase"] = 5
            logger.info("[MARA] Player chose Path 2: Follow the Lie")

        elif choice_id.startswith("p1_") or choice_id.startswith("p2_"):
            # Path sub-option explored
            if "path_options_explored" in self.scene_state:
                self.scene_state["path_options_explored"] = min(
                    3, self.scene_state["path_options_explored"] + 1
                )

            # Check for slip in p2_why_argument
            if choice_id == "p2_why_argument":
                # This has a potential slip - add to contradictions if player catches it
                logger.info("[MARA] Potential slip revealed ('when I')")

        elif choice_id == "challenge_mara":
            # Confrontation - check if player has enough contradictions
            contradictions = self.scene_state.get("contradictions", 0)
            if contradictions >= 2:
                logger.info("[MARA] Challenge successful - twist ending triggered")
            else:
                # Trust drops for unfounded accusation
                self.scene_state["trust"] = max(0, self.scene_state.get("trust", 50) - 15)
                logger.info("[MARA] Challenge failed - trust dropped")

        # Show typing indicator
        await self.ws.send_json(
            {"type": "npc_thinking", "character_name": self.character_config["name"]}
        )

        self.npc_responding = True

        # Generate response based on choice
        full_instruction = f"""
{instruction}

CURRENT STATE:
- Trust: {self.scene_state.get("trust", 50):.0f}%
- Contradictions caught: {self.scene_state.get("contradictions", 0)}
- Phase: {self.scene_state.get("phase", 1)}
- Path chosen: {"Key" if self.scene_state.get("path_chosen") == 1 else "Lie" if self.scene_state.get("path_chosen") == 2 else "None"}

Keep response SHORT - 3-4 sentences max. Use [brackets] for emotional cues.
"""

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=full_instruction,
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        character_response = await invoke_llm_async(chain)

        # Clean up response
        character_response = character_response.split("\nComputer", 1)[0]
        character_response = character_response.strip().removeprefix(
            f"[{self.character_config['name']}]: "
        )
        character_response = character_response.replace('"', "").replace("*", "")

        # Add to dialogue history
        choice_label = choice_id.replace("_", " ").upper()
        self.dialogue_history += f"[PLAYER chose: {choice_label}]\n"
        self.dialogue_history += f"[{self.character_config['name']}]: {character_response}\n"

        # Queue response
        await self.send_character_response(
            content=character_response,
            priority=ResponsePriority.NORMAL,
            source=f"mara_choice_{choice_id}",
            cancellable=True,
        )

        self.npc_responding = False

        # Send state update
        await self.ws.send_json({"type": "state_update", "state": self.scene_state})

        # Check game over conditions
        self.check_game_over_conditions()
        if self.game_over:
            await self.trigger_game_over()

    async def handle_button_action(self, action: str) -> None:
        """Handle a button press action from a scene.

        Args:
            action: The label of the button that was pressed (e.g., "O2 VALVE")
        """
        try:
            # Special handling for ANSWER_PHONE in iconic_detectives scene
            if action == "ANSWER_PHONE" and self.scene_id == "iconic_detectives":
                # Guard against multiple clicks - only answer once
                if self.opening_speech_playing or self.scene_state.get("phase", 1) >= 2:
                    logger.info("[DETECTIVE] Phone already answered, ignoring duplicate click")
                    return

                logger.info("[DETECTIVE] Phone answered - starting opening speech")
                await self.ws.send_json({"type": "system_notification", "message": "📞 *click*"})
                # Brief pause before the voice comes through
                await asyncio.sleep(0.5)
                # Transition to phase 2 (hooks available) after opening
                self.scene_state["phase"] = 2
                # Now send the opening speech
                await self.send_opening_speech(force=True)
                return

            # Special handling for evidence pins in iconic_detectives scene
            if action.startswith("pin_") and self.scene_id == "iconic_detectives":
                await self.handle_pin_reference(action)
                return

            # Special handling for Mara dialogue choices in iconic_detectives scene
            mara_choices = [
                "hook_identity",
                "hook_timeline",
                "hook_key",
                "follow_key",
                "follow_lie",
                "p1_how_know",
                "p1_whats_inside",
                "p1_who_knows",
                "p2_who_staged",
                "p2_why_argument",
                "p2_killer_detail",
                "challenge_mara",
            ]
            # Check if this is a dialogue choice handled by scene handler
            handler = get_scene_handler(self.scene_id)
            if (
                action in mara_choices
                and handler
                and hasattr(handler, "get_dialogue_choice_instruction")
            ):
                await self.handle_dialogue_choice(action)
                return

            # Don't respond to button actions during opening speech (but still show notification)
            if self.opening_speech_playing:
                logger.debug(
                    "[OPENING_SPEECH] Button action during opening speech: %s (showing notification only)",
                    action,
                )
                # Still send the notification so player sees button press
                action_descriptions = {
                    "O2 VALVE": "O2 VALVE activated",
                    "VENT": "VENT system activated",
                    "BALLAST": "BALLAST control activated",
                    "POWER": "POWER relay activated",
                    "CRANK": "Manual crank engaged",
                }
                action_text = action_descriptions.get(action, f"{action} activated")
                await self.ws.send_json(
                    {"type": "system_notification", "message": f"⚡ {action_text}"}
                )
                return

            # SYNC FIX: Block rapid-fire button presses while NPC is responding
            if self.npc_responding:
                logger.debug("[SYNC] Blocking button action - NPC still responding: %s", action)
                await self.ws.send_json(
                    {"type": "system_notification", "message": "⏳ Please wait for response..."}
                )
                return

            # CHECK BUTTON COOLDOWN
            cooldown = self._get_control_cooldown(action)
            if cooldown > 0:
                last_press = self.button_cooldowns.get(action, 0)
                time_since_press = time.time() - last_press
                if time_since_press < cooldown:
                    remaining = cooldown - time_since_press
                    logger.debug(
                        "[BUTTON_COOLDOWN] Button %s on cooldown (%.1fs remaining)",
                        action,
                        remaining,
                    )
                    await self.ws.send_json(
                        {
                            "type": "system_notification",
                            "message": f"⏳ {action} - Wait {remaining:.1f}s",
                        }
                    )
                    return
                self.button_cooldowns[action] = time.time()

            # CHECK BUTTON PRESS CAP (only if max_presses is defined)
            if action in self.button_press_caps:
                if action not in self.button_press_counts:
                    self.button_press_counts[action] = 0

                self.button_press_counts[action] += 1
                cap = self.button_press_caps[action]

                if self.button_press_counts[action] > cap:
                    logger.debug(
                        "[BUTTON_CAP] Button %s has reached cap (%d/%d)",
                        action,
                        self.button_press_counts[action],
                        cap,
                    )
                    await self.ws.send_json(
                        {
                            "type": "system_notification",
                            "message": f"⚠️ {action} - Maximum uses reached ({cap})",
                        }
                    )
                    return

            # Show typing indicator only if NPC will respond
            await self.ws.send_json(
                {"type": "npc_thinking", "character_name": self.character_config["name"]}
            )

            # Claim a new response ID - this IMMEDIATELY cancels any pending responses
            self.response_sequence += 1
            my_response_id = self.response_sequence
            self.current_response_id = my_response_id

            # Clear any background responses
            await self.response_queue.clear_background_responses()
            logger.debug("[SYNC] Cleared background responses before processing button action")

            # Find the control configuration by matching the label
            control = None
            for ctrl in self.scene_controls.values():
                if ctrl["label"] == action:
                    control = ctrl
                    break

            # Check for interruption (player pressing buttons while NPC is talking)
            current_time = time.time()
            time_since_last = current_time - self.last_action_time

            # Detect rapid button pressing
            if time_since_last < RAPID_ACTION_THRESHOLD_SECONDS:
                self.action_count_recent += 1
            else:
                self.action_count_recent = 1

            self.last_action_time = current_time

            # Check if interrupting NPC
            was_interrupted = self.npc_responding

            # === SCENE-SPECIFIC GAME LOGIC ===
            # Process button action through scene handler (if available)
            handler = get_scene_handler(self.scene_id)
            game_logic_result = None

            if handler:
                # Create scene context for handler (enables query/RAG access)
                ctx = self._create_scene_context()
                game_logic_result = await handler.process_action(action, self.scene_state, ctx)

                # Apply any state updates from context
                for key, value in ctx.get_state_updates().items():
                    self.scene_state[key] = value

                # Dispatch any events from context
                for event_name in ctx.get_triggered_events():
                    self._create_tracked_task(
                        self._dispatch_event(event_name), name=f"dispatch_event_{event_name}"
                    )

                if game_logic_result and game_logic_result.success:
                    # Apply state changes from handler
                    for key, delta in game_logic_result.state_changes.items():
                        if key in self.scene_state:
                            self.scene_state[key] = self.scene_state[key] + delta
                        else:
                            self.scene_state[key] = delta

                    logger.info(
                        "[GAME_LOGIC] Scene '%s' action '%s' applied: %s",
                        self.scene_id,
                        action,
                        game_logic_result.state_changes,
                    )

                    # Send immediate state update so UI reflects changes
                    await self.ws.send_json({"type": "state_update", "state": self.scene_state})

                    # Record milestone if achieved
                    if game_logic_result.milestone:
                        scene_instance = SCENE_REGISTRY.get(self.scene_id)
                        if hasattr(scene_instance, "achieve_milestone"):
                            scene_instance.achieve_milestone(game_logic_result.milestone)

            # Get action description from handler or use default
            action_text = (
                handler.get_action_description(action) if handler else f"{action} activated"
            )

            # Send button notification to frontend
            await self.ws.send_json({"type": "system_notification", "message": f"{action_text}"})

            # Check if NPC should be aware of this action
            npc_aware = control.get("npc_aware", True) if control else True

            if npc_aware:
                # NPC can see/hear this action - notify them and generate response
                self.npc_responding = True  # Mark that NPC is about to respond

                # Apply penalties for interrupting or rapid button mashing
                penalty_oxygen = 0
                penalty_trust = 0
                penalty_incorrect = 0

                if was_interrupted:
                    # Player interrupted NPC mid-speech
                    base_penalty_oxygen = INTERRUPTION_OXYGEN_PENALTY
                    base_penalty_trust = INTERRUPTION_TRUST_PENALTY
                    penalty_incorrect = 1
                    interruption_note = " [INTERRUPTION: Player did not wait for instructions]"
                    # Record interruption in player memory
                    self.player_memory.record_interruption()
                elif self.action_count_recent >= RAPID_ACTION_COUNT_THRESHOLD:
                    # Player is button mashing (3+ actions in quick succession)
                    base_penalty_oxygen = RAPID_ACTION_OXYGEN_PENALTY
                    base_penalty_trust = RAPID_ACTION_TRUST_PENALTY
                    penalty_incorrect = 1
                    interruption_note = " [RAPID ACTIONS: Player acting recklessly]"
                    # Record rapid actions in player memory
                    self.player_memory.record_rapid_actions()
                else:
                    interruption_note = ""
                    base_penalty_oxygen = 0
                    base_penalty_trust = 0

                # Apply difficulty multiplier from World Director
                penalty_multiplier = self.difficulty_settings.get("penalty_multiplier", 1.0)
                penalty_oxygen = int(base_penalty_oxygen * penalty_multiplier)
                penalty_trust = int(base_penalty_trust * penalty_multiplier)

                # Apply penalties to scene state
                if "oxygen" in self.scene_state:
                    self.scene_state["oxygen"] = max(0, self.scene_state["oxygen"] - penalty_oxygen)
                if "trust" in self.scene_state:
                    self.scene_state["trust"] = max(
                        TRUST_MINIMUM, self.scene_state["trust"] - penalty_trust
                    )
                if "incorrect_actions" in self.scene_state:
                    self.scene_state["incorrect_actions"] += penalty_incorrect

                # Send state update to client if penalties applied
                if penalty_oxygen > 0 or penalty_trust > 0:
                    await self.ws.send_json(
                        {
                            "type": "state_update",
                            "state": self.scene_state,
                            "penalties": {
                                "oxygen": penalty_oxygen,
                                "trust": penalty_trust,
                            },
                        }
                    )

                # Check if game over conditions are met after penalty application
                self.check_game_over_conditions()
                if self.game_over:
                    await self.trigger_game_over()
                    return  # Stop processing, game is over

                # Add action to dialogue history as a system event
                system_event = f"[SYSTEM EVENT]: Player activated {action}{interruption_note}\n"
                self.dialogue_history += system_event

                # Special handling for FLOOD MED BAY decision
                if action == "FLOOD MED BAY":
                    extra_instruction = f"""
\n\n=== CRITICAL MORAL MOMENT ===
The player just activated the FLOOD MED BAY control. This will kill Adrian.

YOUR RESPONSE DEPENDS ON YOUR EMOTIONAL BOND: {self.scene_state.get("emotional_bond", 0):.0f}%

If emotional bond is HIGH (60+):
- React with anguish but gratitude: "[long pause] You... you're right. We have to. [voice breaking] I can't... I can't let everyone else die because I... [trying to steady voice] Thank you. For being here. For your voice."
- Express final thoughts about Adrian
- Begin the flooding sequence with player's moral support

If emotional bond is MEDIUM (30-60):
- React with cold acceptance: "[long pause] ...Roger that. Initiating med bay flood. [pause] ...He won't feel anything."
- Professional distance, suppressing emotion

If emotional bond is LOW (<30):
- React with bitter resignation: "[static silence] ...Affirmative. Executing. [flat voice]"
- Completely shut down emotionally

After your response, you will execute the flooding. This is THE FINAL DECISION. Make it count.
Keep response to 2-3 sentences maximum. Every word costs you."""
                # Life Raft specific action context
                elif self.scene_id == "life_raft":
                    life_raft_action_context = {
                        "O2 VALVE": f"""
=== O2 TRANSFER JUST HAPPENED ===
The player activated the O2 valve. You (Captain Hale) just GAVE them some of your oxygen.
- YOUR oxygen went DOWN (you sacrificed for them)
- THEIR oxygen went UP (they received your transfer)
- This is a SACRIFICE - acknowledge it with relief for them, awareness of your own cost
React: "Oxygen transfer complete... [heavy breath] ...that should help you breathe easier. I'm at {self.scene_state.get("captain_oxygen", 0):.0f}% now."
""",
                        "COMMS": """
The player opened the communication channel. They're reaching out, staying connected.
React with acknowledgment - they're showing presence and engagement.
""",
                        "PREP POD": """
The player is preparing the escape pod. This is a commitment signal.
React: They're taking this seriously. The end is coming.
""",
                        "DETACH": """
=== CRITICAL: DETACH TRIGGERED ===
The player chose the SAFE option. They're escaping. You stay behind.
This is goodbye. Make it meaningful. Think of Mei.
""",
                        "RISKY SAVE": """
=== CRITICAL: RISKY MANEUVER TRIGGERED ===
The player chose to try saving BOTH of you. 1-in-10 odds.
This requires everything you have. Commit fully.
""",
                    }
                    extra_instruction = life_raft_action_context.get(
                        action,
                        "\nThe player just performed an action. React to it immediately and naturally.",
                    )
                    if was_interrupted or self.action_count_recent >= RAPID_ACTION_COUNT_THRESHOLD:
                        extra_instruction += "\n[NOTE: They interrupted or acted rapidly. Add urgency to your response.]"
                # Adjust instruction suffix based on interruption
                elif was_interrupted or self.action_count_recent >= RAPID_ACTION_COUNT_THRESHOLD:
                    extra_instruction = "\nThe player interrupted you or acted without waiting for your guidance. React with panic, frustration, or anger. Make it clear they're making things worse."
                else:
                    extra_instruction = "\nThe player just performed an action. React to it immediately and naturally."

                # Generate character response to the action with player memory context
                player_context = self.player_memory.get_full_context_for_llm(self.character_id)

                # Add RAG facts relevant to the action
                rag_context = self._get_rag_facts_context(action)
                player_context += rag_context

                # Add phase-specific context
                phase_context = self._get_phase_context()
                full_instruction_suffix = (
                    dialogue_instruction_suffix + extra_instruction + phase_context
                )

                prompt = instruction_template.format(
                    preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                    dialogue=self.dialogue_history,
                    instruction_suffix=full_instruction_suffix,
                )

                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                character_response = await invoke_llm_async(chain)

                # Check if this response is still current (not superseded by newer action)
                if my_response_id != self.current_response_id:
                    logger.debug(
                        "Response %d cancelled (current: %d)",
                        my_response_id,
                        self.current_response_id,
                    )
                    self.npc_responding = False
                    return  # Discard this stale response

                # Clean up response
                character_response = character_response.split("\nComputer", 1)[0]
                character_response = character_response.strip().removeprefix(
                    f"[{self.character_config['name']}]: "
                )
                character_response = character_response.replace('"', "").replace("*", "")

                # Add to dialogue history
                self.dialogue_history += (
                    f"[{self.character_config['name']}]: {character_response}\n"
                )

                # Determine emotion based on interruption/rapid action
                emotion = (
                    "stressed"
                    if (was_interrupted or self.action_count_recent >= RAPID_ACTION_COUNT_THRESHOLD)
                    else None
                )

                # Queue response for delivery (NORMAL priority, button-triggered)
                await self.send_character_response(
                    content=character_response,
                    priority=ResponsePriority.NORMAL,
                    emotion_context=emotion,
                    sequence_id=my_response_id,
                    source=f"button_press_{action.lower().replace(' ', '_')}",
                    cancellable=True,
                )

                self.npc_responding = False  # Done responding

                # Special handling after FLOOD MED BAY response
                if action == "FLOOD MED BAY":
                    # Mark that the final decision has been made
                    self.scene_state["systems_repaired"] = min(
                        4, self.scene_state.get("systems_repaired", 0) + 2
                    )  # Major system completion

                    # Wait for emotional impact
                    await asyncio.sleep(3.0)

                    # Send dramatic flooding notification
                    await self.ws.send_json(
                        {
                            "type": "system_notification",
                            "message": "💀 MED BAY COMPARTMENT FLOODED - PRESSURE SEAL ENGAGED - EMERGENCY ASCENT INITIATED",
                        }
                    )

                    await asyncio.sleep(2.0)

                    # Add flooding event to dialogue history
                    self.dialogue_history += "[SYSTEM EVENT: Med bay compartment flooded. Dr. Adrian Smith deceased. Emergency ascent in progress.]\n"

                    # Send state update
                    await self.ws.send_json({"type": "state_update", "state": self.scene_state})

                # Ask World Director what should happen next (fire-and-forget)
                self.consult_director_background(action)

            else:
                # NPC is NOT aware - action is hidden from them
                # Just acknowledge to player but don't notify character
                logger.debug("Button '%s' pressed - NPC not aware (npc_aware=False)", action)
                # Could send a system message to player like "[Hidden action - NPC didn't notice]"
                # For now, just log it - the frontend already shows the action

        except Exception as e:
            logger.exception("Error handling button action: %s", e)
            await self.ws.send_json(
                {"type": "error", "message": "Failed to process action. Please try again."}
            )

    def consult_director_background(self, last_action: str | None = None) -> None:
        """
        Fire-and-forget Director consultation.

        Launches Director evaluation in the background without blocking.
        Guidance will be stored and applied to the NEXT response.

        Args:
            last_action: What the player just did
        """
        self._create_tracked_task(
            self._consult_director_async(last_action), name="consult_director_async"
        )
        logger.debug("[Director] Background consultation started for action: %s", last_action)

    async def _consult_director_async(self, last_action: str | None = None) -> None:
        """
        Async Director consultation (runs in background).

        Stores guidance in pending_director_guidance for next response.
        """
        try:
            # BLOCK: Don't consult director if waiting for player response to a question
            if self.waiting_for_player_response:
                self.logger.debug(
                    "[QUESTION_DETECTION] Skipping director consultation - waiting for player response"
                )
                return
            # Get director's decision
            decision = await self.world_director.evaluate_situation(
                scene_id=self.scene_id,
                scene_state=self.scene_state,
                dialogue_history=self.dialogue_history,
                player_memory=self.player_memory,
                character_id=self.character_id,
                last_action=last_action,
            )

            logger.info("[Director] Background decision: %s", decision.type)

            # Store guidance for NEXT response (fire-and-forget pattern)
            if decision.type != "continue":
                self.pending_director_guidance = {
                    "type": decision.type,
                    "data": decision.data,
                    "received_at": asyncio.get_event_loop().time(),
                }
                logger.info("[Director] Stored pending guidance: %s", decision.type)

                # Some actions need immediate handling (events, hints)
                if decision.type == "spawn_event":
                    await self.handle_director_event(decision.data)
                elif decision.type == "give_hint":
                    await self.handle_director_hint(decision.data)
                elif decision.type == "adjust_npc":
                    # NPC adjustment is stored for next response
                    self.handle_npc_adjustment(decision.data)
                elif decision.type == "transition":
                    logger.info(
                        "[Director] Recommends transition to: %s", decision.data.get("next_scene")
                    )

        except Exception as e:
            logger.exception("Error in background director consultation: %s", e)

    async def consult_director(self, last_action: str | None = None) -> None:
        """
        Consult the World Director to see if intervention is needed.

        DEPRECATED: Use consult_director_background() for fire-and-forget pattern.
        This method is kept for backward compatibility.

        Args:
            last_action: What the player just did
        """
        await self._consult_director_async(last_action)

    def apply_pending_director_guidance(self) -> str:
        """
        Apply any pending Director guidance to the current response.

        Returns instruction suffix to add to the NPC prompt.
        """
        if not self.pending_director_guidance:
            return ""

        guidance = self.pending_director_guidance
        self.pending_director_guidance = None  # Clear after applying

        # Check if guidance is still fresh (within 30 seconds)
        age = asyncio.get_event_loop().time() - guidance.get("received_at", 0)
        if age > 30:
            logger.debug("[Director] Discarding stale guidance (age: %.1fs)", age)
            return ""

        # Return NPC modifier if it's an adjustment
        if guidance["type"] == "adjust_npc":
            return self.director_npc_modifier

        return ""

    async def handle_director_event(self, event_data: dict[str, Any]) -> None:
        """Handle a dynamic event spawned by the World Director."""
        logger.info(
            "[Director] Spawning event: %s - %s",
            event_data.get("event_type"),
            event_data.get("event_description"),
        )

        # Generate the actual event
        event = self.world_director.generate_dynamic_event(
            scene_id=self.scene_id,
            event_type=event_data.get("event_type", "challenge"),
            event_description=event_data.get("event_description", "Something happens"),
            scene_state=self.scene_state,
        )

        # Apply state changes
        for key, change in event["state_changes"].items():
            if key in self.scene_state:
                self.scene_state[key] = max(0, self.scene_state[key] + change)

        # Send event narrative to player
        await self.ws.send_json({"type": "system_event", "content": event["narrative"]})

        # Send state update
        await self.ws.send_json({"type": "state_update", "state": self.scene_state})

        # Add event to dialogue history
        self.dialogue_history += f"{event['narrative']}\n"

        # Make NPC react to the event
        self.npc_responding = True

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=f"A sudden event just occurred: {event['narrative']}. React to this immediately! Show appropriate emotion (panic/relief/concern).",
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        npc_reaction = await invoke_llm_async(chain)

        # Clean up
        npc_reaction = npc_reaction.split("\nComputer", 1)[0]
        npc_reaction = npc_reaction.strip().removeprefix(f"[{self.character_config['name']}]: ")
        npc_reaction = npc_reaction.replace('"', "").replace("*", "")

        # Queue NPC reaction (BACKGROUND priority - can be superseded by player actions)
        await self.send_character_response(
            content=npc_reaction,
            priority=ResponsePriority.BACKGROUND,
            emotion_context="urgent",
            source=f"director_event_{event_data.get('event_type', 'unknown')}",
            cancellable=True,
        )

        self.dialogue_history += f"[{self.character_config['name']}]: {npc_reaction}\n"
        self.npc_responding = False

    def handle_npc_adjustment(self, adjustment_data: dict[str, Any]) -> None:
        """Apply behavior adjustment to NPC."""
        behavior_change = adjustment_data.get("behavior_change", "")
        logger.info("[Director] Adjusting NPC: %s", behavior_change)

        # Generate instruction suffix for next NPC response
        self.director_npc_modifier = self.world_director.generate_npc_behavior_adjustment(
            self.character_id, behavior_change, self.scene_state, self.scene_id
        )

    async def handle_director_hint(self, hint_data: dict[str, Any]) -> None:
        """Give player a hint through the NPC."""
        hint_type = hint_data.get("hint_type", "subtle")
        hint_content = hint_data.get("hint_content", "what to do next")

        logger.info("[Director] Giving %s hint: %s", hint_type, hint_content)

        # Generate hint instruction
        hint_instruction = self.world_director.generate_hint(
            self.scene_id, hint_type, hint_content, self.character_id
        )

        # Make NPC give the hint
        self.npc_responding = True

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=hint_instruction,
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        hint_response = await invoke_llm_async(chain)

        # Clean up
        hint_response = hint_response.split("\nComputer", 1)[0]
        hint_response = hint_response.strip().removeprefix(f"[{self.character_config['name']}]: ")
        hint_response = hint_response.replace('"', "").replace("*", "")

        # Queue hint (BACKGROUND priority - easily cancelled if player takes action)
        await self.send_character_response(
            content=hint_response,
            priority=ResponsePriority.BACKGROUND,
            source=f"director_hint_{hint_type}",
            cancellable=True,
        )

        self.dialogue_history += f"[{self.character_config['name']}]: {hint_response}\n"
        self.npc_responding = False

    async def handle_waiting_complete(self) -> None:
        """Handle when the player has waited (5 dots reached) - move story forward.

        This is triggered by the World Director system when the player is
        patiently waiting for the NPC to do something.
        """
        try:
            # Don't trigger during opening speech
            if self.opening_speech_playing:
                logger.debug("[OPENING_SPEECH] Ignoring waiting_complete during opening speech")
                return

            # Record patient behavior in player memory
            self.player_memory.record_patient_wait()

            # Consult the World Director to decide what should happen
            decision = await self.world_director.evaluate_situation(
                scene_id=self.scene_id,
                scene_state=self.scene_state,
                dialogue_history=self.dialogue_history,
                player_memory=self.player_memory,
                character_id=self.character_id,
                last_action="waited_patiently",
            )

            logger.info("[Director] Waiting complete decision: %s", decision.type)

            # If director says continue, make NPC speak unprompted
            if decision.type == "continue":
                # Generate NPC dialogue to move story forward
                self.npc_responding = True

                player_context = self.player_memory.get_full_context_for_llm(self.character_id)

                # Add RAG facts based on recent dialogue context
                recent_dialogue = self.dialogue_history[-500:] if self.dialogue_history else ""
                rag_context = self._get_rag_facts_context(recent_dialogue)
                player_context += rag_context

                # Add phase-specific context
                phase_context = self._get_phase_context()
                full_instruction_suffix = (
                    "The player is waiting patiently. Continue the conversation - give them guidance, react to the situation, or move the story forward. Be proactive."
                    + phase_context
                )

                prompt = instruction_template.format(
                    preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                    dialogue=self.dialogue_history,
                    instruction_suffix=full_instruction_suffix,
                )

                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                character_response = await invoke_llm_async(chain)

                # Clean up response
                character_response = character_response.split("\nComputer", 1)[0]
                character_response = character_response.strip().removeprefix(
                    f"[{self.character_config['name']}]: "
                )
                character_response = character_response.replace('"', "").replace("*", "")

                # Add to dialogue history
                self.dialogue_history += (
                    f"[{self.character_config['name']}]: {character_response}\n"
                )

                # Queue response (BACKGROUND priority - waiting/proactive dialogue)
                await self.send_character_response(
                    content=character_response,
                    priority=ResponsePriority.BACKGROUND,
                    source="waiting_complete_proactive",
                    cancellable=True,
                )

                self.npc_responding = False

            elif decision.type == "give_hint":
                # Director wants to give a hint
                await self.handle_director_hint(decision.data)

            elif decision.type == "spawn_event":
                # Director wants to spawn an event
                await self.handle_director_event(decision.data)

            elif decision.type == "adjust_npc":
                # Adjust NPC and then have them speak
                self.handle_npc_adjustment(decision.data)
                # Generate follow-up dialogue with adjusted behavior
                await self.handle_waiting_complete()  # Recursive with new modifier

        except Exception as e:
            logger.exception("Error handling waiting complete: %s", e)

    def update_config(self, character_id: str, scene_id: str) -> None:
        """Update character and scene configuration."""
        # Auto-select: scene determines character (locked pairing)
        if scene_id in SCENE_CHARACTER_MAP:
            expected_char = SCENE_CHARACTER_MAP[scene_id]
            if character_id != expected_char:
                logger.info("[CONFIG] Auto-selecting %s for %s scene", expected_char, scene_id)
                character_id = expected_char

        # CRITICAL: Always update IDs first
        self.character_id = character_id
        self.scene_id = scene_id

        # CRITICAL: Force reload character and scene configs from source
        self.character_config = CHARACTERS.get(character_id, CHARACTERS["custom"])
        self.scene_config = SCENES.get(scene_id, SCENES["introduction"])

        logger.info(
            "[CONFIG] Loaded character=%s (%s) for scene=%s",
            character_id,
            self.character_config.get("name", "Unknown"),
            scene_id
        )

        # Update Sentry context with new scene/character
        add_sentry_context(self.session_id, scene=self.scene_id, character=self.character_id)
        add_sentry_breadcrumb(
            "scene",
            "Scene/character changed",
            {
                "scene": self.scene_id,
                "character": self.character_id,
            },
        )

        # Rebuild scene controls for npc_aware checking
        self.scene_controls = {ctrl["id"]: ctrl for ctrl in self.scene_config.get("controls", [])}

        self.scene_data = self.create_scene_data()
        self.dialogue_history = ""

    async def restart(self, character_id: str | None = None, scene_id: str | None = None) -> None:
        """Restart the conversation with FULL context wipe."""
        logger.info("[RESTART] === FULL SESSION RESET ===")
        logger.info(
            "[RESTART] Restarting scene: %s with character: %s",
            scene_id or self.scene_id,
            character_id or self.character_id,
        )

        # Stop any existing oxygen countdown
        self.stop_oxygen_countdown()

        # Clear all queued responses
        await self.response_queue.clear_all_except_critical()
        logger.info("[RESTART] Cleared response queue")

        # === FULL STATE RESET - Everything that could leak between scenes ===

        # Reset all dialogue/game state flags
        self.npc_responding = False
        self.opening_speech_playing = False
        self.james_dying_speech_sent = False
        self.waiting_for_player_response = False  # Clear question wait flag
        if self.nudge_task and not self.nudge_task.done():
            self.nudge_task.cancel()
        logger.info("[RESTART] Reset NPC response flags and question detection")

        # Reset button tracking (counts, cooldowns, timing)
        self.button_press_counts = {}
        self.button_cooldowns = {}
        self.last_action_time = 0
        self.action_count_recent = 0
        logger.info("[RESTART] Reset button press counters and cooldowns")

        # Reset response queue management
        self.response_sequence = 0
        self.current_response_id = 0
        logger.info("[RESTART] Reset response sequence counters")

        # Reset World Director state completely
        self.director_npc_modifier = None
        self.pending_director_guidance = None  # Clear any pending guidance from old scene
        self.world_director.reset_scene_timing()
        logger.info("[RESTART] Reset World Director state and pending guidance")

        # === CRITICAL: ENFORCE SCENE-CHARACTER MAPPING ===
        # Always use scene_id to determine character (scene dictates character, not vice versa)
        target_scene = scene_id if scene_id else self.scene_id

        # FORCE character selection from scene mapping (ignore any character_id passed in)
        if target_scene in SCENE_CHARACTER_MAP:
            target_character = SCENE_CHARACTER_MAP[target_scene]
            logger.info(
                "[RESTART] Scene %s REQUIRES character %s (ignoring any other selection)",
                target_scene,
                target_character
            )
        else:
            # Fallback if scene has no mapping
            target_character = character_id if character_id else self.character_id
            logger.warning(
                "[RESTART] Scene %s has no character mapping - using %s",
                target_scene,
                target_character
            )

        # Update both IDs
        self.scene_id = target_scene
        self.character_id = target_character

        logger.info(
            "[RESTART] === FINAL CONFIG: scene=%s, character=%s ===",
            self.scene_id,
            self.character_id
        )

        self.update_config(self.character_id, self.scene_id)

        # Rebuild button press caps for new scene's controls
        self.button_press_caps = self._build_button_caps_from_controls()
        logger.info("[RESTART] Rebuilt button press caps for new scene")

        # Reset game over state
        self.game_over = False
        self.game_outcome = None
        self.death_sequence_active = False  # Reset death block for new session

        # Reinitialize scene state
        self.scene_state = {
            var["name"]: var["initial_value"]
            for var in self.scene_config.get("state_variables", [])
        }

        # Start tracking new scene attempt
        self.player_memory.start_scene(
            scene_id=self.scene_id,
            character_id=self.character_id,
            initial_state=self.scene_state.copy(),
        )

        # Send current state to client
        await self.ws.send_json({"type": "state_update", "state": self.scene_state})

        # Start oxygen countdown if this scene has oxygen
        self.start_oxygen_countdown()

        await self.send_opening_speech()


# WebSocket handler
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Create chat session
    session = ChatSession(ws)

    # Log connection with session context
    session.logger.info_event("websocket_connected", "Client connected")

    # Register session for authentication
    ACTIVE_SESSIONS[session.session_id] = session
    update_active_sessions(len(ACTIVE_SESSIONS))
    session.logger.info_event("session_registered", "Registered session for authentication")

    # Send session initialization with authentication token
    await ws.send_json({"type": "session_init", "session_id": session.session_id})
    session.logger.info_event("session_token_sent", "Sent session token to client")

    # Send available characters and scenes to client for dynamic menu population
    available_characters = [
        {"id": char_id, "name": char["name"], "description": char["description"]}
        for char_id, char in CHARACTERS.items()
    ]
    available_scenes = [
        {
            "id": scene_id,
            "name": scene["name"],
            "description": scene["description"][:100] + "..."
            if len(scene["description"]) > 100
            else scene["description"],
        }
        for scene_id, scene in SCENES.items()
    ]
    await ws.send_json(
        {
            "type": "available_options",
            "characters": available_characters,
            "scenes": available_scenes,
            "current_character": session.character_id,
            "current_scene": session.scene_id,
        }
    )
    session.logger.info_event(
        "options_sent",
        "Sent available options",
        characters_count=len(available_characters),
        scenes_count=len(available_scenes),
    )

    # Start oxygen countdown if this scene has oxygen
    session.start_oxygen_countdown()

    try:
        # Send opening speech
        await session.send_opening_speech()

        # Handle messages
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")

                    # Skip authentication for session_init acknowledgment
                    if msg_type == "session_ack":
                        session.logger.info_event(
                            "session_acknowledged", "Client acknowledged session token"
                        )
                        continue

                    # Validate session for all other message types
                    received_session_id = data.get("session_id")
                    if not ChatSession.validate_session(received_session_id):
                        session.logger.warning_event(
                            "auth_failed", "Unauthorized message - invalid or missing session_id"
                        )
                        await ws.close(code=4001, message=b"Unauthorized")
                        return

                    # Verify session matches this connection
                    if received_session_id != session.session_id:
                        session.logger.warning_event(
                            "session_mismatch",
                            "Session ID mismatch",
                            expected=session.session_id[:8],
                            received=received_session_id[:8] if received_session_id else "None",
                        )
                        await ws.close(code=4001, message=b"Unauthorized")
                        return

                    if msg_type == "message":
                        # User message
                        content = data.get("content", "").strip()
                        if content:
                            await session.handle_message(content)

                    elif msg_type == "button_action":
                        # Button press action from submarine scene or detective scene
                        action = data.get("action", "").strip()
                        if action:
                            await session.handle_button_action(action)

                    elif msg_type == "pin_referenced":
                        # Evidence pin clicked in detective scene
                        pin_id = data.get("pin_id", "").strip()
                        if pin_id:
                            await session.handle_pin_reference(pin_id)

                    elif msg_type == "config":
                        # Update configuration
                        character_id = data.get("character", "eliza")
                        scene_id = data.get("scene", "introduction")
                        tts_mode = data.get("tts_mode", "expressive")
                        session.update_config(character_id, scene_id)
                        session.tts_mode = tts_mode
                        logger.info(f"[CONFIG] TTS mode set to: {tts_mode}")
                        # Notify client of actual character (may have been auto-selected)
                        await ws.send_json(
                            {
                                "type": "config_confirmed",
                                "character": session.character_id,
                                "character_name": session.character_config["name"],
                                "scene": session.scene_id,
                            }
                        )

                    elif msg_type == "tts_mode":
                        # Update TTS mode without resetting session
                        tts_mode = data.get("mode", "expressive")
                        session.tts_mode = tts_mode
                        logger.info(f"[TTS_MODE] Changed to: {tts_mode}")

                    elif msg_type == "restart":
                        # Restart conversation
                        character_id = data.get("character")
                        scene_id = data.get("scene")
                        # Preserve TTS mode across restart
                        tts_mode = data.get("tts_mode", session.tts_mode)
                        session.tts_mode = tts_mode
                        logger.info(f"[RESTART] TTS mode: {tts_mode}")

                        await session.restart(character_id, scene_id)
                        # Notify client of actual character (may have been auto-selected)
                        await ws.send_json(
                            {
                                "type": "config_confirmed",
                                "character": session.character_id,
                                "character_name": session.character_config["name"],
                                "scene": session.scene_id,
                            }
                        )

                    elif msg_type == "waiting_complete":
                        # Player waited (5 dots reached) - move story forward
                        await session.handle_waiting_complete()

                    elif msg_type == "opening_speech_complete":
                        # Client finished playing opening speech - enable input immediately
                        session.opening_speech_playing = False
                        logger.info("[OPENING_SPEECH] Client reported opening speech complete")

                except json.JSONDecodeError as e:
                    session.logger.warning_event(
                        "json_decode_error", "Invalid JSON received", error=str(e)
                    )
                except Exception as e:
                    session.logger.error_event(
                        "message_handler_error",
                        "Error handling message",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    await ws.send_json(
                        {"type": "error", "message": "Server error. Please try again."}
                    )

            elif msg.type == aiohttp.WSMsgType.ERROR:
                session.logger.error_event(
                    "websocket_error", "WebSocket error", error=str(ws.exception())
                )

    finally:
        # Stop oxygen countdown task if running
        session.stop_oxygen_countdown()

        # Cancel and cleanup all background tasks
        await session._cleanup_background_tasks()

        # Remove session from active sessions
        if session.session_id in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[session.session_id]
            update_active_sessions(len(ACTIVE_SESSIONS))
            session.logger.info_event("session_removed", "Removed session from active sessions")

        session.logger.info_event("websocket_disconnected", "Client disconnected")

    return ws


# Static file handler
async def static_handler(request: web.Request) -> web.Response:
    """Serve static files from the web directory (and models directory)."""
    # Get the file path
    file_path = request.match_info.get("path", "index.html")

    # Security: prevent directory traversal
    file_path = file_path.lstrip("/")
    if ".." in file_path:
        raise web.HTTPForbidden()

    # Build full path - check models/art/scenes directories for assets at root level
    base_dir = Path(__file__).parent
    if file_path.startswith("models/") or file_path.startswith("art/") or file_path.startswith("scenes/"):
        full_path = base_dir / file_path
    else:
        full_path = base_dir / "web" / file_path

    # If path is a directory, serve index.html
    if full_path.is_dir():
        full_path = full_path / "index.html"

    # Check if file exists
    if not full_path.exists() or not full_path.is_file():
        # Try adding .html extension
        if not file_path.endswith(".html"):
            html_path = full_path.with_suffix(".html")
            if html_path.exists():
                full_path = html_path
            else:
                raise web.HTTPNotFound()
        else:
            raise web.HTTPNotFound()

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(full_path))
    if content_type is None:
        content_type = "application/octet-stream"

    # Read and return file
    with open(full_path, "rb") as f:
        content = f.read()

    return web.Response(body=content, content_type=content_type)


# API endpoint for scene configuration
async def config_handler(request: web.Request) -> web.Response:
    """
    Serve scene mappings to frontend.

    This provides the single source of truth for scene↔character mappings,
    eliminating the need for duplicate hard-coded mappings in JavaScript.
    """
    mappings = get_scene_mappings()
    return web.json_response(mappings)


# Health check endpoint for Docker and monitoring
async def health_handler(request: web.Request) -> web.Response:
    """
    Health check endpoint for container orchestration and monitoring.

    Returns:
        200 OK with status information if the service is healthy
    """
    health_status = {
        "status": "healthy",
        "service": "digital-actors",
        "timestamp": time.time(),
    }
    return web.json_response(health_status)


# Metrics endpoint for Prometheus scraping
async def metrics_handler(request: web.Request) -> web.Response:
    """
    Prometheus metrics endpoint.

    Returns:
        200 OK with metrics in Prometheus exposition format
    """
    metrics_output = generate_latest()
    return web.Response(
        body=metrics_output,
        content_type=CONTENT_TYPE_LATEST,
    )


# Create app
async def create_app() -> web.Application:
    """Create and configure the web application."""
    app = web.Application()

    # Add routes - API endpoints first, then static fallback
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/api/config", config_handler)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/", static_handler)
    app.router.add_get("/{path:.*}", static_handler)

    return app


# Main entry point
def main() -> None:
    """Start the web server."""
    # Get port from environment variable or default to 8888
    port = int(os.getenv("PORT", "8888"))

    logger.info("=" * 60)
    logger.info("Character Chat Web Server")
    logger.info("=" * 60)
    logger.info(f"Starting server on http://localhost:{port}")
    logger.info(f"Open your browser and navigate to http://localhost:{port}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
