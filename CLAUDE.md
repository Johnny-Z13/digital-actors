# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Digital Actors is an AI-powered interactive narrative framework where characters remember players across sessions, adapt dynamically to behavior, and participate in 3D WebGL environments. The system uses a World Director AI (dungeon master) to orchestrate pacing, difficulty, and emergent gameplay.

**Key Technologies:** Python 3.12+, aiohttp, WebSocket, Claude Haiku (Anthropic), ElevenLabs TTS, Three.js, SQLite

---

## Essential Commands

### Development

```bash
# Start the web server (loads .env automatically)
./start-web.sh

# Manual start with environment variables
export $(cat .env | grep -v '^#' | xargs) && python web_server.py

# Lint Python code
ruff check .

# Format Python code
ruff format .

# Lint JavaScript (frontend)
cd web && npm run lint

# Format JavaScript (frontend)
cd web && npm run format
```

### Testing

```bash
# Run all unit tests
python -m unittest discover tests/

# Run specific test file
python -m unittest tests/test_emotion_engine.py

# Run single test class
python -m unittest tests.test_emotion_engine.TestEmotionProfile

# Run single test method
python -m unittest tests.test_emotion_engine.TestEmotionProfile.test_dataclass_defaults
```

**Test Coverage:** Comprehensive tests for emotion processing, encryption, logging, session modules, scene conditions, query system, player memory, and World Director. Integration tests available in `tests/integration/`.

### Docker

```bash
# Development mode (hot-reload)
docker-compose up digital-actors-dev

# Production mode with monitoring
docker-compose up

# Includes Prometheus (port 9090) and Grafana (port 3030)
```

See `DOCKER.md` and `docs/DEPLOYMENT.md` for production deployment.

---

## Critical Architecture Concepts

### 1. Response Cancellation System

**Problem:** Rapid button clicking queues multiple LLM calls, resulting in delayed, stale responses.

**Solution:** `response_queue.py` implements priority-based queueing with sequence IDs:

```python
# Each action increments sequence counter
self.response_sequence += 1
my_response_id = self.response_sequence

# After LLM generation completes, check if response is still current
if my_response_id != self.current_response_id:
    return  # Discard stale response
```

**Key Files:**
- `response_queue.py` - Priority queue with CRITICAL > URGENT > NORMAL > BACKGROUND levels
- `web_server.py:ChatSession` - Manages sequence tracking

**When editing:** Ensure all async response paths check sequence validity before sending to client.

---

### 2. Scene Data vs Scene Logic Separation

Scenes separate **static definitions** (data) from **dynamic behavior** (logic):

**Scene Definition** (`scenes/submarine.py`):
- Controls, state variables, success/failure criteria
- RAG facts (lore for character knowledge)
- Post-speak hooks (declarative event system)
- Scene constants (penalty overrides)

**Scene Handler** (`scenes/handlers/submarine_handler.py`):
- Button action processing
- State change calculations
- Evidence pin reactions (detective scenes)

```python
# Handler returns ActionResult with state changes
result = handler.process_action('VENT', scene_state, ctx)
# Returns: ActionResult(success=True, state_changes={'oxygen': +15})
```

**Key Principle:** Handlers are **optional**. If a scene only needs dialogue without custom button logic, no handler is needed.

---

### 3. Configuration Single Source of Truth

`config/scene_mappings.json` is the **only** place that defines scene↔character mappings:

```json
{
  "scenes": {
    "submarine": {
      "character": "engineer",
      "characterName": "Casey Reeves",
      "displayName": "Pressure Point",
      "sceneClass": "SubmarineScene"
    }
  }
}
```

Both frontend and backend load this via `/api/config` endpoint. **Never hardcode mappings elsewhere.**

**Why:** Eliminates duplicate definitions, makes pairing changes trivial.

---

### 4. RAG Facts System

Scenes can define facts that are **automatically indexed and retrieved** based on player dialogue:

```python
# In scenes/submarine.py
facts = [
    "Lt. Commander James Smith has a son named Adrian aboard.",
    "The reactor uses a VM-5 pressurized water design.",
    "Emergency ascent requires flooding the med bay compartment.",
]

super().__init__(id="submarine", facts=facts, ...)
```

**How it works:**
1. `rag_facts.py` embeds facts using `all-MiniLM-L6-v2` at scene load
2. Player message triggers semantic search (top-K retrieval)
3. Relevant facts are injected into LLM prompt automatically
4. Falls back to keyword matching if embeddings unavailable

