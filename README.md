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

### 🔍 Query System & RAG Facts (NEW)

AI-powered scene intelligence for richer, more dynamic storytelling:

#### Query System (`query_system.py`)
LLM-based condition evaluation with caching and latching:

```python
# In a scene handler
async def process_action(self, action, scene_state, ctx=None):
    if ctx and action == "CHALLENGE":
        # Query evaluates natural language conditions
        has_evidence = await ctx.query(
            ctx.dialogue_history,
            "Player has caught the suspect in at least two contradictions",
            latch=True  # Once True, stays True for session
        )
        if has_evidence:
            ctx.trigger_event("confrontation_ready")
```

Features:
- **Caching**: MD5-hashed results avoid redundant LLM calls
- **Latching**: Once a condition is True, it stays True for the session
- **Session isolation**: Latch state isolated per player session
- **Fast evaluation**: Uses Claude Haiku with low temperature

#### RAG Facts (`rag_facts.py`)
Embedding-based fact retrieval for dense scene lore:

```python
# In scene definition (scenes/submarine.py)
facts = [
    "Lt. Commander James Kovich has a son named Adrian who is aboard.",
    "The reactor uses a VM-5 pressurized water design.",
    "Emergency ascent requires flooding the med bay compartment.",
    ...
]

super().__init__(
    id="submarine",
    facts=facts,  # Automatically indexed at scene load
    ...
)
```

How it works:
1. Facts are embedded at scene load using `all-MiniLM-L6-v2`
2. When player asks about something, relevant facts are retrieved
3. Retrieved facts are injected into the LLM prompt automatically
4. Falls back to keyword matching if sentence-transformers unavailable

#### Post-Speak Hooks (`scene_hooks.py`)
Data-driven hooks that run after every NPC response:

```python
# In scene definition - declarative, no custom code needed
from scene_hooks import create_standard_hooks

hooks = create_standard_hooks(
    slip_detection=True,           # Catch "when I..." reveals
    emotional_tracking=True,        # Track bonding moments
    name_mentions=["Adrian", "Mei"], # Track key names
    custom_hooks=[
        {
            "name": "sacrifice_mentioned",
            "query": "Speaker mentioned sacrifice or dying",
            "latch": False,
            "on_true": {
                "state": {"emotional_bond": "+5"},
                "event": "sacrifice_moment",
            },
        },
    ]
)

super().__init__(
    id="submarine",
    hooks=hooks,  # Registered automatically
    ...
)
```

Standard hook patterns:
- **slip_detection**: Catches verbal slips and contradictions
- **emotional_tracking**: Tracks bonding/vulnerability moments
- **name_mentions**: Tracks when specific names are mentioned
- **location_mentions**: Tracks when specific places are mentioned

Hook actions:
- `state`: Update scene state (use `"+1"` for delta, `50` for absolute)
- `event`: Trigger a named event (sent to frontend)
- `milestone`: Record a milestone for phase progression

#### Scene Context (`scene_context.py`)
Unified API for scene authors:

```python
@dataclass
class SceneContext:
    async def query(text, condition, latch=False) -> bool
    def get_relevant_facts(query, top_k=3) -> list[str]
    def get_state(key, default=None) -> Any
    def update_state(key, value) -> None
    def trigger_event(event_name) -> None
```

Passed to `process_action` for handlers that need advanced features.

### 💬 Contextual Reply Suggestions

For players who prefer quick interactions over typing, the system generates **3 contextual reply options** after each NPC response. These appear as clickable buttons below the chat input.

**How It Works:**

1. After each NPC response, the system generates suggestions using Claude Haiku
2. Suggestions are contextually aware of:
   - Current scene type (survival/crisis vs narrative)
   - Recent dialogue history
   - Scene state and situation
3. Players click a suggestion to send it as their response
4. Suggestions clear when typing or during NPC speech

