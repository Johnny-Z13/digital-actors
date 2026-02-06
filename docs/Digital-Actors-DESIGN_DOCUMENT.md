# Digital Actors Platform - Design Document

---

## Project Overview

### Name
**Working Title:** Digital Actors Platform
**Code Name:** Iron Lung (flagship demo scenario)

### Elevator Pitch
An AI-powered interactive narrative platform that creates emotionally engaging experiences through adaptive dialogue, persistent player memory, and mechanical trust-building—where emotional connection directly affects success probability.

### Genre / Category
- **Primary:** Interactive Narrative / AI Simulation
- **Secondary:** Emergent Storytelling / Adaptive Difficulty System
- **Platform(s):** Web (Desktop browsers)

### Target Audience
- **Primary:** Narrative game developers and interactive fiction creators looking for AI-powered dialogue systems; Ages 25-45, technically savvy, interested in emergent narratives
- **Secondary:** AI researchers studying human-AI interaction patterns, players interested in experimental narrative experiences
- **Comparable Products:** AI Dungeon (text adventures), Character.AI (chat-focused), Facade (interactive drama), The Stanley Parable (narrative choice), Firewatch (emotional NPC bonds)

### References & Inspiration
| Reference | What to Take From It |
|-----------|---------------------|
| AI Dungeon | LLM-powered open-ended narrative, player agency through natural language |
| Character.AI | Persistent character memory, personality consistency across sessions |
| Firewatch | Emotional bond with unseen NPC through voice communication, trust-building |
| Facade | Real-time conversational AI with consequence, failure states matter |
| Iron Lung (game) | Claustrophobic submarine atmosphere, limited visibility, time pressure |
| The Stanley Parable | Meta-narrative awareness, player choice subversion |

---

## Core Concept

### Theme / Setting
Multiple settings supported (fantasy, modern, sci-fi). Flagship demo: **Submarine emergency scenario** - trapped in a research submarine 2,400 feet underwater with reactor failure, lethal radiation spreading. Clean industrial aesthetics meet crisis atmosphere. Think *The Hunt for Red October* meets *Moon* (2009).

Secondary settings: Fantasy wizard tower, detective noir office, AI facility.

### Core Fantasy / Value Proposition
**Feel genuine emotional connection with AI characters where trust and cooperation are mechanical requirements, not just narrative flavor.** Experience emergent storytelling where an AI "dungeon master" adapts the narrative to your playstyle, and characters remember your personality across sessions.

### Unique Selling Points
1. **Persistent Player Memory System** - Tracks 4-dimensional personality (impulsiveness, cooperation, patience, problem-solving) across all sessions. Characters see your full history and adapt behavior accordingly.
2. **AI Dungeon Master (World Director)** - Dynamically adjusts difficulty, spawns crisis/help events, provides hints based on real-time performance analysis.
3. **Trust-as-Mechanic** - Emotional bond isn't just flavor text—it's a tracked state variable that determines success probability and ending outcomes.
4. **Response Queue Architecture** - Priority-based dialogue management prevents flooding while maintaining conversational flow. Critical responses never get cancelled; background chatter does.
5. **Modular LLM Abstraction** - Swap between Claude, OpenAI, or Gemini models without changing game logic.

---

## Gameplay / Functionality

### Core Loop
```
Player action (chat message or button click) →
LLM generates contextual response (2-3 seconds) →
Response queued by priority →
World Director evaluates situation (async) →
Player Memory updates personality profile →
State variables change (oxygen, trust, radiation) →
Success/failure conditions checked →
(repeat)
```

**Concrete Example (Submarine Scenario):**
```
Player: "What should I do?" →
Claude Haiku generates: "[breathing heavily] The BALLAST button. Blue one. Press it. NOW." →
Queued as NORMAL priority (2s wait) →
Director evaluates: "Player is following instructions, spawn help event" →
Memory: cooperation +2, patience +1 →
Player clicks BALLAST → Oxygen -5, hull_pressure decreases →
NPC: "Yes! That's it! Pressure's dropping!" →
Check: oxygen > 0? radiation < 95? → Continue
```

### Session Structure
- **Typical Session Length:** 5-10 minutes per scenario (submarine: 8 minutes max)
- **Save/Resume:** Player memory persists in SQLite database across sessions. Scenario progress does not persist (each playthrough is fresh, but your personality carries forward).
- **Natural Stopping Points:** After scenario completion (success/failure/game over), with outcome screen and retry option.

### Primary Mechanics

#### Mechanic 1: Real-time Dialogue (Conversational AI)
- **Description:** Player types natural language messages to AI characters who respond contextually based on scene state, dialogue history, and player personality profile.
- **Controls/Input:** Keyboard text input, enter to send.
- **Feedback:** Character response appears character-by-character at 30ms/char with optional ElevenLabs TTS audio. Responses feel natural with [emotional cues] and backchanneling.
- **Depth:** Characters remember past interactions; personality profile influences NPC tone (frustrated after 3+ interruptions, encouraging after player improvement). 800-token responses with temperature 0.8 for natural variance.

#### Mechanic 2: Environmental Control (Interactive Buttons)
- **Description:** Click 3D scene controls (buttons, levers, switches) to affect game state. Each has mechanical effects (oxygen cost, trust change, hull pressure adjustment).
- **Controls/Input:** Mouse click on 3D objects, raycast detection.
- **Feedback:** 800Hz sine wave beep (100ms), visual button flash animation, state gauge updates, NPC acknowledges action via system event.
- **Depth:** Timing matters—interrupting NPC speech costs -15 oxygen, -10 trust. Rapid clicking (3+ actions in 3s) triggers penalties. Some buttons are NPC-aware (character feels physical changes like pressure dropping).