**Key Files:**
- `rag_facts.py` - Embedding-based fact retrieval
- `scene_context.py` - `get_relevant_facts()` API for handlers

---

### 5. Post-Speak Hooks (Declarative Event System)

Hooks execute **after every NPC response** without custom code:

```python
from scene_hooks import create_standard_hooks

hooks = create_standard_hooks(
    slip_detection=True,           # Catch "when I..." reveals
    emotional_tracking=True,        # Track bonding moments
    name_mentions=["Adrian", "Mei"],
    custom_hooks=[
        {
            "name": "sacrifice_mentioned",
            "query": "Speaker mentioned sacrifice or dying",
            "latch": True,  # Once True, stays True
            "on_true": {
                "state": {"emotional_bond": "+5"},  # +5 delta
                "event": "sacrifice_moment",        # Frontend event
            },
        },
    ]
)
```

**Hook Actions:**
- `state`: Update scene state (`"+5"` = delta, `50` = absolute)
- `event`: Trigger named event (sent to frontend)
- `milestone`: Record milestone for phase progression

**Key Files:**
- `scene_hooks.py` - Declarative hook configuration
- `post_speak_hooks.py` - Hook execution engine
- `query_system.py` - LLM-based condition evaluation with caching

---

### 6. Query System (LLM-Based Conditions)

Evaluate natural language conditions without bespoke code:

```python
# In a scene handler
has_evidence = await ctx.query(
    ctx.dialogue_history,
    "Player has caught suspect in at least two contradictions",
    latch=True  # Once True, stays True for session
)
```

**Features:**
- **MD5 caching:** Identical queries return cached results
- **Latching:** Once True, stays True for session (optional)
- **Session isolation:** Latch state isolated per player
- **Fast model:** Uses Claude Haiku with temperature 0.2

**Key Files:**
- `query_system.py` - Core evaluation logic with caching
- `scene_context.py` - `ctx.query()` API

---

### 7. Player Memory Integration

`player_memory.py` tracks persistent player personality across sessions:

**Tracked Attributes:**
- **Personality:** Impulsiveness (0-100), Patience (0-100), Cooperation (0-100), Problem-solving (0-100)
- **Behavioral patterns:** Button mashing, interruptions, success rates
- **Relationships:** Trust level per character (-100 to +100)
- **Performance:** Scene attempts, learning curves

**Integration:** Character prompts automatically include:

```
=== PLAYER MEMORY ===
Player Profile:
- IMPULSIVE: Acts without thinking, interrupts frequently (75/100)
- COOPERATIVE: Listens and follows instructions (45/100)

Relationship with you (casey):
You've worked with this player 3 times before.
You're frustrated with their past behavior.
They ignored your warnings 5 times.
```

**Key Files:**
- `player_memory.py` - SQLite-based persistence
- `data/player_memory.db` - SQLite database (created at runtime)

---

### 8. World Director (Dungeon Master AI)

`world_director.py` + `director_rules.py` implement a **hybrid decision system**:

**Fast Rules Layer** (milliseconds):
- Pattern-matched scenarios return decisions immediately (~70% of cases)
- Example: "Player failed 3 times → give hint"

**LLM Layer** (1-2 seconds):
- Complex, nuanced decisions for ambiguous situations
- Fallback when rules don't match

**Decisions:**
- `continue` (~80%) - Player doing fine
- `spawn_event` (~10%, 10s cooldown) - Crisis/opportunity
- `adjust_npc` (~5%, 8s cooldown) - Change character attitude
- `give_hint` (~5%, 8s cooldown) - Offer guidance

**Key Files:**
- `world_director.py` - Main orchestration logic
- `director_rules.py` - Fast pattern matching rules
- `constants.py` - Cooldown timings, difficulty thresholds

---

### 9. JavaScript Scene Lifecycle

All 3D scenes extend `BaseScene` interface:

```javascript
class BaseScene {
    init()      // Initialize Three.js scene, camera, renderer
    dispose()   // Clean up all resources (CRITICAL for memory leaks)
    updateState(state)   // Receive state updates from server
    setPhase(phase)      // Handle phase transitions
}
```

**Critical:** Every scene **MUST** implement `dispose()` to prevent memory leaks:

```javascript
dispose() {
    window.removeEventListener('resize', this.onWindowResize);
    this.scene.traverse((object) => {
        if (object.geometry) object.geometry.dispose();
        if (object.material) object.material.dispose();
    });
    this.renderer.dispose();
    this.renderer.domElement.remove();
}
```

