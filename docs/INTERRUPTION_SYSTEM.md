# Interruption & Penalty System

## Overview

The system now detects and penalizes players who:
- Press buttons while the NPC is talking (interruption)
- Button mash / press multiple buttons rapidly (reckless behavior)

This creates realistic consequences for not listening to instructions and adds tension to time-sensitive scenarios.

## How It Works

### Tracking NPC State

```python
# web_server.py - ChatSession
self.npc_responding = False  # Is NPC currently talking?
self.last_action_time = 0     # When was last button pressed?
self.action_count_recent = 0  # How many rapid actions?
```

### Interruption Detection

**Scenario 1: Interrupting NPC**
```
Casey is typing response...
self.npc_responding = True
    ↓
Player clicks button mid-response
    ↓
was_interrupted = True
    ↓
PENALTY APPLIED
```

**Scenario 2: Button Mashing**
```
Player clicks BALLAST (time = 0s)
Player clicks O2 VALVE (time = 1.5s)
Player clicks VENT (time = 2.8s)
    ↓
3 actions within 3 seconds
action_count_recent = 3
    ↓
PENALTY APPLIED
```

### Penalties

#### Interrupting NPC (was_interrupted = True)
- **-15 seconds oxygen** (severe)
- **-10 trust points**
- **+1 incorrect action**
- Event note: `[INTERRUPTION: Player did not wait for instructions]`

#### Button Mashing (3+ rapid actions)
- **-10 seconds oxygen** (moderate)
- **-5 trust points**
- **+1 incorrect action**
- Event note: `[RAPID ACTIONS: Player acting recklessly]`

#### Normal Action
- **No penalties**
- NPC reacts normally

### State Updates

Penalties are applied to scene state variables:
```python
self.scene_state['oxygen'] -= penalty_oxygen
self.scene_state['trust'] -= penalty_trust
self.scene_state['incorrect_actions'] += penalty_incorrect
```

Client receives state update:
```json
{
  "type": "state_update",
  "state": {
    "oxygen": 165,
    "trust": -10,
    "incorrect_actions": 1
  },
  "penalties": {
    "oxygen": 15,
    "trust": 10
  }
}
```

### NPC Reaction

When player interrupts or button mashes, the LLM receives special instructions:

```python
extra_instruction = """
The player interrupted you or acted without waiting for your guidance.
React with panic, frustration, or anger.
Make it clear they're making things worse.
"""
```

This makes Casey respond with:
- Panic: "What are you DOING?! I didn't tell you to press that!"
- Frustration: "Stop! You're not listening to me!"
- Anger: "We're going to DIE if you don't WAIT for my instructions!"

## Example Scenarios

### Good Playthrough (No Penalties)

```
Casey: "Okay, listen carefully. I need you to hit the BALLAST button."
[Player waits for Casey to finish]
Player clicks BALLAST
Casey: "Good! I can feel the pressure dropping. Now wait..."
[Time passes]
Casey: "Okay, next I need you to—"
Player clicks O2 VALVE
Casey: "Perfect timing! The oxygen is rebalancing."

Result: No penalties, trust increases, cooperative play
```

### Bad Playthrough (Interruption)

```
Casey: "Okay, listen carefully. I need you—"
[Player clicks VENT mid-sentence]

PENALTY: -15s oxygen, -10 trust
[INTERRUPTION: Player did not wait for instructions]

Casey: "NO! What are you DOING?! I didn't say VENT!"
Casey: "You just wasted oxygen! LISTEN TO ME!"
Casey: "*breathing heavily* We don't have time for mistakes!"

Result: Oxygen drops to 165s, trust at -10, likely to fail
```

### Bad Playthrough (Button Mashing)

```
Player clicks BALLAST
Player clicks O2 VALVE (0.5s later)
Player clicks VENT (1.2s later)

PENALTY: -10s oxygen, -5 trust
[RAPID ACTIONS: Player acting recklessly]

Casey: "Stop! STOP! You're just hitting buttons randomly!"
Casey: "You need to SLOW DOWN and work with me!"
Casey: "Every wrong move costs us oxygen we don't have!"

Result: Oxygen drops, trust decreases, panicked NPC
```

## Technical Implementation

### 1. Mark When NPC Responds

```python
async def handle_message(self, message):
    self.npc_responding = True
    # ... generate response ...
    self.npc_responding = False
```

