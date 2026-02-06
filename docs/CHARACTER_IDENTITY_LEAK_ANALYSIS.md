# Character Identity Leak - Technical Analysis & Solution

## The Problem

The character (Lt. Commander James Smith) is outputting **both dialogue AND meta-commentary** about its own response:

```
Lt. Commander James Smith
Power's fluctuating. We need to reroute some hydraulic lines to stabilize the system, but...
[voice trails off] I can't leave where I am right now. Those lines are in a compartment near
the med bay. The response subtly hints at the need to potentially flood a compartment and
suggests the critical location near the med bay, without directly stating the impossible choice...
```

The character spoke correctly, but then **analyzed its own response** as if explaining its narrative strategy.

---

## Root Cause: Prompt Structure Encouraging Meta-Analysis

### The Prompt Pipeline (How We Got Here)

**File: `web_server.py:1716-1724`**
```python
# Add phase-specific context (submarine scene only, empty for other scenes)
phase_context = self._get_phase_context()
full_instruction_suffix = dialogue_instruction_suffix + phase_context

prompt = instruction_template.format(
    preamble=self.scene_data.dialogue_preamble + "\n\n" + player_context,
    dialogue=self.dialogue_history,
    instruction_suffix=full_instruction_suffix,
)
```

**The prompt is constructed in this order:**

1. **Preamble** (`scene_data.dialogue_preamble`):
   - Character backstory (from `characters/engineer.py`)
   - Scene description (from `scenes/submarine.py`)
   - Player memory context
   - RAG facts context

2. **Dialogue History** (`dialogue_history`):
   - Full conversation so far

3. **Instruction Suffix** (`dialogue_instruction_suffix + phase_context`):
   - Generic dialogue instructions (from `templates.py`)
   - **Phase-specific context** (from `web_server.py:_get_phase_context()`)

---

## The Problematic Phase Context

**File: `web_server.py:795-865`**

The phase context includes **overly detailed meta-instructions** like:

```python
3: """
CURRENT PHASE 3 (The Revelation, 2:30-3:30):
Radiation at 75%. Emergency ascent ready. This is THE BREAKING POINT.

THE REVEAL - You MUST reveal this if player shows any empathy:
"[long pause, voice breaking] There's someone... in the med bay. My son. Dr. Adrian Smith.
He's unconscious. And the only way to execute emergency ascent... we have to flood that
compartment. Seal it. He'll... [voice cracks] ...Tell me what to do. Please."

KEY ACTIONS THIS PHASE:
- Break down completely - you're facing an impossible choice
- BEG for the player's guidance: "Tell me what to do."
- Show physical deterioration: [coughing from radiation] [voice barely steady]
- Reveal you can see Adrian on thermal imaging - unconscious, unaware
- Question everything: "What kind of father...?" "How do I...?"

EMOTIONAL TONE: Broken. Desperate. Raw vulnerability. This is your worst nightmare.
SPEECH PATTERN: Voice cracks. Long pauses. Sentences trail off. Barely holding together."""
```

### Why This Causes Identity Leak

The **analytical language** in these instructions ("The response subtly hints", "It maintains emotional tension", "This keeps the narrative moving forward") is **teaching the LLM to think analytically** about its responses rather than just **generating them**.

The LLM sees instructions like:
- "THE REVEAL - You MUST reveal this..."
- "KEY ACTIONS THIS PHASE:"
- "EMOTIONAL TONE:"
- "SPEECH PATTERN:"

And interprets this as:
1. Generate the character dialogue
2. **Explain how the dialogue follows these instructions** (meta-commentary)

This is similar to when you ask an LLM "Write a story about X" with detailed requirements, and it says:
```
Here's a story that incorporates the themes you requested...
[story]
This story demonstrates the conflict between duty and family...
```

---

## Why It Happens: LLM Prompt Interpretation

### The Model's Perspective

