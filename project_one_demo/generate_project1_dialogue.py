import os
import sys
import re
import math
import time
from iconic_tools.langchain import (
    InstructSonnet,
    InstructOpus3,
    InstructGPT4,
    InstructO1,
    InstructGeminiPro,
    InstructGPT35,
    InstructGeminiFlash,
    InstructGeminiFlash2,
)
from langchain_core.prompts import ChatPromptTemplate
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple, List, Tuple
from dataclasses import dataclass, field

# CONSTANTS AND INITIALISATION
# DIALOGUE_MODEL = InstructGeminiPro(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructGeminiPro(temperature=1.0, max_tokens=3000)

# DIALOGUE_MODEL = InstructGPT4(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructGPT4(temperature=1.0, max_tokens=3000)

DIALOGUE_MODEL = InstructGeminiFlash2(temperature=1.0, max_tokens=3000)
QUERY_MODEL = InstructGeminiFlash2(temperature=0.0, max_tokens=300)

# DIALOGUE_MODEL = InstructO1()
# QUERY_MODEL = InstructO1()

# DIALOGUE_MODEL = InstructSonnet(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructSonnet(temperature=1.0, max_tokens=3000)


GAME = "act_1"
ACTORS = ["Eliza", "Player"]

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
WHITE = "\033[0m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BRIGHT_WHITE = "\033[97m"
BLACK = "\033[90m"
ORANGE = "\033[33m"


# UTILITIES
def list_to_conjunction(L):
    """Takes a list strings and returns a string with every element in the list separated by commas."""
    if L == "":
        return ""
    elif len(L) == 1:
        return L[0]
    elif len(L) == 2:
        return f"{L[0]} and {L[1]}"
    else:
        return ", ".join(L[:-1]) + f", and {L[-1]}"


def load_prompt(filename):
    cwd = os.path.abspath(os.getcwd())
    prompt_path = os.path.join(cwd, "project_one_demo", "prompts", filename)
    with open(prompt_path) as f:
        return f.read()


# PROMPT TEMPLATES AND INSTRUCTION PROMPTS
preamble_template = """
{instruction_prefix}
This is the game back story. {back_story}\n
Here is a description of the scene in question. {previous_scenes_description}\n{scene_description}\n{scene_supplement}\n
The characters in the dialogue are {actors}.
"""

preamble_plus_template = """
{instruction_prefix}
This is the game back story. {back_story}\n
Here is a summary of the script from previous scenes. {previous_scenes_description}\n
Here's a summary of information acquired from dialogues earlier in the game. The non-playable characters should make use of this information where appropriate to bond with the player. {dialogue_summary}\n
Here is a description of the scene in question. {scene_description}
"""

merge_preamble_template = """
{instruction_prefix}
This is the game back story. {back_story}\n
Here is a summary of the script from previous scenes. {previous_scenes_description}\n
"""

merge_instruction_template = """
{preamble}
Here is the first summary:\n
{summary1} \n
Here is the second summary:\n
{summary2} \n
{instruction_suffix}
"""

merge_instruction_suffix = """
Give me a short paragraph summarising the information from the two summaries above. Do not ommit any biographical information or events that might have happened in the dialogue that weren't mentioned in the script for this scene. Provide only the summary paragraph, no other text.\n
"""

instruction_template = """
{preamble}
Here is the dialogue so far\n\n
{dialogue}
{instruction_suffix}
"""

speech_template = "[{actor}]: {speech}\n"

dialogue_instruction_suffix = """
Give me the next line in the dialogue in the same format. Don't provide stage directions, just the character's words. Don't give me a line for the player or Computer but for one of the other characters.\n
"""

query_instruction_prefix = """
You are going to answer a single question about the current state of the dialogue in a scene in the middle of a computer game.
"""

query_instruction_suffix_template = """
Now consider the following statement about this dialogue. {statement} Is this statement true or false? Answer with a single word, true or false.
"""

summary_instruction_suffix = """
Give me a short paragraph summarising any information revealed by the player or the other characters that might be relevant for later dialogues, for example personal or biographical information, or any events that might have happened in the scene that weren't mentioned in the script. Provide only the summary paragraph, no other text.\n
"""

# BUILDING DIALOGUES
def prompt_llm(prompt, model):
    prompt = ChatPromptTemplate.from_template(template=prompt)
    chain = prompt | model
    return chain


@dataclass
class Line:
    text: str
    delay: float


@dataclass
class StateChange:
    name: str
    value: str


@dataclass
class Query:
    text: str
    state_changes: List[StateChange]
    handled: bool = False
    query_printed: bool = (
        False  # When this query is evaluated a message is printed to the NPC dialogue
    )
    query_printed_text_true: str = ""
    query_printed_text_false: str = ""


@dataclass
class SceneData:
    scene_name: str
    scene_description: str
    previous_scenes_description: str
    scene_supplement: str
    back_story: str
    dialogue_instruction_prefix: str
    summary_instruction_prefix: str
    merge_instruction_prefix: str
    opening_speech: List[Line]
    queries: List[Query]

    dialogue_preamble: str = ""
    query_preamble: str = ""
    dialogue_summary: str = ""

    def __post_init__(self):
        if self.dialogue_summary:
            self.dialogue_preamble = preamble_plus_template.format(
                instruction_prefix=self.dialogue_instruction_prefix,
                back_story=self.back_story,
                dialogue_summary=self.dialogue_summary,
                scene_description=self.scene_description,
                scene_supplement=self.scene_supplement,
                actors=list_to_conjunction(ACTORS),
                previous_scenes_description=self.previous_scenes_description,
            )
        else:
            self.dialogue_preamble = preamble_template.format(
                instruction_prefix=self.dialogue_instruction_prefix,
                back_story=self.back_story,
                scene_description=self.scene_description,
                scene_supplement=self.scene_supplement,
                actors=list_to_conjunction(ACTORS),
                previous_scenes_description=self.previous_scenes_description,
            )
        self.query_preamble = preamble_template.format(
            instruction_prefix=query_instruction_prefix,
            back_story=self.back_story,
            scene_description="",
            scene_supplement="",
            actors=list_to_conjunction(ACTORS),
            previous_scenes_description=self.previous_scenes_description,
        )
        self.summary_preamble = preamble_template.format(
            instruction_prefix=self.summary_instruction_prefix,
            back_story=self.back_story,
            scene_description="",
            scene_supplement="",
            actors=list_to_conjunction(ACTORS),
            previous_scenes_description=self.previous_scenes_description,
        )
        self.merge_preamble = merge_preamble_template.format(
            instruction_prefix=self.merge_instruction_prefix,
            back_story=self.back_story,
            previous_scenes_description=self.previous_scenes_description,
        )


    def __str__(self):
        field = "\033[97m"
        text = "\033[90m"
        reset = "\033[0m"
        return f"{field}SceneData\n{{\n   scene_name:{text} {self.scene_name}\n{field}   scene_description:{text}  {self.scene_description}\n{field}   previous_scenes_description:{text} {self.previous_scenes_description}\n{field}   dialogue_summary:{text} {self.dialogue_summary}\n{field}   scene_supplement:{text} {self.scene_supplement}\n{field}   dialogue_instruction_prefix:{text} {self.dialogue_instruction_prefix}\n{field}   back_story:{text} {self.back_story}\n{field}   opening_speech:{reset}\n{self.opening_speech}\n{field}   queries:{reset}\n{self.queries}\n{field}}}{reset}"

    def get_initial_dialog(self) -> str:
        dialogue = ""
        for line in self.opening_speech:
            response = speech_template.format(actor=ACTORS[0], speech=line.text)
            dialogue += response + "\n"
            print(GREEN + response)

        return dialogue

    def run_queries(self, dialogue: str) -> Tuple[List[StateChange], str]:
        state_changes = []
        to_print = ""

        for query in self.queries:
            if query.handled == False:
                instruction = query_instruction_suffix_template.format(
                    statement=query.text
                )
                prompt = instruction_template.format(
                    preamble=self.query_preamble,
                    dialogue=dialogue,
                    instruction_suffix=instruction,
                )
                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                response = chain.invoke({})
                print(ORANGE + f'Query for "{query.text}" - response: "{response}"')
                print(YELLOW + f"To print: {to_print}")
                if response[0:4].lower() == "true":
                    query.handled = True
                    print(
                        YELLOW
                        + f'Query passed for "{query.text}" - returning state_id "{query.state_changes}"'
                    )
                    if query.query_printed_text_true:
                        query.query_printed = True
                        to_print = query.query_printed_text_true
                    state_changes.extend(query.state_changes)
                else:
                    if query.query_printed_text_true and not query.query_printed:
                        to_print = query.query_printed_text_false
                    break
        return state_changes, to_print

    def all_queries_handled(self) -> bool:
        return all(query.handled for query in self.queries)


def resource_path():
    cwd = os.path.abspath(os.getcwd())
    relative_path = "/project_one_demo/prompts/act_1"
    return cwd + relative_path
    # # Get the absolute path to the resource in both development and PyInstaller environments
    # if hasattr(sys, "_MEIPASS"):
    #     # PyInstaller environment
    #     return os.path.join(sys._MEIPASS, relative_path)
    # else:
    #     # Development environment
    #     return os.path.join(os.path.abspath("."), relative_path)


def load_root_file(file) -> str:
    file_path = resource_path() + f"/{file}.txt"
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""  # Return an empty string if the file doesn't exist


def load_scene_file(scene_name: str, suffix: str) -> str:
     # we need to remove the first digit and underscore, e.g. 1_ from the scene_name for the file name
    scene_name_file = scene_name[2:]
    file_path = resource_path() + f"/scenes/{scene_name}/{scene_name_file}_{suffix}.txt"
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""  # Return an empty string if the file doesn't exist


def load_queries(scene_name: str) -> List[Query]:
    queries = []
    query_text = None
    state_changes = []
    query_printed = False
    query_printed_text_true = ""
    query_printed_text_false = ""

    file = load_scene_file(scene_name, "queries")
    for line in file.splitlines():
        line = line.strip()
        if not line:
            continue  # Skip empty lines

        # Check if line is a state change line
        if line.startswith("[") and line.endswith("]"):
            # Remove brackets and parse state changes
            state_changes = []
            state_changes_text = line[1:-1]  # Remove [ and ]
            state_parts = state_changes_text.split(",")

            for part in state_parts:
                name, value = map(str.strip, part.split("="))
                state_changes.append(
                    StateChange(name=name.strip(), value=value.strip())
                )

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
            # If there was previous query text, create a Query object and reset
            if query_text is not None:
                queries.append(
                    Query(
                        text=query_text,
                        state_changes=state_changes,
                        query_printed=query_printed,
                        query_printed_text_true=query_printed_text_true,
                        query_printed_text_false=query_printed_text_false,
                    )
                )
                state_changes = []
                query_printed = False
                query_printed_text_true = ""
                query_printed_text_false = ""

            # Update query_text to the current line
            query_text = line

    # Add the last query if there is one
    if query_text is not None:
        queries.append(
            Query(
                text=query_text,
                state_changes=state_changes,
                query_printed=query_printed,
                query_printed_text_true=query_printed_text_true,
                query_printed_text_false=query_printed_text_false,
            )
        )

    return queries


def load_opening_speech(scene_name: str) -> List[Line]:
    lines = []
    file = load_scene_file(scene_name, "opening_speech")
    for line in file.splitlines():
        # Remove any leading or trailing whitespace
        line = line.strip()
        if not line:
            continue  # Skip empty lines

        # Match optional scene ID at the start of the line
        match = re.match(r"^\[(\d+(\.\d+)?)\]\s+(.+)$", line)
        if match:
            delay = float(match.group(1))
            text = match.group(3)
        else:
            delay = 0  # Empty if no scene ID is present
            text = line

        # Add to list with handled defaulting to False
        lines.append(Line(text=text, delay=delay))

    return lines


def load_scene_data(scene_name: str, dialogue_summary: str = "") -> SceneData:

    scene_description = load_scene_file(scene_name, "scene_description")
    previous_scenes_description = load_scene_file(scene_name, "prev_scenes_description")
    scene_supplement = load_scene_file(scene_name, "scene_supplement")
    dialogue_instruction_prefix = load_root_file("dialogue_instruction_prefix")
    summary_instruction_prefix = load_root_file(
        "summary_instruction_prefix"
    )
    merge_instruction_prefix = load_root_file(
        "merge_instruction_prefix"
    )
    back_story = load_root_file("back_story")
    opening_speech = load_opening_speech(scene_name)
    queries = load_queries(scene_name)
    print(RED + f'queries: {queries}')
    return SceneData(
        scene_name=scene_name,
        scene_description=scene_description,
        scene_supplement=scene_supplement,
        dialogue_instruction_prefix=dialogue_instruction_prefix,
        back_story=back_story,
        opening_speech=opening_speech,
        queries=queries,
        dialogue_summary=dialogue_summary,
        summary_instruction_prefix=summary_instruction_prefix,
        merge_instruction_prefix=merge_instruction_prefix,
        previous_scenes_description=previous_scenes_description,
    )


class SceneClient:
    def __init__(self):
        self.scene_data = None
        self.scene_dialogue = ""
        self.dialogue_summary = ""
        self.scenes = [
            "1_meet_the_caretaker",
            "2_locate_an_engineer",
            "3_describe_the_failures",
            "4_find_exit",
            "5_exit_the_room",
        ]
        self.is_first_scene = True
        self.is_second_scene = False

    def generate_dialogue_summary(self) -> str:
        prompt = instruction_template.format(
            preamble=self.scene_data.summary_preamble,
            dialogue=self.scene_dialogue,
            instruction_suffix=summary_instruction_suffix,
        )
        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        return chain.invoke({})

    def generate_merge_summary(self, summary: str) -> str:
        prompt = merge_instruction_template.format(
            preamble=self.scene_data.merge_preamble,
            dialogue=self.scene_dialogue,
            instruction_suffix=merge_instruction_suffix,
            summary1=self.dialogue_summary,
            summary2=summary,
        )
        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        return  chain.invoke({})

    def load_next_scene(self) -> bool:
        if self.scenes:
            if self.is_first_scene:
                print("First Scene")
                self.is_first_scene = False
                self.is_second_scene = True
            elif self.is_second_scene:
                print("Second Scene")
                self.dialogue_summary = self.generate_dialogue_summary()
                print(CYAN + f'Dialogue summary: {self.dialogue_summary}')
                self.is_second_scene = False
            else:
                print("Third Scene")
                temp_dialogue_summary = self.generate_dialogue_summary()
                print(CYAN + f'Temporary dialogue summary: {temp_dialogue_summary}')
                self.dialogue_summary = self.generate_merge_summary(temp_dialogue_summary)
                print(ORANGE + f'Merged Dialogue summary: {self.dialogue_summary}')
            print(CYAN + f'Loading scene "{self.scenes[0]}"')
            self.scene_data = load_scene_data(self.scenes.pop(0), self.dialogue_summary)
            self.scene_dialogue = self.scene_data.get_initial_dialog()
            return True
        return False

    def start_scene(self, scene: str):
        if (
            self.scenes and self.scenes[0] == scene
        ):  # Hacky guard due to events getting sent twice from game
            self.load_next_scene()
            return self.scene_data.opening_speech, []
        return [], []

    def reset_response_handler(self):
        self.scenes = [
            "1_meet_the_caretaker",
            "2_locate_an_engineer",
            "3_describe_the_failures",
            "4_find_exit",
            "5_exit_the_room",
        ]
        print(CYAN + f'Starting response handler for scenes: "{self.scenes}"')
        self.load_next_scene()

    def add_luna_commands(self, message: str):
        self.scene_dialogue += "[Player]: " + message + "\n\n"

    def handle_player_response(
        self, message: str, automated: bool
    ) -> Tuple[List[Line], List[StateChange]]:
        if message:
            print(CYAN + f'Handling player response: "{message}"')

            if False:
                self.scene_dialogue += "Eliza to comment on " + message + "\n"
            else:
                player_dialogue = speech_template.format(
                    actor=ACTORS[1], speech=message
                )
                self.scene_dialogue += player_dialogue + "\n"

            state_changes, to_print = self.scene_data.run_queries(self.scene_dialogue)
            if to_print:
                self.scene_dialogue += to_print + "\n\n"
            result_lines = []
            if self.scene_data.all_queries_handled():
                print(
                    ORANGE
                    + f"All queries for {self.scene_data.scene_name} complete, autoloading next scene"
                )
                if self.load_next_scene():
                    result_lines = self.scene_data.opening_speech

            if not result_lines:
                prompt = instruction_template.format(
                    preamble=self.scene_data.dialogue_preamble,
                    dialogue=self.scene_dialogue,
                    instruction_suffix=dialogue_instruction_suffix,
                )
                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                eliza_response = chain.invoke({})

                # print(RED + f"Eliza response: {eliza_response}")
                eliza_response = eliza_response.split("\nComputer", 1)[0]

                # print(ORANGE + f"Eliza response post processed: {eliza_response}")

                self.scene_dialogue += eliza_response + "\n"
                state_changes2, to_print = self.scene_data.run_queries(
                    self.scene_dialogue
                )

                if to_print:
                    self.scene_dialogue += to_print + "\n\n"

                print(CYAN + f"Scene dialogue: {self.scene_dialogue}")

                state_changes.extend(state_changes2)

                eliza_text = (
                    str(eliza_response).strip().removeprefix(f"[{ACTORS[0]}]: ")
                )
                eliza_text = eliza_text.replace('"', "")
                eliza_text = eliza_text.replace("*", "")

                print(
                    CYAN
                    + f'Results: text="{eliza_text}" state_changes="{state_changes}"'
                )

                result_lines = [Line(text=eliza_text, delay=0)]

                if self.scene_data.all_queries_handled():
                    print(
                        ORANGE
                        + f"All queries for {self.scene_data.scene_name} complete, autoloading next scene"
                    )
                    if self.load_next_scene():
                        result_lines.extend(self.scene_data.opening_speech)

            return result_lines, state_changes
