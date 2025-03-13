from dataclasses import dataclass
import os
import re
import sys
import json
import datetime
from dotenv import load_dotenv
import random
from langchain_core.language_models.llms import LLM
from iconic_tools.langchain import (
    InstructSonnet,
    InstructOpus3,
    InstructGPT4,
    InstructO1,
    InstructGeminiPro,
    InstructGeminiFlash,
    InstructGeminiFlash2,
    InstructGPT35,
)
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env file
load_dotenv()

# --------------------------------
# GLOBALS AND CONSTANTS

PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# DIALOGUE_MODEL = InstructGeminiPro(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructGeminiPro(temperature=1.0, max_tokens=3000)

# DIALOGUE_MODEL = InstructGPT4(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructGPT4(temperature=1.0, max_tokens=3000)

# DIALOGUE_MODEL = InstructGeminiFlash(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructGeminiFlash(temperature=1.0, max_tokens=3000)

# DIALOGUE_MODEL = InstructO1()
# QUERY_MODEL = InstructO1()

# DIALOGUE_MODEL = InstructSonnet(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructSonnet(temperature=0.0, max_tokens=1000)
# PLAYER_MODEL = InstructGPT35(temperature=1.0, max_tokens=3000)

ACTORS = ["Eliza", "Player"]

gScenes = [
    "1_meet_the_caretaker",
    "2_locate_an_engineer",
    "3_describe_the_failures",
    "4_find_exit",
    "5_exit_the_room",
]

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
WHITE = "\033[0m"
CYAN = "\033[96m"
ORANGE = "\033[93m"

PREAMBLE_TEMPLATE = """{instruction_prefix}
Back Story:
{back_story}

Scene Description:
{scene_description}

Scene Supplement:
{scene_supplement}

Actors in scene: {actors}
"""


INSTRUCTION_TEMPLATE = """{preamble}
Dialogue so far:
{dialogue}

{instruction_suffix}
"""

SPEECH_TEMPLATE = "{actor}: {speech}"

PREAMBLE_PLUS_TEMPLATE = """
{instruction_prefix}
This is the game back story. 
{back_story}
\n
Here's a summary of information acquired from dialogues earlier in the game. The non-playable characters should make use of this information where appropriate to bond with the player. 
{dialogue_summary}\n

Here is a description of the scene in question. 
{scene_description}\n

Scene Supplement:
{scene_supplement}\n
"""

MERGE_PREAMBLE_TEMPLATE = """{instruction_prefix}
This is the game back story. {back_story}\n
"""

MERGE_INSTRUCTION_TEMPLATE = """{preamble}
Here is the first summary:\n
{summary1} \n
Here is the second summary:\n
{summary2} \n
{instruction_suffix}
"""

MERGE_INSTRUCTION_SUFFIX = """
Give me a paragraph merging the information from the two summaries above. Your objective is to eliminate duplicities and redundancy. Do not ommit any biographical information, tastes and preferences from the player or the other characters. Keep the information about events that might have happened in the dialogue that are not mentioned in the script for this scene, that includes deals made, promises kept, grudges, etc. Provide only the summary paragraph, no other text.\n
"""

SUMMARY_INSTRUCTION_SUFFIX = """
Give me a short paragraph summarising any information in the dialogue revealed by the player or the other characters that might be relevant for later dialogues. Include all personal or biographical information revealed in the dialoguethat helps to build a profile of the characters, including informations about their tastes and preferences. Also include any events that might have happened in the scene that weren't mentioned in the script, for instance deals made, promises kept, grudges, etc. Do not provide information that is already on the script, do not list things that are not present in the dialogue. Provide only the summary paragraph, no other text.\n
"""


@dataclass
class Query:
    text: str
    handled: bool = False
    query_printed: bool = (
        False  # When this query is evaluated a message is printed to the NPC dialogue
    )
    query_printed_text_true: str = ""
    query_printed_text_false: str = ""


# --------------------------------
# HELPER FUNCTIONS


def print_header(model_name, scene):
    print(WHITE + "Game or movie: {}".format(GAME))
    print("Scene name: {}".format(scene))
    print("Dialogue model: {}".format(model_name))
    print()