**Key Files:**
- `scenes/base/base_scene.js` - Base interface
- `scenes/submarine/submarine_scene.js` - Example implementation
- `web/js/app.js` - Scene lifecycle management

---

### 10. 3D Environment Integration

**New architecture:** Scenes are now organized in **scene-centric folders** with all assets co-located:

```
scenes/
├── base/
│   ├── base.py               # Scene, SceneControl, StateVariable
│   ├── base_scene.js         # JavaScript BaseScene interface
│   ├── handler_base.py       # SceneHandler base class
│   └── world_labs_importer.js  # GLB import utility
├── wizard/                   # GLB-based 3D environment
│   ├── quest.py              # Scene definition
│   ├── merlins_room_scene.js # 3D scene code
│   ├── merlins_workshop.glb  # World Labs environment (142MB)
│   ├── camera_config.json    # Camera positioning preset
│   └── art_prompt.md         # World Labs generation prompt
├── foxhole/                  # Panoramic 360° environment
│   ├── foxhole.py            # Scene definition
│   ├── foxhole_scene.js      # Panorama scene code
│   ├── foxhole_panorama.jpg  # 360° panoramic image
│   ├── foxhole_handler.py    # Button action handler
│   ├── camera_config.json    # Camera positioning
│   └── art_prompt.md         # Art generation prompt
└── submarine/, detective/, etc.
```

**Two Environment Approaches:**

1. **GLB Models (World Labs)** - Full 3D environments with depth and complex geometry
2. **Panoramic Spheres** - 360° images mapped to inverted sphere (lighter weight, simpler)

**World Labs Importer** (`scenes/base/world_labs_importer.js`):
- Standardized GLB loading with automatic scaling/centering
- Smart camera positioning using bounding box heuristics
- Save/load camera presets from `camera_config.json`
- Developer workflow: **SHIFT+C** to export camera positions
- WASD debug controls for manual positioning

**Usage:**
```javascript
const result = await WorldLabsImporter.load(
    '/scenes/wizard/merlins_workshop.glb',
    scene,
    camera,
    {
        targetSize: 15,
        cameraConfigPath: '/scenes/wizard/camera_config.json',
        autoPositionCamera: true
    }
);
```

**Camera Config Format:**
```json
{
  "position": {"x": -1.74, "y": 1.43, "z": -1.6},
  "target": {"x": 0.19, "y": 0.93, "z": -1.44},
  "fov": 60,
  "description": "Optimal viewing angle"
}
```

#### Panoramic Sphere Scenes

**Alternative to GLB:** Use 360° panoramic images for lighter weight, simpler environments.

**Implementation** (`scenes/foxhole/foxhole_scene.js`):
```javascript
loadPanorama() {
    // Create inverted sphere geometry
    const geometry = new THREE.SphereGeometry(500, 60, 40);
    geometry.scale(-1, 1, 1); // Invert so texture is on inside

    // Load 360° panoramic image
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load('/scenes/foxhole/foxhole_panorama.png', (texture) => {
        const material = new THREE.MeshBasicMaterial({
            map: texture,
            side: THREE.BackSide  // Render inside of sphere
        });
        this.panoramaSphere = new THREE.Mesh(geometry, material);
        this.scene.add(this.panoramaSphere);
    });
}

setupMouseControls() {
    // Mouse drag to rotate camera
    let cameraRotationX = 0;
    let cameraRotationY = 0;

    this.container.addEventListener('mousemove', (event) => {
        if (!isMouseDown) return;

        const deltaX = event.clientX - previousMouseX;
        const deltaY = event.clientY - previousMouseY;

        cameraRotationY -= deltaX * 0.003;
        cameraRotationX -= deltaY * 0.003;

        // Limit vertical rotation
        cameraRotationX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, cameraRotationX));

        this.camera.rotation.order = 'YXZ';
        this.camera.rotation.x = cameraRotationX;
        this.camera.rotation.y = cameraRotationY;
    });
}
```

**When to use:**
- **GLB models**: Full 3D environments with depth, multiple objects, complex lighting
- **Panoramic spheres**: Single viewpoint scenes (submarine bridges, offices, rooms), faster loading, simpler implementation

**Asset requirements:**
- 360° equirectangular panoramic image (PNG or JPG)
- 4096x2048 or higher resolution recommended
- Can be generated by World Labs, rendered in Blender, or photographed with 360° cameras

