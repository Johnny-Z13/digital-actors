# Scene Architecture Documentation

## Overview

The Digital Actors scene system has been enhanced to support fully self-contained, data-driven scenes with controls, state management, success/failure criteria, character requirements, and audio/visual assets.

## Scene Data Structure

### Base Components

Every scene inherits from `scenes/base.py` and can define the following:

#### 1. **SceneControl** - User Controls
Define interactive elements (buttons, levers, dials):

```python
SceneControl(
    id="o2_valve",
    label="O2 VALVE",
    type="button",  # "button", "lever", "dial", "switch"
    color=0xff3333,  # Hex color
    position={'x': -0.4, 'y': 0.2, 'z': 0},
    description="What this control does",
    action_type="critical"  # "critical", "dangerous", "safe", "normal"
)
```

#### 2. **StateVariable** - Scene State Tracking
Track dynamic values during the scene:

```python
StateVariable(
    name="oxygen",
    initial_value=180.0,  # 3 minutes
    min_value=0.0,
    max_value=180.0,
    update_rate=-1.0  # Auto-decreases by 1 per second
)
```

Common state variables:
- `oxygen`: Remaining oxygen/time
- `trust`: Trust level with character (0-100)
- `systems_repaired`: Number of systems fixed
- `correct_actions`: Player successes
- `incorrect_actions`: Player mistakes

#### 3. **SuccessCriterion** - Win Conditions
Define what constitutes success:

```python
SuccessCriterion(
    id="full_success",
    description="Full trust with systems restored",
    condition="state['oxygen'] > 0 and state['trust'] >= 80 and state['systems_repaired'] >= 3",
    message="You trusted me. That's what saved us!",
    required=True  # Must be met to win
)
```

#### 4. **FailureCriterion** - Failure Conditions
Define ways the player can fail:

```python
FailureCriterion(
    id="oxygen_depleted",
    description="Ran out of oxygen",
    condition="state['oxygen'] <= 0",
    message="*static* ...I can't... breathe... *signal lost*",
    ending_type="death"  # Categorize failure type
)
```

#### 5. **CharacterRequirement** - Skill Requirements
Specify what expertise characters need:

```python
CharacterRequirement(
    skill="submarine_engineering",
    importance="required",  # "required", "recommended", "helpful"
    impact_without="Will not know which controls to press. High chance of failure.",
    alternative_path=False  # Can the scene be completed without this skill?
)
```

**Key Concept**: Any character can attempt any scene, but characters without required skills should:
- Show uncertainty in dialogue
- Make poor decisions
- Likely fail the scene
- Ask player for help/ideas

Example:
- **Casey (Engineer)** in submarine: Knows exact button sequence, confident
- **Merlin (Wizard)** in submarine: "I know not these arcane devices! Perhaps... this glowing rune?" → probably fails

#### 6. **SceneArtAssets** - Visual and Audio Assets

```python
SceneArtAssets(
    scene_type="submarine",  # "character", "submarine", "custom"
    custom_scene_file="/js/submarine_scene.js",
    ui_elements={
        'oxygen_gauge': '/images/ui/oxygen_gauge.png',
        'intercom': '/images/ui/intercom.png',
    },
    audio=AudioAssets(
        background_music="/audio/submarine_ambient.mp3",
        sfx_library={
            'button_press': '/audio/sfx/button_press.mp3',
            'alarm': '/audio/sfx/alarm.mp3',
            'success_chime': '/audio/sfx/success.mp3',
            # ... more sound effects
        },
        volume_levels={
            'music': 0.3,
            'sfx': 0.7,
            'voice': 1.0
        }
    )
)
```

### Audio System (SFX Library)

Each scene defines its sound effect library. Common events:
- `button_press`: When player clicks controls
- `alarm`: Danger warnings
- `success_chime`: Achievement sounds
- `failure_alarm`: Failure sounds
- `ambient_loop`: Background atmosphere

Sound effects are mapped to game events and played automatically when those events occur.

## Creating a New Scene

### Example: Spaceship Bridge Emergency

