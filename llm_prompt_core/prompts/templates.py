"""
Prompt templates for character dialogue generation.

This module contains all the template strings used to construct prompts for
dialogue generation, queries, summaries, and merging operations.
"""

# Basic preamble template for dialogue generation
preamble_template = """
{instruction_prefix}
This is the game back story. {back_story}\n
Here is a description of the scene in question. {previous_scenes_description}\n{scene_description}\n {steer_back_instructions}\n{scene_supplement}\n
The characters in the dialogue are {actors}.\n\n
"""

# Preamble template for query evaluation
query_preamble_template = """
{instruction_prefix}
This is the game back story. {back_story}\n
The characters in the dialogue are {actors}.\n\n
"""

# Extended preamble template with dialogue summary
preamble_plus_template = """
{instruction_prefix}
This is the game back story. {back_story}\n\n
Here is a summary of the script from previous scenes. {previous_scenes_description}\n\n
Here's a summary of information acquired from dialogues earlier in the game. The non-playable characters should make use of this information where appropriate to bond with the player. {dialogue_summary}\n\n
Here is a description of the scene in question. {scene_description}\n{steer_back_instructions}\n{scene_supplement}\n\n
The characters in the dialogue are {actors}.\n\n
"""

# Preamble template for merging summaries
merge_preamble_template = """
{instruction_prefix}
This is the game back story. {back_story}\n\n
Here is a summary of the script from previous scenes. {previous_scenes_description}\n\n
"""

# Instruction template for merging summaries
merge_instruction_template = """
{preamble}
Here is the first summary:\n
{prev_summary} \n\n
Here is the second summary:\n
{new_summary} \n\n
{instruction_suffix}
"""

# Suffix instruction for merging summaries
merge_instruction_suffix = """
Give me a paragraph merging the information from the two summaries above. The second summary details what happened just after the first summary. Your objective is to eliminate duplicities and redundancy. Do not omit any biographical information, tastes and preferences from the player or the other characters. Keep the information about events that might have happened in the dialogue that are not mentioned in the back story and scene description above. Keep any description of how the non-playable characters typically address the player (or any evolution of this description if it changes). Provide only the summary paragraph, no other text.\n
"""

# Main instruction template combining preamble, dialogue, and suffix
instruction_template = """
{preamble}
Here is the dialogue so far:\n
{dialogue}
{instruction_suffix}
"""

# Template for formatting individual speech lines
speech_template = "[{actor}]: {speech}\n"

# Instruction suffix for dialogue generation
dialogue_instruction_suffix = """
Continue the dialogue as your character. Stay in character. Respond naturally to what just happened.

CRITICAL RULES:
1. BREVITY: 1-2 sentences MAX. If you can say it in one sentence, do that.
2. NO REPETITION: Look at the dialogue history. See what you JUST said. Don't say it again. Move forward.
3. NO STAGE DIRECTIONS: Do NOT describe your tone, emotion, or voice. Just speak naturally.
4. MINIMAL BRACKETS: Only [coughing] or [pause] for critical moments. NO emotion descriptions.
5. NO META-COMMENTARY: NEVER analyze, explain, or describe your response. Just speak as the character.

OUTPUT FORMAT:
- Output ONLY your character's spoken dialogue
- NO explanations like "This response..." or "The line hints at..."
- NO analysis of narrative strategy or emotional subtext
- If you catch yourself explaining what you're doing, STOP and just speak

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

# Instruction prefix for query evaluation
query_instruction_prefix = """
You are going to answer a single question about the current state of the dialogue in a scene in the middle of a computer game.\n
"""

# Instruction suffix template for query evaluation
query_instruction_suffix_template = """
Now consider the following statement about this dialogue. {statement} Is this statement true or false? Answer with a single word, true or false.\n
"""

# Instruction suffix for summary generation
summary_instruction_suffix = """
Give me a short paragraph summarising any information in the dialogue revealed by the player or the other characters that might be relevant for later dialogues. Include all personal or biographical information revealed in the dialogue that helps to build a profile of the characters, including informations about their tastes and preferences. Also describe any events that have occurred that weren't mentioned in the back story and scene description above. Include a description of how the non-playable characters typically address the player. You don't need to provide information that's already in the back story or scene description above. Please provide only the summary paragraph, no other text.\n
"""

# Turn-type instruction template for context-aware responses
turn_type_instruction_template = """
Consider what the player just said:
- If they asked a QUESTION: Answer it directly, then you may add one follow-up thought.
- If they made a STATEMENT: Acknowledge it briefly, then move the conversation forward.
- If they took an ACTION: React to the action's result, guide next steps if needed.
- If they're SILENT/IDLE: Prompt them gently or continue your thought.
- If they expressed EMOTION: Respond with appropriate empathy, acknowledge their feelings.

Do NOT repeat yourself. If you just said something, say something different.
Progress the conversation. Keep it moving.
"""

# Turn-type specific instruction suffixes (can be appended based on detected turn type)
turn_type_instructions = {
    "question": """
The player asked a QUESTION. Answer it DIRECTLY and CONCISELY.
You may add ONE brief follow-up thought after answering.
Do not deflect or avoid the question.
""",
    "statement": """
The player made a STATEMENT. Acknowledge it BRIEFLY (1-2 words is fine).
Then move the conversation FORWARD - don't dwell on what they said.
""",
    "action": """
The player took an ACTION. React to the RESULT of their action.
Guide them on next steps if needed. Be specific about what happened.
""",
    "silence": """
The player is SILENT or idle. You may:
- Prompt them gently ('Still there?')
- Continue your thought if you were interrupted
- Share something relevant to the situation
Do NOT repeat your last statement verbatim.
""",
    "emotion": """
The player expressed EMOTION. Respond with appropriate EMPATHY.
Acknowledge their feelings before continuing with practical matters.
Don't dismiss their emotional state.
""",
}

# Escalation instruction template (added when warnings need variation)
escalation_instruction_template = """
ANTI-REPETITION NOTE: You have warned about this {count} time(s).
{escalation_guidance}
Tone: {tone}. Intensity: {intensity}.
If you've warned 3+ times: STOP repeating. Accept the situation or change tactics.
"""