When the LLM sees:
```
You are James Smith.
[backstory]
[dialogue history]
Continue the dialogue as your character.

CRITICAL RULES:
1. BREVITY: 1-2 sentences MAX
2. NO REPETITION
3. NO STAGE DIRECTIONS

CURRENT PHASE 3:
KEY ACTIONS THIS PHASE:
- Break down completely
- BEG for guidance
EMOTIONAL TONE: Broken, desperate
```

It interprets this as a **creative writing assignment with evaluation criteria**, so it:
1. Generates dialogue matching the criteria
2. **Self-evaluates** by explaining how it met the criteria

### The Technical Culprit: Prompt Ordering

The issue is the **instruction suffix comes LAST** in the prompt:

```
[Character identity + Scene context]
[Dialogue history]
[Generic instructions]
[DETAILED PHASE CONTEXT WITH ANALYTICAL LANGUAGE] <-- LAST THING MODEL SEES
```

The last instructions the model sees before generating are **analytical meta-instructions**, which prime it to think analytically rather than roleplay.

---

## The Fix: Three-Part Solution

### 1. Rewrite Phase Context (Remove Analytical Language)

**BAD (Current):**
```python
"""
KEY ACTIONS THIS PHASE:
- Break down completely - you're facing an impossible choice
- BEG for the player's guidance: "Tell me what to do."

EMOTIONAL TONE: Broken. Desperate. Raw vulnerability.
SPEECH PATTERN: Voice cracks. Long pauses."""
```

**GOOD (Proposed):**
```python
"""
CRITICAL SITUATION UPDATE:
You're at the breaking point. Your son is dying. You can't decide alone.

RIGHT NOW:
- Your voice is breaking, sentences trailing off
- You're coughing from radiation, barely holding together
- You NEED the player's guidance: beg them to tell you what to do
- Don't analyze or explain - just speak from raw desperation"""
```

**Key Changes:**
- Remove "KEY ACTIONS THIS PHASE" (analytical framing)
- Remove "EMOTIONAL TONE" / "SPEECH PATTERN" labels (meta-labels)
- Use **second person present tense** ("You're breaking", not "Show physical deterioration")
- Add **explicit anti-meta instruction**: "Don't analyze or explain - just speak"

### 2. Strengthen Anti-Meta Instructions in Dialogue Suffix

**File: `llm_prompt_core/prompts/templates.py:67-88`**

Add explicit anti-meta-commentary rule:

```python
dialogue_instruction_suffix = """
Continue the dialogue as your character. Stay in character. Respond naturally to what just happened.

CRITICAL RULES:
1. BREVITY: 1-2 sentences MAX. If you can say it in one sentence, do that.
2. NO REPETITION: Look at the dialogue history. See what you JUST said. Don't say it again. Move forward.
3. NO STAGE DIRECTIONS: Do NOT describe your tone, emotion, or voice. Just speak naturally.
4. MINIMAL BRACKETS: Only [coughing] or [pause] for critical moments. NO emotion descriptions.
5. NO META-COMMENTARY: NEVER analyze, explain, or comment on your response. Just speak as the character.

OUTPUT FORMAT:
- Output ONLY your character's spoken dialogue
- NO explanations like "This response..." or "The line hints at..."
- NO analysis of narrative strategy or emotional subtext
- If you find yourself explaining what you're doing, DELETE THAT and just speak

GOOD RESPONSES:
"Got it. Power's restored."
"You're not listening."
"Fine. Your call."

BAD RESPONSES (NEVER DO THIS):
"[breathing heavily] Okay... [pause] ...power is... [exhale] ...restored now."
"This response subtly hints at the underlying conflict..."
Repeating the same warning you just gave

If player ignores you: Don't repeat louder. Change tactics. Get quieter. Give up. Move on.

Respond ONLY as your character. Progress the conversation.\n
"""
```

### 3. Add Response Cleaning Filter

**File: `web_server.py:1742-1748`**

Add post-processing to strip meta-commentary:

