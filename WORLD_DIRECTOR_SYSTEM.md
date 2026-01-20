# World Director System - The Dungeon Master AI

## Overview

The World Director is an AI "dungeon master" that orchestrates the narrative experience in real-time. It evaluates situations after player actions and decides whether to intervene by spawning events, adjusting NPC behavior, giving hints, or letting the scene play out naturally.

**Think of it as**: A D&D dungeon master watching your game and stepping in at dramatic moments to keep things engaging, challenging, and fair.

## What It Does

### 1. **Situation Evaluation**
After each player action, the Director assesses:
- Current scene state (oxygen, trust, etc.)
- Player's behavioral history
- Recent dialogue
- Whether player is struggling
- Tension level
- Pacing

### 2. **Dynamic Interventions**
Based on assessment, the Director can:
- ✅ **Continue**: Let natural dialogue flow (most common)
- 🎲 **Spawn Event**: Create dynamic crisis/challenge/help
- 🎭 **Adjust NPC**: Change character behavior mid-scene
- 💡 **Give Hint**: Help struggling players
- 🚪 **Transition**: Recommend scene change (future)

### 3. **Difficulty Adaptation**
Director adjusts difficulty based on player skill:
- **Struggling Players**: Reduced penalties, more hints, bonus oxygen
- **Skilled Players**: Harsher penalties, fewer hints, less oxygen
- **Normal Players**: Standard difficulty

## How It Works

### Architecture

```
Player Action → Character Response → World Director Evaluation
                                              ↓
                        ┌─────────────────────┴──────────────────┐
                        ↓                                        ↓
                [Intervention Needed?]                    [Let it play out]
                        ↓
        ┌───────────────┼───────────────┬──────────────┐
        ↓               ↓               ↓              ↓
    Spawn Event    Adjust NPC      Give Hint    Scene Transition
```

### Decision Process

**Director's Prompt:**
```
=== CURRENT SITUATION ===
Scene: submarine
Character: casey
Last Player Action: Player activated VENT

Scene State:
- oxygen: 95
- trust: -15
- incorrect_actions: 3

Player Profile:
- VERY IMPULSIVE: Acts without thinking, interrupts frequently
- IMPATIENT: Button mashes, doesn't wait for instructions

Scene History:
- Attempts at this scene: 3 (Struggling - failed multiple times)

Recent Dialogue:
[Casey]: "Wait! Don't touch that yet!"
[Player]: *presses VENT*
[Casey]: "NO! I said WAIT!"

=== YOUR ROLE ===
Decide if intervention is needed. Options:
1. Continue (let it play out)
2. Spawn crisis event (make it worse)
3. Spawn help event (give player a break)
4. Adjust NPC behavior
5. Give hint
```

**Director's Decision (JSON):**
```json
{
    "assessment": "Player is struggling badly. Failed 3 times, button mashing, oxygen critical.",
    "tension_level": "high",
    "player_struggling": true,
    "action": "give_hint",
    "details": {
        "hint_type": "direct",
        "hint_content": "explain which button to press next in clear terms"
    }
}
```

### Decision Types

#### 1. Continue (Most Common)
```
Director: "Situation is tense but manageable. Let natural dialogue flow."
Result: No intervention, Casey responds normally
```

#### 2. Spawn Event
**Crisis Event:**
```
Director: "Oxygen critically low and player keeps making mistakes. Spawn crisis."
Event: "EMERGENCY - Sudden pressure spike causes oxygen leak!"
State Change: oxygen -20
Casey: "OH NO! The pressure spike! We're losing oxygen FAST!"
```

**Help Event:**
```
Director: "Player doing well but has been stuck for a while. Give lucky break."
Event: "LUCKY BREAK - You find an emergency oxygen canister!"
State Change: oxygen +15
Casey: "Wait, you found a backup canister! Quick, use it!"
```

**Challenge Event:**
```
Director: "Scene is getting stale. Add tension without catastrophe."
Event: "CHALLENGE - You hear ominous creaking from the hull"
Casey: "That sound... that's not good. We need to work faster."
```

#### 3. Adjust NPC Behavior
```
Director: "Player keeps interrupting. Make Casey more assertive."
Adjustment: "more_frustrated"
Next Response: Casey's dialogue becomes MORE URGENT and FIRM
Casey: "LISTEN TO ME! If you keep acting like this, we're BOTH going to die!"
```

**Predefined Adjustments:**
- `more_helpful`: Give clearer instructions (for struggling players)
- `more_urgent`: Show stress and danger
- `more_frustrated`: React to player mistakes
- `more_trusting`: Be relaxed (player doing well)
- `more_worried`: Critical situation awareness
- `encouraging`: Positive reinforcement

