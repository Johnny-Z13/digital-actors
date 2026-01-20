# NPC Aware Flag - Design Pattern

## Overview

The `npc_aware` flag on SceneControl objects determines whether the NPC character can perceive player actions. This allows for:
- **Shared awareness**: NPC reacts to player actions (submarine scenario)
- **Hidden actions**: Player can perform actions without NPC knowing (investigation scenario)
- **Mixed scenarios**: Some actions visible, others hidden

## Implementation

### SceneControl Definition

```python
SceneControl(
    id="control_id",
    label="BUTTON LABEL",
    npc_aware=True,  # or False
    # ... other properties
)
```

### Default Behavior

- **Default**: `npc_aware=True` - NPC is notified and can react
- **When False**: Player action is acknowledged but NPC receives no notification

## Example Scenarios

### 1. Submarine Emergency (All Aware)

**Context**: Casey is in the engine room. All submarine systems are connected, so Casey can see/hear/feel everything that happens in the forward cabin.

```python
SceneControl(
    id="o2_valve",
    label="O2 VALVE",
    npc_aware=True,  # Casey sees oxygen gauges drop
)

SceneControl(
    id="vent",
    label="VENT",
    npc_aware=True,  # Casey hears the loud hissing sound
)

SceneControl(
    id="ballast",
    label="BALLAST",
    npc_aware=True,  # Casey feels the submarine move
)

SceneControl(
    id="power",
    label="POWER",
    npc_aware=True,  # Casey sees power indicators light up
)
```

**Result**: Casey reacts to every button press.

```
Player clicks BALLAST
    ↓
[Control] BALLAST activated (shown to player)
    ↓
[SYSTEM EVENT] added to dialogue
    ↓
Casey: "Good! I can feel the pressure dropping!"
```

---

### 2. Crime Scene Investigation (Mixed Awareness)

**Context**: Detective is in another room. Player is examining evidence at the crime scene.

```python
# Detective CAN hear radio communication
SceneControl(
    id="call_backup",
    label="RADIO",
    npc_aware=True,  # Detective hears radio call
)

# Detective CANNOT see what player is examining
SceneControl(
    id="examine_evidence",
    label="EXAMINE",
    npc_aware=False,  # Player quietly examines without alerting detective
)

SceneControl(
    id="take_photo",
    label="CAMERA",
    npc_aware=False,  # Silent action, detective doesn't know
)

# Detective CAN hear door opening
SceneControl(
    id="open_door",
    label="DOOR",
    npc_aware=True,  # Makes noise, detective reacts
)
```

**Result**: Detective only reacts to radio and door.

```
Player clicks EXAMINE
    ↓
[Control] EXAMINE activated (shown to player)
    ↓
No notification to Detective
    ↓
Player continues investigating privately
```

```
Player clicks RADIO
    ↓
[Control] RADIO activated (shown to player)
    ↓
[SYSTEM EVENT] added to dialogue
    ↓
Detective: "Backup? What's going on out there?"
```

---

### 3. Hostage Negotiation (Mostly Hidden)

**Context**: Negotiator is on phone with suspect. Player (commander) makes tactical decisions suspect shouldn't know about.

```python
# Suspect CANNOT see tactical decisions
SceneControl(
    id="deploy_snipers",
    label="SNIPERS",
    npc_aware=False,  # Secret tactical decision
)

SceneControl(
    id="cut_power",
    label="POWER",
    npc_aware=False,  # Suspect doesn't know until power actually cuts
)

# Suspect CAN hear what's offered
SceneControl(
    id="offer_food",
    label="SEND FOOD",
    npc_aware=True,  # Negotiator communicates this offer
)

SceneControl(
    id="offer_transport",
    label="TRANSPORT",
    npc_aware=True,  # Negotiator communicates this offer
)
```

**Result**: Suspect only hears what negotiator tells them.

```
Player clicks DEPLOY_SNIPERS
    ↓
[Control] SNIPERS activated (shown to player)
    ↓
No notification to Suspect
    ↓
[Tactical advantage gained silently]
```

```
Player clicks OFFER_FOOD
    ↓
[Control] SEND FOOD activated (shown to player)
    ↓
[SYSTEM EVENT] added to dialogue
    ↓
Suspect: "Food? Alright... but I want the helicopter too!"
```

---

### 4. Medical Emergency (Partially Hidden)

**Context**: Surgeon is performing operation. Player (assistant) manages equipment.