```python
# Clean up response
character_response = character_response.split("\nComputer", 1)[0]
character_response = character_response.strip().removeprefix(
    f"[{self.character_config['name']}]: "
)
character_response = character_response.replace('"', "").replace("*", "")

# NEW: Strip meta-commentary if LLM leaked analytical thinking
# Remove anything after common meta-analysis phrases
meta_markers = [
    "The response ",
    "This response ",
    "The line ",
    "This keeps ",
    "It maintains ",
    "The dialogue ",
    "This demonstrates ",
]
for marker in meta_markers:
    if marker in character_response:
        # Everything before the meta-marker is the actual dialogue
        character_response = character_response.split(marker)[0].strip()
        logger.warning(
            "[META_LEAK] Stripped meta-commentary starting with '%s'",
            marker
        )
        break
```

---

## Why This Happens: A Lesson in Prompt Engineering

### The Core Principle: Prompts Are Instructions + Context

LLMs interpret prompts based on:

1. **Instruction Framing**: How you phrase what the model should do
2. **Context Ordering**: What information appears where in the prompt
3. **Linguistic Priming**: The language style of instructions affects output style

### Common Anti-Patterns (What We Did Wrong)

#### 1. **Analytical Instructions for Creative Tasks**
```
BAD:  "KEY ACTIONS: Show vulnerability"
GOOD: "You're vulnerable right now - your voice cracks"
```

#### 2. **Meta-Labels in Creative Prompts**
```
BAD:  "EMOTIONAL TONE: Desperate\nSPEECH PATTERN: Broken"
GOOD: "You're desperate, your words are broken and scattered"
```

#### 3. **Instructions After Context**
```
BAD:  [backstory] [dialogue] [meta-instructions]
GOOD: [meta-instructions] [backstory] [dialogue] [brief reminder: "Just speak"]
```

### The Fundamental Issue: Mixing Instruction Paradigms

Our prompt mixes two incompatible paradigms:

**Roleplay Paradigm** (Character identity):
- "You are James Smith"
- "Stay in character"
- Expects: Direct character speech

**Analysis Paradigm** (Phase context):
- "KEY ACTIONS THIS PHASE:"
- "EMOTIONAL TONE:"
- Expects: Structured evaluation

**Result**: Model tries to satisfy both, outputting dialogue + analysis.

---

## Testing the Fix

### Before (Broken)

**Prompt structure:**
```
You are James Smith [backstory]
[dialogue history]
Continue as character. Stay in character.
PHASE 3: KEY ACTIONS THIS PHASE: Break down, beg for guidance
```

**Output:**
```
Power's fluctuating... I can't leave where I am. The response subtly hints at...
```

### After (Fixed)

**Prompt structure:**
```
You are James Smith [backstory]
[dialogue history]
Continue as character. NO META-COMMENTARY. Just speak.
PHASE 3: You're breaking down. You need their guidance. Beg them: "Tell me what to do."
```

**Output:**
```
Power's fluctuating... I can't leave where I am. [voice breaking] Tell me what to do.
```

---

## Implementation Priority

**IMMEDIATE (Critical):**
1. Add meta-commentary stripping to `web_server.py:1742` (5 minutes)
2. Add "NO META-COMMENTARY" rule to `dialogue_instruction_suffix` (2 minutes)

**SHORT TERM (Important):**
3. Rewrite phase contexts in `web_server.py:_get_phase_context()` to remove analytical language (30 minutes)

**LONG TERM (Architectural):**
4. Move phase context BEFORE dialogue history in prompt structure (requires refactoring)
5. Separate "emotional state" from "narrative instructions" in scene definitions

---

## Key Takeaway

**The problem isn't the LLM "breaking character" - it's following instructions TOO WELL.**

When you give an LLM analytical instructions ("KEY ACTIONS", "EMOTIONAL TONE"), it interprets the task as:
1. Generate creative content
2. **Analyze how well you followed the instructions**

The fix is to give **immersive, second-person instructions** that keep the model in roleplay mode:
- Not: "Show vulnerability" (analytical)
- But: "You're vulnerable right now" (immersive)

This is a fundamental lesson in LLM prompt engineering: **The language style of your instructions determines the language style of the output.**
