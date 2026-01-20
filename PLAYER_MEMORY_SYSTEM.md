# Player Memory System

## Overview

The Player Memory system tracks player behavior, personality, and relationships across sessions. Characters now "remember" you and adapt their dialogue based on your play style and history.

## What's Tracked

### Personality Profile (0-100 scale)
- **Impulsiveness**: Increases when interrupting NPCs or acting without thinking
- **Patience**: Decreases with button mashing, increases when waiting for instructions
- **Cooperation**: Increases with successful cooperation, decreases when ignoring guidance
- **Problem Solving**: Increases with correct actions, decreases with repeated mistakes

### Relationships
For each character (Casey, Eliza, etc.):
- **Trust**: Net change in trust across all encounters
- **Familiarity**: Number of times you've interacted

### Performance History
- Total scenes played
- Success/failure rate
- Attempts per scene
- Achievements and failures

## How It Works

### 1. Session Start
When you connect to the server, a `PlayerMemory` object is created:
```
Player ID: player_<websocket_id>
Database: data/player_memory.db (SQLite)
```

### 2. Scene Tracking
Each scene attempt is tracked:
- **Start**: Records initial state (oxygen, trust, etc.)
- **During**: Records interruptions and rapid actions
- **End**: Saves final state, outcome, and updates personality

### 3. Character Adaptation
Characters receive player context in their prompts:

**Example for an impulsive player:**
```
=== PLAYER MEMORY ===
Player behavioral profile:
- VERY IMPULSIVE: Acts without thinking, interrupts frequently
- IMPATIENT: Button mashes, doesn't wait for instructions
- UNCOOPERATIVE: Ignores instructions, acts independently

Relationship with you (casey):
You've worked with this player 3 times before. You're somewhat frustrated with their past behavior.

Statistics:
- Total scenes played: 5
- Success rate: 20%
- This scene attempts: 2

INSTRUCTION: Adapt your dialogue to match this player's history and personality.
```

**Casey's Response Changes:**
- *First time*: "Okay, listen carefully..."
- *After 3 interruptions*: "STOP! You keep interrupting me! WAIT until I finish!"
- *Repeat player*: "Look, I know you like to act fast, but you NEED to listen this time."

### 4. Personality Updates

**Interrupting Casey (+3 impulsiveness, -2 cooperation):**
```python
# Before: Impulsiveness = 50
Player interrupts → Impulsiveness = 53
Player interrupts again → Impulsiveness = 56
Player interrupts 10 times → Impulsiveness = 80 (VERY IMPULSIVE)
```

**Waiting for instructions (-1 impulsiveness, +2 patience):**
```python
# After being patient for 5 scenes:
Impulsiveness drops from 80 → 75
Patience increases from 40 → 50
```

**Success with cooperation (+3 cooperation):**
```python
# Completing submarine without interrupting:
Cooperation: 50 → 53 → 56 → 70 (after multiple successes)
```

## Database Schema

### Tables Created

**players**
- player_id (primary key)
- created_at, last_seen
- total_sessions, total_playtime_seconds

**sessions**
- session_id, player_id
- started_at, ended_at
- scenes_completed

**scene_attempts**
- attempt_id, player_id, scene_id, character_id
- started_at, ended_at
- outcome (success/failure)
- final_trust, correct_actions, incorrect_actions
- interrupted_npc (boolean)
- data (JSON - full final state)

**personality_profiles**
- player_id (primary key)
- impulsiveness, cooperation, problem_solving, patience (0-100)
- updated_at

**relationships**
- player_id, character_id (composite primary key)
- trust, familiarity
- last_interaction

## Example Scenarios

### Scenario 1: Button Masher

**Session 1 - Submarine:**
- Player clicks VENT, BALLAST, O2 VALVE rapidly
- Interrupts Casey 5 times
- **Result**: Failure, oxygen depleted

**Personality Updated:**
- Impulsiveness: 50 → 65
- Patience: 50 → 35
- Cooperation: 50 → 44
- Casey trust: 0 → -25

**Session 2 - Same Player Returns:**
Casey's opening: "You again? Look, I need you to actually LISTEN this time. Last time was a disaster because you kept hitting buttons without waiting!"

**If player interrupts again:**
Casey: "ARE YOU KIDDING ME?! We just talked about this! STOP pressing buttons!"

---

### Scenario 2: Cooperative Player

**Session 1 - Submarine:**
- Player waits for Casey's instructions
- Presses correct buttons
- **Result**: Success

**Personality Updated:**
- Cooperation: 50 → 56
- Patience: 50 → 56
- Problem Solving: 50 → 54
- Casey trust: 0 → 35

**Session 2 - Same Player Returns:**
Casey's opening: "Hey! Good to see you again. You did great last time - really worked well with me. Ready for another challenge?"

**During scene:**
Casey: "Okay, you know the drill. I trust you on this one."

---

### Scenario 3: Learning Player