**Key Files:**
- `scenes/base/world_labs_importer.js` - GLB import system
- `scenes/foxhole/foxhole_scene.js` - Panoramic scene example
- `WORLD_LABS_INTEGRATION.md` - Complete integration guide
- `docs/scenes/README.md` - Scene development guide with art prompts

---

## File Organization Patterns

### Backend Python Structure

```
digital-actors/
├── web_server.py              # Main server (CRITICAL - 2000+ lines, needs refactoring)
├── response_queue.py          # Response priority system
├── player_memory.py           # Persistent player tracking (SQLite)
├── world_director.py          # Dungeon master AI
├── director_rules.py          # Fast pattern matching for director
├── query_system.py            # LLM-based condition evaluation
├── rag_facts.py               # Embedding-based fact retrieval
├── post_speak_hooks.py        # Hook execution engine
├── scene_hooks.py             # Declarative hook configuration
├── scene_context.py           # Unified API for scene authors
├── constants.py               # Centralized magic numbers
├── exceptions.py              # Custom exception hierarchy
│
├── config/                    # Single source of truth
│   ├── __init__.py           # Config loader functions
│   └── scene_mappings.json   # Scene↔character mappings
│
├── characters/                # Character definitions
│   ├── base.py               # Character dataclass
│   └── [character_name].py   # Individual character modules
│
├── scenes/                    # SCENE-CENTRIC FOLDER STRUCTURE
│   ├── base/                 # Shared scene utilities
│   │   ├── base.py          # Scene, SceneControl, StateVariable
│   │   ├── base_scene.js    # JavaScript BaseScene interface
│   │   ├── handler_base.py  # SceneHandler base class
│   │   └── world_labs_importer.js  # GLB import utility
│   ├── wizard/               # Merlin's Room (GLB-based 3D)
│   │   ├── quest.py         # Scene definition
│   │   ├── merlins_room_scene.js
│   │   ├── merlins_workshop.glb  # World Labs environment
│   │   ├── camera_config.json
│   │   └── art_prompt.md
│   ├── foxhole/              # Foxhole (panoramic 360°)
│   │   ├── foxhole.py       # Scene definition (597 lines)
│   │   ├── foxhole_scene.js # Panorama scene code
│   │   ├── foxhole_panorama.png  # 360° panoramic image
│   │   ├── foxhole_handler.py    # Button action handler
│   │   ├── camera_config.json
│   │   └── art_prompt.md
│   ├── submarine/            # Submarine scene
│   │   ├── submarine.py
│   │   └── submarine_scene.js
│   └── detective/            # Detective office
│       ├── iconic_detectives.py
│       ├── iconic_detectives_handler.py
│       ├── detective_scene.js
│       └── phone.glb
│
├── sessions/                  # ChatSession refactoring (in progress)
│   ├── response_handler.py   # TTS, audio generation (16 tests)
│   ├── game_state_manager.py # State tracking (11 tests)
│   ├── dialogue_engine.py    # LLM interaction (8 tests)
│   └── session_orchestrator.py  # Component coordination
│
├── llm_prompt_core/          # Generic LLM dialogue framework
│   ├── models/               # Claude, OpenAI, Gemini wrappers
│   ├── prompts/              # Prompt templates
│   └── types.py              # Core data structures
│
└── tests/                    # Comprehensive test suite
    ├── test_emotion_engine.py
    ├── test_database_encryption.py
    ├── test_logging.py
    ├── test_sessions_refactoring.py  # 24 tests for session modules
    ├── test_scene_conditions.py
    ├── test_query_system.py
    ├── test_player_memory.py
    ├── test_world_director.py
    └── integration/          # Integration tests
```

### Frontend JavaScript Structure

**Note:** 3D scene JavaScript files are now co-located with their scenes in `scenes/[scene_name]/` folders (see above).

```
web/
├── index.html
├── css/style.css
└── js/
    ├── app.js                 # Main app logic, WebSocket handling
    ├── scene.js               # Character conversation scene
    └── welcome_scene.js       # Welcome/intro scene
```

---

## Production Features

### Monitoring & Observability

**Prometheus Metrics** (`metrics.py`):
- Request counts by scene/character/status
- Response time distribution (p50/p95/p99 percentiles)
- LLM API latency by provider/model
- TTS processing time
- Error counts by type
- Active session gauge
- Database query time

