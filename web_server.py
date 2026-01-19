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
from pathlib import Path
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

# Initialize models
print("Initializing LLM models...")
DIALOGUE_MODEL = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
QUERY_MODEL = ClaudeSonnet45Model(temperature=0.2, max_tokens=300)
print("✓ Models initialized")

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

    def __init__(self, ws, character_id='eliza', scene_id='introduction'):
        self.ws = ws
        self.character_id = character_id
        self.scene_id = scene_id
        self.dialogue_history = ""
        self.character_config = CHARACTERS.get(character_id, CHARACTERS['custom'])
        self.scene_config = SCENES.get(scene_id, SCENES['introduction'])

        # Build scene data
        self.scene_data = self.create_scene_data()

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
            # Add user message to dialogue history
            user_dialogue = speech_template.format(
                actor="Player",
                speech=message
            )
            self.dialogue_history += user_dialogue + "\n"

            # Generate character response
            prompt = instruction_template.format(
                preamble=self.scene_data.dialogue_preamble,
                dialogue=self.dialogue_history,
                instruction_suffix=dialogue_instruction_suffix
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

            # Send response to client
            await self.ws.send_json({
                'type': 'character_response',
                'character_name': self.character_config['name'],
                'content': character_response
            })

        except Exception as e:
            print(f"Error generating response: {e}")
            await self.ws.send_json({
                'type': 'error',
                'message': 'Failed to generate response. Please try again.'
            })

    def update_config(self, character_id, scene_id):
        """Update character and scene configuration."""
        self.character_id = character_id
        self.scene_id = scene_id
        self.character_config = CHARACTERS.get(character_id, CHARACTERS['custom'])
        self.scene_config = SCENES.get(scene_id, SCENES['introduction'])
        self.scene_data = self.create_scene_data()
        self.dialogue_history = ""

    async def restart(self, character_id=None, scene_id=None):
        """Restart the conversation."""
        if character_id:
            self.character_id = character_id
        if scene_id:
            self.scene_id = scene_id

        self.update_config(self.character_id, self.scene_id)
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