```python
from scenes.base import (
    Scene, SceneControl, StateVariable, SuccessCriterion,
    FailureCriterion, CharacterRequirement, SceneArtAssets, AudioAssets
)
from llm_prompt_core.types import Line

class SpaceshipBridge(Scene):
    def __init__(self):
        # Define audio
        audio = AudioAssets(
            background_music="/audio/spaceship_ambient.mp3",
            sfx_library={
                'shields_up': '/audio/sfx/shields.mp3',
                'engine_boost': '/audio/sfx/engine.mp3',
                'weapons_fire': '/audio/sfx/laser.mp3',
                'explosion': '/audio/sfx/explosion.mp3',
            }
        )

        art_assets = SceneArtAssets(
            scene_type="spaceship",
            custom_scene_file="/js/spaceship_scene.js",
            audio=audio
        )

        # Define controls
        controls = [
            SceneControl(
                id="shields",
                label="SHIELDS",
                color=0x0088ff,
                description="Activate defensive shields"
            ),
            SceneControl(
                id="weapons",
                label="WEAPONS",
                color=0xff0000,
                description="Fire weapons systems"
            ),
        ]

        # Define state
        state_variables = [
            StateVariable(name="hull_integrity", initial_value=100.0, min_value=0, max_value=100),
            StateVariable(name="enemy_distance", initial_value=1000.0, update_rate=-10),  # Gets closer
        ]

        # Define success
        success_criteria = [
            SuccessCriterion(
                id="survived_attack",
                condition="state['hull_integrity'] > 20 and state['enemy_distance'] <= 0",
                message="Enemy ship destroyed! We made it!"
            )
        ]

        # Define failure
        failure_criteria = [
            FailureCriterion(
                id="hull_breach",
                condition="state['hull_integrity'] <= 0",
                message="Hull breach detected! Evacuate! *explosion*"
            )
        ]

        # Define requirements
        character_requirements = [
            CharacterRequirement(
                skill="starship_command",
                importance="required",
                impact_without="Won't know tactical procedures. Likely to be destroyed."
            )
        ]

        super().__init__(
            id="spaceship_bridge",
            name="Spaceship Bridge Emergency",
            description="Enemy ship attacking! Coordinate with the character to survive.",
            opening_speech=[
                Line(text="Captain! Enemy ship on sensors!", delay=0),
                Line(text="They're charging weapons! What are your orders?", delay=2),
            ],
            art_assets=art_assets,
            controls=controls,
            state_variables=state_variables,
            success_criteria=success_criteria,
            failure_criteria=failure_criteria,
            character_requirements=character_requirements,
            time_limit=120.0,  # 2 minutes
            allow_freeform_dialogue=True
        )
```

## Character Skills System

Characters define their skills in `characters/[name].py`:

```python
class Engineer(Character):
    def __init__(self):
        super().__init__(
            id="engineer",
            name="Casey Reeves",
            skills=[
                "submarine_engineering",
                "crisis_management",
                "technical_communication",
                "mechanical_systems"
            ],
            back_story="...",
            # ... other attributes
        )
```

### Skill Checking

The system automatically checks character compatibility:

```python
# In web_server.py or scene logic
character_has_skill = character.has_skill("submarine_engineering")

if not character_has_skill:
    # Character will struggle, make mistakes, show uncertainty
    # Scene description should inform LLM of character's lack of expertise
```

The LLM receives information about missing skills in the scene description, allowing it to roleplay appropriately:
- Confident if they have the skill
- Uncertain/guessing if they don't
- Might ask player for advice
- Higher chance of incorrect actions

## Mouse Look Controls

Each scene can specify camera/mouse look settings:

**Submarine Scene** (current default):
- ~100 degree field of view
- ±50 degrees horizontal (left/right)
- ±50 degrees vertical (up/down)
- No zoom or pan - only rotation
- Medium sensitivity (0.5)

Future scenes can customize these values in their 3D scene file.

**Future WASD Support**: Planned for scenes that allow full movement (exploration, walking around).

## Scene Flow Example

### Submarine Emergency (Iron Lung) Flow

1. **Scene loads** with oxygen at 180 seconds
2. **Casey's opening speech** plays with typing animation
3. **Player can**:
   - Chat naturally with Casey
   - Look around (±50° in all directions)
   - Click control buttons
