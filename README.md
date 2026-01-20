# Digital Actors

An AI-powered interactive narrative system featuring dynamic characters with persistent memory, adaptive difficulty, and real-time storytelling orchestration.

## What Is This?

Digital Actors is a complete framework for creating AI-driven narrative experiences where:

- **Characters remember you** - Player memory system tracks your behavior, personality, and relationships across sessions
- **Stories adapt to you** - World Director AI adjusts difficulty and spawns events based on your performance
- **Every playthrough is different** - Dynamic event generation creates emergent gameplay
- **3D immersive environments** - WebGL-powered scenes (submarine interiors, character conversations)
- **Real-time orchestration** - AI dungeon master manages pacing, tension, and player assistance

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or with `uv`:
```bash
uv pip install -r requirements.txt
```

### 2. Configure API Key

Create or edit `.env` file:
```bash
nano .env
```

Add your Anthropic API key:
```env
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### 3. Launch the Web Interface

```bash
./start-web.sh
```

Then open: **http://localhost:8080**

## Key Features

### 🧠 Player Memory System

Every player interaction is tracked and remembered:

- **Personality profiling** - System learns if you're impulsive, cooperative, patient, or methodical
- **Behavioral patterns** - Tracks button mashing, interruptions, successful actions
- **Relationship tracking** - Characters remember past interactions and adjust attitudes
- **Performance history** - Success rates, failure counts, learning curves
- **Persistent across sessions** - SQLite database maintains long-term memory

Example: If you button-mash and interrupt frequently, characters will become frustrated and give more direct instructions. If you're patient and cooperative, they'll trust you more and provide encouragement.

**Documentation**: [PLAYER_MEMORY_SYSTEM.md](docs/PLAYER_MEMORY_SYSTEM.md)

### 🎮 World Director (Dungeon Master AI)

An AI orchestrator that watches your gameplay and intervenes dynamically:

- **Situation evaluation** - Analyzes scene state, player behavior, and tension after each action
- **Dynamic events** - Spawns crisis moments, lucky breaks, or challenges based on context
- **NPC behavior adjustment** - Changes character attitudes mid-scene (more helpful, frustrated, encouraging)
- **Adaptive difficulty** - Makes scenes easier if you're struggling, harder if you're skilled
- **Smart hints** - Provides subtle or direct guidance when you're stuck
- **Cooldown system** - Prevents over-intervention to maintain natural dialogue flow

Example: If you fail a scene 3 times, the Director spawns a "lucky break" event (bonus oxygen) and gives direct hints. If you're playing perfectly, it spawns a crisis to add challenge.

**Documentation**: [WORLD_DIRECTOR_SYSTEM.md](docs/WORLD_DIRECTOR_SYSTEM.md)

### 🎬 Interactive Scenes

#### Submarine Emergency Scenario

A tense survival scene where you work with engineer Casey Reeves to escape a flooded submarine:

- **Real-time state tracking** - Oxygen levels, trust meter, incorrect actions count
- **Interactive controls** - Mouse-look camera (~100° range), clickable control panel buttons (VENT, BALLAST, PUMP, ENGINE)
- **Interruption penalties** - Clicking buttons during character speech costs oxygen
- **Dynamic responses** - Character reacts to your specific button presses
- **Multiple endings** - Success (escape), failure (oxygen depleted), or relationship breakdown (trust too low)
- **3D environment** - Submarine interior with porthole view, bubbles, atmospheric lighting

#### Character Conversations

Standard dialogue mode with:
- Multiple character personalities (Eliza, Merlin, Detective Stone, Casey Reeves)
- Scene-based narrative progression
- 3D character visualization

### 🎯 Game Over System

Complete win/lose condition detection:

- **Failure criteria** - Oxygen depletion, trust breakdown, critical errors
- **Success criteria** - Scene objectives completed
- **Final NPC speech** - Character delivers contextual ending dialogue
- **Styled overlay screen** - "THE END" with outcome description and retry button
- **Memory recording** - Performance logged for future difficulty adjustments

### ⚡ Performance Optimizations

System optimized for smooth 60fps gameplay:

**Backend:**
- Claude Haiku 3.5 for 2-3x faster responses (1-2 seconds vs 4-6 seconds)
- Reduced token limits (800 vs 1500)
- Async architecture for concurrent operations

**Frontend:**
- Reduced particle counts (50 underwater particles, 20 bubbles)
- Optimized lighting (4 point lights, shadows disabled)
- Throttled canvas texture updates (every 15 frames)
- Smart raycasting (only on mouse movement)
- Pixel ratio capping (max 2x)

## Project Structure

```
digital-actors/
├── web_server.py              # Main application server (aiohttp + WebSocket)
├── player_memory.py           # Player tracking and personality profiling
├── world_director.py          # AI dungeon master orchestration
├── characters/                # Character definitions
│   ├── base.py
│   ├── eliza.py              # AI Caretaker
│   ├── wizard.py             # Merlin the Wizard
│   ├── detective.py          # Detective Stone
│   └── engineer.py           # Casey Reeves (submarine engineer)
├── scenes/                    # Scene definitions
│   ├── base.py
│   ├── introduction.py
│   ├── submarine.py          # Emergency submarine scenario
│   └── conversation.py
├── llm_prompt_core/          # Generic LLM dialogue framework
│   ├── models/               # Claude, OpenAI, Gemini wrappers
│   ├── prompts/              # Prompt templates
│   └── types.py              # Core data structures
├── web/                      # Frontend assets
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js            # Main app logic
│       ├── scene.js          # Character scene (Three.js)
│       └── submarine_scene.js # Submarine scene (Three.js)
├── data/                     # Runtime data
│   └── player_memory.db      # SQLite player database
├── docs/                     # Documentation
│   ├── PLAYER_MEMORY_SYSTEM.md
│   ├── WORLD_DIRECTOR_SYSTEM.md
│   ├── INTERRUPTION_SYSTEM.md
│   └── UPDATE_SUMMARY.md
├── .env                      # API keys (not in git)
├── requirements.txt
└── start-web.sh             # Launch script
```

## Architecture

### The Framework

```
          World Director (Dungeon Master AI)
                      ↓
    ┌─────────────────┴─────────────────┐
    ↓                                   ↓
