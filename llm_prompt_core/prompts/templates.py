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
Give me the next line in the dialogue in the same format. Don't provide stage directions, just the character's words. Don't give me a line for the player or Computer but for one of the other characters.\n
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
