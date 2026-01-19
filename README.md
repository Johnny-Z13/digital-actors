# Digital Actors

LLM-powered character dialogue system with multiple interfaces:
- 🌐 **Web Interface** - Self-contained browser-based chat with 3D character (NEW!)
- 🎮 **Game Integration** - WebSocket server for Unity/Unreal game clients
- 🔊 **Text-to-Speech** - Optional local TTS with [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M)

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

Or with `uv`:
```bash
uv pip install -r requirements.txt
```

### 2. Configure API Keys

The `.env` file is already created. Just add your API key:
```bash
nano .env
```

Add your Anthropic API key:
```env
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### 3. Choose Your Interface

#### 🌐 **Web Interface** (Recommended - Self-Contained Experience)

Start the web server and chat with characters in your browser:

```bash
./start-web.sh
```

Then open your browser to: **http://localhost:8080**

Features:
- ✨ 3D character visualization with Three.js
- 💬 Real-time chat interface
- 🎭 Multiple character personalities
- 🎬 Scene-based conversations
- ⚙️ Easy configuration via UI

See [web/README.md](web/README.md) for details.

#### 🎮 **Game Integration** (For External Game Clients)

For connecting Unity/Unreal game clients:

```bash
./start.sh          # WebSocket server (port 8765)
# or
./start-http.sh     # HTTP server (port 5000)
```

These listen for external game client connections.

## Project Structure

```
digital-actors/
├── llm_prompt_core/           # Generic LLM dialogue framework
│   ├── models/                # Claude, OpenAI, Gemini wrappers
│   ├── prompts/               # Prompt templates
│   ├── types.py               # Core data structures
│   └── README.md              # Detailed documentation
│
├── characters/                # Character definitions (modular)
│   ├── base.py                # Base Character class
│   ├── eliza.py               # Eliza - AI Caretaker
│   ├── wizard.py              # Merlin - Wise Wizard
│   ├── detective.py           # Detective Stone
│   └── custom.py              # Custom character template
│
├── scenes/                    # Scene definitions (modular)
│   ├── base.py                # Base Scene class
│   ├── introduction.py        # Introduction scene
│   ├── conversation.py        # General conversation
│   └── quest.py               # Quest beginning
│
├── audio/                     # Audio processing (prepared for future)
│   ├── README.md              # Future TTS/STT integration guide
│   └── __init__.py
│
├── web/                       # Web frontend
│   ├── index.html             # Main page
│   ├── css/style.css          # Styling
│   └── js/                    # JavaScript (Three.js scene + chat logic)
│
├── web_server.py              # Web server (main application)
├── start-web.sh               # Startup script
├── .env                       # API keys configuration
├── requirements.txt           # Python dependencies
│
├── legacy_files/              # Archived Unity/Unreal integration
│   ├── README.md              # Legacy system documentation
│   ├── project_one_demo/      # Original game integration
│   ├── websocket.py           # Old WebSocket server
│   └── ...                    # Other archived files
│
├── CREATE_CHARACTER.md        # Guide for creating new characters
└── README.md                  # This file
```

## Architecture

### Core System (`llm_prompt_core/`)

A **generic, reusable framework** for building LLM-powered dialogue systems. Key features:

- **Multi-provider support** - Easily switch between Claude, OpenAI, and Gemini
- **Scene-based narratives** - Structure conversations into manageable scenes
- **Query system** - Trigger state changes based on conversation content
- **Context management** - Intelligent summarization to maintain conversation history
- **Provider-agnostic** - Clean abstractions work with any LLM

**Documentation**: See [`llm_prompt_core/README.md`](llm_prompt_core/README.md) for comprehensive documentation.

### Modular Content System

**Characters** (`characters/`)
- Each character in its own file with personality, backstory, and configuration
- Easy to add new characters - just create a new Python file
- Clean separation of character definitions from application logic

**Scenes** (`scenes/`)
- Each scene in its own file with description and opening lines
- Modular scene creation for different story moments
- Simple template for adding new scenarios

See [`CREATE_CHARACTER.md`](CREATE_CHARACTER.md) for a guide on creating custom characters and scenes.

### Web Interface

- **Frontend** - Three.js 3D character visualization + chat UI
- **Backend** - aiohttp WebSocket server
- **Real-time** - Instant bidirectional communication
- **Self-contained** - No game engine required

## Key Features

### LLM-Powered Dialogue

The system uses large language models (currently Claude Sonnet 4.5) to generate dynamic, context-aware NPC responses. Models can be switched easily:

```python
# Current configuration (in project_one_demo/generate_project1_dialogue.py)
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model

