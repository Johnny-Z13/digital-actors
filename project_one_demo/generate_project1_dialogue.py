import os
import sys
import re
import math
from iconic_tools.langchain import InstructSonnet, InstructOpus3, InstructGPT4, InstructO1, InstructGeminiPro, InstructGPT35, InstructGeminiFlash
from langchain_core.prompts import ChatPromptTemplate
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple, List, Tuple
from dataclasses import dataclass, field

# CONSTANTS AND INITIALISATION
# DIALOGUE_MODEL = InstructGeminiPro(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructGeminiPro(temperature=1.0, max_tokens=3000)

# DIALOGUE_MODEL = InstructGPT4(temperature=1.0, max_tokens=3000)
# QUERY_MODEL = InstructGPT4(temperature=1.0, max_tokens=3000)

DIALOGUE_MODEL = InstructGeminiFlash(temperature=1.0, max_tokens=3000)
QUERY_MODEL = InstructGeminiFlash(temperature=1.0, max_tokens=3000)

#DIALOGUE_MODEL = InstructO1()
#QUERY_MODEL = InstructO1()

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


# PROMPT TEMPLATES AND INSTRUCTION PROMPTS
dialogue_instruction_prefix = """
You are going to generate one line of dialogue for a scene in the middle of a computer game.
"""

preamble_template = """
{instruction_prefix}
This is the game back story. {back_story}\n
Here is a description of the scene in question. {scene_description}{scene_supplement}\n
The characters in the dialogue are {actors}.
"""

instruction_template = """
{preamble}
Here is the dialogue so far\n\n
{dialogue}
{instruction_suffix}
"""

speech_template = '[{actor}]: {speech}\n'

dialogue_instruction_suffix = """
Give me the next line in the dialogue in the same format. Don't provide stage directions, just the character's words. Don't give me a line for the player, but for one of the other characters.\n
"""

query_preamble_template = """
{instruction_prefix}
This is the game back story. {back_story}\n
"""

query_instruction_prefix = """
You are going to answer a single question about the current state of the dialogue in a scene in the middle of a computer game.
"""

query_instruction_suffix_template = """
Now consider the following statement about this dialogue. {statement} Is this statement true or false? Answer with a single word, true or false.
"""

