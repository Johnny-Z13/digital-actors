from dataclasses import dataclass
import os
import re
import sys
import json
import datetime
from dotenv import load_dotenv
from typing import Any, List, Tuple
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

PATH = os.path.abspath(os.getcwd())

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

GAME = "act_1"
ACTORS = ["Eliza", "Player"]

gScenes = [
    "meet_the_caretaker",
    "locate_an_engineer",
    "describe_the_failures",
    "find_exit",
    "exit_the_room",
]

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
WHITE = "\033[0m"

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


@dataclass
class Query:
    text: str
    handled: bool = False
    query_printed: bool = False  # When this query is evaluated a message is printed to the NPC dialogue
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
    with open(os.path.join(PATH, "prompts", filename)) as f:
        return f.read()


def write_transcript(dialogue, filename):
    with open(os.path.join(PATH, "transcripts", filename), "w", encoding="utf-8") as f:
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


def read_queries(filename: str) -> List[Query]:
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

        if line.startswith('[') and line.endswith(']'):
            # It's a game change, we don't care for now, skip
            continue
        elif line.startswith('(') and line.endswith(')'):
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
                queries.append(Query(
                    text=query_text,
                    handled=False,
                    query_printed=query_printed,
                    query_printed_text_true=query_printed_text_true,
                    query_printed_text_false=query_printed_text_false
                ))
            # reset for the next query
            query_text = line
            query_printed = False
            query_printed_text_true = ""
            query_printed_text_false = ""

    # Add the last query if not None
    if query_text is not None:
        queries.append(Query(
            text=query_text,
            handled=False,
            query_printed=query_printed,
            query_printed_text_true=query_printed_text_true,
            query_printed_text_false=query_printed_text_false
        ))

    return queries


def prompt_llm(prompt, model):
    prompt = ChatPromptTemplate.from_template(template=prompt)
    chain = prompt | model
    return chain


# --------------------------------
# DIALOGUE UTILITIES
# TODO: I added the player_info files, we need to add the player_info to the prompts

def load_prompts(supplement_version=-1, scene="meet_the_caretaker"):
    back_story = load_prompt(GAME + "/back_story.txt")
    scene_description = load_prompt(
        GAME + "/scenes/" + scene + "/" + scene + "_scene_description.txt"
    )
    if supplement_version == -1:
        scene_supplement = ""
    else:
        # Load an alternate supplemental prompt if needed
        scene_supplement = load_prompt(
            GAME
            + "/scenes/"
            + scene
            + "_scene/"
            + scene
            + "_supplement_"
            + str(supplement_version)
            + ".txt"
        )
    opening_speech = load_prompt(
        GAME + "/scenes/" + scene + "/" + scene + "_opening_speech.txt"
    )
    player_info = load_prompt(
        GAME + "/scenes/" + scene + "/" + scene + "_player_info.txt"
    )
    queries = read_queries(GAME + "/scenes/" + scene + "/" + scene + "_queries.txt")
    return (back_story, scene_description, scene_supplement, opening_speech, queries, player_info)

# --------------------------------
# SCENE SIMULATION


def get_player_llm_response(
    dialogue: str,
    player_model: Any,
    back_story: str,
    scene_description: str,
    scene_supplement: str,
    player_info: str,
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
    player_instruction_prefix = player_instruction_prefix.format(adjective_character=adjective_character)
    player_instruction_suffix = player_instruction_suffix.format(adjective_character=adjective_character)

    scene_supplement += "\n" + \
                        """
                        Through this scene, this information will become available to the player:
                        {player_info}
                        """.format(player_info=player_info)

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
dialogue_model: Any,
back_story: str,
scene_description: str,
scene_supplement: str,
dialogue_instruction_prefix: str = """
        You are going to generate one line of dialogue for a scene in the middle of a computer game.
        """,
    dialogue_instruction_suffix: str = """
        Give me the next line in the dialogue in the same format. 
        Don't provide stage directions, just the character's words.
        Don't give me a the words for the player, but for one of the other characters.\n
        """,
) -> str:

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
    query_model: Any,
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
    dialogue: str,
    queries: List[Query],
    query_model: Any,
    back_story: str
) -> Tuple[int, str]:
    fails = 0
    to_print = ""
    # print queries in Yellow

    for query in queries:
        # Only evaluate if not handled
        if not query.handled:
            query_resp = get_query_llm_response(dialogue, query.text, query_model, back_story)
            if query_resp.lower().startswith("true"):
                query.handled = True
                if query.query_printed_text_true and not query.query_printed:
                    query.query_printed = True
                    to_print += query.query_printed_text_true
            else:
                fails += 1
                if query.query_printed_text_false and not query.query_printed:
                    query.query_printed = True
                    to_print += query.query_printed_text_false
                break
    # print(queries)
    return fails, to_print


def sim_mini_scene(
    supplement_version: int,
    player: bool,
    max_turns: int,
    dialogue_model: Any,
    query_model: Any,
    player_model: Any,
) -> Tuple[str, bool]:
    actors = ACTORS
    (back_story, scene_description, scene_supplement, opening_speech, queries, player_info) = (
        load_prompts(supplement_version)
    )

    lines = split_text(opening_speech)
    dialogue = ""

    for line in lines:
        dialogue += SPEECH_TEMPLATE.format(actor=actors[0], speech=line) + "\n"
        print(GREEN + SPEECH_TEMPLATE.format(actor=actors[0], speech=line))

    turn = 1
    success = False

    while turn < max_turns and not success:
        if player and (turn % 2 == 1):
            speech = get_player_llm_response(dialogue, player_model, back_story, scene_description, scene_supplement, player_info)
            if re.match(r'^\S+:\s+', speech):
                speech = re.sub(r'^\S+:\s+', '', speech)
            response = SPEECH_TEMPLATE.format(actor=actors[1], speech=speech)
        else:
            npc_speech = get_npc_llm_response(
                dialogue,
                dialogue_model,
                back_story,
                scene_description,
                scene_supplement,
            )
            if re.match(r'^\S+:\s+', npc_speech):
                npc_speech = re.sub(r'^\S+:\s+', '', npc_speech)
            response = SPEECH_TEMPLATE.format(actor=actors[0], speech=npc_speech)
        dialogue += response + "\n"
        print(GREEN + response)

        fails, to_print = evaluate_queries(dialogue, queries, query_model, back_story)
        if to_print:
            dialogue += to_print + "\n"
            print(YELLOW + to_print)

        success = fails == 0
        turn += 1

    if success:
        print("Mini scene completed successfully")
    else:
        print("Mini scene ended unsuccessfully")

    return (dialogue, success)


def save_dialogue_with_timestamp(dialogue: str) -> None:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output_dialogue_{stamp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(dialogue)
    print(f"Dialogue saved to {filename}")


# --------------------------------
# GENERATE ONE DIALOGUE


def main(dialogue_model: Any, query_model: Any, player_model: Any) -> None:
    player = True
    supplement_version = -1
    dialogue, success = sim_mini_scene(
        supplement_version,
        player=player,
        max_turns=25,
        dialogue_model=dialogue_model,
        query_model=query_model,
        player_model=player_model,
    )
    save_dialogue_with_timestamp(dialogue)


if __name__ == "__main__":
    main(
        InstructGeminiFlash2(temperature=1.0, max_tokens=3000),
        InstructGeminiFlash2(temperature=0.0, max_tokens=1000),
        InstructGeminiFlash2(temperature=1.0, max_tokens=3000),
    )