DIALOGUE_MODEL = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
SUMMARY_MODEL = ClaudeSonnet45Model(temperature=0.2, max_tokens=5000)
QUERY_MODEL = ClaudeSonnet45Model(temperature=0.2, max_tokens=300)
```

### Scene-Based Conversations

Conversations are organized into **scenes** with:
- Scene descriptions and context
- Opening speeches
- Conditional queries that trigger state changes
- Summaries of previous scenes

Example scene flow:
1. Player enters "1_meet_the_caretaker"
2. NPC speaks opening lines
3. Player responds via voice/text
4. System evaluates queries, checks for state changes
5. NPC responds dynamically based on conversation
6. When queries complete, transition to next scene

### Text-to-Speech

Multiple TTS providers supported:
- **ElevenLabs** - High-quality cloud TTS (requires API key)
- **Kokoro** - Local GPU-accelerated TTS model

Switch providers in `websocket.py`:
```python
# ElevenLabs (cloud)
voice_client = CachedVoiceClient("voice_id", "eleven_turbo_v2", 3, "elevenlabs")

# Kokoro (local)
voice_client = CachedVoiceClient(None, None, None, tts_provider="kokoro")
```

## Running

### Basic Usage

```bash
# Start the WebSocket server (default port 8765)
python websocket.py
```

The server will listen for connections from game clients.

### GPU Support for Local TTS

To run Kokoro TTS on GPU, install PyTorch matching your CUDA version:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Check your CUDA version:
```bash
nvcc --version  # CUDA toolkit version
nvidia-smi      # GPU driver CUDA support
```

### Testing Kokoro TTS

```bash
python cachedvoiceclient.py
```

## Model Configuration

### Switching LLM Providers

Edit `project_one_demo/generate_project1_dialogue.py`:

**Claude (Anthropic)** - Current default:
```python
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model
DIALOGUE_MODEL = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
```

**OpenAI**:
```python
from llm_prompt_core.models.openai import GPT4oModel
DIALOGUE_MODEL = GPT4oModel(temperature=0.8, max_tokens=1500)
```

**Gemini**:
```python
from llm_prompt_core.models.gemini import GeminiFlash25NoThinking
DIALOGUE_MODEL = GeminiFlash25NoThinking(temperature=0.8, max_tokens=1500)
```

### Model Recommendations

- **Claude Sonnet 4.5** (default) - Best overall balance of quality, speed, and cost
- **Claude Opus 4** - Maximum quality for critical narrative moments
- **GPT-4o** - Strong alternative with good performance
- **Gemini Flash 2.5** - Fast and cost-effective for testing

## Implementation Details

### Message Handling

The core logic is in `ant_server.py`, which implements:
- `on_event_triggered(event_name)` - Handle game events (scene transitions)
- `on_user_transcript(message)` - Process player messages and generate NPC responses

### Adding New Scenes

1. Create scene directory in `project_one_demo/prompts/act_1/scenes/`
2. Add required files:
   - `scene_description.txt`
   - `opening_speech.txt`
   - `queries.txt`
   - `prev_scenes_description.txt`
3. Update scene list in `generate_project1_dialogue.py`

See [`llm_prompt_core/README.md`](llm_prompt_core/README.md) for file format details.

## Development

### Using Core System Standalone

The `llm_prompt_core` module can be used independently:

```python
from llm_prompt_core.types import SceneData, Line
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model

# Create a scene
scene = SceneData(
    scene_name="example",
    scene_description="A mysterious room.",
    actors=["Guide", "Player"],
    opening_speech=[Line(text="Welcome!", delay=0)],
    # ... other fields ...
)

# Generate dialogue
model = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
dialogue = scene.get_initial_dialog()
```

See the core documentation for complete examples.

### Testing

```bash
# Test core module imports
python -c "from llm_prompt_core.types import SceneData; print('✓ Core works')"

# Test game integration
export ANTHROPIC_API_KEY=test
python -c "from project_one_demo.generate_project1_dialogue import ACTORS; print('✓ Integration works')"
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'anthropic'"**
```bash
pip install anthropic
```

**"ANTHROPIC_API_KEY environment variable must be set"**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**Slow TTS with Kokoro**
- Ensure PyTorch is installed with CUDA support
- Check GPU is being used: `nvidia-smi`

**Model generates unexpected responses**
- Lower temperature for more focused output (0.2-0.5)
- Add more specific instructions to scene descriptions
- Review prompt templates in `llm_prompt_core/prompts/templates.py`

## Documentation

- **[LLM Prompt Core Documentation](llm_prompt_core/README.md)** - Comprehensive guide to the dialogue system
- **[LangChain Docs](https://python.langchain.com/)** - LLM abstraction framework
- **[Anthropic API](https://docs.anthropic.com/)** - Claude API reference

## License

[Add license information]

## Contributing

Contributions welcome! Please maintain separation between:
- Core system (`llm_prompt_core/`) - Keep game-agnostic
- Game integration (`project_one_demo/`) - Game-specific code