def load_prompt(filename):
    prompt_path = os.path.join(PATH, "project_one_demo", "prompts", filename)
    with open(prompt_path) as f:
        return f.read()


def write_transcript(dialogue, filename):
    transcript_path = os.path.join(PATH, "qa_research", "transcripts", filename)
    os.makedirs(os.path.dirname(transcript_path), exist_ok=True)
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(dialogue)


def list_to_conjunction(L):
    if not L:
        return ""
    elif len(L) == 1:
        return L[0]
    elif len(L) == 2:
        return f"{L[0]} and {L[1]}"
    else:
        return ", ".join(L[:-1]) + " and " + L[-1]


def list_to_string(L):
    return "\n".join(L)


def split_text(text):
    paragraphs = text.split("\n\n")
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    return paragraphs


def read_queries(filename: str) -> list[Query]:
    content = load_prompt(filename)
    lines = content.splitlines()
    queries = []

    query_text = None
    query_printed = False
    query_printed_text_true = ""
    query_printed_text_false = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            # It's a game change, we don't care for now, skip
            continue
        elif line.startswith("(") and line.endswith(")"):
            query_printed_text = line[1:-1]  # Remove ( and )
            parts = query_printed_text.split(", ", 1)
            if len(parts) == 2:
                query_printed_text_true = str(parts[0])
                query_printed_text_false = str(parts[1])
            else:
                query_printed_text_true = query_printed_text
                query_printed_text_false = ""

        else:
            # It's a new query text
            # If we already had a query text in progress, finalize it
            if query_text is not None:
                # finalize previous query
                queries.append(
                    Query(
                        text=query_text,
                        handled=False,
                        query_printed=query_printed,
                        query_printed_text_true=query_printed_text_true,
                        query_printed_text_false=query_printed_text_false,
                    )
                )
            # reset for the next query
            query_text = line
            query_printed = False
            query_printed_text_true = ""
            query_printed_text_false = ""

    # Add the last query if not None
    if query_text is not None:
        queries.append(
            Query(
                text=query_text,
                handled=False,
                query_printed=query_printed,
                query_printed_text_true=query_printed_text_true,
                query_printed_text_false=query_printed_text_false,
            )
        )

    return queries


def prompt_llm(prompt, model):
    prompt = ChatPromptTemplate.from_template(template=prompt)
    chain = prompt | model
    return chain


# --------------------------------
# DIALOGUE UTILITIES

def collect_game_scenes() -> list[dict[str, list[str]]]:
    # Get the root directory (one level up from qa_research)
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompts_path = os.path.join(root_path, "project_one_demo", "prompts")
    scenes = []

    # Get all game folders
    for act in os.listdir(prompts_path):
        game_path = os.path.join(prompts_path, act)
        if os.path.isdir(game_path):
            scenes_path = os.path.join(game_path, "scenes")

            if os.path.exists(scenes_path):
                # Get all scene folders
                act_scenes = [
                    scene
                    for scene in os.listdir(scenes_path)
                    if os.path.isdir(os.path.join(scenes_path, scene))
                ]

                scenes.append({act: act_scenes})

    return scenes


def load_prompts(scene, game, supplement_version=-1):
    # remove the first digit and _
    if re.match(r'^\d+_', scene):
        file_name = re.sub(r'^\d+_', '', scene)
    back_story = load_prompt(game + "/back_story.txt")
    scene_description = load_prompt(
        game + "/scenes/" + scene + "/" + file_name + "_scene_description.txt"
    )
    if supplement_version == -1:
        scene_supplement = ""
    else:
        # Load an alternate supplemental prompt if needed
        scene_supplement = load_prompt(
            game
            + "/scenes/"
            + scene
            + "_scene/"
            + file_name
            + "_supplement_"
            + str(supplement_version)
            + ".txt"
        )
    opening_speech = load_prompt(
        game + "/scenes/" + scene + "/" + file_name + "_opening_speech.txt"
    )

    dialogue_instruction_prefix = load_prompt("dialogue_instruction_prefix.txt")
    summary_instruction_prefix = load_prompt("summary_instruction_prefix.txt")
    merge_instruction_prefix = load_prompt("merge_instruction_prefix.txt")

    # opening speech could have delays in squared brakets, lets remove them
    opening_speech = re.sub(r"\[.*?\]", "", opening_speech)
    player_info = load_prompt(
        game + "/scenes/" + scene + "/" + file_name + "_player_info.txt"
    )
    queries = read_queries(game + "/scenes/" + scene + "/" + file_name + "_queries.txt")
    return (
        back_story,
        dialogue_instruction_prefix,
        scene_description,
        scene_supplement,
        opening_speech,
        queries,
        player_info,
        summary_instruction_prefix,
        merge_instruction_prefix,
    )