#### 4. Give Hint
**Subtle Hint** (first attempt):
```
Director: "Player failed once. Give subtle hint."
Casey: "You know... the BALLAST control might help with the pressure..."
```

**Direct Hint** (multiple failures):
```
Director: "Player failed 3 times. Be explicit."
Casey: "Okay, LISTEN. Press the BALLAST button. The one on the LEFT. Do it NOW."
```

#### 5. Scene Transition (Future)
```
Director: "Success criteria met. Recommend transition to next scene."
```

## Difficulty Adaptation

### Based on Player Skill

**Struggling Player** (success rate < 30% OR 3+ scene attempts):
```python
{
    'penalty_multiplier': 0.7,      # 30% less harsh
    'hint_frequency': 'frequent',
    'oxygen_bonus': +30             # Start with more oxygen
}
```

**Result:**
- Interruption penalty: 15s → 10s oxygen
- Button mashing penalty: 10s → 7s oxygen
- More hints from Director
- Extra 30s oxygen at scene start

**Skilled Player** (success rate > 80%, < 2 attempts):
```python
{
    'penalty_multiplier': 1.3,      # 30% harsher
    'hint_frequency': 'rare',
    'oxygen_bonus': -30             # Start with less oxygen
}
```

**Result:**
- Interruption penalty: 15s → 19s oxygen
- Button mashing penalty: 10s → 13s oxygen
- Rare hints
- Start with 150s oxygen instead of 180s

**Normal Player**:
```python
{
    'penalty_multiplier': 1.0,
    'hint_frequency': 'normal',
    'oxygen_bonus': 0
}
```

### Cooldown System

Director doesn't intervene too often:
- After spawning event: 5-action cooldown
- After adjusting NPC: 3-action cooldown
- After giving hint: 4-action cooldown

This prevents:
- Constant interruptions
- Breaking natural dialogue flow
- Overwhelming player with events

## Integration with Player Memory

Director receives full player context:
```
Player Profile:
- VERY IMPULSIVE: Acts without thinking, interrupts frequently
- IMPATIENT: Button mashes, doesn't wait for instructions
- UNCOOPERATIVE: Ignores instructions, acts independently
- STRUGGLES: Often makes incorrect choices

Relationship with you (casey):
You've worked with this player 3 times before.
You're seriously frustrated with their past behavior.

Statistics:
- Total scenes played: 5
- Success rate: 20%
- This scene attempts: 3
```

**Director uses this to:**
- Give more hints to struggling players
- Spawn help events for those who need it
- Make scenes harder for skilled players
- Understand if player is learning or stuck

## Example Scenarios

### Scenario 1: Struggling Newbie

**State:**
- Player failed submarine twice
- Keeps button mashing
- Oxygen critically low (40s)

**Director Decision:**
```
Action: spawn_event (type: help)
Event: "You notice a secondary oxygen valve you missed before!"
State: oxygen +20
```

**Then:**
```
Action: give_hint (type: direct)
Hint: "Press the BALLAST button next, then wait for my instructions"
```

**Result:** Player gets breathing room and clear guidance

---

### Scenario 2: Skilled Speedrunner

**State:**
- Player has 90% success rate
- First submarine attempt
- Playing perfectly so far
- Oxygen still at 150s

**Director Decision:**
```
Action: spawn_event (type: crisis)
Event: "EMERGENCY - Hull breach detected! Oxygen venting rapidly!"
State: oxygen -30
```

**Result:** Adds challenge for skilled player, keeps them engaged

---

### Scenario 3: Learning Player

**Attempt 1:** Button mashing, failed
**Attempt 2:** Still impulsive, failed
**Attempt 3:** Player is now waiting for instructions!

**Director Decision:**
```
Action: adjust_npc (behavior: encouraging)
NPC Modifier: "Show ENCOURAGEMENT and positive reinforcement"
Casey: "Hey! You're actually listening this time. That's MUCH better. Keep it up!"
```

**Result:** Positive reinforcement for behavioral improvement

---

### Scenario 4: Stale Dialogue

**State:**
- Player and Casey exchanging normal dialogue
- Nothing dramatic happening
- Been 5 actions without tension

**Director Decision:**
```
Action: spawn_event (type: challenge)
Event: "You hear an ominous grinding sound from the ballast tanks"
Casey: "*pauses* ...Did you hear that? That's not supposed to happen..."
```

**Result:** Reignites tension, prevents boredom

## Technical Implementation

### Core Files

**world_director.py**: The dungeon master brain
- `WorldDirector` class
- `evaluate_situation()` - Main decision maker
- `generate_dynamic_event()` - Creates events
- `generate_npc_behavior_adjustment()` - Modifies NPCs
- `generate_hint()` - Creates hints
- `get_difficulty_adjustment()` - Skill-based scaling

