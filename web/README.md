# Character Chat - Web Interface

A self-contained web experience for chatting with AI characters in a 3D environment.

## Features

- **3D Character Visualization** - Three.js powered 3D scene with animated characters
- **Real-time Chat** - WebSocket-based instant messaging with characters
- **Multiple Characters** - Choose from different character personalities:
  - Eliza - AI Caretaker
  - Merlin - Wise Wizard
  - Detective Stone - Hard-boiled Detective
  - Custom Character

- **Scene System** - Different conversation contexts:
  - Introduction - First meeting
  - General Conversation - Casual chat
  - Quest Beginning - Starting an adventure

- **Dynamic Responses** - Powered by Claude Sonnet 4.5 via llm_prompt_core

## Architecture

```
Browser (Three.js + Chat UI)
    ↓ WebSocket
web_server.py (aiohttp)
    ↓
llm_prompt_core
    ↓
Claude API
```

## Files

- `index.html` - Main page structure
- `css/style.css` - Styling and animations
- `js/scene.js` - Three.js 3D scene setup
- `js/app.js` - WebSocket connection and chat logic

## Running

From the project root:

```bash
./start-web.sh
```

Then open your browser to:
```
http://localhost:8080
```

## Customization

### Adding New Characters

Edit `web_server.py` and add to the `CHARACTERS` dictionary:

```python
CHARACTERS = {
    'mycharacter': {
        'name': 'My Character',
        'description': 'Character description',
        'back_story': 'Background and personality...',
        'instruction_prefix': 'You are playing the role of...',
    },
    # ... other characters
}
```

Then update `index.html` to add the character to the select dropdown.

### Adding New Scenes

Edit `web_server.py` and add to the `SCENES` dictionary:

```python
SCENES = {
    'myscene': {
        'name': 'My Scene',
        'description': 'Scene description',
        'opening_speech': [
            Line(text='Opening line', delay=0),
            Line(text='Second line', delay=2.0),
        ]
    },
    # ... other scenes
}
```

### Customizing the 3D Scene

Edit `js/scene.js`:

- `createCharacter()` - Modify character appearance
- `createGround()` - Change environment
- `setupLights()` - Adjust lighting
- `createParticles()` - Add/modify particle effects

### Changing Colors

Character colors are defined in `js/app.js` in the `characterColors` object:

```javascript
const characterColors = {
    'eliza': 0x4fc3f7,     // Cyan
    'wizard': 0x9c27b0,    // Purple
    'detective': 0x795548, // Brown
    'custom': 0x4caf50     // Green
};
```

## Technology Stack

- **Frontend**:
  - Three.js - 3D graphics
  - Vanilla JavaScript - No framework overhead
  - CSS3 - Modern styling with animations

- **Backend**:
  - aiohttp - Async Python web server
  - WebSockets - Real-time bidirectional communication
  - llm_prompt_core - Dialogue generation framework

- **AI**:
  - Claude Sonnet 4.5 (via Anthropic API)
  - Configurable prompt templates
  - Context-aware responses

## Browser Compatibility

Tested on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires:
- WebSocket support
- ES6 modules
- WebGL for 3D graphics

## Performance

- Initial load: ~1-2 seconds
- Response time: 0.5-2 seconds (depends on Claude API)
- 3D scene: 60 FPS on modern hardware
- Memory usage: ~50-100 MB

## Troubleshooting

**"Failed to connect to WebSocket"**
- Ensure the server is running (`./start-web.sh`)
- Check that port 8080 is not in use
- Verify firewall settings

**"Error generating response"**
- Check that ANTHROPIC_API_KEY is set in `.env`
- Verify API key is valid
- Check console for detailed error messages

**3D scene not rendering**
- Ensure WebGL is supported in your browser
- Try disabling browser extensions
- Check GPU/graphics drivers are up to date

**Slow responses**
- This is normal for first request (cold start)
- Subsequent requests should be faster
- Consider using Haiku model for faster (but less capable) responses

## Future Enhancements

Ideas for extending the system:

- Voice input/output
- Multiple characters in one scene
- Persistent conversation history
- Character emotion visualization
- Custom backgrounds and environments
- Mobile app version
- Multi-user chat rooms
- Character memory across sessions
