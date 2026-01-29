# How to Create a New Character

This guide shows you how to add a custom character with their own backstory, personality, environment, and story to the web chat interface.

## Overview

Creating a character involves editing 3-4 files:
1. **`characters/mycharacter.py`** - Create a new character file (RECOMMENDED - Clean & Modular!)
2. **`characters/__init__.py`** - Register your character
3. **`web/index.html`** - Add character to the UI dropdown
4. **`web/js/app.js`** - Set character appearance (color)
5. **`scenes/myscene.py`** - Create custom story scenes (optional)

---

## Step 1: Create Your Character File (New Modular Way!)

### Create: `characters/pirate.py`

The easiest way is to copy an existing character file and modify it:

```python
"""
Captain Redbeard - Pirate Captain Character

A swashbuckling sailor of the high seas.
Personality: Gruff but caring, speaks in pirate dialect, loves adventure.
"""

from characters.base import Character


class Pirate(Character):
    """Captain Redbeard - Pirate Captain"""

    def __init__(self):
        super().__init__(
            id="pirate",
            name="Captain Redbeard",
            description="Pirate Captain - A swashbuckling sailor of the high seas",
            back_story="""You are Captain Redbeard, a notorious pirate captain who has sailed
            the seven seas for over 20 years. You speak in pirate dialect, using nautical terms
            like 'ahoy', 'matey', 'aye', and 'arr'. You have countless tales of adventure.
            You're gruff but have a heart of gold. You love rum, treasure, and a good story.
            You lost your eye in a battle with a sea monster and your ship, the Black Pearl,
            is your pride and joy. You're loyal to your crew and have a personal code of honor.
            Despite your rough exterior, you're wise and give good advice through stories
            of your adventures.""",
            instruction_prefix="You are playing the role of Captain Redbeard, a pirate captain.",
            color=0xff6b35,  # Orange/red - adventurous, warm
        )
```

### Step 2: Register Your Character

### File: `characters/__init__.py`

Add your character to the imports and registry:

```python
from characters.base import Character
from characters.eliza import Eliza
from characters.wizard import Wizard
from characters.detective import Detective
from characters.custom import Custom
from characters.pirate import Pirate  # ADD THIS

# Registry of all available characters
CHARACTERS = {
    'eliza': Eliza(),
    'wizard': Wizard(),
    'detective': Detective(),
    'custom': Custom(),
    'pirate': Pirate(),  # ADD THIS
}
```

That's it! Your character is now integrated. ✨

### Character Configuration Fields:

| Field | Description | Example |
|-------|-------------|---------|
| **Key** (`'pirate'`) | Unique ID (lowercase, no spaces) | `'pirate'`, `'knight'`, `'alien'` |
| **name** | Display name | `'Captain Redbeard'`, `'Sir Galahad'` |
| **description** | Short subtitle | `'Pirate Captain - Swashbuckling sailor'` |
| **back_story** | Full personality & context (can be long!) | Character's history, personality, speech style, motivations |
| **instruction_prefix** | LLM instruction | `'You are playing the role of...'` |

### Tips for Writing Backstory:

✅ **DO:**
- Be specific about personality traits
- Include how they speak (dialect, formality, etc.)
- Mention their motivations and goals
- Add memorable details (scars, catchphrases, quirks)
- Make it 3-5 sentences minimum

❌ **DON'T:**
- Be too vague ("You are a nice person")
- Forget to specify how they talk
- Make it too short (less detailed = more generic responses)

---

## Step 2: Add Character to the UI

### File: `web/index.html`

Find the character select dropdown (around line 39) and add your option:

```html
<select id="character-select">
    <option value="eliza">Eliza - AI Caretaker</option>
    <option value="wizard">Merlin - Wise Wizard</option>
    <option value="detective">Detective Stone</option>
    <option value="custom">Custom Character</option>

    <!-- ADD YOUR CHARACTER HERE: -->
    <option value="pirate">Captain Redbeard - Pirate Captain</option>
</select>
```

**Important:** The `value` must match the key you used in `web_server.py` (e.g., `'pirate'`)

---

## Step 3: Set Character Appearance (3D Model Color)

### File: `web/js/app.js`

Find the `changeCharacter()` method (around line 170) and add your character's info:

```javascript
changeCharacter(characterId) {
    this.currentCharacter = characterId;

    // Character names
    const characterNames = {
        'eliza': 'Eliza',
        'wizard': 'Merlin',
        'detective': 'Detective Stone',
        'custom': 'Custom Character',
        'pirate': 'Captain Redbeard',  // ADD THIS
    };

    // Character descriptions
    const characterDescriptions = {
        'eliza': 'AI Caretaker',
        'wizard': 'Wise Wizard',
        'detective': 'Hard-boiled Detective',
        'custom': 'Custom Character',
        'pirate': 'Pirate Captain',  // ADD THIS
    };

    // Character colors (hex values for the 3D model)
    const characterColors = {
        'eliza': 0x4fc3f7,      // Cyan
        'wizard': 0x9c27b0,     // Purple
        'detective': 0x795548,  // Brown
        'custom': 0x4caf50,     // Green
        'pirate': 0xff6b35,     // Orange/red  // ADD THIS
    };

    // ... rest of the function
}
```