**web_server.py**: Integration
- `consult_director()` - Calls director after actions
- `handle_director_event()` - Spawns events
- `handle_npc_adjustment()` - Applies behavior changes
- `handle_director_hint()` - Delivers hints

### LLM Usage

Director uses **Haiku** (fast, cheap):
- Temperature: 0.7 (balanced creativity)
- Max tokens: 500 (concise decisions)
- Structured JSON output

### Performance

- **Speed**: Haiku responds in ~1-2 seconds
- **Cost**: ~$0.001 per decision (very cheap)
- **Frequency**: Intervenes ~20% of actions (cooldown-controlled)

## Frontend Integration

New message type: `system_event`

```javascript
case 'system_event':
    // World Director spawned an event
    this.addSystemMessage(data.content);
    // Example: "[EMERGENCY] Sudden pressure spike - oxygen dropping fast!"
    break;
```

System events appear in chat as special messages, distinct from character dialogue.

## Benefits

### For Players
- ✅ **Adaptive difficulty**: Easier if struggling, harder if skilled
- ✅ **Dynamic storytelling**: Events feel emergent, not scripted
- ✅ **Help when stuck**: Hints appear when needed
- ✅ **Never boring**: Director adds tension when needed
- ✅ **Fair challenge**: Difficulty matches your skill level

### For Developers
- ✅ **Emergent gameplay**: Don't need to script every scenario
- ✅ **Player retention**: Struggling players get help instead of quitting
- ✅ **Replayability**: Different interventions each playthrough
- ✅ **Balancing**: Auto-adjusts based on player performance
- ✅ **Narrative flexibility**: Director fills gaps in scripted content

## Future Enhancements

### Phase 2
- **Multi-scene arcs**: Director tracks progress across scenes
- **Story branching**: Director creates unique paths based on player history
- **NPC coordination**: Director manages multiple NPCs simultaneously
- **Emotional tracking**: Director monitors player frustration/engagement

### Phase 3
- **Procedural content**: Director generates new scenes on the fly
- **Personality-driven events**: Tailor events to player archetypes
- **Meta-commentary**: Director breaks fourth wall in creative ways
- **Collaborative storytelling**: Director and player co-create narrative

## Testing the Director

### Test 1: Struggling Player
1. Fail submarine scene twice (button mash)
2. On 3rd attempt, keep making mistakes
3. **Watch for**: Director spawns help event OR gives direct hint
4. **Expected**: "You notice emergency oxygen!" or "Press BALLAST now!"

### Test 2: Skilled Player
1. Beat submarine scene successfully
2. Restart and play perfectly again
3. **Watch for**: Director spawns crisis event
4. **Expected**: "EMERGENCY - Hull breach!" (oxygen drops significantly)

### Test 3: Stale Scene
1. Play submarine but don't press any buttons
2. Just chat with Casey for several exchanges
3. **Watch for**: Director spawns challenge event for tension
4. **Expected**: "You hear creaking..." or similar

### Test 4: Learning Behavior
1. Fail by button mashing
2. Restart and wait patiently for instructions
3. **Watch for**: Director adjusts Casey to be encouraging
4. **Expected**: Casey says "You're listening! Much better!"

## Monitoring Director Activity

Check server logs for Director decisions:
```bash
tail -f /tmp/webserver.log | grep "\[Director\]"
```

Output:
```
[Director] Decision: continue
[Director] Decision: give_hint
[Director] Giving direct hint: which button to press
[Director] Decision: spawn_event
[Director] Spawning event: crisis - Pressure spike causes oxygen leak
[Director] Adjusting NPC: more_helpful
```

## Summary

The World Director transforms Digital Actors from a **static narrative experience** into a **dynamic, adaptive storytelling system** where:

- 🎮 Every playthrough is different
- 🎯 Difficulty matches your skill
- 💡 Help appears when needed
- 🎲 Events feel emergent and surprising
- 🎭 NPCs adapt their behavior dynamically
- 🚀 Stories evolve organically

**You now have a real dungeon master orchestrating your experience!** 🧙‍♂️

---

## Architecture Comparison

**Before Director:**
```
Player → Character → Response
         ↓
    Static scene
```

**After Director:**
```
Player → Character → Response
         ↓           ↓
    Scene State → Director Evaluation
                     ↓
         ┌───────────┼──────────┬────────┐
         ↓           ↓          ↓        ↓
     Events    NPC Changes   Hints   Continue
```

**The Framework Vision:**
```
          Narrator (not needed)
              ↓
    World Director (✅ IMPLEMENTED!)
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Environment      Virtual Actors
    ↓                   ↓
         Player ↔ Experience
```

We've built the **orchestration layer** that was missing! 🎉
