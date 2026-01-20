"""
Web server for the character chat interface.

This server:
- Serves the static web frontend (HTML/CSS/JS)
- Handles WebSocket connections for real-time chat
- Uses llm_prompt_core for dialogue generation
- Supports multiple characters and scenes
"""

import asyncio
import json
import os
import mimetypes
import time
from pathlib import Path
from typing import Dict, Any
from aiohttp import web
import aiohttp

from llm_prompt_core.models.anthropic import ClaudeSonnet45Model
from llm_prompt_core.types import Line, Query, StateChange, SceneData
from llm_prompt_core.utils import prompt_llm
from llm_prompt_core.prompts.templates import (
    instruction_template,
    dialogue_instruction_suffix,
    speech_template,
)

# Import modular character and scene systems
from characters import CHARACTERS as CHARACTER_REGISTRY
from scenes import SCENES as SCENE_REGISTRY

# Import player memory system
from player_memory import PlayerMemory

# Import world director (dungeon master)
from world_director import WorldDirector

# Initialize models
print("Initializing LLM models...")
# Use Haiku for faster responses (2-3x faster than Sonnet)
from llm_prompt_core.models.anthropic import ClaudeHaikuModel
DIALOGUE_MODEL = ClaudeHaikuModel(temperature=0.8, max_tokens=800)  # Reduced tokens for speed
QUERY_MODEL = ClaudeHaikuModel(temperature=0.2, max_tokens=200)
print("✓ Models initialized (using Haiku for performance)")

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

    def __init__(self, ws, character_id='eliza', scene_id='introduction', player_id=None):
        self.ws = ws
        self.character_id = character_id
        self.scene_id = scene_id
        self.dialogue_history = ""
        self.character_config = CHARACTERS.get(character_id, CHARACTERS['custom'])
        self.scene_config = SCENES.get(scene_id, SCENES['introduction'])

        # Player memory system
        self.player_id = player_id or f"player_{id(ws)}"  # Use websocket ID if no player_id provided
        self.player_memory = PlayerMemory(self.player_id)
        print(f"Loaded player memory for {self.player_id}")

        # World Director (dungeon master)
        self.world_director = WorldDirector()
        self.director_npc_modifier = ""  # Behavior modifications from director
        print("World Director initialized")

        # Store scene controls for npc_aware checking
        self.scene_controls = {
            ctrl['id']: ctrl for ctrl in self.scene_config.get('controls', [])
        }

        # Track if NPC is currently responding (for interruption detection)
        self.npc_responding = False
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
            print(f"Director adjusted oxygen: {difficulty['oxygen_bonus']:+d} (player skill-based)")

        self.difficulty_settings = difficulty  # Store for later use

    def create_scene_data(self):
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

    def check_game_over_conditions(self):
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

    def evaluate_condition(self, condition_str):
        """Evaluate a condition string using scene state."""
        try:
            # Create a safe evaluation environment with just the state
            state = self.scene_state
            return eval(condition_str, {"__builtins__": {}}, {"state": state})
        except Exception as e:
            print(f"Error evaluating condition '{condition_str}': {e}")
            return False

    async def trigger_game_over(self):
        """Trigger final speech and send game over message to client."""
        if not self.game_over or not self.game_outcome:
            return

        # Generate final speech from NPC based on outcome
        outcome_type = self.game_outcome['type']
        outcome_message = self.game_outcome['message']

        # Create special instruction for final speech
        if outcome_type == 'failure':
            final_instruction = f"""
This is THE END. The player has FAILED. {outcome_message}

Generate Casey's FINAL words - this is her death speech or final moment of despair.
Be dramatic, emotional, and final. This is the last thing she will ever say.
Keep it to 2-3 short sentences maximum."""
        else:  # success
            final_instruction = f"""
This is THE END. The player has SUCCEEDED! {outcome_message}

Generate Casey's FINAL words - this is her victory speech or relief at survival.
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

        # Send final speech
        await self.ws.send_json({
            'type': 'character_response',
            'character_name': self.character_config['name'],
            'content': final_speech
        })

        # Wait a moment for final speech to be displayed
        await asyncio.sleep(3)

        # Record scene completion in player memory
        outcome_type = self.game_outcome['type']
        self.player_memory.end_scene(outcome_type, self.scene_state)

        # Send game over screen
        await self.ws.send_json({
            'type': 'game_over',
            'outcome': self.game_outcome
        })

    async def send_opening_speech(self):
        """Send the character's opening lines."""
        await self.ws.send_json({
            'type': 'opening_speech',
            'character_name': self.character_config['name'],
            'lines': [
                {'text': line.text, 'delay': line.delay}
                for line in self.scene_config['opening_speech']
            ]
        })

        # Add to dialogue history
        for line in self.scene_config['opening_speech']:
            response = speech_template.format(
                actor=self.character_config['name'],
                speech=line.text
            )
            self.dialogue_history += response + "\n"

    async def handle_message(self, message):
        """Handle a user message and generate a response."""
        try:
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
            prompt = instruction_template.format(
                preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                dialogue=self.dialogue_history,
                instruction_suffix=dialogue_instruction_suffix
            )

            chain = prompt_llm(prompt, DIALOGUE_MODEL)
            character_response = chain.invoke({})

            # Check if this response is still current (not superseded by newer action)
            if my_response_id != self.current_response_id:
                print(f"Response {my_response_id} cancelled (current: {self.current_response_id})")
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

            # Send response to client
            await self.ws.send_json({
                'type': 'character_response',
                'character_name': self.character_config['name'],
                'content': character_response
            })

            self.npc_responding = False  # Done responding

            # Check if game over conditions are met
            self.check_game_over_conditions()
            if self.game_over:
                await self.trigger_game_over()

        except Exception as e:
            print(f"Error generating response: {e}")
            self.npc_responding = False
            await self.ws.send_json({
                'type': 'error',
                'message': 'Failed to generate response. Please try again.'
            })

    async def handle_button_action(self, action):
        """Handle a button press action from a scene.

        Args:
            action: The label of the button that was pressed (e.g., "O2 VALVE")
        """
        try:
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

            # Detect rapid button pressing (less than 3 seconds between actions)
            if time_since_last < 3.0:
                self.action_count_recent += 1
            else:
                self.action_count_recent = 1

            self.last_action_time = current_time

            # Check if interrupting NPC
            was_interrupted = self.npc_responding

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
                    base_penalty_oxygen = 15
                    base_penalty_trust = 10
                    penalty_incorrect = 1
                    interruption_note = " [INTERRUPTION: Player did not wait for instructions]"
                    # Record interruption in player memory
                    self.player_memory.record_interruption()
                elif self.action_count_recent >= 3:
                    # Player is button mashing (3+ actions in quick succession)
                    base_penalty_oxygen = 10
                    base_penalty_trust = 5
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
                    self.scene_state['trust'] = max(-100, self.scene_state['trust'] - penalty_trust)
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

                action_descriptions = {
                    'O2 VALVE': 'Player activated the O2 VALVE control',
                    'VENT': 'Player activated the VENT system',
                    'BALLAST': 'Player activated the BALLAST control',
                    'POWER': 'Player activated the POWER relay'
                }

                action_text = action_descriptions.get(action, f'Player activated {action}')

                # Add action to dialogue history as a system event
                system_event = f"[SYSTEM EVENT]: {action_text}{interruption_note}\n"
                self.dialogue_history += system_event

                # Adjust instruction suffix based on interruption
                if was_interrupted or self.action_count_recent >= 3:
                    extra_instruction = "\nThe player interrupted you or acted without waiting for your guidance. React with panic, frustration, or anger. Make it clear they're making things worse."
                else:
                    extra_instruction = "\nThe player just performed an action. React to it immediately and naturally."

                # Generate character response to the action with player memory context
                player_context = self.player_memory.get_full_context_for_llm(self.character_id)
                prompt = instruction_template.format(
                    preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
                    dialogue=self.dialogue_history,
                    instruction_suffix=dialogue_instruction_suffix + extra_instruction
                )

                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                character_response = chain.invoke({})

                # Check if this response is still current (not superseded by newer action)
                if my_response_id != self.current_response_id:
                    print(f"Response {my_response_id} cancelled (current: {self.current_response_id})")
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

                # Send response to client
                await self.ws.send_json({
                    'type': 'character_response',
                    'character_name': self.character_config['name'],
                    'content': character_response
                })

                self.npc_responding = False  # Done responding

                # Ask World Director what should happen next
                await self.consult_director(action)

            else:
                # NPC is NOT aware - action is hidden from them
                # Just acknowledge to player but don't notify character
                print(f"Button '{action}' pressed - NPC not aware (npc_aware=False)")
                # Could send a system message to player like "[Hidden action - NPC didn't notice]"
                # For now, just log it - the frontend already shows the action

        except Exception as e:
            print(f"Error handling button action: {e}")
            await self.ws.send_json({
                'type': 'error',
                'message': 'Failed to process action. Please try again.'
            })

    async def consult_director(self, last_action: str = None):
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

            print(f"[Director] Decision: {decision.type}")

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
                print(f"[Director] Recommends transition to: {decision.data.get('next_scene')}")
                # For now, log it. Could auto-transition in future.

        except Exception as e:
            print(f"Error consulting director: {e}")

    async def handle_director_event(self, event_data: Dict):
        """Handle a dynamic event spawned by the World Director."""
        print(f"[Director] Spawning event: {event_data.get('event_type')} - {event_data.get('event_description')}")

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

        # Send NPC reaction
        await self.ws.send_json({
            'type': 'character_response',
            'character_name': self.character_config['name'],
            'content': npc_reaction
        })

        self.dialogue_history += f"[{self.character_config['name']}]: {npc_reaction}\n"
        self.npc_responding = False

    def handle_npc_adjustment(self, adjustment_data: Dict):
        """Apply behavior adjustment to NPC."""
        behavior_change = adjustment_data.get('behavior_change', '')
        print(f"[Director] Adjusting NPC: {behavior_change}")

        # Generate instruction suffix for next NPC response
        self.director_npc_modifier = self.world_director.generate_npc_behavior_adjustment(
            self.character_id,
            behavior_change,
            self.scene_state
        )

    async def handle_director_hint(self, hint_data: Dict):
        """Give player a hint through the NPC."""
        hint_type = hint_data.get('hint_type', 'subtle')
        hint_content = hint_data.get('hint_content', 'what to do next')

        print(f"[Director] Giving {hint_type} hint: {hint_content}")

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

        # Send hint
        await self.ws.send_json({
            'type': 'character_response',
            'character_name': self.character_config['name'],
            'content': hint_response
        })

        self.dialogue_history += f"[{self.character_config['name']}]: {hint_response}\n"
        self.npc_responding = False

    def update_config(self, character_id, scene_id):
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

    async def restart(self, character_id=None, scene_id=None):
        """Restart the conversation."""
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

        await self.send_opening_speech()


# WebSocket handler
async def websocket_handler(request):
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    print("Client connected")

    # Create chat session
    session = ChatSession(ws)

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

                except json.JSONDecodeError:
                    print("Invalid JSON received")
                except Exception as e:
                    print(f"Error handling message: {e}")
                    await ws.send_json({
                        'type': 'error',
                        'message': 'Server error. Please try again.'
                    })

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')

    finally:
        print("Client disconnected")

    return ws


# Static file handler
async def static_handler(request):
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
async def create_app():
    """Create and configure the web application."""
    app = web.Application()

    # Add routes
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/', static_handler)
    app.router.add_get('/{path:.*}', static_handler)

    return app


# Main entry point
def main():
    """Start the web server."""
    print("=" * 60)
    print("Character Chat Web Server")
    print("=" * 60)
    print()
    print("Starting server on http://localhost:8080")
    print("Open your browser and navigate to http://localhost:8080")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080)


if __name__ == '__main__':
    main()