### Color Reference:

| Color | Hex Value | Description |
|-------|-----------|-------------|
| Red | `0xff0000` | Bold, aggressive |
| Orange | `0xff6b35` | Warm, adventurous |
| Yellow | `0xffeb3b` | Bright, cheerful |
| Green | `0x4caf50` | Natural, calm |
| Cyan | `0x4fc3f7` | Tech, modern |
| Blue | `0x2196f3` | Cool, trustworthy |
| Purple | `0x9c27b0` | Mystical, royal |
| Pink | `0xe91e63` | Playful, energetic |
| Brown | `0x795548` | Earthy, grounded |
| Gray | `0x9e9e9e` | Neutral, robotic |

💡 **Tip:** Use an [HTML color picker](https://www.w3schools.com/colors/colors_picker.asp) to find hex colors, then convert to `0x` format.

---

## Step 4: Create Custom Story Scenes (Optional)

### Create: `scenes/treasure_hunt.py`

Like characters, scenes are now modular! Create a new file:

```python
"""
Treasure Hunt Scene

The pirate captain shares an ancient treasure map.
"""

from scenes.base import Scene
from llm_prompt_core.types import Line


class TreasureHunt(Scene):
    """Treasure Hunt - Seeking buried treasure"""

    def __init__(self):
        super().__init__(
            id="treasure_hunt",
            name="Treasure Hunt",
            description="The pirate captain shares a treasure map.",
            opening_speech=[
                Line(text="Ahoy there, matey! Look what I found!", delay=0),
                Line(text="This be an ancient treasure map from me grandfather.", delay=2.5),
                Line(text="Are ye brave enough to seek the treasure with me?", delay=5.0),
            ]
        )
```

### Register Your Scene

### File: `scenes/__init__.py`

```python
from scenes.base import Scene
from scenes.introduction import Introduction
from scenes.conversation import Conversation
from scenes.quest import Quest
from scenes.treasure_hunt import TreasureHunt  # ADD THIS

# Registry of all available scenes
SCENES = {
    'introduction': Introduction(),
    'conversation': Conversation(),
    'quest': Quest(),
    'treasure_hunt': TreasureHunt(),  # ADD THIS
}
```

### Scene Configuration:

| Field | Description |
|-------|-------------|
| **Key** (`'treasure_hunt'`) | Unique scene ID |
| **name** | Display name shown in UI |
| **description** | Context for the LLM about this scene |
| **opening_speech** | List of `Line` objects the character says when scene starts |

### Line Object:

```python
Line(text='What they say', delay=0)
```

- **text**: What the character says
- **delay**: Seconds to wait before showing this line (creates dramatic timing)

### Example Scene Structures:

**Quest Start:**
```python
'quest_start': {
    'name': 'Begin the Quest',
    'description': 'The knight asks for your help.',
    'opening_speech': [
        Line(text="Greetings, brave traveler!", delay=0),
        Line(text="The kingdom is in grave danger.", delay=2.0),
        Line(text="Will you aid me in this quest?", delay=4.0),
    ]
}
```

**Crisis Moment:**
```python
'ship_sinking': {
    'name': 'Ship is Sinking',
    'description': 'Emergency - the ship has been damaged and is taking on water.',
    'opening_speech': [
        Line(text="Blast! We've hit rocks!", delay=0),
        Line(text="All hands on deck! The ship be sinkin'!", delay=1.5),
        Line(text="Quick, help me patch the hull!", delay=3.0),
    ]
}
```

### Add Scene to UI:

Edit `web/index.html` (around line 44):

```html
<select id="scene-select">
    <option value="introduction">Introduction</option>
    <option value="conversation">General Conversation</option>
    <option value="quest">Quest Beginning</option>

    <!-- ADD YOUR SCENE: -->
    <option value="treasure_hunt">Treasure Hunt</option>
</select>
```

---

## Complete Example: Creating a Space Explorer Character

### 1. Add to `web_server.py` CHARACTERS:

```python
'astronaut': {
    'name': 'Commander Nova',
    'description': 'Space Explorer - Veteran astronaut on a deep space mission',
    'back_story': '''You are Commander Nova, a veteran astronaut on a deep space
    exploration mission. You've been traveling through the cosmos for 5 years,
    studying alien planets and cosmic phenomena. You speak with calm professionalism
    but occasionally show excitement about scientific discoveries. You miss Earth
    but are dedicated to your mission. You love astronomy, physics, and sharing
    stories about the wonders of space. You're thoughtful, intelligent, and have
    a dry sense of humor.''',
    'instruction_prefix': 'You are playing the role of Commander Nova, a space explorer.',
},
```

### 2. Add to `web_server.py` SCENES:

```python
'alien_planet': {
    'name': 'Alien Planet Discovery',
    'description': 'The explorer has just landed on a mysterious alien world.',
    'opening_speech': [
        Line(text="Houston, we've touched down on the planet's surface.", delay=0),
        Line(text="The atmosphere is breathable, and... wait.", delay=3.0),
        Line(text="I'm detecting unusual energy readings nearby.", delay=5.5),
        Line(text="This planet might not be as uninhabited as we thought.", delay=8.0),
    ]
},
```

### 3. Add to `web/index.html`:

```html
<!-- In character-select -->
<option value="astronaut">Commander Nova - Space Explorer</option>

<!-- In scene-select -->
<option value="alien_planet">Alien Planet Discovery</option>
```

### 4. Add to `web/js/app.js`:

```javascript
// In characterNames:
'astronaut': 'Commander Nova',

// In characterDescriptions:
'astronaut': 'Space Explorer',

// In characterColors:
'astronaut': 0x1e88e5,  // Deep space blue
```

---

## Testing Your Character

1. **Stop the server** (Ctrl+C)

2. **Restart the server:**
   ```bash
   ./start-web.sh
   ```

3. **Refresh your browser** (F5 or Cmd+R)

4. **Open Settings** (⚙️ icon)

5. **Select your new character** from the dropdown

6. **Try different scenes** if you created custom ones

7. **Chat with your character!**

---

## Advanced: Using the Full Prompt System

The simple method above works great for most cases. But if you want full control over the prompt system, you can use `llm_prompt_core` directly:

### Create Scene Data Files

Instead of defining scenes in `web_server.py`, you can create a full scene directory:

```
project_one_demo/prompts/
└── my_characters/
    └── scenes/
        └── 1_first_meeting/
            ├── scene_description.txt
            ├── opening_speech.txt
            ├── queries.txt
            ├── back_story.txt
            └── prev_scenes_description.txt
```

See `project_one_demo/prompts/act_1/scenes/` for examples.

### Scene File Formats:

**back_story.txt:**
```
You are Captain Redbeard, a notorious pirate captain. You speak in
pirate dialect and have countless tales of adventure.
```

**scene_description.txt:**
```
You are on the deck of your ship, the Black Pearl. The sea is calm
and the sun is setting. You're examining an old treasure map.
```

**opening_speech.txt:**
```
[0] Ahoy there, matey!
[2.5] I've got something special to show ye.
[5.0] This map leads to the greatest treasure ever buried!
```

**queries.txt:**
```
The player has agreed to join the treasure hunt
[quest_started=true]
(Excellent! We set sail at dawn., Keep thinkin' about it...)

The player has asked about the sea monster
[monster_revealed=true]
(Aye, there be a fearsome beast guardin' the treasure., )
```

See [`llm_prompt_core/README.md`](llm_prompt_core/README.md) for full documentation.

---

## Troubleshooting

**Character not appearing in dropdown:**
- Check that you added it to `web/index.html`
- Make sure the `value` attribute matches the key in `web_server.py`
- Refresh your browser

**Character responds but personality is generic:**
- Make your `back_story` more detailed and specific
- Include how they speak (dialect, formality, etc.)
- Add more personality traits and quirks

**Character color not changing:**
- Verify you added the color to `characterColors` in `web/js/app.js`
- Make sure the hex value starts with `0x` not `#`
- Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)