4. **State updates**:
   - Oxygen decreases automatically (-1/sec)
   - Trust increases/decreases based on dialogue and actions
   - Systems repair counter updates when correct sequence followed
5. **Button presses**:
   - Sent to backend as `[SYSTEM EVENT]`
   - Casey reacts immediately
   - State variables update
6. **Condition checking** (every second):
   - Check failure conditions first
   - Check success conditions
   - If either met, end scene with appropriate message
7. **Endings**:
   - **Success**: "You trusted me. That's what saved us!"
   - **Partial**: "We survived, barely..."
   - **Failure**: "*static* ...I can't... breathe... *signal lost*"

## Integration with Web Server

The web server (`web_server.py`) handles:
- Scene state tracking
- Condition evaluation
- Button action processing
- Success/failure detection
- Character skill checking
- Audio event triggering

The frontend (`web/js/app.js`) handles:
- Typing animation for character messages
- Button click feedback
- Scene state display
- Audio playback (when implemented)

## Example Scenes

### 1. Submarine Emergency (Implemented)
- **Type**: Survival/Crisis
- **Controls**: 4 buttons (O2 Valve, Vent, Ballast, Power)
- **Required Skill**: submarine_engineering
- **Time Limit**: 3 minutes
- **Success**: All systems repaired, high trust, oxygen remaining
- **SFX**: Alarms, button clicks, venting, radio static

### 2. Possible Future Scenes

**Hostage Negotiation**:
- Skill: negotiation, psychology
- Controls: Offer options (Release hostages, Send food, etc.)
- State: Hostage stress, negotiator trust, time remaining
- Success: Hostages freed, suspect surrenders
- SFX: Phone rings, crowd noise, police radio

**Medical Emergency**:
- Skill: medical_knowledge, surgery
- Controls: Medical tools/procedures
- State: Patient vitals, bleeding, time to critical
- Success: Patient stabilized
- SFX: Heart monitor, medical equipment, emergency sounds

**Bomb Disposal**:
- Skill: explosives, electronics
- Controls: Wire cutters, tools
- State: Timer, correct wires cut, mistakes made
- Success: Bomb defused
- SFX: Ticking, beeps, cutting wires, explosion (if failed)

## Best Practices

1. **Character Requirements**: Always define what skills characters should have, but allow any character to attempt the scene
2. **Multiple Endings**: Define at least 2-3 success/failure states for variety
3. **Audio Mapping**: Map sounds to specific game events for immersion
4. **State Variables**: Track everything that affects success/failure
5. **Control Descriptions**: Make control purposes clear to inform player decisions
6. **Time Pressure**: Use for dramatic effect, but allow reasonable time to think
7. **Trust Mechanics**: Reward cooperation, punish rushing or ignoring advice

## File Structure

```
digital-actors/
├── scenes/
│   ├── base.py                 # Enhanced scene classes
│   ├── submarine.py            # Submarine emergency scene
│   ├── introduction.py         # Simple intro scene
│   └── [new_scene].py          # Your new scene
├── characters/
│   ├── base.py                 # Character class with skills
│   ├── engineer.py             # Casey (has submarine skills)
│   └── [character].py          # Other characters
├── web/
│   ├── js/
│   │   ├── submarine_scene.js  # Submarine 3D scene
│   │   └── scene.js            # Default character scene
│   └── audio/
│       ├── sfx/                # Sound effects library
│       └── music/              # Background music
└── web_server.py               # Backend scene management
```

## Testing Your Scene

```bash
# Test scene loads correctly
python3 -c "from scenes.your_scene import YourScene; s = YourScene(); print(s)"

# Test character skills
python3 -c "from characters import CHARACTERS; print(CHARACTERS['engineer'].skills)"

# Start server and test in browser
./start-web.sh
# Open http://localhost:8080
```

## Summary

The enhanced scene architecture provides:
- ✅ Self-contained scene definitions
- ✅ Dynamic control systems
- ✅ State tracking and condition evaluation
- ✅ Character skill requirements
- ✅ Success/failure criteria
- ✅ Audio/visual asset mapping
- ✅ Any character can attempt any scene (with consequences)
- ✅ Mouse look controls (~100° FOV)
- ✅ Typing animation for immersion

This makes it easy to create new scenarios without touching core code!