**Access:** `/metrics` endpoint (scraped every 15s by Prometheus)

**Grafana Dashboards:**
- Pre-built `grafana-dashboard.json` with 8 monitoring panels
- Request rate, active sessions, error rate, response times
- LLM/TTS performance tracking

**Structured JSON Logging** (`logging_config.py`):
- Production-grade structured logging with contextual data
- Auto-detection of environment (dev/production)
- ELK/Datadog compatible field naming
- Event-based logging: `log_event()`, `info_event()`, etc.

**Configuration:**
```env
LOG_LEVEL=INFO              # INFO or DEBUG
LOG_FORMAT_JSON=true        # true for JSON, false for readable
ENV=production              # production or development
```

**Sentry Error Tracking:**
- Optional Sentry integration for exception tracking
- Performance tracing with configurable sample rate
- Environment-aware error reporting

**See:** `docs/MONITORING.md` (447 lines), `docs/LOGGING.md` (150+ lines)

---

### Security Features

**Database Encryption** (`encryption_utils.py`):
- Fernet-based symmetric encryption for sensitive player data
- Encrypts personality profiles, relationships, conversation history
- Key rotation support with `rotate_key()`
- Transparent integration with PlayerMemory system

**Configuration:**
```env
DB_ENCRYPTION_KEY=your-fernet-key-here
```

**Generate key:** `python generate_encryption_key.py`

**WebSocket Security:**
- HTML escaping for all user content (XSS prevention)
- AST-based condition parsing (code injection prevention)
- Background task tracking (prevents silent failures)

**Docker Security:**
- Non-root user (`appuser`) in containers
- Multi-stage builds with minimal attack surface
- Health check endpoints
- Environment-based secrets management

**See:** `docs/DEPLOYMENT.md` for production security best practices

---

### ChatSession Refactoring (In Progress)

**Status:** Phase 1 complete - 4 new session modules with 35+ tests

The monolithic `ChatSession` class (2000+ lines) is being refactored into focused modules:

1. **`sessions/response_handler.py`** (228 lines, 16 tests, 69% coverage)
   - TTS, audio generation, response delivery
   - Response queue management
   - WebSocket sending

2. **`sessions/game_state_manager.py`** (268 lines, 11 tests, 45% coverage)
   - Scene state tracking
   - Dynamic state updates (oxygen, radiation, etc.)
   - Game over condition evaluation
   - Phase transitions

3. **`sessions/dialogue_engine.py`** (373 lines, 8 tests)
   - LLM interaction (Claude Haiku)
   - Prompt building with context
   - RAG facts retrieval
   - Death speech generation

4. **`sessions/session_orchestrator.py`** (323 lines)
   - Coordinates all session components
   - Component lifecycle management
   - Future ChatSession replacement (not yet integrated)
   - Dependency injection pattern

**Purpose:** Break down god object into testable, maintainable components. Current `ChatSession` in `web_server.py` remains unchanged for backward compatibility.

**See:** `docs/REFACTORING_SESSION_MODULES.md` (232 lines)

---

## Common Patterns

### Adding a New Scene

**Modern approach:** Create a scene-centric folder with all assets co-located.

1. **Create scene folder structure:**

```bash
mkdir -p scenes/my_scene
touch scenes/my_scene/__init__.py
```

**Choose environment approach:**
- **GLB Model**: Full 3D environment with depth (see `scenes/wizard/`)
- **Panoramic Sphere**: 360° image for single viewpoint (see `scenes/foxhole/`)

2. **Create scene definition** (`scenes/my_scene/my_scene.py`):

```python
from scenes.base import Scene, SceneControl, StateVariable
from scene_hooks import create_standard_hooks

class MyScene(Scene):
    def __init__(self):
        # Define RAG facts (10-30 facts covering lore)
        facts = [
            "Character X has a secret.",
            "Location Y is important.",
        ]

        # Define hooks (data-driven, no custom code)
        hooks = create_standard_hooks(
            slip_detection=True,
            emotional_tracking=True,
            custom_hooks=[...]
        )

        # Define controls
        controls = [
            SceneControl(id="action_1", label="DO THING", npc_aware=True),
        ]

        super().__init__(
            id="my_scene",
            name="My Scene",
            description="Scene description for LLM...",
            facts=facts,
            hooks=hooks,
            controls=controls,
        )
```

2. **Create JavaScript scene** (`scenes/my_scene/my_scene_scene.js`):