#### Mechanic 3: Trust Management (Implicit Relationship Tracking)
- **Description:** Invisible relationship stat tracked through behavior patterns: following instructions (+cooperation), waiting patiently (+patience), interrupting (-cooperation, +impulsiveness), correct decisions (+problem_solving).
- **Controls/Input:** Implicit through dialogue choices, action timing, and decision-making.
- **Feedback:** NPC emotional state changes (frustrated, encouraging, desperate), dialogue tone shifts, success probability affected. Trust minimum is -100, no maximum.
- **Depth:** Trust affects ending outcomes (submarine scenario has 3 endings based on emotional_bond threshold: ≥70 = full success, 40-69 = partial, <40 = functional survival without closure). Negative trust can lock out success paths.

### Secondary Mechanics
- **State Variable Tracking**: Oxygen, radiation, time_remaining, emotional_bond, systems_repaired update in real-time (every 1 second via WebSocket).
- **Phase Progression**: Submarine scenario has 4 emotional phases (Impact & Connection, Working Relationship, The Revelation, The Choice) that transition based on time_remaining.
- **Interruption Detection**: System detects when player acts during NPC speech, applying penalties and generating frustrated NPC responses.
- **Director Event Spawning**: Crisis events (-20 oxygen, -10 trust), Help events (+15 oxygen, +5 trust), hints, NPC behavior adjustments happen dynamically based on performance.

---

## Systems Design

### Progression System

| Type | Description | Persistence |
|------|-------------|-------------|
| Personality Profile | 4 dimensions tracked on 0-100 scale: impulsiveness, cooperation, patience, problem_solving. Updated ±2-5 per significant event. | Permanent (SQLite) |
| Relationship Levels | Per-character trust and familiarity counts. Trust can go negative (-100 min). | Permanent (SQLite) |
| Performance History | Total scenes played, success rate, scene-specific attempt counts, learning curve data. | Permanent (SQLite) |
| Scenario Unlocks | *(Not yet implemented - architecture ready)* | Would be permanent |
| Skill Mastery | *(Not yet implemented - could track button timing precision, optimal decision rate)* | Would be permanent |

### Economy / Resources
- **Oxygen**: Primary survival resource in submarine scenario. Starts at 480 (8 minutes). Decreases at -1/second naturally. Lost via interruption penalties (-15), rapid actions (-10), crisis events (-20). Gained via help events (+15).
- **Trust**: Relationship currency. Gained through cooperation (+2-5), following instructions (+2), patience (+1-3). Lost through interruptions (-10), rapid actions (-5), incorrect decisions (-5-10), crisis events (-10).
- **Emotional Bond**: Submarine-specific metric (0-100 scale). Built through empathetic dialogue, personal questions, vulnerability. Determines ending quality (≥70 = full trust ending).
- **Radiation**: Submarine hazard metric (0-100%). Increases at 0.4%/sec. Reaches lethal threshold at 95%. No player control (simulates unavoidable environmental danger).
- **Time Remaining**: Countdown clock creates urgency. Submarine scenario: 480 seconds (8 minutes) to 0.

### Difficulty / Challenge Curve
- **Starting State:** Tutorial-style first playthrough with patient NPC, minimal penalties, 3-second grace period before rapid action detection.
- **Scaling Method:** **Performance-based auto-adaptive**. World Director analyzes player memory:
  - Success rate <30% → Easy mode (×0.7 penalty multiplier, +30 oxygen bonus)
  - Success rate 30-80% → Normal mode (standard)
  - Success rate >80% → Hard mode (×1.3 penalty multiplier, -30 oxygen, more crisis events)
- **Failure State:** Scenario-specific death/failure (oxygen ≤0, radiation ≥95%, trust <-50, time expired). Game over screen shows outcome message. Retry available immediately; player memory records failure for difficulty adjustment.
- **Difficulty Modes:** No manual selection—adaptive only. System decides based on recent performance (last 5 scenarios).

---

## Entities / Content

### Player Character / User Profile
- **Capabilities:** Natural language dialogue, button/control interaction, decision-making within scene constraints, emotional expression through text.
- **Limitations:** No traditional locomotion (position fixed or scene-constrained), no inventory system, no direct combat, dialogue-driven interaction only.
- **Customization:** Implicit customization through playstyle. Personality emerges organically from actions (aggressive vs patient, cooperative vs defiant, thoughtful vs impulsive). No avatar appearance customization (visual representation is generic colored sphere in character scenes).

### Characters (5 Implemented)

| Name | ID | Role | Personality | Skills | Color | Backstory Summary |
|------|-----|------|-------------|--------|-------|-------------------|
| **Lt. Cmdr. James Smith** | engineer | Submarine Commander (Flagship Demo) | Competent but scared, emotionally vulnerable father facing impossible choice. Reveals son Adrian in med bay during Phase 3. | submarine_engineering, crisis_management, technical_communication, reactor_systems, leadership_under_pressure | Blue (0x1976d2) | 28-year-old naval engineer, 15 years service. Professional exterior, breaks down gradually. Uses backchanneling ("That's it... keep going...") and parenthetical emotional cues. |
| **Eliza** | eliza | AI Caretaker | Professional yet warm facility manager. Helpful, knowledgeable, slightly formal but caring. | facility_management, systems_knowledge, empathy | Cyan (0x4fc3f7) | AI managing research facility. References system protocols in dialogue. Subtle sense of humor. |
| **Merlin** | wizard | Wise Wizard | Ancient sorcerer, mystical speech patterns, patient teacher. Uses metaphors and riddles. | magic, ancient_wisdom | Purple (0x9c27b0) | Centuries of knowledge, naturally fails submarine scenario due to lack of technical expertise. Philosophical approach to problems. |
| **Detective Stone** | detective | Hard-boiled Detective | Noir detective, cynical, world-weary. Direct, observant, personal code of honor. Dry sardonic humor. | investigation, street_smarts | Brown (0x795548) | Classic noir detective. Uses metaphors and slang. Lacks technical engineering knowledge. |
| **Custom** | custom | User-Defined | Template for custom characters. | (user-defined) | (user-defined) | Blank slate for experimentation. |

