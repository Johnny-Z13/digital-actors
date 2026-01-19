import os
import sys
import re
import math
import time
from langchain_core.prompts import ChatPromptTemplate
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple, List, Tuple
from dataclasses import dataclass, field
from llm_prompt_core.models.anthropic import ClaudeSonnet45Model
from llm_prompt_core.models.gemini import GeminiFlash25NoThinking
from llm_prompt_core.types import Line, Query, StateChange, SceneData
from llm_prompt_core.utils import (
    list_to_conjunction,
    prompt_llm,
    RED,
    GREEN,
    BLUE,
    YELLOW,
    WHITE,
    CYAN,
    MAGENTA,
    BRIGHT_WHITE,
    BLACK,
    ORANGE,
)
from llm_prompt_core.prompts.templates import (
    preamble_template,
    query_preamble_template,
    preamble_plus_template,
    merge_preamble_template,
    merge_instruction_template,
    speech_template,
    instruction_template,
    dialogue_instruction_suffix,
    query_instruction_suffix_template,
    summary_instruction_suffix,
    query_instruction_prefix,
    merge_instruction_suffix,
)

# CONSTANTS AND INITIALISATION
# Models switched to Claude Sonnet 4.5 for improved performance
# Set ANTHROPIC_API_KEY environment variable to use Claude models
# To use Gemini instead, set LLM_PROVIDER=gemini and GOOGLE_API_KEY

# Primary model configuration (Claude Sonnet 4.5)
DIALOGUE_MODEL = ClaudeSonnet45Model(temperature=0.8, max_tokens=1500)
SUMMARY_MODEL = ClaudeSonnet45Model(temperature=0.2, max_tokens=5000)
QUERY_MODEL = ClaudeSonnet45Model(temperature=0.2, max_tokens=300)

# Alternative: Use Gemini Flash 2.5 (uncomment to switch)
# DIALOGUE_MODEL = GeminiFlash25NoThinking(temperature=0.8, max_tokens=1500)
# SUMMARY_MODEL = GeminiFlash25NoThinking(temperature=0.2, max_tokens=5000)
# QUERY_MODEL = GeminiFlash25NoThinking(temperature=0.2, max_tokens=300)

# DIALOGUE_MODEL = InstructO1()
# QUERY_MODEL = InstructO1()

# DIALOGUE_MODEL = InstructSonnet(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructSonnet(temperature=1.0, max_tokens=3000)


GAME = "act_1"
ACTORS = ["Eliza", "Player"]


def load_prompt(filename):
    cwd = os.path.abspath(os.getcwd())
    prompt_path = os.path.join(cwd, "project_one_demo", "prompts", filename)
    with open(prompt_path) as f:
        return f.read()


def resource_path():
    cwd = os.path.abspath(os.getcwd())
    relative_path = "/project_one_demo/prompts"
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
        print(RED + f'File "{file}" not found')
        return ""  # Return an empty string if the file doesn't exist
    

def load_act_file(file) -> str:
    file_path = resource_path() + f"/act_1/{file}.txt"
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        print(RED + f'File "{file}" not found')
        return ""  # Return an empty string if the file doesn't exist