**For GLB models:**
```javascript
import { WorldLabsImporter } from '../base/world_labs_importer.js';

async init() {
    // ... camera, renderer setup ...
    const result = await WorldLabsImporter.load(
        '/scenes/my_scene/environment.glb',
        this.scene,
        this.camera
    );
}
```

**For panoramic spheres:**
```javascript
loadPanorama() {
    const geometry = new THREE.SphereGeometry(500, 60, 40);
    geometry.scale(-1, 1, 1);

    const textureLoader = new THREE.TextureLoader();
    textureLoader.load('/scenes/my_scene/panorama.png', (texture) => {
        const material = new THREE.MeshBasicMaterial({
            map: texture,
            side: THREE.BackSide
        });
        this.panoramaSphere = new THREE.Mesh(geometry, material);
        this.scene.add(this.panoramaSphere);
    });
}
```

3. **Register scene** (`scenes/__init__.py`):

```python
from scenes.my_scene.my_scene import MyScene

SCENES = {
    'my_scene': MyScene(),
}
```

4. **Add mapping** (`config/scene_mappings.json`):

```json
{
  "scenes": {
    "my_scene": {
      "character": "existing_character_id",
      "characterName": "Character Name",
      "displayName": "Scene Display Name",
      "requiresCustomScene": true
    }
  }
}
```

5. **Register JavaScript scene class** (`web/js/app.js`):

Add scene class mapping in the `SCENE_CLASSES` object and import at the top of the file.

6. **Optional: Create handler** (only if custom button logic needed):

```python
# scenes/handlers/my_scene_handler.py
from scenes.handlers.base import SceneHandler, ActionResult

class MySceneHandler(SceneHandler):
    async def process_action(self, action, scene_state, ctx=None):
        if action == "action_1":
            return ActionResult(
                success=True,
                state_changes={'score': '+10'}
            )
        return ActionResult(success=True)
```

---

### Switching LLM Models

Edit `web_server.py`:

```python
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model

# For higher quality (slower, more expensive)
DIALOGUE_MODEL = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
```

**Available models:**
- `ClaudeHaikuModel` - Fast, cost-effective (current default)
- `ClaudeSonnet45Model` - High quality, slower
- `ClaudeOpus4Model` - Maximum quality, expensive
- `GeminiFlash25NoThinking` - Alternative fast option

---

### Testing World Director Decisions

```bash
# Watch Director decisions in real-time
tail -f /tmp/webserver.log | grep "\[Director\]"

# Output shows:
# [Director] Decision: continue
# [Director] Decision: give_hint (direct)
# [Director] Decision: spawn_event (crisis)
```

---

## Known Issues & Gotchas

### 1. Race Condition in Sequence ID Generation - FIXED ✅

**File:** `response_queue.py:303-312`

```python
async def get_next_sequence_id(self) -> int:
    """Thread-safe: Uses lock to ensure atomic increment."""
    async with self._sequence_lock:
        self._global_sequence += 1
        return self._global_sequence
```

**Status:** Fixed with asyncio.Lock() protecting sequence ID generation. Safe for concurrent WebSocket connections.

---

### 2. Dynamic Code Evaluation (eval Security Vulnerability) - FIXED ✅

**Files:** `scene_conditions.py` (new), `scenes/base.py:395-412`

**Old Implementation:**
```python
# UNSAFE - Code injection vulnerability
return eval(condition, {"__builtins__": {}}, safe_dict)
```

**New Implementation:**
```python
# SAFE - AST-based parsing, no code execution
if isinstance(condition, str):
    condition_fn = parse_condition_string(condition)  # AST parsing
    return condition_fn(state)
else:
    return condition(state)  # Direct function call
```

**Status:** Fixed with AST-based safe condition parsing. All scene success/failure conditions now use safe evaluation that:
- Blocks code injection attempts (verified with 25 security tests)
- Blocks attribute access and object introspection
- Maintains backwards compatibility with existing condition strings
- Supports new type-safe condition builder functions

**Security verified:** `tests/test_scene_conditions.py` and `tests/test_eval_security_fix.py`

---

### 3. Fire-and-Forget Async Tasks - FIXED ✅

**Files:** `web_server.py:304-368` (new tracking methods), multiple call sites updated

**Old Implementation:**
```python
# UNSAFE - Silent failures, no error logging
asyncio.create_task(self._execute_post_speak_hooks(content))
asyncio.create_task(self._consult_director_async(last_action))
```