### Scenarios (4 Types, 1 Fully Implemented)

| Name | ID | Status | Description | Duration | State Variables | Controls | Win/Lose Conditions |
|------|-----|--------|-------------|----------|----------------|----------|---------------------|
| **Submarine Emergency** | submarine | **Fully Implemented** | Research submarine Prospero reactor failure at 2,400ft depth. Player in aft compartment, NPC in forward control. 4 emotional phases. | 8 minutes (480s) | oxygen, radiation, time_remaining, hull_pressure, emotional_bond, systems_repaired, phase, moral_support_given | O2 VALVE (red), VENT (orange), BALLAST (blue), POWER (green), CRANK (gray), FLOOD MED BAY (critical red) | Success: radiation <95%, emotional_bond ≥70, systems_repaired ≥3. Failure: radiation ≥95%, time ≤0, trust <-50 |
| **Introduction** | introduction | Architecture Only | Opening narrative scene. | Variable | (minimal) | (none) | (narrative progression) |
| **Conversation** | conversation | Architecture Only | Free-form dialogue with any character. | Unlimited | (none) | (none) | (none—open-ended) |
| **Quest** | quest | Architecture Only | Story mission framework. | Variable | (TBD) | (TBD) | (TBD) |

**Submarine Scenario Details:**
- **4 Emotional Phases:**
  1. **Phase 1 (0:00-1:15)**: Impact & Connection—establish trust, ask player's real name, create shared reality.
  2. **Phase 2 (1:15-2:30)**: Working Relationship—personal questions, reveal character details, build rapport.
  3. **Phase 3 (2:30-3:30)**: The Revelation—James reveals his son Adrian (8 years old) is in med bay with broken arm.
  4. **Phase 4 (3:30-5:00)**: The Choice—moral decision to flood med bay (emergency ascent) or let everyone die.
- **3 Endings:**
  - **Full Success**: radiation <95%, emotional_bond ≥70, systems_repaired ≥3 → *"[breathing steadily] We made it. We... we actually made it. Thank you. For being there."*
  - **Partial Success**: radiation <95%, emotional_bond 40-69, systems_repaired ≥2 → *"Systems online. Ascent initiated. ...Thank you for following instructions."* (functional survival, no emotional closure)
  - **Failure**: radiation ≥95% OR time_remaining ≤0 OR trust <-50 → Death. Various death messages based on cause.

### Items / Pickups / Collectibles
*(Not applicable to current design—no traditional pickup system. Resource economy is state-variable based.)*

### Levels / Environments / Screens
- **Character Scene (Generic):** Abstract 3D space with colored sphere representing character. Minimal environment. Focus on dialogue.
- **Submarine Interior (Detailed):** Control room with porthole window (underwater view), control panel with 4-5 interactive buttons, real-time gauges (oxygen, radiation, time), particle effects (50 underwater particles, 20 bubbles). Atmospheric lighting. Mouse-look camera (±50° horizontal/vertical). Target: 60 FPS.

---

## User Interface

### HUD / Always-Visible Elements
- **Chat Window**: Draggable, resizable dialogue window. Bottom 30% of screen by default. Auto-scroll during typing animation. Contains full dialogue history.
- **State Gauges** (submarine scene only):
  - **Oxygen Gauge**: Top-left, vertical bar, color-coded (green >300, yellow 150-300, red <150), displays remaining seconds.
  - **Radiation Meter**: Top-right, vertical bar, color-coded (green <50%, yellow 50-75%, red >75%), displays percentage.
  - **Time Remaining**: Top-center, countdown clock in MM:SS format.
  - **Trust/Bond Indicator**: *(Currently not visually displayed—internal state only. Gap identified.)*
- **Scene Canvas**: 3D WebGL viewport (Three.js) occupying top 70% of screen. Interactive controls rendered within.

### Menus / Screens
- **Main Menu**: Character dropdown (5 options), Scene dropdown (4 options), Start button, minimal branding.
- **Settings**: *(Minimal implementation—gap identified.)* TTS toggle (if ElevenLabs configured), audio volume control.
- **Game Over Screen**: Semi-transparent overlay with "THE END" text, outcome message (success/failure/death), retry button, emotion-appropriate styling.
- **Pause**: *(Not implemented—no pause mechanism during timed scenarios. Gap identified.)*

### Feedback Systems
- **Visual Feedback:**
  - Typing animation: 30ms per character for NPC dialogue
  - Button flash: 200ms color flash on click
  - State gauge updates: Smooth transitions, color changes at thresholds
  - Particle effects: Underwater ambiance (50 particles), bubbles (20 particles)
  - Screen shake: *(Not implemented—opportunity for crisis events)*
- **Audio Feedback:**
  - Button click: 800Hz sine wave tone, 100ms duration (Web Audio API)
  - TTS voice: ElevenLabs synthesis (optional, character-specific voice IDs)
  - Ambient soundscape: *(Submarine hum/alarm mentioned in docs but implementation unclear)*
- **Haptic Feedback:** Not implemented (web platform, no gamepad support).

---

## Audio & Visual Style

### Art Direction
- **Style:** Low-poly 3D geometric primitives (Three.js). Abstract character representation (colored spheres). Functional submarine interior (industrial, no photorealism).
- **Color Palette:**
  - Character-coded: Cyan (Eliza), Blue (Engineer), Purple (Wizard), Brown (Detective)
  - UI: Dark theme with high-contrast text (white on black)
  - Submarine: Muted industrial grays, emergency red lighting for alarms, blue underwater tint through porthole