**Sessions 1-2:**
- Button mashes, interrupts (Impulsiveness: 70)
- Fails both times

**Session 3:**
- Player *tries* to be patient
- Only interrupts once
- Follows most instructions
- **Result**: Partial success

**Personality Updated:**
- Impulsiveness: 70 → 67 (slowly improving)
- Cooperation: 45 → 48
- Casey trust: -30 → -15

**Session 4:**
- No interruptions!
- Good cooperation
- **Result**: Success

**Personality Updated:**
- Impulsiveness: 67 → 64
- Patience: 40 → 48
- Cooperation: 48 → 57
- Casey trust: -15 → 15

Casey's response: "Wow. You really learned from last time. I'm impressed. Let's keep this up!"

---

## API Usage

### Creating Player Memory
```python
from player_memory import PlayerMemory

# Automatic (uses websocket ID)
memory = PlayerMemory(f"player_{id(ws)}")

# Or with custom ID
memory = PlayerMemory("player_alice")
```

### Recording Events
```python
# Start scene
memory.start_scene("submarine", "casey", initial_state)

# During scene
memory.record_interruption()
memory.record_rapid_actions()

# End scene
memory.end_scene("success", final_state)
```

### Getting Context for LLM
```python
# Full context
context = memory.get_full_context_for_llm("casey")

# Just personality
personality = memory.get_personality_summary()

# Just relationship
relationship = memory.get_character_context("casey")
```

### Checking Player Patterns
```python
# Should we give a hint?
if memory.should_give_hint("submarine"):
    # Player has failed this scene 2+ times
    casey_hints = True

# Recommend difficulty
difficulty = memory.get_difficulty_recommendation()
# Returns: "easier", "normal", or "harder"
```

## Integration Points

### web_server.py Changes

1. **Session Init**: Creates PlayerMemory on websocket connect
2. **Scene Start**: Tracks when scene begins (opening speech)
3. **Interruptions**: Records when player interrupts
4. **Rapid Actions**: Records button mashing
5. **LLM Prompts**: Adds player context to all character responses
6. **Scene End**: Saves final state on game over
7. **Restart**: Reinitializes tracking for new attempt

### Character Responses Affected

Every time a character generates dialogue, they receive:
- Player's personality profile
- Relationship history with that character
- Success/failure statistics
- Scene-specific attempt history

This allows characters to:
- **Adapt tone**: More patient with cooperative players, more firm with impulsive ones
- **Remember past**: "Last time you...", "You and I have worked together before..."
- **Give hints**: If player is struggling, offer more guidance
- **Build relationships**: Characters become friendlier/hostile based on history

## Future Enhancements

### Phase 1 (Completed) ✅
- Basic personality tracking
- Relationship system
- Database storage
- LLM integration

### Phase 2 (Potential)
- **Player profiles in UI**: Show stats in browser
- **Achievements system**: Unlock badges for patterns
- **Difficulty auto-adjustment**: Easier for struggling players
- **Cross-session continuity**: "It's been 3 days since I saw you last..."

### Phase 3 (Advanced)
- **Multi-character coordination**: Characters gossip about player
- **Long-term arcs**: Relationships evolve over many sessions
- **Player types**: Classify as "Speedrunner", "Explorer", "Completionist"
- **Dynamic content**: Unlock new scenes based on personality

## Testing the System

### Test 1: Button Masher
1. Start submarine scene
2. Rapidly click buttons while Casey is talking
3. Interrupt her 3+ times
4. Fail the scene
5. **Restart and try again**
6. Casey should say something like: "You AGAIN? After what happened last time?!"

### Test 2: Good Player
1. Start submarine scene
2. Wait patiently for all of Casey's instructions
3. Press correct buttons
4. Succeed
5. **Restart and try again**
6. Casey should be more trusting: "Good to see you again. Let's do this."

### Test 3: Learning Curve
1. Fail 2-3 times by button mashing
2. On 4th attempt, play cooperatively
3. Casey should acknowledge improvement: "Okay, you're actually listening this time. Good."

## Database Location

```
/Users/johnny.venables/Projects/digital-actors/data/player_memory.db
```

To inspect:
```bash
sqlite3 data/player_memory.db
sqlite> .tables
sqlite> SELECT * FROM personality_profiles;
sqlite> SELECT * FROM relationships;
sqlite> SELECT scene_id, outcome, final_trust FROM scene_attempts;
```

## Summary

The Player Memory system transforms Digital Actors from a static chat experience into a **dynamic relationship simulation** where your behavior has consequences and characters genuinely remember and adapt to you.

**Key Benefits:**
- ✅ Characters feel alive (they remember you)
- ✅ Replayability (different interactions each time)
- ✅ Player progression (your behavior shapes the experience)
- ✅ Emergent storytelling (relationships evolve organically)
- ✅ Learning encouragement (characters adapt to help you improve)

**Next Step:** Add World Director agent to orchestrate dynamic story beats based on player memory! 🚀
