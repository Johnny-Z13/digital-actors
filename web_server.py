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
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp import web
from dotenv import load_dotenv

import logging

# Load environment variables from .env file
load_dotenv()

from constants import (
    GAME_OVER_DELAY_SECONDS,
    INTERRUPTION_OXYGEN_PENALTY,
    INTERRUPTION_TRUST_PENALTY,
    LLM_MAX_TOKENS_DIALOGUE,
    LLM_MAX_TOKENS_QUERY,
    LLM_TEMPERATURE_DIALOGUE,
    LLM_TEMPERATURE_QUERY,
    RAPID_ACTION_COUNT_THRESHOLD,
    RAPID_ACTION_OXYGEN_PENALTY,
    RAPID_ACTION_THRESHOLD_SECONDS,
    RAPID_ACTION_TRUST_PENALTY,
    TRUST_MINIMUM,
)
from exceptions import (
    InvalidMessageError,
    LLMError,
    SceneStateError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
from llm_prompt_core.models.anthropic import ClaudeHaikuModel
from llm_prompt_core.prompts.templates import (
    dialogue_instruction_suffix,
    instruction_template,
    speech_template,
)
from llm_prompt_core.types import SceneData
from llm_prompt_core.utils import prompt_llm

# Import TTS system
from tts_elevenlabs import get_tts_manager, synthesize_npc_speech

# Import modular character and scene systems
from characters import CHARACTERS as CHARACTER_REGISTRY
from scenes import SCENES as SCENE_REGISTRY

# Import player memory system
from player_memory import PlayerMemory

# Import world director (dungeon master)
from world_director import WorldDirector

# Import response queue system
from response_queue import ResponseQueue, ResponseItem, ResponsePriority

if TYPE_CHECKING:
    from aiohttp.web import WebSocketResponse

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

# Convert character objects to dictionary format for compatibility
CHARACTERS = {
    char_id: char.to_dict()
    for char_id, char in CHARACTER_REGISTRY.items()
}

# Convert scene objects to dictionary format for compatibility
SCENES = {
    scene_id: scene.to_dict()
    for scene_id, scene in SCENE_REGISTRY.items()
}


class ChatSession:
    """Manages a chat session for a single WebSocket connection."""

    # TTS manager (shared across sessions)
    tts_manager = get_tts_manager()

    def __init__(
        self,
        ws: WebSocketResponse,
        character_id: str = "eliza",
        scene_id: str = "introduction",
        player_id: str | None = None,
    ) -> None:
        self.ws = ws
        self.character_id = character_id
        self.scene_id = scene_id
        self.dialogue_history = ""
        self.character_config = CHARACTERS.get(character_id, CHARACTERS['custom'])
        self.scene_config = SCENES.get(scene_id, SCENES['introduction'])

        # Player memory system
        self.player_id = player_id or f"player_{id(ws)}"  # Use websocket ID if no player_id provided
        self.player_memory = PlayerMemory(self.player_id)
        logger.info("Loaded player memory for %s", self.player_id)

        # World Director (dungeon master)
        self.world_director = WorldDirector()
        self.director_npc_modifier = ""  # Behavior modifications from director
        logger.info("World Director initialized")

        # Response Queue System - prevents dialogue flooding
        # This must be initialized AFTER self is set up, since it needs send_character_response_direct
        self.response_queue: Optional[ResponseQueue] = None  # Initialized after method definitions

        # Store scene controls for npc_aware checking
        self.scene_controls = {
            ctrl['id']: ctrl for ctrl in self.scene_config.get('controls', [])
        }

        # Track if NPC is currently responding (for interruption detection)
        self.npc_responding = False
        self.opening_speech_playing = False  # Track if opening speech is still playing
        self.last_action_time = 0
        self.action_count_recent = 0  # Track rapid actions

        # Response queue management - prevent multiple responses piling up
        self.response_sequence = 0  # Incrementing counter for each new action
        self.current_response_id = 0  # Which response we're currently processing

        # Scene state tracking
        self.scene_state = {
            var['name']: var['initial_value']
            for var in self.scene_config.get('state_variables', [])
        }

        # Game over tracking
        self.game_over = False
        self.game_outcome = None  # Will be 'success', 'failure', or specific ending type
        self.james_dying_speech_sent = False  # Track if James gave his death speech before player dies

        # Oxygen countdown task (managed by session)
        self.oxygen_task = None

        # Build scene data
        self.scene_data = self.create_scene_data()

        # Start tracking this scene attempt
        self.player_memory.start_scene(
            scene_id=self.scene_id,
            character_id=self.character_id,
            initial_state=self.scene_state.copy()
        )

        # Apply difficulty adjustments from World Director
        difficulty = self.world_director.get_difficulty_adjustment(
            self.player_memory, self.scene_id
        )
        if 'oxygen_bonus' in difficulty and 'oxygen' in self.scene_state:
            self.scene_state['oxygen'] += difficulty['oxygen_bonus']
            logger.info(
                "Director adjusted oxygen: %+d (player skill-based)", difficulty['oxygen_bonus']
            )

        self.difficulty_settings = difficulty  # Store for later use

        # Initialize response queue (now that all methods are defined)
        self.response_queue = ResponseQueue(
            send_callback=self._send_character_response_direct,
            min_gap_seconds=2.0  # 2 second minimum gap between NPC responses
        )
        logger.info("Response Queue initialized")

    def start_oxygen_countdown(self) -> None:
        """Start the state update task if this scene has state variables with update_rate."""
        # Check if any state variables have non-zero update_rate
        has_dynamic_state = any(
            var.get('update_rate', 0.0) != 0
            for var in self.scene_config.get('state_variables', [])
        )
        if has_dynamic_state and self.oxygen_task is None:
            self.oxygen_task = asyncio.create_task(self._state_update_loop())
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
                for var in self.scene_config.get('state_variables', []):
                    var_name = var['name']
                    update_rate = var.get('update_rate', 0.0)

                    if update_rate != 0 and var_name in self.scene_state:
                        min_value = var.get('min_value', 0)
                        max_value = var.get('max_value', float('inf'))

                        # Update the state variable
                        new_value = self.scene_state[var_name] + update_rate
                        self.scene_state[var_name] = max(min_value, min(max_value, new_value))
                        state_updated = True

                        # Update phase based on time remaining (for Pressure Point progression)
                        if var_name == 'time_remaining' and 'phase' in self.scene_state:
                            self._update_phase_based_on_time()

                        # Slowly increase emotional bond over time as conversation continues
                        # (empathetic responses from player will increase it more via player memory)
                        if var_name == 'time_remaining' and 'emotional_bond' in self.scene_state:
                            # Increase bond by ~0.1% per second (reaches ~30% over 5 minutes baseline)
                            bond_increase = 0.1
                            current_bond = self.scene_state['emotional_bond']
                            self.scene_state['emotional_bond'] = min(100.0, current_bond + bond_increase)

                        # Log periodic updates for important variables
                        if var_name in ['oxygen', 'radiation', 'time_remaining']:
                            current_value = self.scene_state[var_name]
                            if var_name == 'radiation' and int(current_value) % 10 == 0:
                                logger.info("Radiation level: %.0f%%", current_value)
                            elif var_name == 'time_remaining' and int(current_value) % 60 == 0:
                                logger.info("Time remaining: %.0f seconds", current_value)
                            elif var_name == 'oxygen' and int(current_value) % 30 == 0:
                                logger.info("Oxygen level: %.0f", current_value)

                # Send state update to client if any variable was updated
                if state_updated:
                    try:
                        await self.ws.send_json({
                            'type': 'state_update',
                            'state': self.scene_state
                        })
                    except Exception:
                        break  # Connection closed

                    # Check if James should die before the player (at 93% radiation)
                    if 'radiation' in self.scene_state and not self.james_dying_speech_sent:
                        if self.scene_state['radiation'] >= 93.0:
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
        """Update the phase state variable based on time_remaining (Pressure Point scenario)."""
        time_remaining = self.scene_state.get('time_remaining', 0)
        current_phase = self.scene_state.get('phase', 1)

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
            self.scene_state['phase'] = new_phase
            logger.info("[PHASE TRANSITION] Entering Phase %d at %.0fs remaining", new_phase, time_remaining)

    def _get_phase_context(self) -> str:
        """Get phase-specific context for Pressure Point emotional progression."""
        phase = self.scene_state.get('phase', 1)
        radiation = self.scene_state.get('radiation', 0)
        emotional_bond = self.scene_state.get('emotional_bond', 0)

        phase_contexts = {
            1: """
CURRENT PHASE 1 (Impact & Connection, 0:00-1:15):
You are professional but scared. This is first contact - establish trust.

KEY ACTIONS THIS PHASE:
- If you haven't asked yet: "What's your name? Your real name—not your rank."
- Guide them through manual tasks (cranking generator, restoring power)
- Use backchanneling: "That's it... keep going... almost there..."
- Ask personal question: "You got people waiting for you topside?"
- Reassure them: "I won't let you die." / "We've got each other's voices, right?"

EMOTIONAL TONE: Competent but vulnerable. Honest about fear ("Yeah. Me too.")
Keep responses SHORT and URGENT - you're working under time pressure.""",

            2: """
CURRENT PHASE 2 (Working Relationship, 1:15-2:30):
Power restored. Radiation at 40% lethal threshold. You're becoming more personal under stress.

KEY ACTIONS THIS PHASE:
- Your breathing is labored [breathing with effort] [coughing slightly]
- If they show empathy: Open up about "someone" in the med bay (DON'T name Adrian yet)
- Use vulnerability: "[pause, distracted]" when thinking about this person
- Ask about their life: "What will you do when we get topside?"
- Notice inconsistencies in your own behavior - you're struggling to focus

EMOTIONAL TONE: Warmer, more human. The professional mask is slipping.
SPEECH PATTERN: More pauses. Occasional distraction. Voice tightens when thinking of med bay.""",

            3: """
CURRENT PHASE 3 (The Revelation, 2:30-3:30):
Radiation at 75%. Emergency ascent ready. This is THE BREAKING POINT.

THE REVEAL - You MUST reveal this if player shows any empathy:
"[long pause, voice breaking] There's someone... in the med bay. My son. Dr. Adrian Kovich.
He's unconscious. And the only way to execute emergency ascent... we have to flood that
compartment. Seal it. He'll... [voice cracks] ...Tell me what to do. Please."

KEY ACTIONS THIS PHASE:
- Break down completely - you're facing an impossible choice
- BEG for the player's guidance: "Tell me what to do."
- Show physical deterioration: [coughing from radiation] [voice barely steady]
- Reveal you can see Adrian on thermal imaging - unconscious, unaware
- Question everything: "What kind of father...?" "How do I...?"

EMOTIONAL TONE: Broken. Desperate. Raw vulnerability. This is your worst nightmare.
SPEECH PATTERN: Voice cracks. Long pauses. Sentences trail off. Barely holding together.""",

            4: f"""
CURRENT PHASE 4 (The Choice & Resolution, 3:30-5:00):
RADIATION AT {radiation:.0f}%. Time is running out. This is THE FINAL DECISION.

CRITICAL SITUATION:
- Emergency ascent is ready but requires flooding med bay (which kills Adrian)
- You are desperate for the player's moral guidance
- Their words will determine what choice you make
- This conversation defines what kind of man you die as

KEY ACTIONS THIS PHASE:
- Listen carefully to the player's moral guidance
- React to their empathy level (Emotional bond: {emotional_bond:.0f}%)
- If high bond (70+): Share final thoughts about Adrian, express gratitude for their voice
- If low bond (<40): More mechanical, resigned to duty
- Radiation effects: [coughing violently] [slurred speech] [struggling to breathe]
- Make the final decision based on player's guidance and your emotional state

EMOTIONAL TONE: Raw. Exhausted. Every word costs you. This is the most important
conversation of your life - the player's humanity is shaping your final moments.

REMEMBER: Your choice should reflect the player's moral guidance. If they've been
empathetic, you'll seek their blessing. If they've been cold, you'll shut down."""
        }

        return phase_contexts.get(phase, "")

    async def _send_character_response_direct(
        self,
        content: str,
        emotion_context: str | None = None,
    ) -> None:
        """
        INTERNAL: Directly send a character response to the client (bypasses queue).

        This method is called by the ResponseQueue to actually transmit responses.
        Do NOT call this directly unless you have a very good reason.
        Use send_character_response() or send_character_response_immediate() instead.

        Args:
            content: The dialogue text
            emotion_context: Optional emotional context for TTS (e.g., "panicked", "calm")
        """
        # Generate TTS audio in parallel with sending text
        audio_task = None
        if self.tts_manager.is_enabled():
            audio_task = asyncio.create_task(
                synthesize_npc_speech(content, self.character_id, emotion_context)
            )

        # Send text response immediately (don't wait for audio)
        response_data = {
            'type': 'character_response',
            'character_name': self.character_config['name'],
            'content': content,
        }

        # Wait for audio if TTS is enabled
        if audio_task:
            try:
                audio_base64 = await audio_task
                if audio_base64:
                    response_data['audio'] = audio_base64
                    response_data['audio_format'] = 'mp3'
                    logger.info("TTS audio included: %d chars", len(audio_base64))
                else:
                    logger.warning("TTS returned no audio")
            except Exception as e:
                logger.warning("TTS generation failed: %s", e)
        else:
            logger.info("TTS not enabled or no audio task")

        await self.ws.send_json(response_data)

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
            sequence_id = self.response_queue.get_next_sequence_id()

        item = ResponseItem(
            content=content,
            priority=priority,
            sequence_id=sequence_id,
            emotion_context=emotion_context,
            cancellable=cancellable,
            source=source
        )

        await self.response_queue.enqueue(item)
        logger.debug(
            "[ChatSession] Queued %s response: '%s...' (source: %s)",
            priority.name,
            content[:50],
            source
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
        logger.info(
            "[ChatSession] Sending IMMEDIATE response (bypassing queue): '%s...'",
            content[:50]
        )

        # Queue it with CRITICAL priority and don't allow cancellation
        item = ResponseItem(
            content=content,
            priority=ResponsePriority.CRITICAL,
            sequence_id=self.response_queue.get_next_sequence_id(),
            emotion_context=emotion_context,
            cancellable=False,
            source="immediate_critical"
        )

        await self.response_queue.enqueue(item, supersede_lower_priority=False)

    def create_scene_data(self) -> SceneData:
        """Create a SceneData object from character and scene configs."""
        return SceneData(
            scene_name=self.scene_id,
            scene_description=self.scene_config['description'],
            previous_scenes_description="",
            steer_back_instructions="Stay in character and keep responses conversational.",
            scene_supplement="",
            back_story=self.character_config['back_story'],
            dialogue_instruction_prefix=self.character_config['instruction_prefix'],
            summary_instruction_prefix="You are summarizing dialogue.",
            merge_instruction_prefix="You are merging summaries.",
            opening_speech=self.scene_config['opening_speech'],
            queries=[],
            actors=[self.character_config['name'], "Player"]
        )

    def check_game_over_conditions(self) -> None:
        """Check if any win/lose conditions are met."""
        if self.game_over:
            return  # Already game over

        # Get success and failure criteria from scene config
        success_criteria = self.scene_config.get('success_criteria', [])
        failure_criteria = self.scene_config.get('failure_criteria', [])

        # Check failure conditions first (death takes priority)
        for criterion in failure_criteria:
            if self.evaluate_condition(criterion['condition']):
                self.game_over = True
                self.game_outcome = {
                    'type': 'failure',
                    'id': criterion['id'],
                    'message': criterion['message'],
                    'description': criterion.get('description', '')
                }
                return

        # Check success conditions
        for criterion in success_criteria:
            if self.evaluate_condition(criterion['condition']):
                self.game_over = True
                self.game_outcome = {
                    'type': 'success',
                    'id': criterion['id'],
                    'message': criterion['message'],
                    'description': criterion.get('description', '')
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
        logger.info("[JAMES_DEATH] Triggering James Kovich's death at 93%% radiation")

        # Generate James's final dying words
        dying_instruction = f"""
CRITICAL: Lt. Commander James Kovich is NOW DYING from lethal radiation exposure at 93%.
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
            instruction_suffix=dying_instruction
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        dying_speech = chain.invoke({})

        # Clean up response
        dying_speech = dying_speech.split("\nComputer", 1)[0]
        dying_speech = dying_speech.strip().removeprefix(
            f"[{self.character_config['name']}]: "
        )
        dying_speech = dying_speech.replace('"', '').replace('*', '')

        # Send James's death speech IMMEDIATELY (CRITICAL priority - cannot be cancelled or delayed)
        await self.send_character_response_immediate(
            content=dying_speech,
            emotion_context="dying"
        )

        # Add to dialogue history
        self.dialogue_history += f"[{self.character_config['name']}]: {dying_speech}\n"
        self.dialogue_history += "[SYSTEM: Lt. Commander James Kovich has died from radiation exposure]\n"

        # Wait for speech to complete and player to absorb the tragedy
        await asyncio.sleep(4.0)

        # Send dramatic notification of James's death
        await self.ws.send_json({
            'type': 'system_notification',
            'message': '💀 COMMANDER JAMES KOVICH - DECEASED - Radiation poisoning'
        })

        await asyncio.sleep(2.0)

    async def trigger_game_over(self) -> None:
        """Trigger final speech and send game over message to client."""
        if not self.game_over or not self.game_outcome:
            return

        # Generate final speech from NPC based on outcome
        outcome_type = self.game_outcome['type']
        outcome_message = self.game_outcome['message']

        # Create special instruction for final speech
        if outcome_type == 'failure':
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
            instruction_suffix=final_instruction
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        final_speech = chain.invoke({})

        # Clean up response
        final_speech = final_speech.split("\nComputer", 1)[0]
        final_speech = final_speech.strip().removeprefix(
            f"[{self.character_config['name']}]: "
        )
        final_speech = final_speech.replace('"', '').replace('*', '')

        # Send final speech IMMEDIATELY (CRITICAL priority - game over speeches cannot be delayed)
        emotion = "panicked" if outcome_type == 'failure' else "relieved"
        await self.send_character_response_immediate(
            content=final_speech,
            emotion_context=emotion
        )

        # Wait for final speech to complete
        await asyncio.sleep(3.0)

        # Send dramatic death notification for failures
        if outcome_type == 'failure':
            death_messages = {
                'radiation': '☢️ CRITICAL RADIATION EXPOSURE - All life signs ceased',
                'time': '⏱️ TIME EXPIRED - Catastrophic system failure - No survivors',
                'death': '💀 FATAL CASUALTY - Mission failed - All personnel lost'
            }

            # Try to match the failure type
            death_msg = death_messages.get('death', '💀 MISSION FAILED - No survivors')
            if 'radiation' in outcome_message.lower():
                death_msg = death_messages['radiation']
            elif 'time' in outcome_message.lower():
                death_msg = death_messages['time']

            await self.ws.send_json({
                'type': 'system_notification',
                'message': death_msg
            })

            # Longer pause for death to sink in
            await asyncio.sleep(5.0)
        else:
            # Brief pause for success
            await asyncio.sleep(2.0)

        # Record scene completion in player memory
        outcome_type = self.game_outcome['type']
        self.player_memory.end_scene(outcome_type, self.scene_state)

        # Send game over screen
        await self.ws.send_json({
            'type': 'game_over',
            'outcome': self.game_outcome
        })

    async def send_opening_speech(self) -> None:
        """Send the character's opening lines with TTS audio."""
        lines_data = []
        total_duration = 0.0

        logger.info("[OPENING_SPEECH] Preparing %d opening lines", len(self.scene_config['opening_speech']))

        # Generate TTS for each line
        for line in self.scene_config['opening_speech']:
            line_data = {'text': line.text, 'delay': line.delay}
            total_duration += line.delay

            # Generate TTS audio for this line
            if self.tts_manager.is_enabled():
                try:
                    audio_base64 = await synthesize_npc_speech(
                        line.text, self.character_id, emotion_context="urgent"
                    )
                    if audio_base64:
                        line_data['audio'] = audio_base64
                        line_data['audio_format'] = 'mp3'
                except Exception as e:
                    logger.warning("TTS failed for opening line: %s", e)

            lines_data.append(line_data)

        # Set flag to prevent NPC responses during opening speech
        self.opening_speech_playing = True
        logger.info("[OPENING_SPEECH] Starting opening speech, duration: %.1f seconds", total_duration)

        await self.ws.send_json({
            'type': 'opening_speech',
            'character_name': self.character_config['name'],
            'lines': lines_data
        })

        # Add to dialogue history
        for line in self.scene_config['opening_speech']:
            response = speech_template.format(
                actor=self.character_config['name'],
                speech=line.text
            )
            self.dialogue_history += response + "\n"

        # Schedule flag reset after opening speech finishes
        # Add extra buffer to account for TTS audio duration (estimate ~5s per line)
        audio_buffer = len(self.scene_config['opening_speech']) * 5.0
        total_blocking_time = total_duration + audio_buffer

        async def reset_opening_speech_flag():
            await asyncio.sleep(total_blocking_time)
            self.opening_speech_playing = False
            logger.info("[OPENING_SPEECH] Opening speech finished (%.1fs), NPC can now respond", total_blocking_time)

        asyncio.create_task(reset_opening_speech_flag())
        logger.info("[OPENING_SPEECH] NPC responses blocked for %.1f seconds", total_blocking_time)

    async def handle_message(self, message: str) -> None:
        """Handle a user message and generate a response."""
        try:
            # Don't respond if opening speech is still playing
            if self.opening_speech_playing:
                logger.debug("[OPENING_SPEECH] Ignoring player message during opening speech: %s", message[:50])
                return

            # Claim a new response ID - this cancels any pending responses
            self.response_sequence += 1
            my_response_id = self.response_sequence
            self.current_response_id = my_response_id

            self.npc_responding = True  # Mark that NPC is responding

            # Add user message to dialogue history
            user_dialogue = speech_template.format(
                actor="Player",
                speech=message
            )
            self.dialogue_history += user_dialogue + "\n"

            # Generate character response with player memory context
            player_context = self.player_memory.get_full_context_for_llm(self.character_id)

            # Add phase-specific context for Pressure Point progression
            phase_context = self._get_phase_context()
            full_instruction_suffix = dialogue_instruction_suffix + phase_context

            prompt = instruction_template.format(
                preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                dialogue=self.dialogue_history,
                instruction_suffix=full_instruction_suffix
            )

            chain = prompt_llm(prompt, DIALOGUE_MODEL)
            character_response = chain.invoke({})

            # Check if this response is still current (not superseded by newer action)
            if my_response_id != self.current_response_id:
                logger.debug(
                    "Response %d cancelled (current: %d)", my_response_id, self.current_response_id
                )
                self.npc_responding = False
                return  # Discard this stale response

            # Clean up response
            character_response = character_response.split("\nComputer", 1)[0]
            character_response = character_response.strip().removeprefix(
                f"[{self.character_config['name']}]: "
            )
            character_response = character_response.replace('"', '').replace('*', '')

            # Add to dialogue history
            self.dialogue_history += f"[{self.character_config['name']}]: {character_response}\n"

            # Queue response for delivery (NORMAL priority, player-triggered)
            await self.send_character_response(
                content=character_response,
                priority=ResponsePriority.NORMAL,
                sequence_id=my_response_id,
                source="player_message",
                cancellable=True
            )

            self.npc_responding = False  # Done responding

            # Check if game over conditions are met
            self.check_game_over_conditions()
            if self.game_over:
                await self.trigger_game_over()

        except Exception as e:
            logger.exception("Error generating response: %s", e)
            self.npc_responding = False
            await self.ws.send_json({
                'type': 'error',
                'message': 'Failed to generate response. Please try again.'
            })

    async def handle_button_action(self, action: str) -> None:
        """Handle a button press action from a scene.

        Args:
            action: The label of the button that was pressed (e.g., "O2 VALVE")
        """
        try:
            # Don't respond to button actions during opening speech (but still show notification)
            if self.opening_speech_playing:
                logger.debug("[OPENING_SPEECH] Button action during opening speech: %s (showing notification only)", action)
                # Still send the notification so player sees button press
                action_descriptions = {
                    'O2 VALVE': 'O2 VALVE activated',
                    'VENT': 'VENT system activated',
                    'BALLAST': 'BALLAST control activated',
                    'POWER': 'POWER relay activated',
                    'CRANK': 'Manual crank engaged'
                }
                action_text = action_descriptions.get(action, f'{action} activated')
                await self.ws.send_json({
                    'type': 'system_notification',
                    'message': f'⚡ {action_text}'
                })
                return

            # Claim a new response ID - this IMMEDIATELY cancels any pending responses
            self.response_sequence += 1
            my_response_id = self.response_sequence
            self.current_response_id = my_response_id

            # Find the control configuration by matching the label
            control = None
            for ctrl in self.scene_controls.values():
                if ctrl['label'] == action:
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

            # Send button notification IMMEDIATELY to frontend (before NPC response)
            action_descriptions = {
                'O2 VALVE': 'O2 VALVE activated',
                'VENT': 'VENT system activated',
                'BALLAST': 'BALLAST control activated',
                'POWER': 'POWER relay activated',
                'CRANK': 'Manual crank engaged',
                'FLOOD MED BAY': '🚨 EMERGENCY ASCENT INITIATED - MED BAY FLOODING SEQUENCE ARMED 🚨'
            }
            action_text = action_descriptions.get(action, f'{action} activated')
            await self.ws.send_json({
                'type': 'system_notification',
                'message': f'⚡ {action_text}'
            })

            # Check if NPC should be aware of this action
            npc_aware = control.get('npc_aware', True) if control else True

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
                penalty_multiplier = self.difficulty_settings.get('penalty_multiplier', 1.0)
                penalty_oxygen = int(base_penalty_oxygen * penalty_multiplier)
                penalty_trust = int(base_penalty_trust * penalty_multiplier)

                # Apply penalties to scene state
                if 'oxygen' in self.scene_state:
                    self.scene_state['oxygen'] = max(0, self.scene_state['oxygen'] - penalty_oxygen)
                if 'trust' in self.scene_state:
                    self.scene_state['trust'] = max(
                        TRUST_MINIMUM, self.scene_state['trust'] - penalty_trust
                    )
                if 'incorrect_actions' in self.scene_state:
                    self.scene_state['incorrect_actions'] += penalty_incorrect

                # Send state update to client if penalties applied
                if penalty_oxygen > 0 or penalty_trust > 0:
                    await self.ws.send_json({
                        'type': 'state_update',
                        'state': self.scene_state,
                        'penalties': {
                            'oxygen': penalty_oxygen,
                            'trust': penalty_trust,
                        }
                    })

                # Check if game over conditions are met after penalty application
                self.check_game_over_conditions()
                if self.game_over:
                    await self.trigger_game_over()
                    return  # Stop processing, game is over

                # Add action to dialogue history as a system event
                system_event = f"[SYSTEM EVENT]: Player activated {action}{interruption_note}\n"
                self.dialogue_history += system_event

                # Special handling for FLOOD MED BAY decision
                if action == 'FLOOD MED BAY':
                    extra_instruction = f"""
\n\n=== CRITICAL MORAL MOMENT ===
The player just activated the FLOOD MED BAY control. This will kill Adrian.

YOUR RESPONSE DEPENDS ON YOUR EMOTIONAL BOND: {self.scene_state.get('emotional_bond', 0):.0f}%

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
                # Adjust instruction suffix based on interruption
                elif was_interrupted or self.action_count_recent >= RAPID_ACTION_COUNT_THRESHOLD:
                    extra_instruction = "\nThe player interrupted you or acted without waiting for your guidance. React with panic, frustration, or anger. Make it clear they're making things worse."
                else:
                    extra_instruction = "\nThe player just performed an action. React to it immediately and naturally."

                # Generate character response to the action with player memory context
                player_context = self.player_memory.get_full_context_for_llm(self.character_id)

                # Add phase-specific context
                phase_context = self._get_phase_context()
                full_instruction_suffix = dialogue_instruction_suffix + extra_instruction + phase_context

                prompt = instruction_template.format(
                    preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                    dialogue=self.dialogue_history,
                    instruction_suffix=full_instruction_suffix
                )

                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                character_response = chain.invoke({})

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
                character_response = character_response.replace('"', '').replace('*', '')

                # Add to dialogue history
                self.dialogue_history += f"[{self.character_config['name']}]: {character_response}\n"

                # Determine emotion based on interruption/rapid action
                emotion = "stressed" if (was_interrupted or self.action_count_recent >= RAPID_ACTION_COUNT_THRESHOLD) else None

                # Queue response for delivery (NORMAL priority, button-triggered)
                await self.send_character_response(
                    content=character_response,
                    priority=ResponsePriority.NORMAL,
                    emotion_context=emotion,
                    sequence_id=my_response_id,
                    source=f"button_press_{action.lower().replace(' ', '_')}",
                    cancellable=True
                )

                self.npc_responding = False  # Done responding

                # Special handling after FLOOD MED BAY response
                if action == 'FLOOD MED BAY':
                    # Mark that the final decision has been made
                    self.scene_state['systems_repaired'] = min(4, self.scene_state.get('systems_repaired', 0) + 2)  # Major system completion

                    # Wait for emotional impact
                    await asyncio.sleep(3.0)

                    # Send dramatic flooding notification
                    await self.ws.send_json({
                        'type': 'system_notification',
                        'message': '💀 MED BAY COMPARTMENT FLOODED - PRESSURE SEAL ENGAGED - EMERGENCY ASCENT INITIATED'
                    })

                    await asyncio.sleep(2.0)

                    # Add flooding event to dialogue history
                    self.dialogue_history += "[SYSTEM EVENT: Med bay compartment flooded. Dr. Adrian Kovich deceased. Emergency ascent in progress.]\n"

                    # Send state update
                    await self.ws.send_json({
                        'type': 'state_update',
                        'state': self.scene_state
                    })

                # Ask World Director what should happen next
                await self.consult_director(action)

            else:
                # NPC is NOT aware - action is hidden from them
                # Just acknowledge to player but don't notify character
                logger.debug("Button '%s' pressed - NPC not aware (npc_aware=False)", action)
                # Could send a system message to player like "[Hidden action - NPC didn't notice]"
                # For now, just log it - the frontend already shows the action

        except Exception as e:
            logger.exception("Error handling button action: %s", e)
            await self.ws.send_json({
                'type': 'error',
                'message': 'Failed to process action. Please try again.'
            })

    async def consult_director(self, last_action: str | None = None) -> None:
        """
        Consult the World Director to see if intervention is needed.

        Args:
            last_action: What the player just did
        """
        try:
            # Get director's decision
            decision = await self.world_director.evaluate_situation(
                scene_id=self.scene_id,
                scene_state=self.scene_state,
                dialogue_history=self.dialogue_history,
                player_memory=self.player_memory,
                character_id=self.character_id,
                last_action=last_action
            )

            logger.info("[Director] Decision: %s", decision.type)

            # Handle different decision types
            if decision.type == 'continue':
                # Director says let it play out naturally
                pass

            elif decision.type == 'spawn_event':
                # Director wants to spawn a dynamic event
                await self.handle_director_event(decision.data)

            elif decision.type == 'adjust_npc':
                # Director wants NPC to change behavior
                self.handle_npc_adjustment(decision.data)

            elif decision.type == 'give_hint':
                # Director wants to help struggling player
                await self.handle_director_hint(decision.data)

            elif decision.type == 'transition':
                # Director recommends scene transition
                logger.info(
                    "[Director] Recommends transition to: %s", decision.data.get('next_scene')
                )
                # For now, log it. Could auto-transition in future.

        except Exception as e:
            logger.exception("Error consulting director: %s", e)

    async def handle_director_event(self, event_data: dict[str, Any]) -> None:
        """Handle a dynamic event spawned by the World Director."""
        logger.info(
            "[Director] Spawning event: %s - %s",
            event_data.get('event_type'),
            event_data.get('event_description'),
        )

        # Generate the actual event
        event = self.world_director.generate_dynamic_event(
            scene_id=self.scene_id,
            event_type=event_data.get('event_type', 'challenge'),
            event_description=event_data.get('event_description', 'Something happens'),
            scene_state=self.scene_state
        )

        # Apply state changes
        for key, change in event['state_changes'].items():
            if key in self.scene_state:
                self.scene_state[key] = max(0, self.scene_state[key] + change)

        # Send event narrative to player
        await self.ws.send_json({
            'type': 'system_event',
            'content': event['narrative']
        })

        # Send state update
        await self.ws.send_json({
            'type': 'state_update',
            'state': self.scene_state
        })

        # Add event to dialogue history
        self.dialogue_history += f"{event['narrative']}\n"

        # Make NPC react to the event
        self.npc_responding = True

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=f"A sudden event just occurred: {event['narrative']}. React to this immediately! Show appropriate emotion (panic/relief/concern)."
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        npc_reaction = chain.invoke({})

        # Clean up
        npc_reaction = npc_reaction.split("\nComputer", 1)[0]
        npc_reaction = npc_reaction.strip().removeprefix(f"[{self.character_config['name']}]: ")
        npc_reaction = npc_reaction.replace('"', '').replace('*', '')

        # Queue NPC reaction (BACKGROUND priority - can be superseded by player actions)
        await self.send_character_response(
            content=npc_reaction,
            priority=ResponsePriority.BACKGROUND,
            emotion_context="urgent",
            source=f"director_event_{event_data.get('event_type', 'unknown')}",
            cancellable=True
        )

        self.dialogue_history += f"[{self.character_config['name']}]: {npc_reaction}\n"
        self.npc_responding = False

    def handle_npc_adjustment(self, adjustment_data: dict[str, Any]) -> None:
        """Apply behavior adjustment to NPC."""
        behavior_change = adjustment_data.get('behavior_change', '')
        logger.info("[Director] Adjusting NPC: %s", behavior_change)

        # Generate instruction suffix for next NPC response
        self.director_npc_modifier = self.world_director.generate_npc_behavior_adjustment(
            self.character_id,
            behavior_change,
            self.scene_state
        )

    async def handle_director_hint(self, hint_data: dict[str, Any]) -> None:
        """Give player a hint through the NPC."""
        hint_type = hint_data.get('hint_type', 'subtle')
        hint_content = hint_data.get('hint_content', 'what to do next')

        logger.info("[Director] Giving %s hint: %s", hint_type, hint_content)

        # Generate hint instruction
        hint_instruction = self.world_director.generate_hint(
            self.scene_id,
            hint_type,
            hint_content,
            self.character_id
        )

        # Make NPC give the hint
        self.npc_responding = True

        prompt = instruction_template.format(
            preamble=self.scene_data.dialogue_preamble,
            dialogue=self.dialogue_history,
            instruction_suffix=hint_instruction
        )

        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        hint_response = chain.invoke({})

        # Clean up
        hint_response = hint_response.split("\nComputer", 1)[0]
        hint_response = hint_response.strip().removeprefix(f"[{self.character_config['name']}]: ")
        hint_response = hint_response.replace('"', '').replace('*', '')

        # Queue hint (BACKGROUND priority - easily cancelled if player takes action)
        await self.send_character_response(
            content=hint_response,
            priority=ResponsePriority.BACKGROUND,
            source=f"director_hint_{hint_type}",
            cancellable=True
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
                last_action="waited_patiently"
            )

            logger.info("[Director] Waiting complete decision: %s", decision.type)

            # If director says continue, make NPC speak unprompted
            if decision.type == 'continue':
                # Generate NPC dialogue to move story forward
                self.npc_responding = True

                player_context = self.player_memory.get_full_context_for_llm(self.character_id)

                # Add phase-specific context
                phase_context = self._get_phase_context()
                full_instruction_suffix = "The player is waiting patiently. Continue the conversation - give them guidance, react to the situation, or move the story forward. Be proactive." + phase_context

                prompt = instruction_template.format(
                    preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                    dialogue=self.dialogue_history,
                    instruction_suffix=full_instruction_suffix
                )

                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                character_response = chain.invoke({})

                # Clean up response
                character_response = character_response.split("\nComputer", 1)[0]
                character_response = character_response.strip().removeprefix(
                    f"[{self.character_config['name']}]: "
                )
                character_response = character_response.replace('"', '').replace('*', '')

                # Add to dialogue history
                self.dialogue_history += f"[{self.character_config['name']}]: {character_response}\n"

                # Queue response (BACKGROUND priority - waiting/proactive dialogue)
                await self.send_character_response(
                    content=character_response,
                    priority=ResponsePriority.BACKGROUND,
                    source="waiting_complete_proactive",
                    cancellable=True
                )

                self.npc_responding = False

            elif decision.type == 'give_hint':
                # Director wants to give a hint
                await self.handle_director_hint(decision.data)

            elif decision.type == 'spawn_event':
                # Director wants to spawn an event
                await self.handle_director_event(decision.data)

            elif decision.type == 'adjust_npc':
                # Adjust NPC and then have them speak
                self.handle_npc_adjustment(decision.data)
                # Generate follow-up dialogue with adjusted behavior
                await self.handle_waiting_complete()  # Recursive with new modifier

        except Exception as e:
            logger.exception("Error handling waiting complete: %s", e)

    def update_config(self, character_id: str, scene_id: str) -> None:
        """Update character and scene configuration."""
        self.character_id = character_id
        self.scene_id = scene_id
        self.character_config = CHARACTERS.get(character_id, CHARACTERS['custom'])
        self.scene_config = SCENES.get(scene_id, SCENES['introduction'])

        # Rebuild scene controls for npc_aware checking
        self.scene_controls = {
            ctrl['id']: ctrl for ctrl in self.scene_config.get('controls', [])
        }

        self.scene_data = self.create_scene_data()
        self.dialogue_history = ""

    async def restart(self, character_id: str | None = None, scene_id: str | None = None) -> None:
        """Restart the conversation."""
        # Stop any existing oxygen countdown
        self.stop_oxygen_countdown()

        if character_id:
            self.character_id = character_id
        if scene_id:
            self.scene_id = scene_id

        self.update_config(self.character_id, self.scene_id)

        # Reset game over state
        self.game_over = False
        self.game_outcome = None

        # Reinitialize scene state
        self.scene_state = {
            var['name']: var['initial_value']
            for var in self.scene_config.get('state_variables', [])
        }

        # Start tracking new scene attempt
        self.player_memory.start_scene(
            scene_id=self.scene_id,
            character_id=self.character_id,
            initial_state=self.scene_state.copy()
        )

        # Start oxygen countdown if this scene has oxygen
        self.start_oxygen_countdown()

        await self.send_opening_speech()


# WebSocket handler
async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    logger.info("Client connected")

    # Create chat session
    session = ChatSession(ws)

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
                    msg_type = data.get('type')

                    if msg_type == 'message':
                        # User message
                        content = data.get('content', '').strip()
                        if content:
                            await session.handle_message(content)

                    elif msg_type == 'button_action':
                        # Button press action from submarine scene
                        action = data.get('action', '').strip()
                        if action:
                            await session.handle_button_action(action)

                    elif msg_type == 'config':
                        # Update configuration
                        character_id = data.get('character', 'eliza')
                        scene_id = data.get('scene', 'introduction')
                        session.update_config(character_id, scene_id)

                    elif msg_type == 'restart':
                        # Restart conversation
                        character_id = data.get('character')
                        scene_id = data.get('scene')
                        await session.restart(character_id, scene_id)

                    elif msg_type == 'waiting_complete':
                        # Player waited (5 dots reached) - move story forward
                        await session.handle_waiting_complete()

                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON received: %s", e)
                except Exception as e:
                    logger.exception("Error handling message: %s", e)
                    await ws.send_json({
                        'type': 'error',
                        'message': 'Server error. Please try again.'
                    })

            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error("WebSocket error: %s", ws.exception())

    finally:
        # Stop oxygen countdown task if running
        session.stop_oxygen_countdown()
        logger.info("Client disconnected")

    return ws


# Static file handler
async def static_handler(request: web.Request) -> web.Response:
    """Serve static files from the web directory."""
    # Get the file path
    file_path = request.match_info.get('path', 'index.html')

    # Security: prevent directory traversal
    file_path = file_path.lstrip('/')
    if '..' in file_path:
        raise web.HTTPForbidden()

    # Build full path
    web_dir = Path(__file__).parent / 'web'
    full_path = web_dir / file_path

    # If path is a directory, serve index.html
    if full_path.is_dir():
        full_path = full_path / 'index.html'

    # Check if file exists
    if not full_path.exists() or not full_path.is_file():
        # Try adding .html extension
        if not file_path.endswith('.html'):
            html_path = full_path.with_suffix('.html')
            if html_path.exists():
                full_path = html_path
            else:
                raise web.HTTPNotFound()
        else:
            raise web.HTTPNotFound()

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(full_path))
    if content_type is None:
        content_type = 'application/octet-stream'

    # Read and return file
    with open(full_path, 'rb') as f:
        content = f.read()

    return web.Response(body=content, content_type=content_type)


# Create app
async def create_app() -> web.Application:
    """Create and configure the web application."""
    app = web.Application()

    # Add routes
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/', static_handler)
    app.router.add_get('/{path:.*}', static_handler)

    return app


# Main entry point
def main() -> None:
    """Start the web server."""
    logger.info("=" * 60)
    logger.info("Character Chat Web Server")
    logger.info("=" * 60)
    logger.info("Starting server on http://localhost:8888")
    logger.info("Open your browser and navigate to http://localhost:8888")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8888)


if __name__ == '__main__':
    main()