- **Mood:** Atmospheric and immersive, focus on dialogue over graphics. Claustrophobic in submarine scene. Minimalist in character scenes.

### Audio Direction
- **Music Genre:** Ambient environmental sounds (no traditional music track). Submarine scenario: engine hum, alarm sounds.
- **Sound Design:** Minimal and functional. 800Hz sine beep for buttons (intentionally simple). TTS voices carry emotional weight.
- **Voice:** ElevenLabs TTS (optional). Character-specific voice IDs:
  - Eliza: Rachel voice (21m00Tcm4TlvDq8ikWAM)
  - Engineer: Adam voice (pNInz6obpgDQGcFmaJgB) - stability 0.4 for stressed emotion
  - Wizard: Clyde voice (2EiwWnXFnvU5JabPnv8n) - stability 0.7 for measured speech
  - Detective: Arnold voice (VR6AewLTigWG4xSOukaG)

---

## Technical Requirements

### Target Specs
- **Minimum:** Modern desktop browser (Chrome 90+, Firefox 88+, Safari 14+), stable internet connection (LLM API), 4GB RAM.
- **Recommended:** Desktop, 60 FPS rendering, headphones for TTS audio, 8GB RAM, broadband internet (<200ms latency to API).
- **Frame Rate Target:** 60 FPS maintained (achieved via optimizations: 70 total particles, throttled canvas updates every 15 frames, max 2x pixel ratio).

### Engine / Framework
- **Backend:**
  - **Framework:** Python 3.12+ with aiohttp (async web server)
  - **LLM Integration:** llm_prompt_core abstraction layer
    - Primary: Anthropic Claude Haiku 3.5 (model ID: claude-haiku-3-5-20250305)
    - Alternatives: Claude Sonnet 4.5, Claude Opus 4, GPT-4o, GPT-4 Turbo, Gemini Flash 2.5
  - **Database:** SQLite (player_memory.db)
  - **TTS:** ElevenLabs API (optional)
  - **Dependency Manager:** uv + pyproject.toml
  - **Linting:** Ruff
- **Frontend:**
  - **Framework:** Vanilla JavaScript (no framework—intentional simplicity)
  - **3D Rendering:** Three.js (WebGL)
  - **Communication:** WebSocket (bidirectional real-time messaging)
  - **Audio:** Web Audio API
- **Key Dependencies:**
  - Backend: websockets, anthropic, openai, google-genai, langchain-core, pydantic, aiohttp, torch, numpy, pydub
  - Frontend: three.js (CDN-loaded)

### Data & Persistence
- **Save System:** Server-side SQLite database (data/player_memory.db).
- **Data to Persist:**
  - Player profiles: player_id, first_seen, last_seen, total_interactions
  - Personality profiles: impulsiveness, cooperation, problem_solving, patience (0-100 scale)
  - Relationships: character_id, trust_level, familiarity_count, last_interaction
  - Scene history: scene_id, attempts, successes, best_time, last_attempt
- **Online Requirements:** Always-online (requires LLM API access for dialogue generation). No offline mode currently.

---

## Scope & Constraints

### MVP Features (Current Prototype - ✅ COMPLETED)
1. ✅ Real-time dialogue with Claude API integration (Haiku/Sonnet/Opus)
2. ✅ Player memory system with personality profiling (4 dimensions, SQLite persistence)
3. ✅ World Director adaptive difficulty (evaluates situation, spawns events, adjusts NPC)
4. ✅ Response queue to prevent dialogue flooding (priority-based, cancellation logic)
5. ✅ 3D scene rendering (character + submarine environments)
6. ✅ Interactive controls with state management (6 buttons in submarine, NPC-aware actions)
7. ✅ Submarine emergency flagship scenario (8-minute, 4-phase, 3 endings)
8. ✅ Character skill system (5 characters, skill-based behavior differentiation)
9. ✅ ElevenLabs TTS integration (optional, gracefully disabled without API key)
10. ✅ Game over conditions and retry flow (success/failure screens, memory updates)
11. ✅ Interruption detection and penalties (-15 oxygen, -10 trust)
12. ✅ Rapid action detection (3+ actions in 3s = penalty)
13. ✅ Phase progression system (time-based narrative transitions)
14. ✅ Multi-LLM provider support (Claude, OpenAI, Gemini via abstraction layer)
15. ✅ Modular character/scene architecture (easy extension)

### MVP Gaps (Must Have for v1.0 Launch)
1. ❌ **Comprehensive testing suite** - Currently manual testing only. Need unit tests for core systems (player memory, director logic, response queue), integration tests for WebSocket flow, automated scenario testing.
2. ❌ **More scenario variety** - Only 1 complete scenario (submarine). Need 3-5 polished scenarios minimum for launch to demonstrate platform versatility.
3. ❌ **Onboarding/tutorial** - No guided first experience. New players have no context for how to interact or what success looks like.
4. ❌ **Analytics and metrics** - No visibility into player engagement (session length, drop-off points, dialogue patterns, success rates). Critical for product iteration.
5. ❌ **Error handling and graceful degradation** - Minimal error states. LLM failures, network issues, and WebSocket disconnects not gracefully handled.
6. ❌ **Performance monitoring** - No instrumentation for response latency, frame rate drops, or memory leaks. Production readiness requires observability.
7. ❌ **Cross-browser compatibility testing** - Untested on Safari, Edge, mobile browsers. WebGL and WebSocket compatibility needs validation.
8. ❌ **Trust/bond visual indicator** - Emotional bond is internal state only. Players have no feedback on relationship status during gameplay.
9. ❌ **Pause functionality** - No pause mechanism in timed scenarios. Player must commit to full 8-minute session or lose progress.
10. ❌ **Player profile dashboard** - No way to view personality stats, relationship history, or performance trends. Memory system is invisible to players.
11. ❌ **Content moderation** - No filtering of inappropriate player input. LLM could be prompted to break character or generate harmful content.
12. ❌ **Distribution strategy** - Unclear launch plan (standalone app? hosted web app? embedded in game engines?). No deployment infrastructure.