def load_scene_file(scene_name: str, suffix: str) -> str:
     # we need to remove the first digit and underscore, e.g. 1_ from the scene_name for the file name
    scene_name_file = scene_name[2:]
    file_path = resource_path() + f"/act_1/scenes/{scene_name}/{scene_name_file}_{suffix}.txt"
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        print(RED + f'File "{file_path}" not found')
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
    steer_back_instructions = load_root_file("steer_back_instructions")
    dialogue_instruction_prefix = load_root_file("dialogue_instruction_prefix")
    summary_instruction_prefix = load_root_file(
        "summary_instruction_prefix"
    )
    merge_instruction_prefix = load_root_file(
        "merge_instruction_prefix"
    )
    back_story = load_act_file("back_story")
    opening_speech = load_opening_speech(scene_name)
    queries = load_queries(scene_name)
    return SceneData(
        scene_name=scene_name,
        scene_description=scene_description,
        steer_back_instructions=steer_back_instructions,
        scene_supplement=scene_supplement,
        dialogue_instruction_prefix=dialogue_instruction_prefix,
        back_story=back_story,
        opening_speech=opening_speech,
        queries=queries,
        actors=ACTORS,  # Pass game-specific actors list
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
        chain = prompt_llm(prompt, SUMMARY_MODEL)
        return chain.invoke({})

    def generate_merge_summary(self, summary: str) -> str:
        prompt = merge_instruction_template.format(
            preamble=self.scene_data.merge_preamble,
            dialogue=self.scene_dialogue,
            instruction_suffix=merge_instruction_suffix,
            prev_summary=self.dialogue_summary,
            new_summary=summary,
        )
        chain = prompt_llm(prompt, SUMMARY_MODEL)
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
            self.scene_dialogue = self.scene_data.get_initial_dialog(
                print_callback=lambda msg: print(GREEN + msg)
            )
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

    def add_luna_commands(self, message: str, luna_message: str = ""):
        self.scene_dialogue += "[Player]: " + message + "\n\n"

        # if self.scene_data.scene_name == "4_find_exit" and luna_message:
        #     print(GREEN + f'Adding Luna message: "{luna_message}"')
        #     self.scene_dialogue += "[Luna]: " + luna_message + "\n\n"
        #     self.handle_player_response(luna_message, False, True)

    def handle_player_response(
        self, message: str, automated: bool, from_luna: bool = False
    ) -> Tuple[List[Line], List[StateChange]]:
        if message:
            print(CYAN + f'Handling player response: "{message}"')
            if False:
                self.scene_dialogue += "Eliza to comment on " + message + "\n"
            else:
                if not from_luna:
                    player_dialogue = speech_template.format(
                        actor=ACTORS[1], speech=message
                    )
                    self.scene_dialogue += player_dialogue + "\n"
            result_lines = []
            if not from_luna:
                state_changes, to_print = self.scene_data.run_queries(
                    self.scene_dialogue,
                    QUERY_MODEL,
                    print_callback=lambda msg: print(ORANGE + msg) if "Query for" in msg or "Query passed" in msg else print(YELLOW + msg)
                )
                if to_print:
                    self.scene_dialogue += to_print + "\n\n"
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

                eliza_response = eliza_response.split("\nComputer", 1)[0]

                # print(ORANGE + f"Eliza response post processed: {eliza_response}")

                self.scene_dialogue += eliza_response + "\n"
                state_changes2, to_print = self.scene_data.run_queries(
                    self.scene_dialogue,
                    QUERY_MODEL,
                    print_callback=lambda msg: print(ORANGE + msg) if "Query for" in msg or "Query passed" in msg else print(YELLOW + msg)
                )

                if to_print:
                    self.scene_dialogue += to_print + "\n\n"

                print(CYAN + f"Scene dialogue: {self.scene_dialogue}")
                
                if not from_luna:
                    state_changes.extend(state_changes2)
                else:
                    state_changes = state_changes2

                eliza_text = (
                    str(eliza_response).strip().removeprefix(f"[{ACTORS[0]}]: ")
                )
                eliza_text = eliza_text.replace('"', "")
                eliza_text = eliza_text.replace("*", "")
                # eliza_text = re.sub(r'\(.*?\)', 'uh', eliza_text)
                result_lines = [Line(text=eliza_text, delay=0)]

                if self.scene_data.all_queries_handled():
                    print(
                        ORANGE
                        + f"All queries for {self.scene_data.scene_name} complete, autoloading next scene"
                    )
                    if self.load_next_scene():
                        result_lines.extend(self.scene_data.opening_speech)

            return result_lines, state_changes