**Example Flow:**
```
NPC: "The reactor pressure is climbing. We need to vent, but the
     manual release is jammed. What do you want to try?"

[Suggested Replies]
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Try the valve   │ │ Is there another│ │ How bad is it?  │
│ manually        │ │ way?            │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

**Configuration:**

Suggestions are generated in `web_server.py` via `generate_suggested_questions()`:
- **Timeout:** 2 seconds (falls back to defaults if LLM is slow)
- **Scene defaults:** Welcome scene has static suggestions; others are dynamic
- **Fallback options:** "What should I do?", "Tell me more", "I understand"

**Toggle Setting:**

Users can enable/disable reply suggestions via the Configuration panel:
- **Reply Suggestions toggle** - ON by default
- When disabled, suggestions are hidden globally across all scenes
- Setting persists for the session (resets on page reload)

**Design Notes:**
- Suggestions use the fast Haiku model for low latency
- They're generated in parallel with TTS synthesis
- Disabled during opening speeches and game over states
- Clicking a suggestion sends it immediately (no confirmation)

This feature balances accessibility for casual players with the full typing experience for those who prefer deeper engagement.

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
│
├── config/                    # Centralized configuration (single source of truth)
│   ├── __init__.py           # Config loader functions
│   └── scene_mappings.json   # Scene↔character mappings, categories, aliases
│
├── characters/                # Character definitions (NPCs)
│   ├── base.py               # Base Character dataclass
│   ├── eliza.py              # AI Caretaker
│   ├── wizard.py             # Merlin the Wizard
│   ├── detective.py          # Detective Stone
│   ├── engineer.py           # Casey Reeves (submarine engineer)
│   ├── mara_vane.py          # Mara Vane (murder mystery informant)
│   └── captain_hale.py       # Captain Hale (submarine captain)
│
├── scenes/                    # Scene definitions (data + structure)
│   ├── base.py               # Base Scene, SceneControl, SceneConstants
│   ├── submarine.py          # Submarine emergency (with facts + hooks)
│   ├── iconic_detectives.py  # Murder mystery (with facts + hooks)
│   ├── life_raft.py          # Submarine survival (with facts + hooks)
│   └── handlers/             # Scene-specific game logic (separated from data)
│       ├── __init__.py       # Handler registry
│       ├── base.py           # SceneHandler interface + post_speak
│       ├── life_raft_handler.py       # Life Raft button actions
│       └── iconic_detectives_handler.py  # Detective pin reactions
│
├── query_system.py           # LLM-based condition evaluation with caching
├── rag_facts.py              # Embedding-based fact retrieval
├── post_speak_hooks.py       # Post-response hook execution
├── scene_hooks.py            # Data-driven hook configuration
├── scene_context.py          # Unified API for scene authors
│
├── llm_prompt_core/          # Generic LLM dialogue framework
│   ├── models/               # Claude, OpenAI, Gemini wrappers
│   ├── prompts/              # Prompt templates
│   └── types.py              # Core data structures
│
├── web/                      # Frontend assets
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js            # Main app logic
│       ├── base_scene.js     # BaseScene interface for all 3D scenes
│       ├── scene.js          # Character conversation scene (Three.js)
│       ├── submarine_scene.js # Submarine scene (Three.js)
│       ├── detective_scene.js # Detective office scene (Three.js)
│       ├── life_raft_scene.js # Life raft scene (Three.js)
│       └── welcome_scene.js  # Welcome/intro scene (Three.js)
│
├── data/                     # Runtime data
│   └── player_memory.db      # SQLite player database
│
├── docs/                     # System documentation
│   ├── PLAYER_MEMORY_SYSTEM.md
│   ├── WORLD_DIRECTOR_SYSTEM.md
│   ├── INTERRUPTION_SYSTEM.md
│   └── SCENE_ARCHITECTURE.md
│
├── documents/                # Design documents & specs
│   ├── Digital-Actors-DESIGN_DOCUMENT.md
│   ├── life-raft.md
│   ├── Pressure-Point.md
│   └── ...
│
├── archive/                  # Historical implementation notes (reference only)
│
├── .env                      # API keys (not in git)
├── requirements.txt
└── start-web.sh             # Launch script
```

## Configuration

### Scenario Selection (Scene → Actor)

**Scenario is the master selection.** Users choose a scenario (e.g., "Iconic Detectives"), and the associated actor is displayed automatically.

In the Configuration panel:
1. **Scenario dropdown** - Select the experience (Pressure Point, Iconic Detectives, etc.)
2. **Actor display** - Shows the paired character name
3. **Tagline** - One-sentence scene description

```json
// config/scene_mappings.json
{
  "scenes": {
    "iconic_detectives": {
      "character": "mara_vane",
      "characterName": "Mara Vane",
      "displayName": "Iconic Detectives",
      "tagline": "You run a one-man detective agency. Mara Vane calls with a case. What happens next?"
    }
  }
}
```

**Why scenario-first?**
- Users think in terms of *experiences*, not character names
- Eliminates confusion from two interdependent dropdowns
- Taglines provide immediate context for what to expect

**Current Design:** Actor/scenario pairs are fixed. Each character has:
- Backstory and personality tuned for their scene
- Voice ID and emotional expression style
- Scene-specific facts and hooks