**New Implementation:**
```python
# SAFE - Tracked, logged, cleaned up
self._create_tracked_task(
    self._execute_post_speak_hooks(content),
    name="execute_post_speak_hooks"
)
```

**Status:** Fixed with comprehensive task tracking system:
- All background tasks tracked in `_background_tasks` set
- Failed tasks logged with full stack traces
- `_cleanup_background_tasks()` cancels all tasks on session shutdown
- 4 unit tests verify tracking, logging, and cleanup

**Locations fixed:**
- Post-speak hooks execution
- World Director consultations
- Event dispatching
- Opening speech flag resets
- State update loops

**Tracking verified:** `tests/test_task_tracking.py`

---

### 4. XSS Vulnerability in Frontend - FIXED ✅

**File:** `web/js/app.js:1671,1687,1712`

**Old Implementation:**
```javascript
// UNSAFE - Direct innerHTML without escaping
contentDiv.innerHTML = this.parseVoiceAnnotations(content);
```

**New Implementation:**
```javascript
// SAFE - HTML escaped before processing
escapeHTML(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

parseVoiceAnnotations(text) {
    // SECURITY: Escape HTML first to prevent XSS
    const escapedText = this.escapeHTML(text);
    // Then process annotations safely...
}
```

**Status:** Fixed with HTML escaping before annotation processing:
- All HTML special characters escaped
- Script tags blocked: `<script>` → `&lt;script&gt;`
- Event handlers blocked: `onerror=` → `onerror=` (as text)
- JavaScript/Data URLs blocked
- Voice annotations still work correctly
- 10 security tests verify XSS prevention

**Security verified:** `tests/test_xss_prevention.js` and `tests/test_xss_prevention.html`

---

### 5. ChatSession God Object (Being Refactored)

**File:** `web_server.py` (2000+ lines)

**Issue:** `ChatSession` class handles WebSocket, dialogue, game state, TTS, hooks, director, memory - violates Single Responsibility Principle.

**Impact:** Hard to test, maintain, debug.

**Status:** Refactoring in progress. 4 new session modules created in `sessions/` directory with 35+ tests. Not yet integrated into main codebase (backward compatibility). See "ChatSession Refactoring" section above.

---

### 6. Database Error Handling

**File:** `player_memory.py:74-80`

```python
conn = sqlite3.connect(self.db_path)
cursor = conn.cursor()
# Multiple cursor.execute() without try-except
```

**Issue:** Database failures crash application. No rollback.

**Workaround:** Database is simple and rarely fails. Fix required: Use context managers, add error handling.

---

## Environment Configuration

Required `.env` variables:

```env
# ============================================================================
# REQUIRED
# ============================================================================
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================
PORT=8080                              # Server port (default: 8080)

# ============================================================================
# TEXT-TO-SPEECH (Required for voice synthesis)
# ============================================================================
ELEVENLABS_API_KEY=your-key-here
ELEVENLABS_MODEL=eleven_turbo_v2_5     # Default TTS model
ELEVENLABS_PRESERVE_AUDIO_TAGS=true    # Keep [laughs], [sighs] for v3

# Voice ID overrides (optional - use your own cloned voices)
ELEVENLABS_VOICE_ENGINEER=voice-id-here
ELEVENLABS_VOICE_CAPTAIN_HALE=voice-id-here
ELEVENLABS_VOICE_MARA=voice-id-here
ELEVENLABS_VOICE_MERLIN=voice-id-here
ELEVENLABS_VOICE_KOVICH=voice-id-here

# ============================================================================
# SECURITY & ENCRYPTION (Optional but recommended for production)
# ============================================================================
DB_ENCRYPTION_KEY=your-fernet-key-here  # Generate with generate_encryption_key.py

# ============================================================================
# MONITORING & LOGGING (Optional)
# ============================================================================
LOG_LEVEL=INFO                         # INFO or DEBUG
LOG_FORMAT_JSON=true                   # true for JSON, false for readable
ENV=production                         # production or development

# ============================================================================
# ERROR TRACKING (Optional)
# ============================================================================
SENTRY_DSN=https://your-sentry-dsn     # Optional Sentry project DSN
SENTRY_ENVIRONMENT=production          # Environment name
SENTRY_TRACES_SAMPLE_RATE=0.1          # Performance tracing sample rate

# ============================================================================
# DOCKER (Used by docker-compose)
# ============================================================================
PYTHONUNBUFFERED=1                     # Disable Python buffering
PYTHONDONTWRITEBYTECODE=1              # Don't write .pyc files
PYTHONPATH=/app                        # Python import path
```