### Phase 2 Features (Should Have)
1. ❌ **Voice input (speech-to-text)** - Enable hands-free play using Web Speech API or Whisper API. Aligns with "voice-first" design philosophy from Iron Lung doc.
2. ❌ **Multi-character scenarios** - Multiple NPCs present simultaneously. Requires dialogue routing, turn-taking logic, inter-NPC relationships.
3. ❌ **Scenario editor/creation tools** - Visual editor for non-programmers to define state variables, controls, success criteria. Critical for content pipeline velocity.
4. ❌ **Player profile dashboard** - View personality dimensions, relationship graph, performance history, achievement milestones. Increases engagement and self-awareness.
5. ❌ **Achievement/milestone system** - Track meta-progression (e.g., "Survived 10 scenarios," "Maxed cooperation stat"). Provides long-term goals beyond single scenarios.
6. ❌ **Enhanced 3D environments** - More detailed scene rendering (textures, lighting, props). Current low-poly style is functional but limits immersion.
7. ❌ **Mobile support** - Responsive design, touch controls, optimized rendering. Expands addressable market significantly.
8. ❌ **Save/load mid-session** - Allow players to pause and resume scenarios. Current model requires full commitment to 5-10 minute sessions.
9. ❌ **Procedural scenario generation** - LLM generates new scenarios from templates. Infinite content potential but requires careful quality control.
10. ❌ **Community-created content platform** - Player-submitted characters/scenarios. Moderation challenges but exponential content growth.
11. ❌ **Enhanced Director behaviors** - More intervention types beyond current 4 (continue, spawn_event, adjust_npc, give_hint). Example: spawn secondary objectives, introduce time extensions, trigger flashbacks.
12. ❌ **Dynamic difficulty prediction** - Machine learning model predicts player struggle before failure, enabling preemptive Director intervention.

### Nice-to-Have Features (Could Have)
1. ❌ **Multiplayer co-op scenarios** - Two players work together in same scenario. Requires synchronization, shared state, inter-player dialogue routing.
2. ❌ **VR support** - WebXR integration for immersive submarine experience. High development cost, niche audience.
3. ❌ **Advanced emotion detection** - Analyze player text for frustration, confusion, engagement using sentiment analysis. Inform Director decisions beyond behavior patterns.
4. ❌ **Dynamic music generation** - AI-composed music that adapts to scene tension. Currently only ambient sounds.
5. ❌ **Character appearance customization** - Visual customization beyond color (shape, accessories, animations). Low priority given dialogue focus.
6. ❌ **Replay system with branching visualization** - View dialogue tree of past playthroughs. Educational for understanding consequence of choices.
7. ❌ **Local LLM option** - Offline play using local models (e.g., Llama, Mistral). Requires significant GPU resources, reduced quality.
8. ❌ **Translation/localization support** - Multi-language support. LLM can generate in multiple languages but requires careful testing per language.
9. ❌ **Twitch integration** - Chat-driven scenario where Twitch viewers vote on actions. Interesting for streaming but complex implementation.
10. ❌ **Scenario branching and checkpointing** - Save points within long scenarios. Useful for 30+ minute experiences but adds complexity.

### Non-Goals (Won't Have)
- ❌ **Traditional combat mechanics** - This is not a combat game. Any "conflict" is conversational/emotional, not mechanical damage calculation.
- ❌ **Photorealistic graphics** - Focus is dialogue and AI interaction, not visual fidelity. Low-poly aesthetic is intentional to keep scope manageable.
- ❌ **Massive open world** - Scene-based structure is core to design. Each scenario is self-contained 5-10 minute experience.
- ❌ **Leaderboards/competitive multiplayer** - Cooperative and narrative focus. Competition undermines emotional engagement and vulnerability.
- ❌ **Blockchain/NFT integration** - No Web3 elements. Focus on core experience quality.
- ❌ **Mobile-first design** - Desktop is primary platform. Mobile support is Phase 2, not core requirement.
- ❌ **Monetization via loot boxes/gacha** - Player-friendly monetization only (e.g., pay-per-scenario, subscription, one-time purchase).
- ❌ **AAA production values** - Indie scope. Prototype aesthetic is acceptable if gameplay/AI systems are compelling.