Environment                     Virtual Actors
(Scenes, State, Events)         (Characters with Memory)
    ↓                                   ↓
         Player ↔ Interactive Experience
```

**Flow:**
1. Player performs action (button click, chat message)
2. Character responds with contextual dialogue
3. World Director evaluates situation
4. Director decides: Continue / Spawn Event / Adjust NPC / Give Hint
5. Player Memory records behavior patterns
6. System adapts difficulty for next interaction

### Response Cancellation System

Critical feature preventing queued responses from rapid actions:

```python
# Each action increments sequence counter
self.response_sequence += 1
my_response_id = self.response_sequence

# After LLM generation, check if response is still current
if my_response_id != self.current_response_id:
    return  # Discard stale response
```

This ensures if a player clicks 7 buttons rapidly, only the latest response is delivered.

### Player Memory Integration

Character prompts include full player context:

```
=== PLAYER MEMORY ===
Player Profile:
- IMPULSIVE: Acts without thinking, interrupts frequently (75/100)
- COOPERATIVE: Listens and follows instructions (45/100)

Relationship with you (casey):
You've worked with this player 3 times before.
You're frustrated with their past behavior.
They ignored your warnings 5 times.

Statistics:
- Total scenes: 5
- Success rate: 20%
- This scene attempt: 3
```

### World Director Decision Making

After each action:

```python
decision = await world_director.evaluate_situation(
    scene_id='submarine',
    scene_state={'oxygen': 40, 'trust': -15},
    dialogue_history=recent_exchanges,
    player_memory=player_memory,
    character_id='casey'
)

# Director returns:
# - 'continue' (most common, ~80%)
# - 'spawn_event' (~10%)
# - 'adjust_npc' (~5%)
# - 'give_hint' (~5%)
```

## Models and API

### Current Configuration

**Primary Model:** Claude Haiku 3.5
- Dialogue generation (temperature 0.8, max_tokens 800)
- World Director decisions (temperature 0.7, max_tokens 500)
- Query evaluation (temperature 0.2, max_tokens 200)

**Why Haiku?**
- 2-3x faster than Sonnet (1-2s vs 4-6s per response)
- Significantly cheaper (~$0.001 per interaction)
- Quality sufficient for real-time gameplay
- Maintains coherent personality and context

### Switching Models

Edit `web_server.py`:

```python
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model

# For higher quality (slower, more expensive)
DIALOGUE_MODEL = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
```

Available models:
- `ClaudeHaikuModel` - Fast, cost-effective (current)
- `ClaudeSonnet45Model` - High quality, slower
- `ClaudeOpus4Model` - Maximum quality, expensive
- `GeminiFlash25NoThinking` - Alternative fast option

## How It Works

### Player Flow

1. **Enter scene** - 3D environment loads, character gives opening speech
2. **Take action** - Click buttons, send chat messages
3. **Character responds** - Context-aware dialogue based on your action
4. **Director evaluates** - AI decides if intervention needed
5. **Scene progresses** - State changes (oxygen, trust), events spawn
6. **Memory updates** - Personality profile adjusts based on behavior
7. **Game over** - Win/lose conditions trigger ending sequence
8. **Memory persists** - Next playthrough uses learned player profile

### Example Interaction

**Player:** *rapidly clicks VENT button 3 times*

**System Response:**
1. Response cancellation discards first 2 clicks, processes only latest
2. Interruption penalty applied: -15 oxygen (player interrupted NPC)
3. Player memory records: `interrupted_count += 1`, `impulsiveness += 2`
4. Casey responds: "STOP! I told you to WAIT! You're going to get us killed!"
5. World Director evaluates: "Player struggling, 3rd attempt, oxygen critical"
6. Director decision: "Give direct hint"
7. Casey adds: "The BALLAST button. Press it. NOW."

## Development

### Adding New Characters

Create new file in `characters/`:

```python
from characters.base import Character