**Future Consideration:** Non-contextual actors (e.g., Mara Vane in the submarine) could enable emergent gameplay, but pairs remain fixed for now to maintain narrative quality.

### TTS Voice Models

Voice synthesis uses ElevenLabs with two operational modes, configurable per-session:

| Mode | Model | Audio Tags | Latency | Use Case |
|------|-------|------------|---------|----------|
| **Expressive** (default) | `eleven_v3` | ✅ `[laughs]`, `[sighs]`, etc. | ~2-3s | Paralinguistic richness |
| **Fast** | `eleven_turbo_v2_5` | ❌ Stripped | ~1s | Low-latency gameplay |

**Mode Selection:**
- Frontend sends `tts_mode: "expressive"` or `tts_mode: "fast"` on session init
- Expressive mode auto-selects v3 when audio tags detected, turbo otherwise
- Fast mode always uses turbo and strips all `[emotion]` tags

**Voice Configuration:**

Voice IDs and settings are modular, defined in `tts_elevenlabs.py`:

```python
# Voice IDs per character (override via environment)
DEFAULT_VOICE_IDS = {
    "engineer": os.getenv("ELEVENLABS_VOICE_ENGINEER", "pNInz6obpgDQGcFmaJgB"),
    "captain_hale": os.getenv("ELEVENLABS_VOICE_CAPTAIN_HALE", "SOYHLrjzK2X1ezoPC6cr"),
    "mara_vane": os.getenv("ELEVENLABS_VOICE_MARA_VANE", "21m00Tcm4TlvDq8ikWAM"),
    ...
}

# Voice settings per character (stability, style, etc.)
VOICE_SETTINGS = {
    "engineer": {"stability": 0.4, "style": 0.2, ...},  # Stressed, urgent
    "captain_hale": {"stability": 0.65, "style": 0.1, ...},  # Calm, measured
    ...
}
```

**Environment Overrides:**
```env
ELEVENLABS_API_KEY=your-key-here
ELEVENLABS_MODEL=eleven_turbo_v2_5          # Default model
ELEVENLABS_VOICE_ENGINEER=your-voice-id     # Per-character overrides
ELEVENLABS_PRESERVE_AUDIO_TAGS=true         # Keep [laughs] etc.
```

**Adding New Voices:**

1. Add voice ID to `DEFAULT_VOICE_IDS` in `tts_elevenlabs.py`
2. Add voice settings to `VOICE_SETTINGS` (stability, style, etc.)
3. Optionally add env var override for easy swapping

The modular design supports easy testing of new TTS providers and voice models.

---

## Architecture

### Global vs Scene-Specific Separation

The codebase maintains a clear separation between **GLOBAL** settings and **SCENARIO-specific** game logic:

#### Centralized Configuration (`config/`)

Single source of truth for scene↔character mappings:

```json
// config/scene_mappings.json
{
  "scenes": {
    "submarine": { "character": "engineer", "sceneClass": "SubmarineScene" },
    "iconic_detectives": { "character": "mara_vane", "sceneClass": "DetectiveScene" }
  },
  "characterAliases": { "casey": "engineer", "mara": "mara_vane" }
}
```

Both frontend and backend use this config via `/api/config` endpoint - no duplicate mappings.

#### Scene Data vs Scene Logic

**Scene Config** (e.g., `scenes/submarine.py`):
- Static data: name, description, controls, state variables
- Success/failure criteria
- Scene-specific constants (penalty values, thresholds)

**Scene Handler** (e.g., `scenes/handlers/life_raft_handler.py`):
- Dynamic game logic: button action processing
- State modifications: oxygen transfers, score updates
- Evidence pin reactions (for investigation scenes)

```python
# Handler processes actions and returns state changes
result = handler.process_action('O2 VALVE', scene_state)
# Returns: ActionResult(success=True, state_changes={'oxygen': +15})
```

#### Scene Constants

Scene-specific values override global defaults via `SceneConstants`:

```python
# In scenes/submarine.py
scene_constants=SceneConstants(
    interruption_oxygen_penalty=10,  # Override global default
    crisis_oxygen_penalty=15,
    critical_level=20,
    max_incorrect_actions=5,
)
```

#### Button Press Limits

Controls can specify max presses and cooldowns per-scene:

```python
SceneControl(
    id="flood_med_bay",
    label="FLOOD MED BAY",
    max_presses=1,        # One-shot action
    cooldown_seconds=5.0, # 5 second cooldown
)
```

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

### JavaScript Scene System

All 3D scenes extend a common interface with lifecycle management:

```javascript
// web/js/base_scene.js defines the interface
class BaseScene {
    init()      // Initialize Three.js scene, camera, renderer
    dispose()   // Clean up all resources (geometries, materials, textures)
    updateState(state)   // Receive state updates from server
    setPhase(phase)      // Handle phase transitions
}
```

**Resource Cleanup:**

Every scene MUST implement `dispose()` to prevent memory leaks:

```javascript
dispose() {
    // Remove event listeners
    window.removeEventListener('resize', this.onWindowResize);

    // Dispose Three.js objects
    this.scene.traverse((object) => {
        if (object.geometry) object.geometry.dispose();
        if (object.material) object.material.dispose();
    });

    // Remove renderer
    this.renderer.dispose();
    this.renderer.domElement.remove();
}
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

### Adding New Scenes (Standardized Approach)

Every scene should follow this standardized pattern with facts and hooks:

```python
# scenes/my_new_scene.py
from scenes.base import (
    Scene, SceneControl, StateVariable, SuccessCriterion,
    FailureCriterion, SceneArtAssets, AudioAssets
)
from llm_prompt_core.types import Line
from scene_hooks import create_standard_hooks


class MyNewScene(Scene):
    def __init__(self):
        # 1. Define audio/art assets
        audio = AudioAssets(...)
        art_assets = SceneArtAssets(...)

        # 2. Define controls (buttons)
        controls = [
            SceneControl(id="action_1", label="DO THING", npc_aware=True),
            ...
        ]

        # 3. Define state variables
        state_variables = [
            StateVariable(name="tension", initial_value=50.0),
            ...
        ]

        # 4. Define RAG facts (lore the NPC can reference)
        facts = [
            "Character X has a secret they're hiding.",
            "Location Y was the site of an incident 10 years ago.",
            "The key to the mystery is the blue envelope.",
            ...
        ]

        # 5. Define hooks (post-speak processing)
        hooks = create_standard_hooks(
            slip_detection=True,         # Catch contradictions
            emotional_tracking=True,     # Track bonding moments
            name_mentions=["Secret Character"],  # Track key names
            custom_hooks=[
                {
                    "name": "secret_revealed",
                    "query": "Speaker revealed or hinted at the secret",
                    "latch": True,
                    "on_true": {
                        "state": {"secret_known": True},
                        "event": "revelation",
                    },
                },
            ]
        )

        # 6. Initialize with all components
        super().__init__(
            id="my_new_scene",
            name="My New Scene",
            description="Scene description for LLM...",
            facts=facts,          # RAG facts
            hooks=hooks,          # Post-speak hooks
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            opening_speech=[Line(text="Opening line", delay=0)],
        )
```

**Key principles:**
1. **Facts**: Write 10-30 facts covering characters, locations, history, and key details
2. **Hooks**: Use `create_standard_hooks()` for common patterns, add `custom_hooks` for scene-specific logic
3. **No bespoke code**: All hook logic is declarative via configuration
4. **Handler optional**: Only create a handler if you need button-specific game logic

**Registering the scene:**

```python
# scenes/__init__.py
from scenes.my_new_scene import MyNewScene

SCENES = {
    ...
    'my_new_scene': MyNewScene(),
}
```

Add character mapping in `config/scene_mappings.json`.

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

- **[Explainer Guide](docs/EXPLAINER.md)** - Friendly overview of all core concepts (start here!)
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
# Required
ANTHROPIC_API_KEY=your-key-here

# Server
PORT=8080  # Optional, defaults to 8080

# TTS (ElevenLabs)
ELEVENLABS_API_KEY=your-key-here           # Required for voice synthesis
ELEVENLABS_MODEL=eleven_turbo_v2_5         # Default TTS model
ELEVENLABS_PRESERVE_AUDIO_TAGS=true        # Keep [laughs], [sighs] for v3

# Voice ID overrides (optional - use your own cloned voices)
ELEVENLABS_VOICE_ENGINEER=voice-id-here
ELEVENLABS_VOICE_CAPTAIN_HALE=voice-id-here
ELEVENLABS_VOICE_MARA_VANE=voice-id-here
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
- Non-contextual actors (characters appearing in different scenes)

**TTS Roadmap:**
- **Local TTS models** - Support for self-hosted voice synthesis (Coqui, XTTS, etc.) for offline/low-latency scenarios
- **New provider testing** - Modular architecture allows road-testing emerging TTS services
- **Voice cloning integration** - Custom character voices from audio samples
- **Real-time streaming TTS** - Chunk-based audio for reduced first-byte latency

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