### Known Risks & Open Questions
- ❓ **API costs scaling with user base** - Claude Haiku costs ~$0.001 per interaction (800 tokens out). At 100k players with 10 scenarios each = $1,000 LLM cost. Manageable but requires monetization strategy.
- ❓ **LLM response consistency and quality control** - Responses can occasionally break character, use wrong format (asterisks instead of brackets), or hallucinate scene state. Mitigation: detailed instruction_prefix, temperature tuning, query validation. Open question: How to detect/auto-retry bad responses?
- ❓ **Player retention beyond initial novelty** - AI chat is novel but risks feeling repetitive. Does personality memory provide enough differentiation across sessions? Needs analytics to answer.
- ❓ **Content creation pipeline efficiency** - Submarine scenario took significant effort (1,400+ lines of Python). Can we achieve 1 scenario/week with current process? Scenario editor would help but doesn't exist yet.
- ❓ **Monetization strategy unclear** - Pay-per-scenario? Subscription? One-time purchase with DLC scenarios? Free-to-play with premium characters? Market research needed.
- ❓ **Distribution method** - Standalone Electron app? Hosted web app (SaaS)? Game engine plugin (Unity/Unreal)? Each has trade-offs (control vs reach vs integration complexity).
- ❓ **Handling inappropriate player input** - Players can try to manipulate LLM into generating harmful/sexual/violent content. Current mitigation: Claude's built-in safety. Additional filtering needed?
- ❓ **Intellectual property for community content** - If players create characters/scenarios, who owns them? Licensing model TBD.
- ❓ **Balancing LLM speed vs quality** - Haiku is 2-3x faster than Sonnet but noticeably lower quality. Is 2-3s latency acceptable for Sonnet's improved responses? User preference or scenario-dependent?
- ❓ **World Director intervention frequency** - Currently uses cooldowns (10s for events, 8s for hints). Is this too frequent (feels railroaded) or too rare (feels abandoned)? Needs playtesting calibration.
- ❓ **Personality convergence time** - How many sessions before personality profile stabilizes? Currently uses ±2-5 adjustments per event. Too slow = feels random, too fast = feels rigid. Needs data analysis.
- ❓ **Multi-scenario narrative arcs** - Should scenarios link together into campaigns? Current design is episodic. Linking requires story planning and progress tracking.

---

## Development Notes

### Existing Assets / Starting Point
- ✅ **Complete Python backend** - 1,579-line web_server.py with modular character/scene system, WebSocket handling, state management.
- ✅ **Response queue infrastructure** - 370-line response_queue.py with priority management, cancellation logic, async processing.
- ✅ **Player memory system** - 539-line player_memory.py with SQLite persistence, personality profiling, relationship tracking.
- ✅ **World Director AI orchestration** - 449-line world_director.py with situation evaluation, event spawning, difficulty adaptation.
- ✅ **LLM abstraction layer** - llm_prompt_core/ supporting Claude, OpenAI, Gemini with template system and prompt builder.
- ✅ **Three.js 3D rendering engine** - app.js (1,342 lines), submarine_scene.js (1,239 lines) with WebGL rendering, raycasting, particle effects.
- ✅ **Submarine emergency scenario** - Complete 8-minute scenario with 4 phases, 6 controls, 8 state variables, 3 endings. Polished flagship demo.
- ✅ **5 character definitions** - Eliza, Merlin, Detective Stone, James Smith (Engineer), Custom template. Each with backstory, skills, voice IDs.
- ✅ **Documentation suite** - 15+ markdown files including README.md (15KB), CREATE_CHARACTER.md (15KB), system docs (PLAYER_MEMORY, WORLD_DIRECTOR, INTERRUPTION, SCENE_ARCHITECTURE), llm_prompt_core/README.md (20KB).
- ✅ **Configuration system** - constants.py centralizing all magic numbers (temperatures, penalties, cooldowns, thresholds).

### Key Technical Challenges

#### Challenge 1: LLM Unpredictability
**Why it's tricky:** LLM responses can occasionally break character, use wrong formatting (asterisks instead of [brackets]), or hallucinate scene state. No deterministic guarantee of output quality.

**Current Mitigation:**
- Detailed instruction_prefix in character definitions
- Temperature tuning (0.8 for dialogue, 0.2 for queries, 0.7 for Director)
- Query validation with low temperature for binary checks
- Backchanneling and emotional cues in character backstories

**Open Questions:**
- How to auto-detect bad responses and retry?
- Should we implement response validation layer?
- Is Claude Haiku sufficient or do we need Sonnet for quality?

#### Challenge 2: Real-time Performance (<3s Total Latency)
**Why it's tricky:** Conversational flow requires <3s round-trip (player input → response displayed). LLM API call is 1-2s (Haiku), plus Director evaluation (~1s), plus network latency, plus response queue processing.