```python
async def handle_button_action(self, action):
    self.npc_responding = True
    # ... generate response ...
    self.npc_responding = False
```

### 2. Check for Interruption

```python
# In handle_button_action
current_time = time.time()
time_since_last = current_time - self.last_action_time

if time_since_last < 3.0:
    self.action_count_recent += 1
else:
    self.action_count_recent = 1

self.last_action_time = current_time
was_interrupted = self.npc_responding  # Were they talking?
```

### 3. Apply Penalties

```python
if was_interrupted:
    penalty_oxygen = 15
    penalty_trust = 10
    penalty_incorrect = 1
elif self.action_count_recent >= 3:
    penalty_oxygen = 10
    penalty_trust = 5
    penalty_incorrect = 1
```

### 4. Send State Update

```python
await self.ws.send_json({
    'type': 'state_update',
    'state': self.scene_state,
    'penalties': {
        'oxygen': penalty_oxygen,
        'trust': penalty_trust,
    }
})
```

### 5. Modify LLM Instructions

```python
if was_interrupted or self.action_count_recent >= 3:
    extra_instruction = "React with panic, frustration, or anger."
else:
    extra_instruction = "React naturally."
```

## Future Enhancements

### Visual Feedback

Could add:
- Red flash on screen when interrupted
- Oxygen gauge pulses red
- Casey's avatar shakes/shows distress
- Screen shake effect

### Audio Feedback

Could add:
- Harsh buzzer sound on interruption
- Casey's voice gets more stressed
- Alarm sound on button mashing
- "Error" beep on penalty

### Difficulty Levels

**Easy Mode**:
- Interruption: -5s oxygen, -5 trust
- Button mashing: -3s oxygen, -2 trust
- More forgiving

**Normal Mode** (current):
- Interruption: -15s oxygen, -10 trust
- Button mashing: -10s oxygen, -5 trust

**Hard Mode**:
- Interruption: -25s oxygen, -20 trust
- Button mashing: -15s oxygen, -10 trust
- Very punishing

### Progressive Penalties

Could increase penalties for repeated offenses:
```python
# First interruption: -15s
# Second interruption: -20s
# Third interruption: -30s (exponential)
```

## Balance Considerations

### Current Penalties (Submarine Scene)

**Starting State**:
- Oxygen: 180 seconds (3 minutes)
- Trust: 0

**Single Interruption**:
- Oxygen: 165s (2:45 remaining)
- Trust: -10
- Still survivable but harder

**Two Interruptions**:
- Oxygen: 150s (2:30 remaining)
- Trust: -20
- Very difficult to recover

**Three Interruptions**:
- Oxygen: 135s (2:15 remaining)
- Trust: -30
- Almost certain failure

**Failure Threshold**:
- Oxygen: 0s = Death
- Trust: -20 + oxygen < 90 = Broken trust ending
- Incorrect actions: 5 = Critical failure

### Design Goal

Penalties should:
- ✅ Discourage interrupting/button mashing
- ✅ Create tension ("Should I wait or act?")
- ✅ Make cooperation feel important
- ✅ Still allow recovery if player listens afterward
- ❌ Not be instantly fatal (one mistake = death)

### Tuning

Adjust penalties in `web_server.py`:
```python
# Make harsher
penalty_oxygen = 20  # Was 15
penalty_trust = 15   # Was 10

# Make more forgiving
penalty_oxygen = 8   # Was 15
penalty_trust = 5    # Was 10
```

## Player Psychology

### Good Player Behavior
1. Listen to NPC speech
2. Wait for instructions to finish
3. Ask questions if unsure
4. Act deliberately, not frantically
5. Build trust through cooperation

### Bad Player Behavior
1. Ignoring NPC dialogue
2. Button mashing
3. Acting impulsively
4. Not waiting for guidance
5. Panicking under pressure

The penalty system **teaches** good behavior by making bad behavior costly.

## Summary

**Interruption System**:
- ✅ Detects when player interrupts NPC
- ✅ Detects rapid button mashing
- ✅ Applies oxygen and trust penalties
- ✅ Makes NPC react with panic/anger
- ✅ Sends state updates to frontend
- ✅ Creates realistic consequences
- ✅ Encourages cooperative play
- ✅ Adds tension to time-limited scenarios

**Result**: Players learn to **listen, think, then act** instead of panic-clicking buttons.

This makes the submarine scenario feel like a **real emergency** where communication and trust are survival mechanics, not just narrative fluff.