```python
# Surgeon CAN see critical actions
SceneControl(
    id="defibrillator",
    label="DEFIB",
    npc_aware=True,  # Surgeon needs to know immediately
)

SceneControl(
    id="administer_drug",
    label="EPINEPHRINE",
    npc_aware=True,  # Surgeon needs to coordinate
)

# Surgeon DOESN'T need to know routine prep
SceneControl(
    id="check_vitals",
    label="VITALS",
    npc_aware=False,  # You're monitoring, surgeon is focused on surgery
)

SceneControl(
    id="adjust_lights",
    label="LIGHTS",
    npc_aware=False,  # Minor adjustment, don't distract surgeon
)
```

---

## Backend Logic Flow

### When Button is Pressed

```python
# web_server.py - handle_button_action()

1. Find control by label: "O2 VALVE"
2. Check control['npc_aware']

If npc_aware == True:
    - Add [SYSTEM EVENT] to dialogue history
    - Generate LLM response
    - Character reacts: "I can see the oxygen dropping!"
    - Send response to player

If npc_aware == False:
    - Log action
    - No dialogue history update
    - No LLM call
    - Character continues as if nothing happened
```

### Player Experience

**NPC Aware (True)**:
```
Player clicks button
    ↓
*beep* + visual flash
    ↓
[Control] BUTTON activated (chat message)
    ↓
Character types response...
    ↓
"I can see that! Good work!"
```

**NPC NOT Aware (False)**:
```
Player clicks button
    ↓
*beep* + visual flash
    ↓
[Control] BUTTON activated (chat message)
    ↓
[No character response]
    ↓
Player continues with hidden action completed
```

---

## Design Considerations

### When to Use npc_aware=True

- NPC is in same location and can see/hear
- Action makes noise/light/movement NPC would notice
- Action directly affects shared environment (submarine systems)
- Action involves communication (radio, phone)
- NPC has sensors/monitors showing the action

### When to Use npc_aware=False

- NPC is in different location
- Action is silent/discreet
- Player is examining something privately
- Action is internal thought/planning
- Action is behind NPC's back
- Player is secretly preparing something

### Mixed Awareness Example

**Bank Robbery Scene**:
- **Open vault door**: `npc_aware=True` (makes noise, robber hears)
- **Call 911 silently**: `npc_aware=False` (hidden from robber)
- **Trigger silent alarm**: `npc_aware=False` (robber doesn't know)
- **Grab gun**: `npc_aware=True` (visible movement, robber sees)

---

## Benefits

1. **Realism**: NPCs only react to what they could actually perceive
2. **Strategy**: Players can make hidden tactical decisions
3. **Tension**: Creates dramatic irony (player knows, NPC doesn't)
4. **Flexibility**: Same action type can be aware/unaware based on context
5. **Stealth**: Enables stealth/investigation scenarios

---

## Current Implementation

### Submarine Scene (scenes/submarine.py)

All controls have `npc_aware=True` because:
- Casey is in same vessel
- All systems are monitored from engine room
- Pressure/power changes are immediately felt
- Sound travels through submarine

```python
controls = [
    SceneControl(
        id="o2_valve",
        label="O2 VALVE",
        npc_aware=True,  # Casey sees oxygen gauges
    ),
    SceneControl(
        id="vent",
        label="VENT",
        npc_aware=True,  # Casey hears venting
    ),
    # ... all True
]
```

### Future Scenes

Can easily mix True/False based on scenario needs:

```python
# Investigation scene
controls = [
    SceneControl(label="EXAMINE BODY", npc_aware=False),     # Private
    SceneControl(label="CALL FOR HELP", npc_aware=True),     # Public
    SceneControl(label="TAKE SAMPLE", npc_aware=False),      # Private
    SceneControl(label="KNOCK ON DOOR", npc_aware=True),     # Public
]
```

---

## Testing npc_aware

### Future: Create Test Scene

```python
class TestScene(Scene):
    def __init__(self):
        controls = [
            SceneControl(
                id="visible_button",
                label="VISIBLE",
                npc_aware=True,
            ),
            SceneControl(
                id="hidden_button",
                label="HIDDEN",
                npc_aware=False,
            ),
        ]
        # ... rest of scene setup
```

Then in browser:
1. Click VISIBLE button → Character responds
2. Click HIDDEN button → No character response
3. Chat with character → They only know about VISIBLE button

---

## Summary

The `npc_aware` flag provides fine-grained control over NPC perception:

- **Submarine**: All controls visible (shared environment)
- **Investigation**: Some hidden (player examining privately)
- **Negotiation**: Most hidden (tactical decisions)
- **Combat**: Mixed (some actions visible, others strategic)

This creates realistic NPC reactions and enables strategic/stealth gameplay without requiring complex game logic - just set a boolean flag!

**Design Philosophy**: NPCs should only react to what they could realistically perceive in the scene context.