class NewCharacter(Character):
    def __init__(self):
        super().__init__()
        self.name = "Character Name"
        self.personality = "Brief personality description"
        self.backstory = "Character background..."
```

Register in `web_server.py` character list.

### Adding New Scenes

Create new file in `scenes/`:

```python
from scenes.base import Scene, Line

class NewScene(Scene):
    def __init__(self):
        super().__init__(
            scene_id="new_scene",
            scene_name="Scene Name",
            description="Scene description for LLM context",
            opening_speech=[
                Line(text="Opening line", delay=0)
            ]
        )
```

Add to scene list in `web_server.py`.

### Testing World Director

```bash
# Watch Director decisions in real-time
tail -f /tmp/webserver.log | grep "\[Director\]"
```

Output shows:
```
[Director] Decision: continue
[Director] Decision: give_hint (direct)
[Director] Decision: spawn_event (crisis)
[Director] Spawning: Pressure spike - oxygen leak
```

## Documentation

Comprehensive guides available:

- **[Player Memory System](docs/PLAYER_MEMORY_SYSTEM.md)** - How player tracking works, database schema, integration
- **[World Director System](docs/WORLD_DIRECTOR_SYSTEM.md)** - Dungeon master AI, decision flow, event generation
- **[Interruption System](docs/INTERRUPTION_SYSTEM.md)** - Penalty mechanics, detection logic
- **[Scene Architecture](docs/SCENE_ARCHITECTURE.md)** - Scene system design
- **[Update Summary](docs/UPDATE_SUMMARY.md)** - Recent changes and additions

## Running

```bash
# Start web server
./start-web.sh

# Or manually
export $(cat .env | grep -v '^#' | xargs)
python web_server.py

# Server runs on http://localhost:8080
```

### Environment Variables

```env
ANTHROPIC_API_KEY=your-key-here
PORT=8080  # Optional, defaults to 8080
```

## Testing the System

### Test 1: Struggling Player Detection

1. Start submarine scene
2. Button mash rapidly (click any button 5+ times)
3. Fail the scene (let oxygen reach 0)
4. Restart scene
5. **Expected:** Director gives direct hints, spawns help events, reduces penalties

### Test 2: Skilled Player Challenge

1. Complete submarine scene successfully
2. Restart and play perfectly (no interruptions, correct sequence)
3. **Expected:** Director spawns crisis events to add difficulty

### Test 3: Learning Behavior Reward

1. First attempt: button mash and interrupt (fail)
2. Second attempt: wait patiently for instructions
3. **Expected:** Character becomes encouraging ("You're listening! Much better!")

### Test 4: Response Cancellation

1. Rapidly click same button 5+ times
2. **Expected:** Only one character response, not 5 queued responses

## Troubleshooting

**"NameError: name 'Dict' is not defined"**
```bash
# Missing typing import in web_server.py
# Add: from typing import Dict, Any
```

**Port 8080 already in use**
```bash
# Kill existing process
lsof -ti:8080 | xargs kill -9
```

**ANTHROPIC_API_KEY not found**
```bash
# Load .env file
export $(cat .env | grep -v '^#' | xargs)
```

**Slow FPS in submarine scene**
- Already optimized to 60fps with Haiku model + reduced particles
- Check browser console for errors
- Try reducing particle count further in submarine_scene.js

**Scene too dark**
- Interior lighting added in latest version
- Adjust ambientLight intensity in submarine_scene.js if needed

**Director not intervening**
- Check cooldown hasn't blocked intervention
- Verify player_memory is being passed to Director
- Watch logs: `tail -f /tmp/webserver.log | grep Director`

## Performance Benchmarks

**Backend (per interaction):**
- Haiku response time: 1-2 seconds
- World Director evaluation: ~1 second
- Total latency: 2-3 seconds

**Frontend (submarine scene):**
- Target: 60 FPS
- Particle count: 70 total (50 underwater + 20 bubbles)
- Lights: 4 point lights, no shadows
- Texture updates: Throttled to 66ms intervals

**Database:**
- Player memory lookup: <10ms
- Scene end save: <50ms

## Future Enhancements

**Planned Features:**
- Multi-scene narrative arcs with Director tracking
- Procedural content generation for infinite replayability
- Voice input/output integration
- Multiplayer scenes with multiple NPCs coordinated by Director
- Emotional state tracking (frustration detection)
- Story branching based on player personality

**Potential Optimizations:**
- LLM response streaming for faster perceived latency
- Cached Director decisions for common situations
- Client-side prediction for smoother interactions

## Credits

**AI Models:**
- Claude Haiku 3.5 by Anthropic

**3D Graphics:**
- Three.js WebGL library

**Backend:**
- aiohttp async web framework
- SQLite database

## License

[Add license information]

---

**Getting Started:** Run `./start-web.sh` and open http://localhost:8080 to experience AI-driven adaptive storytelling with persistent character memory.