# --------------------------------
# SCENE SIMULATION

def generate_dialogue_summary(dialogue: str, back_story: str, summary_instruction_prefix: str, dialogue_model: LLM) -> str:
    summary_preamble = PREAMBLE_TEMPLATE.format( # Reusing PREAMBLE_TEMPLATE, could create a SUMMARY_PREAMBLE_TEMPLATE if needed to customize
        instruction_prefix=summary_instruction_prefix,
        back_story=back_story,
        scene_description="",
        scene_supplement="",
        actors=list_to_conjunction(ACTORS),
    )
    prompt = INSTRUCTION_TEMPLATE.format(
        preamble=summary_preamble,
        dialogue=dialogue,
        instruction_suffix=SUMMARY_INSTRUCTION_SUFFIX,
    )
    chain = prompt_llm(prompt, dialogue_model)
    return chain.invoke({}).strip()


def generate_merge_summary(summary1: str, summary2: str, back_story: str, merge_instruction_prefix: str, dialogue_model: LLM) -> str:
    merge_preamble = MERGE_PREAMBLE_TEMPLATE.format(
        instruction_prefix=merge_instruction_prefix,
        back_story=back_story,
    )
    prompt = MERGE_INSTRUCTION_TEMPLATE.format(
        preamble=merge_preamble,
        summary1=summary1,
        summary2=summary2,
        instruction_suffix=MERGE_INSTRUCTION_SUFFIX,
    )
    chain = prompt_llm(prompt, dialogue_model)
    return chain.invoke({}).strip()


def get_player_llm_response(
    dialogue: str,
    player_model: LLM,
    back_story: str,
    scene_description: str,
    scene_supplement: str,
    player_info: str,
    dialogue_summary: str = "",
    player_instruction_prefix: str = """
        You are going to generate one line of dialogue for a scene in the middle of a computer game.
        Your line will be the one of a {adjective_character} player.
        """,
    player_instruction_suffix: str = """
        Give me the next line in the dialogue in the same format. 
        Don't provide stage directions, just the player's words. 
        Don't give me a line for a character other than the {adjective_character} player.\n
        """,
    adjective_character: str = "",
) -> str:
    player_instruction_prefix = player_instruction_prefix.format(
        adjective_character=adjective_character
    )
    player_instruction_suffix = player_instruction_suffix.format(
        adjective_character=adjective_character
    )

    scene_supplement += (
        "\n"
        + """
                        Through this scene, this information will become available to the player:
                        {player_info}
                        """.format(player_info=player_info)
    )

    if dialogue_summary:
        dialogue_preamble = PREAMBLE_PLUS_TEMPLATE.format(
            instruction_prefix=player_instruction_prefix,
            back_story=back_story,
            dialogue_summary=dialogue_summary,
            scene_description=scene_description,
            scene_supplement=scene_supplement,
            actors=list_to_conjunction(ACTORS),
        )
    else:
        dialogue_preamble = PREAMBLE_TEMPLATE.format(
            instruction_prefix=player_instruction_prefix,
            back_story=back_story,
            scene_description=scene_description,
            scene_supplement=scene_supplement,
            actors=list_to_conjunction(ACTORS),
        )

    prompt = INSTRUCTION_TEMPLATE.format(
        preamble=dialogue_preamble,
        dialogue=dialogue,
        instruction_suffix=player_instruction_suffix,
    )
    chain = prompt_llm(prompt, player_model)
    return chain.invoke({}).strip()