naive_dialogue_prompt = """
Given the following dialogue, predict the next line in that dialogue. Respond with the next line only. Use the same format as the dialogue so far. Don't provide stage directions, just the actor's words. Here's the dialogue until now, along with the contextual information:
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
    query_printed: bool = False  # When this query is evaluated a message is printed to the NPC dialogue
    query_printed_text_true: str = ""
    query_printed_text_false: str = ""

@dataclass
class SceneData:
    scene_name: str
    scene_description: str
    scene_supplement: str
    back_story: str
    opening_speech: List[Line]
    queries: List[Query]

    dialogue_preamble: str = ""
    query_preamble: str = ""


    def __post_init__(self):
        self.dialogue_preamble = preamble_template.format(instruction_prefix=dialogue_instruction_prefix, back_story=self.back_story, scene_description=self.scene_description, scene_supplement=self.scene_supplement, actors=list_to_conjunction(ACTORS))
        self.query_preamble = preamble_template.format(instruction_prefix=query_instruction_prefix, back_story=self.back_story, scene_description="", scene_supplement="", actors=list_to_conjunction(ACTORS))

    def __str__(self):
        field = "\033[97m" 
        text = "\033[90m"
        reset = "\033[0m"
        return f"{field}SceneData\n{{\n   scene_name:{text} {self.scene_name}\n{field}   scene_description:{text}  {self.scene_description}\n{field}   scene_supplement:{text} {self.scene_supplement}\n{field}   back_story:{text} {self.back_story}\n{field}   opening_speech:{reset}\n{self.opening_speech}\n{field}   queries:{reset}\n{self.queries}\n{field}}}{reset}"   

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
                instruction = query_instruction_suffix_template.format(statement=query.text)
                prompt = instruction_template.format(preamble=self.query_preamble, dialogue=dialogue, instruction_suffix=instruction)
                chain = prompt_llm(prompt, DIALOGUE_MODEL)
                response = chain.invoke({})
                print(ORANGE + f"Query for \"{query.text}\" - response: \"{response}\"")
                if response[0:4].lower() == "true":
                    query.handled = True
                    print(YELLOW + f"Query passed for \"{query.text}\" - returning state_id \"{query.state_changes}\"")
                    if query.query_printed:
                        to_print = query.query_printed_text_true
                    state_changes.extend(query.state_changes)
                    break
                else:
                    if query.query_printed:
                        to_print = query.query_printed_text_false
                    break
                    
        return state_changes, to_print

    def all_queries_handled(self) -> bool:
        return all(query.handled for query in self.queries)
    

def resource_path():
    cwd = os.path.abspath(os.getcwd())
    relative_path = "/project_one_demo/prompts"
    return cwd + relative_path
    # Get the absolute path to the resource in both development and PyInstaller environments
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller environment
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # Development environment
        return os.path.join(os.path.abspath("."), relative_path)


def load_root_file(file) -> str:
    file_path = resource_path() + f"/{file}.txt"
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""  # Return an empty string if the file doesn't exist
    
def load_scene_file(scene_name:str, suffix:str) -> str:
    file_path = resource_path() + f"/scenes/{scene_name}/{scene_name}_{suffix}.txt"
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""  # Return an empty string if the file doesn't exist

def load_queries(scene_name:str) -> List[Query]:
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
        if line.startswith('[') and line.endswith(']'):
            # Remove brackets and parse state changes
            state_changes = []
            state_changes_text = line[1:-1]  # Remove [ and ]
            state_parts = state_changes_text.split(',')
            
            for part in state_parts:
                name, value = map(str.strip, part.split('='))
                state_changes.append(StateChange(name=name.strip(), value=value.strip()))

        elif line.startswith('(') and line.endswith(')'):
            query_printed = True
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
                queries.append(Query(text=query_text, state_changes=state_changes, query_printed=query_printed,
                             query_printed_text_true=query_printed_text_true, query_printed_text_false=query_printed_text_false))
                state_changes = []
                
            # Update query_text to the current line
            query_text = line

    # Add the last query if there is one
    if query_text is not None:
        queries.append(Query(text=query_text, state_changes=state_changes, query_printed=query_printed,
                             query_printed_text_true=query_printed_text_true, query_printed_text_false=query_printed_text_false))

    return queries


def load_opening_speech(scene_name:str) -> List[Line]:
    lines = []
    file = load_scene_file(scene_name, "opening_speech")
    for line in file.splitlines():
        # Remove any leading or trailing whitespace
        line = line.strip()
        if not line:
            continue  # Skip empty lines
        
        # Match optional scene ID at the start of the line
        match = re.match(r'^\[(\d+(\.\d+)?)\]\s+(.+)$', line)
        if match:
            delay = float(match.group(1))
            text = match.group(3)
        else:
            delay = 0  # Empty if no scene ID is present
            text = line
        
        # Add to list with handled defaulting to False
        lines.append(Line(text=text, delay=delay))  

    return lines


def load_scene_data(scene_name:str) -> SceneData:
    scene_description = load_scene_file(scene_name, "scene_description")
    scene_supplement = load_scene_file(scene_name, "scene_supplement")
    back_story = load_root_file("back_story")
    opening_speech = load_opening_speech(scene_name)
    queries = load_queries(scene_name)
    return SceneData(scene_name=scene_name, scene_description=scene_description, scene_supplement=scene_supplement, back_story=back_story, opening_speech=opening_speech, queries=queries)



gSceneData = None
gSceneDialogue = ""
gScenes = []

def load_next_scene() -> bool:
    global gSceneDialogue, gSceneData, gScenes

    if (gScenes):
        print(CYAN + f"Loading scene \"{gScenes[0]}\"")
        gSceneData = load_scene_data(gScenes.pop(0))
        gSceneDialogue = gSceneData.get_initial_dialog()
        print(gSceneData)
        print(gSceneDialogue)
        return True

    return False

def start_scene(scene: str):
    global gSceneDialogue, gSceneData, gScenes

    if (gScenes and gScenes[0] == scene): # Hacky guard due to events getting sent twice from game
        load_next_scene()
        return gSceneData.opening_speech, []
    
    return [], []

def reset_reponse_handler():
    global gSceneDialogue, gSceneData, gScenes

    gScenes = ["meet_the_caretaker", "locate_an_engineer", "describe_the_failures", "exit_the_room"]
    print(CYAN + f"Starting response handler for scenes: \"{gScenes}\"")
    load_next_scene()

def handle_player_reponse(message:str, automated:bool) -> Tuple[List[Line], List[StateChange]]:
    global gSceneDialogue, gSceneData, gScenes
    if message:
        print(CYAN + f"Handling player repsonse: \"{message}\"")

        if automated:
            gSceneDialogue += "Eliza to comment on " + message + "\n"
        else:
            player_dialogue = speech_template.format(actor=ACTORS[1], speech=message)
            gSceneDialogue += player_dialogue + "\n"

        state_changes, to_print = gSceneData.run_queries(gSceneDialogue)
        print(CYAN + f"Initial state changes: {state_changes}")
        print(CYAN + f"Additional print: {to_print}" + "print_type: " + str(type(to_print)))
        if to_print:
            print(RED + f"Additional print: {to_print}")
            gSceneDialogue += to_print + "\n"

        prompt = instruction_template.format(preamble=gSceneData.dialogue_preamble, dialogue=gSceneDialogue,
                                             instruction_suffix=dialogue_instruction_suffix)
        chain = prompt_llm(prompt, DIALOGUE_MODEL)
        eliza_response = chain.invoke({})
    
        gSceneDialogue += eliza_response + "\n"
        state_changes2, to_print = gSceneData.run_queries(gSceneDialogue)
        print(CYAN + f"Additional state changes: {state_changes2}")

        if to_print:
            gSceneDialogue += to_print + "\n"

        print(CYAN + f"Scene dialogue: {gSceneDialogue}")

        state_changes.extend(state_changes2)
        print(CYAN + f"Combined state changes: {state_changes}")

        eliza_text = str(eliza_response).strip().removeprefix(f"[{ACTORS[0]}]: ")
        eliza_text = eliza_text.replace('"', '') # remove quotes (causes disconnect when sending back via websocket)
        eliza_text = eliza_text.replace('*', '') # remove * used for emphasis on words (eleven laps speaks it)

        print(CYAN + f"Results: text=\"{eliza_text}\" state_changes=\"{state_changes}\"")

        result_lines = [Line(text=eliza_text, delay=0)]

        if gSceneData.all_queries_handled():
            print(ORANGE + f"All queries for {gSceneData.scene_name} complete, autoloading next scene")
            if load_next_scene():
                result_lines.extend(gSceneData.opening_speech)        
    
        return result_lines, state_changes