**Character says strange things:**
- Check your `back_story` for conflicting instructions
- Make sure `instruction_prefix` matches the role
- Try lowering the temperature in `web_server.py` (line 30) for more focused responses

---

## Tips for Great Characters

### Personality Design:

✅ **Give them quirks:**
- Catchphrases ("Arr, matey!" / "By Jove!" / "Fascinating...")
- Speech patterns (formal, casual, dialect)
- Habits or mannerisms

✅ **Give them depth:**
- Backstory (where they come from, what they've experienced)
- Motivations (what drives them)
- Flaws (what makes them human/interesting)
- Relationships (who they care about)

✅ **Give them expertise:**
- Specific knowledge domains
- Skills and abilities
- Things they're passionate about

### Story/Scene Design:

✅ **Start with conflict or intrigue:**
```python
Line(text="We have a problem.", delay=0)
Line(text="The ancient curse has awakened.", delay=2.0)
```

✅ **Use dramatic timing:**
```python
Line(text="I have something to tell you...", delay=0)
Line(text="...", delay=2.0)  # Dramatic pause
Line(text="The prophecy was about YOU.", delay=4.0)
```

✅ **End with a question or hook:**
```python
Line(text="So, will you help me?", delay=0)
```

---

## Need Help?

- Check the [Web Interface README](web/README.md) for UI customization
- See [llm_prompt_core README](llm_prompt_core/README.md) for advanced prompt engineering
- Look at existing characters in `web_server.py` for examples
- Experiment! The system is very flexible.

---

## Quick Reference Checklist

When creating a new character:

- [ ] Add character config to `web_server.py` CHARACTERS dictionary
- [ ] Add character to dropdown in `web/index.html`
- [ ] Add character name, description, and color to `web/js/app.js`
- [ ] (Optional) Create custom scenes in `web_server.py` SCENES dictionary
- [ ] (Optional) Add scenes to dropdown in `web/index.html`
- [ ] Restart server with `./start-web.sh`
- [ ] Refresh browser and test your character!

Happy character creating! 🎭