def get_npc_llm_response(
    dialogue: str,
    dialogue_model: LLM,
    back_story: str,
    scene_description: str,
    scene_supplement: str,
    dialogue_summary: str = "",
    dialogue_instruction_prefix: str = """
        You are going to generate one line of dialogue for a scene in the middle of a computer game.
        """,
    dialogue_instruction_suffix: str = """
        Give me the next line in the dialogue in the same format. 
        Don't provide stage directions, just the character's words.
        Don't give me a the words for the player, but for one of the other characters.\n
        """,
) -> str:

    if dialogue_summary:
        dialogue_preamble = PREAMBLE_PLUS_TEMPLATE.format(
            instruction_prefix=dialogue_instruction_prefix,
            back_story=back_story,
            dialogue_summary=dialogue_summary,
            scene_description=scene_description,
            scene_supplement=scene_supplement,
            actors=list_to_conjunction(ACTORS),
        )
    else:
        dialogue_preamble = PREAMBLE_TEMPLATE.format(
            instruction_prefix=dialogue_instruction_prefix,
            back_story=back_story,
            scene_description=scene_description,
            scene_supplement=scene_supplement,
            actors=list_to_conjunction(ACTORS),
        )

    prompt = INSTRUCTION_TEMPLATE.format(
        preamble=dialogue_preamble,
        dialogue=dialogue,
        instruction_suffix=dialogue_instruction_suffix,
    )
    chain = prompt_llm(prompt, dialogue_model)
    return chain.invoke({}).strip()


def get_query_llm_response(
    dialogue: str,
    statement: str,
    query_model: LLM,
    back_story: str,
    query_instruction_prefix: str = """
        You are going to answer a single question about the current state of the dialogue in a scene in the middle of a computer game.
        """,
    query_instruction_suffix_template: str = """
        Now consider the following statement about this dialogue. {statement} Is this statement true or false? Answer with a single word, true or false.
        """,
) -> str:
    query_preamble = PREAMBLE_TEMPLATE.format(
        instruction_prefix=query_instruction_prefix,
        back_story=back_story,
        scene_description="",
        scene_supplement="",
        actors=list_to_conjunction(ACTORS),
    )

    prompt = INSTRUCTION_TEMPLATE.format(
        preamble=query_preamble,
        dialogue=dialogue,
        instruction_suffix=query_instruction_suffix_template.format(
            statement=statement
        ),
    )
    chain = prompt_llm(prompt, query_model)
    return chain.invoke({}).strip()


def evaluate_queries(
    dialogue: str, queries: list[Query], query_model: LLM, back_story: str
) -> tuple[int, str]:
    fails = 0
    to_print = ""
    print()

    for query in queries:
        # Only evaluate if not handled
        if not query.handled:
            # print("\n" + YELLOW + query.text)
            query_resp = get_query_llm_response(
                dialogue, query.text, query_model, back_story
            )
            if query_resp.lower().startswith("true"):
                query.handled = True
                if query.query_printed_text_true:
                    query.query_printed = True
                    to_print += query.query_printed_text_true
            else:
                fails += 1
                if query.query_printed_text_false:
                    query.query_printed = True
                    to_print += query.query_printed_text_false
                break
    # print(WHITE + "to_print: ", to_print)
    return fails, to_print