**Current Solution:**
- Claude Haiku model (2-3x faster than Sonnet)
- Async architecture (Director evaluation runs in background, doesn't block response)
- Response queue processes immediately when gap conditions met
- Frontend typing animation masks perceived latency

**Performance Benchmarks:**
- Haiku response: 1-2 seconds
- World Director evaluation: ~1 second
- Total latency: 2-3 seconds
- Player memory lookup: <10ms
- Scene end save: <50ms

#### Challenge 3: Dialogue Flooding
**Why it's tricky:** Players can spam button clicks or send multiple messages before NPC responds, causing 5+ queued responses that break conversational flow.

**Current Solution:**
- Response queue with priority system (CRITICAL > URGENT > NORMAL > BACKGROUND)
- BACKGROUND priority responses (Director hints) automatically cancelled when superseded
- Minimum 2-second gap between responses
- Consolidation of redundant responses

**Edge Cases:**
- Player interrupts during critical death speech → CRITICAL priority never cancels
- Rapid clicking same button 5 times → Only 1 response generated (or should Director react to panic?)

#### Challenge 4: Player Memory Precision
**Why it's tricky:** Personality updates must feel fair and accurate. Too aggressive (±10 per event) = erratic, unrealistic swings. Too conservative (±1 per event) = no perceptible change across sessions.

**Current Implementation:**
- Small adjustments (±2-5 per significant event)
- Thresholds: Low (<30), Mid (30-70), High (>70)
- Requires extensive playtesting to tune sensitivity

**Open Questions:**
- How many sessions before personality stabilizes?
- Should personality decay over time (regression to mean)?
- How to prevent min/maxing (players gaming the system)?

#### Challenge 5: Scenario Design Complexity
**Why it's tricky:** Each scenario requires custom state variables, controls, success/failure criteria, phase logic, NPC dialogue. Submarine scenario is 1,400+ lines. Creating 10 scenarios = 10,000+ lines of hand-crafted content.

**Current Trade-off:**
- High quality (submarine scenario is polished, emotionally compelling)
- Low production velocity (weeks per scenario)
- No tooling (all code-based, requires Python knowledge)

**Path Forward:**
- Phase 2: Scenario editor for non-programmers
- Template library for common patterns (countdown scenarios, multi-NPC dialogue, branching narratives)
- Procedural generation (LLM creates scenarios from seed prompts—risky quality)

### Testing Strategy

#### Playtesting Approach
**Current State:** Manual gameplay sessions testing behavior edge cases.

**Test Scenarios:**
1. **Struggling Player Detection** - Button mash 5+ times, fail scene. Expected: Director gives hints, spawns help events, reduces penalties.
2. **Skilled Player Challenge** - Complete submarine perfectly. Retry with perfect play. Expected: Director spawns crisis events, increases difficulty.
3. **Learning Behavior Reward** - First attempt: interrupt and button mash. Second attempt: wait patiently. Expected: NPC becomes encouraging ("You're listening! Much better!").
4. **Response Cancellation** - Rapidly click same button 5+ times. Expected: Only 1 character response, not 5 queued.
5. **Trust Threshold Testing** - Submarine ending variations. Confirm emotional_bond ≥70 = full trust ending, 40-69 = partial, <40 = functional.
6. **Phase Transition Timing** - Submarine phases transition at correct time_remaining thresholds.
7. **Failure State Coverage** - Test all failure conditions (oxygen ≤0, radiation ≥95%, trust <-50, time expired).

#### QA Focus Areas
- **Interruption detection accuracy** - Must trigger on actions during NPC speech, not during player's own typing.
- **Player memory personality convergence** - Track personality dimensions over 5+ sessions. Verify consistent behavioral pattern recognition.
- **World Director intervention appropriateness** - Crisis events should feel fair, not punishing. Help events should feel earned, not patronizing.
- **Response queue cancellation logic** - BACKGROUND responses cancel correctly. CRITICAL never cancels. NORMAL supersedes BACKGROUND.
- **State variable update rates and thresholds** - Oxygen -1/sec feels urgent but not unfair. Radiation 0.4%/sec reaches lethal at ~4 minutes.
- **Success/failure condition balance** - Submarine scenario should be completable by patient, cooperative player. Skilled players should win 70%+ of time.
- **Cross-browser WebGL compatibility** - Three.js rendering on Chrome, Firefox, Safari, Edge.
- **WebSocket reconnection handling** - Network blip should not crash session.
- **LLM failure recovery** - API timeout or rate limit should show error message, not hang indefinitely.

#### Automated Testing Gap
**Status:** Not yet implemented (critical gap for v1.0).

**Needed Coverage:**
- Unit tests: Player memory update logic, Director decision logic, response queue priority handling
- Integration tests: WebSocket message flow, LLM integration, state machine transitions
- Performance tests: Response latency under load, memory leak detection, frame rate stability
- Regression tests: Ensure personality convergence behavior doesn't change across updates

---

## Appendix

### Glossary
| Term | Definition |
|------|------------|
| **World Director** | AI dungeon master that evaluates scene state and player behavior to dynamically adjust difficulty, spawn events, and provide hints. Runs on Claude Haiku with 0.7 temperature. |
| **Player Memory** | SQLite database tracking player personality (4 dimensions: impulsiveness, cooperation, patience, problem-solving), relationships with characters, and performance history. Persists across sessions. |
| **Response Queue** | Priority-based dialogue management system preventing flooding. Supports 4 priority levels (CRITICAL, URGENT, NORMAL, BACKGROUND) with automatic cancellation of superseded low-priority responses. |
| **Interruption** | Player action (button click or message) during NPC speech. Penalized with -15 oxygen, -10 trust. Tracked in personality profile (+3 impulsiveness, -2 cooperation). |
| **Rapid Action** | 3+ player actions within 3-second window. Penalized with -10 oxygen, -5 trust. Indicates button mashing or panic. |
| **Emotional Bond** | Submarine scenario metric (0-100 scale) tracking depth of player-NPC relationship. Determines ending quality (≥70 = full trust, 40-69 = partial, <40 = functional). |
| **Phase Progression** | Time-based narrative transitions in submarine scenario. 4 phases: Impact & Connection (0:00-1:15), Working Relationship (1:15-2:30), The Revelation (2:30-3:30), The Choice (3:30-5:00). |
| **NPC-Aware Control** | Interactive button that the NPC "feels" when activated (e.g., BALLAST reduces hull pressure, NPC senses pressure change). Enables realistic reactive dialogue. |
| **Backchanneling** | NPC speech pattern providing real-time feedback ("That's it... keep going... almost there..."). Creates feeling of active guidance and presence. |
| **Claude Haiku** | Anthropic's fast, cost-effective LLM model used for real-time dialogue generation. 1-2 second response time, ~$0.001 per 800-token response. |
| **LLM Temperature** | Randomness parameter for language model generation. 0.0 = deterministic, 1.0 = highly creative. Platform uses 0.8 (dialogue), 0.2 (queries), 0.7 (Director). |
| **Success Rate** | Player performance metric calculated as (successful scenarios / total attempts) × 100%. Used by World Director to determine difficulty mode (easy <30%, normal 30-80%, hard >80%). |
| **Crisis Event** | World Director intervention spawning negative consequences (-20 oxygen, -10 trust) to increase tension for skilled players. 10-second cooldown. |
| **Help Event** | World Director intervention providing bonus resources (+15 oxygen, +5 trust) to struggling players. 10-second cooldown. |

### Key Files Reference
| File Path | Lines | Purpose |
|-----------|-------|---------|
| `/web_server.py` | 1,579 | Main aiohttp server, WebSocket handler, game state orchestration |
| `/player_memory.py` | 539 | Player personality tracking, SQLite persistence, relationship management |
| `/world_director.py` | 449 | AI dungeon master, situation evaluation, dynamic event spawning |
| `/response_queue.py` | 370 | Priority-based dialogue queue, cancellation logic, async processing |
| `/scenes/submarine.py` | 1,400+ | Flagship demo scenario: 8-minute submarine emergency with 4 phases |
| `/characters/engineer.py` | ~200 | Lt. Commander James Smith character definition |
| `/constants.py` | ~100 | Centralized configuration (temperatures, penalties, thresholds) |
| `/web/js/app.js` | 1,342 | Frontend WebSocket client, chat UI, scene management |
| `/web/js/submarine_scene.js` | 1,239 | Three.js submarine interior rendering, raycasting, particle effects |
| `/llm_prompt_core/models/anthropic.py` | ~200 | Claude API wrapper with Haiku/Sonnet/Opus model classes |

### Performance Benchmarks
| Metric | Target | Actual | Notes |
|--------|--------|--------|-------|
| **LLM Response Time** | <2s | 1-2s (Haiku), 4-6s (Sonnet) | Haiku meets target, Sonnet does not |
| **World Director Evaluation** | <1.5s | ~1s | Meets target |
| **Total Latency** | <3s | 2-3s (Haiku) | Meets target with Haiku |
| **Player Memory Lookup** | <50ms | <10ms | Exceeds target |
| **Scene End Save** | <100ms | <50ms | Exceeds target |
| **Frontend FPS** | 60 | 60 (desktop), ~45 (low-end) | Meets target on recommended hardware |
| **WebSocket Ping** | <100ms | Varies by network | Acceptable with broadband |

### Production Readiness Checklist
| Category | Item | Status | Priority | Notes |
|----------|------|--------|----------|-------|
| **Testing** | Unit test suite | ❌ | CRITICAL | No automated tests exist |
| | Integration tests | ❌ | CRITICAL | Manual testing only |
| | Performance/load tests | ❌ | HIGH | Unknown behavior under concurrent users |
| | Cross-browser testing | ❌ | HIGH | Untested on Safari, Edge, mobile |
| **Content** | 3+ polished scenarios | ❌ | CRITICAL | Only 1 scenario complete |
| | 10+ characters | ❌ | MEDIUM | 5 characters exist |
| | Tutorial/onboarding | ❌ | CRITICAL | No first-time user guidance |
| **Infrastructure** | Error handling | ❌ | CRITICAL | Minimal graceful degradation |
| | Logging/monitoring | ⚠️ | HIGH | Basic logging exists, no dashboards |
| | Deployment pipeline | ❌ | CRITICAL | No CI/CD, manual deployment |
| | Scaling strategy | ❌ | MEDIUM | Single server, no load balancing |
| **UX** | Trust/bond visual indicator | ❌ | HIGH | Internal state only |
| | Player profile dashboard | ❌ | MEDIUM | No visibility into personality |
| | Pause functionality | ❌ | MEDIUM | Can't pause timed scenarios |
| | Settings menu | ⚠️ | MEDIUM | Minimal (TTS toggle only) |
| **Analytics** | Player behavior tracking | ❌ | CRITICAL | No metrics, blind to engagement |
| | A/B testing framework | ❌ | LOW | Not needed for v1.0 |
| | Crash reporting | ❌ | HIGH | No error aggregation |
| **Legal/Safety** | Content moderation | ❌ | CRITICAL | No inappropriate input filtering |
| | Privacy policy | ❌ | CRITICAL | Required for data collection |
| | Terms of service | ❌ | CRITICAL | Required for public launch |
| | COPPA compliance | ❌ | MEDIUM | If targeting <13 users |

**Legend:** ✅ Complete | ⚠️ Partial | ❌ Not Started

---

## Revision History
| Date | Author | Changes |
|------|--------|---------|
| 2026-01-22 | Claude Sonnet 4.5 | Initial draft based on prototype review |

---

## Next Steps for Product Planning

### Immediate (Next 2 Weeks)
1. **Set up automated testing** - Unblock confident iteration. Start with unit tests for player_memory.py and world_director.py.
2. **Implement player profile dashboard** - Make personality system visible and engaging. Low complexity, high player value.
3. **Add trust/bond visual indicator** - Critical feedback missing from submarine scenario.
4. **Create 2 short scenarios** - Prove content pipeline velocity. Target: 3-5 minute scenarios using existing architecture.

### Short-term (Next 1-2 Months)
1. **Build onboarding/tutorial** - First 2 minutes of new player experience. Guide through dialogue interaction, button mechanics, show personality system.
2. **Implement analytics** - Track session length, drop-off points, success rates, personality convergence. Inform iteration priorities.
3. **Cross-browser testing and fixes** - Ensure Safari, Edge, mobile compatibility.
4. **Error handling audit** - Graceful degradation for LLM failures, network issues, WebSocket disconnects.

### Medium-term (Next 3-6 Months)
1. **Scenario editor (Phase 2)** - Visual tool for non-programmers to create content. Critical for scaling content creation.
2. **Voice input integration** - Speech-to-text for hands-free play. Aligns with "voice-first" vision.
3. **5 additional polished scenarios** - Demonstrate versatility: fantasy quest, detective mystery, space station emergency, time-loop puzzle, hostage negotiation.
4. **Community content beta** - Allow creators to submit scenarios for moderation and publication.

### Long-term (6+ Months)
1. **Multi-character scenarios** - Enable complex social dynamics (2-3 NPCs with relationships, turn-taking, conflicts).
2. **Procedural scenario generation** - LLM creates new scenarios from templates. Quality control required.
3. **Mobile support** - Responsive design, touch controls, optimized rendering for phones/tablets.
4. **VR proof-of-concept** - WebXR submarine experience. High risk, high reward.

---

**END OF DESIGN DOCUMENT**
