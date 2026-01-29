# Digital Actors - How It All Works

A friendly guide for understanding the key concepts behind Digital Actors. No programming experience required.

---

## What Is Digital Actors?

Digital Actors is a system for creating **interactive AI characters** that you can talk to in a web browser. Think of it like a video game where the characters are powered by AI - they listen to what you say, think about it, and respond naturally.

The characters live in **scenes** (a sinking submarine, a detective's office, a life raft) and react to both your words and your actions (like pressing buttons).

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                        YOUR BROWSER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  3D Scene   │  │  Chat Box   │  │  Control Buttons    │  │
│  │  (visuals)  │  │  (dialogue) │  │  (actions)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ WebSocket (live connection)
┌─────────────────────────────────────────────────────────────┐
│                     PYTHON SERVER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  AI Brain   │  │  Memory     │  │  Scene Logic        │  │
│  │  (Claude)   │  │  (database) │  │  (rules & state)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Frontend** = What you see (the browser)
**Backend** = The brains (Python server + AI)

They talk to each other constantly over a "WebSocket" - a live phone line that stays open so responses feel instant.

---

## Core Concepts

### 1. Scenes

A **scene** is a self-contained scenario with:
- A setting (submarine, detective office, life raft)
- A character to interact with
- Buttons you can press (actions)
- State that changes (oxygen level, trust meter)
- Win/lose conditions

Each scene is defined in a Python file like `scenes/submarine.py`. Think of it as a recipe that describes everything about that scenario.

### 2. Characters (Digital Actors)

Each character has:
- A **personality** (gruff engineer, calm captain, suspicious informant)
- A **backstory** (who they are, what they know)
- A **voice** (via ElevenLabs text-to-speech)

The AI reads the personality and backstory before every response, so it stays "in character."

### 3. The AI Brain (Claude)

We use **Claude** (made by Anthropic) as the AI that powers the characters. When you say something:

1. Your message goes to the server
2. Server builds a "prompt" (instructions + context + your message)
3. Claude generates a response as the character
4. Response comes back to your browser
5. Character speaks (text + voice)

We use **Claude Haiku** - a faster, cheaper version - so responses come in 1-2 seconds instead of 5-6.

---

## Intelligence Systems

These make the characters smarter and the scenes more dynamic.

### RAG (Retrieval-Augmented Generation)

**Problem:** Characters have lots of backstory and lore. We can't include everything in every prompt - it's slow and expensive.

**Solution:** Store facts as a searchable list. When you ask something, find the relevant facts and include only those.

**Example:**
- You ask: "Do you have family?"
- System finds: "Kovich has a son named Adrian, age 12, aboard the submarine"
- AI can now mention Adrian naturally

Facts are defined per-scene. Submarine facts stay in the submarine; detective facts stay in the detective scene.

### Post-Speak Hooks

**What:** Automatic checks that run after every character response.

**Why:** We want the scene to react to what the character *says*, not just what the player does.

**Standard hooks** (built-in patterns):
- **Slip detection** - Character accidentally revealed something
- **Emotional tracking** - A bonding moment happened
- **Name mentions** - A specific person was mentioned

**Custom hooks** (per scene):
- Define a condition: "Did they mention sacrifice?"
- Define what happens: Update trust meter, trigger an alarm sound

Hooks are "declarative" - you describe *what* to watch for, not *how* to code it.

### Query System

Sometimes we need to ask: "Has the player earned this character's trust?"

That's not a simple yes/no - it requires reading the conversation and making a judgment. The **Query System** asks Claude to evaluate conditions like this.

**Features:**
- **Caching** - Same question with same context won't ask Claude twice
- **Latching** - Once something becomes true (trust earned), it stays true

---

## How Prompts Work

A "prompt" is the instructions we send to Claude. It's built from layers:

```
┌─────────────────────────────────────────┐
│  1. SYSTEM INSTRUCTIONS                 │
│     "You are Casey Reeves, an engineer" │
├─────────────────────────────────────────┤
│  2. CHARACTER BACKSTORY                 │
│     Personality, history, motivations   │
├─────────────────────────────────────────┤
│  3. SCENE CONTEXT                       │
│     Current situation, what's happening │
├─────────────────────────────────────────┤
│  4. RELEVANT FACTS (from RAG)           │
│     Just the facts related to this turn │
├─────────────────────────────────────────┤
│  5. PLAYER MEMORY                       │
│     "This player interrupts a lot"      │
├─────────────────────────────────────────┤
│  6. RECENT DIALOGUE                     │
│     Last few exchanges                  │
├─────────────────────────────────────────┤
│  7. PLAYER'S MESSAGE                    │
│     What they just said/did             │
└─────────────────────────────────────────┘
```

Claude reads all of this and generates a response that fits the character, situation, and player.

---

## The Server (Backend)

The Python server (`web_server.py`) is the central brain. It:

1. **Receives** messages from browsers via WebSocket
2. **Builds** prompts with all the context
3. **Calls** Claude to generate responses
4. **Runs** hooks and updates scene state
5. **Sends** responses back (text + audio)
6. **Remembers** player behavior for next time

**Key files:**
| File | What it does |
|------|--------------|
| `web_server.py` | Main server, handles everything |
| `player_memory.py` | Remembers player behavior across sessions |
| `world_director.py` | AI "dungeon master" that spawns events |
| `tts_elevenlabs.py` | Converts text to spoken audio |

---

## The Frontend (Browser)

The browser side is HTML, CSS, and JavaScript. It:

1. **Displays** the 3D scene (using Three.js)
2. **Shows** the chat interface
3. **Plays** audio responses
4. **Sends** your messages and button clicks to the server

**Key files:**
| File | What it does |
|------|--------------|
| `web/js/app.js` | Main app logic, WebSocket connection |
| `web/js/*_scene.js` | 3D environments (submarine, detective, etc.) |
| `web/css/style.css` | Visual styling |
| `web/index.html` | Page structure |

---

## Player Memory

The system remembers how you play:

- **Do you interrupt?** Characters get frustrated
- **Do you button-mash?** They give more direct instructions
- **Do you listen carefully?** They trust you more

This memory persists across sessions. Come back tomorrow, and they'll remember you.

---

## World Director

An AI "dungeon master" watching your playthrough. It can:

- **Spawn events** - Create a crisis if you're doing too well
- **Give hints** - Help if you're struggling
- **Adjust NPCs** - Make characters more helpful or frustrated

It runs after each action, deciding whether to intervene or let things play out naturally.

---

## Voice (TTS)

Characters speak using **ElevenLabs** text-to-speech:

- **Expressive mode** - Slower but vocalizes `[laughs]`, `[sighs]`
- **Fast mode** - Quicker responses, no paralinguistics

Each character has their own voice ID and settings (some more animated, some more calm).

---

## Adding a New Scene

To create a new scenario, you need:

1. **Scene file** (`scenes/my_scene.py`)
   - Facts (lore the character knows)
   - Hooks (what to watch for)
   - Controls (buttons)
   - State variables (health, trust, etc.)

2. **Character file** (`characters/my_character.py`)
   - Personality and backstory

3. **3D scene** (`web/js/my_scene.js`) - optional
   - Visual environment

4. **Config mapping** (`config/scene_mappings.json`)
   - Links scene to character

The system is designed so scenes follow the same pattern - no special code needed for each one.

---

## Glossary

| Term | Meaning |
|------|---------|
| **Backend** | Server-side code (Python) |
| **Frontend** | Browser-side code (JavaScript) |
| **Prompt** | Instructions sent to the AI |
| **RAG** | Retrieval-Augmented Generation - finding relevant facts |
| **Hook** | Automatic check that runs after responses |
| **Latch** | Once true, stays true forever |
| **WebSocket** | Live two-way connection between browser and server |
| **TTS** | Text-to-speech (making the AI talk) |
| **State** | Current values (oxygen: 75, trust: 50) |
| **Scene** | A complete scenario with character, setting, rules |

---

## Questions?

This document will be updated as the project evolves. If something's unclear, ask and we'll add clarification here.

*Last updated: January 2026*