def sim_mini_scene(
    supplement_version: int,
    player: bool,
    max_turns: int,
    dialogue_model: LLM,
    query_model: LLM,
    player_model: LLM,
    scene: str,
    game: str,
    dialogue_summary: str = "",
) -> tuple[str, bool]:
    actors = ACTORS
    (
        back_story,
        dialogue_instruction_prefix,
        scene_description,
        scene_supplement,
        opening_speech,
        queries,
        player_info,
        summary_instruction_prefix,
        merge_instruction_prefix,
    ) = load_prompts(scene, game, supplement_version)

    lines = split_text(opening_speech)
    dialogue = ""

    for line in lines:
        dialogue += SPEECH_TEMPLATE.format(actor=actors[0], speech=line) + "\n\n"
        print(GREEN + SPEECH_TEMPLATE.format(actor=actors[0], speech=line))

    turn = 1
    success = False

    print("dialogue_summary", dialogue_summary)
    while turn < max_turns and not success:
        if player and (turn % 2 == 1):
            speech = get_player_llm_response(
                dialogue=dialogue,
                player_model=player_model,
                back_story=back_story,
                scene_description=scene_description,
                scene_supplement=scene_supplement,
                player_info=player_info,
                dialogue_summary=dialogue_summary,
            )
            if re.match(r"^\S+:\s+", speech):
                speech = re.sub(r"^\S+:\s+", "", speech)
            response = SPEECH_TEMPLATE.format(actor=actors[1], speech=speech)
        else:
            npc_speech = get_npc_llm_response(
                dialogue=dialogue,
                dialogue_model=dialogue_model,
                back_story=back_story,
                scene_description=scene_description,
                scene_supplement=scene_supplement,
                dialogue_summary=dialogue_summary,
                dialogue_instruction_prefix=dialogue_instruction_prefix,
            )
            if re.match(r"^\S+:\s+", npc_speech):
                npc_speech = re.sub(r"^\S+:\s+", "", npc_speech)
            response = SPEECH_TEMPLATE.format(actor=actors[0], speech=npc_speech)
        dialogue += response + "\n\n"
        print(GREEN + response)

        fails, to_print = evaluate_queries(dialogue, queries, query_model, back_story)
        if to_print:
            dialogue += to_print + "\n\n"
            print(YELLOW + to_print)

        success = fails == 0
        turn += 1

    # Generate dialogue summary
    current_summary = generate_dialogue_summary(dialogue, back_story, summary_instruction_prefix, dialogue_model)
    print(CYAN + f"Current scene summary: {current_summary}")
    if dialogue_summary:
        dialogue_summary = generate_merge_summary(dialogue_summary, current_summary, back_story, merge_instruction_prefix, dialogue_model)
        print(ORANGE + f"Merged dialogue summary: {dialogue_summary}")
    else:
        dialogue_summary = current_summary
        print(ORANGE + f"Dialogue summary: {dialogue_summary}")

    if success:
        print("Mini scene completed successfully")
    else:
        print("Mini scene ended unsuccessfully")

    return (dialogue, success, dialogue_summary)


def save_dialogue_with_timestamp(
    dialogue: str, dialogue_summary: str, scene: str, npc_model_name: str, game: str, prompt_version: str = "P2"
) -> None:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    npc_model_name += f"_{prompt_version}"

    # Create directory path
    directory = os.path.join(PATH, "qa_research", "dialogues", game, scene, npc_model_name)
    os.makedirs(directory, exist_ok=True)

    # Create filename
    filename = f"dialogue_{stamp}.txt"
    summary_filename = f"summary_{stamp}.txt"

    # Full path
    filepath = os.path.join(directory, filename)
    summary_filepath = os.path.join(directory, summary_filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(dialogue)
    print(f"Dialogue saved to {filepath}")
    if dialogue_summary:
        with open(summary_filepath, "w", encoding="utf-8") as f:
            f.write(dialogue_summary)
        print(f"Dialogue summary saved to {summary_filepath}")


# --------------------------------
# GENERATE ONE DIALOGUE


def generate_dialogue(
    dialogue_model: LLM,
    query_model: LLM,
    player_model: LLM,
    scene: str,
    game: str,
    max_turns: int = 50,
    dialogue_summary: str = "",
) -> str:
    player = True
    supplement_version = -1
    dialogue, _, new_summary= sim_mini_scene(
        supplement_version,
        player=player,
        max_turns=max_turns,
        dialogue_model=dialogue_model,
        query_model=query_model,
        player_model=player_model,
        scene=scene,
        game=game,
        dialogue_summary=dialogue_summary
    )
    save_dialogue_with_timestamp(
        dialogue,
        dialogue_summary,
        scene,
        dialogue_model.__class__.__name__,
        game,
    )
    return new_summary

if __name__ == "__main__":
    # randomly select a scene
    scenes = collect_game_scenes()
    selected_act = random.choice(scenes)
    # Set GAME to selected act
    global GAME
    GAME = list(selected_act.keys())[0]
    # selected_scene = random.choice(selected_act[GAME])
    selected_scene = "find_exit"

    generate_dialogue(
        InstructGeminiFlash2(temperature=1.0, max_tokens=3000),
        InstructGeminiFlash2(temperature=0.0, max_tokens=1000),
        InstructGeminiFlash2(temperature=1.0, max_tokens=3000),
        selected_scene,
        GAME,
    )