**See:** `docs/DEPLOYMENT.md` for complete production configuration guide

---

## Performance Optimizations

### Backend
- **Claude Haiku 3.5:** 2-3x faster than Sonnet (1-2s vs 4-6s per response)
- **Reduced token limits:** 800 vs 1500 for dialogue
- **Async architecture:** Non-blocking LLM calls

### Frontend (Three.js)
- **Particle counts:** 50 underwater + 20 bubbles (reduced from higher counts)
- **Lighting:** 4 point lights, shadows disabled
- **Texture updates:** Throttled to 66ms intervals (every 15 frames)
- **Raycasting:** Only on mouse movement
- **Pixel ratio:** Capped at 2x

---

## Documentation References

### Core Architecture (Start Here!)
- `docs/EXPLAINER.md` - Friendly overview of all core concepts
- `docs/PLAYER_MEMORY_SYSTEM.md` - Player tracking, database schema
- `docs/WORLD_DIRECTOR_SYSTEM.md` - Dungeon master AI, decision flow
- `docs/INTERRUPTION_SYSTEM.md` - Penalty mechanics
- `docs/SCENE_ARCHITECTURE.md` - Scene system design

### Operations & Deployment
- `docs/DEPLOYMENT.md` (850+ lines) - Production deployment guide
- `docs/MONITORING.md` (447 lines) - Prometheus/Grafana setup
- `docs/LOGGING.md` (150+ lines) - JSON logging configuration
- `DOCKER.md` (211 lines) - Docker-specific deployment
- `METRICS.md` (173 lines) - Quick metrics reference

### Development & Refactoring
- `docs/REFACTORING_SESSION_MODULES.md` (232 lines) - ChatSession refactoring
- `WORLD_LABS_INTEGRATION.md` (336 lines) - 3D environment integration
- `docs/scenes/README.md` (246 lines) - Scene development guide
- `CONTRIBUTING.md` - Contribution guidelines

### Scene Documentation
- `docs/scenes/*.md` - 8 scene descriptions (Pressure Point, Life Raft, etc.)
- `docs/scenes/*_3d-art-prompt.md` - 6 World Labs generation prompts

### Analysis & Design
- `docs/CHARACTER_IDENTITY_LEAK_ANALYSIS.md` - Prompt engineering analysis
- `docs/` directory - Scene-specific design documents

---

## Debugging Tips

### Backend Logging

```python
# Logging is configured in web_server.py
logger = logging.getLogger(__name__)
logger.info("[Component] Message")
logger.debug("[Component] Detailed info")
logger.warning("[Component] Recoverable error")
```

**Key log patterns to grep:**
- `[Director]` - World Director decisions
- `[QuerySystem]` - Condition evaluation results
- `[ResponseQueue]` - Queue processing, cancellations
- `[PlayerMemory]` - Memory updates, personality changes

### Frontend Console

```javascript
// Enable verbose logging in app.js
console.log('[WebSocket] Message:', data);
console.log('[Scene] State update:', state);
```

**Common debugging:**
- Check browser console for Three.js errors
- Inspect WebSocket messages in Network tab
- Monitor FPS in browser dev tools Performance panel

---

## Important Constants

Located in `constants.py`:

```python
# LLM Configuration
LLM_TEMPERATURE_DIALOGUE = 0.8  # Creative responses
LLM_TEMPERATURE_QUERY = 0.2     # Deterministic evaluation
LLM_MAX_TOKENS_DIALOGUE = 800   # Reduced for speed

# Penalties
INTERRUPTION_OXYGEN_PENALTY = 15
INTERRUPTION_TRUST_PENALTY = 10

# World Director Cooldowns
DIRECTOR_COOLDOWN_SPAWN_EVENT = 10  # seconds
DIRECTOR_COOLDOWN_ADJUST_NPC = 8
DIRECTOR_COOLDOWN_GIVE_HINT = 8

# Difficulty Adjustment
DIFFICULTY_EASY_SUCCESS_RATE = 0.3
DIFFICULTY_HARD_SUCCESS_RATE = 0.8
DIFFICULTY_SCENE_ATTEMPTS_THRESHOLD = 3
```

**Note:** Scene-specific constants can override globals via `SceneConstants` dataclass.
