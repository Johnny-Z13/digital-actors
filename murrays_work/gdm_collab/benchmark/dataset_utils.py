import enum
import json
import os
import pathlib
import re
from typing import Generator, List, Tuple

from benchmark import dialogue_graph as dg
import pandas as pd  # type: ignore



def _is_all_caps_line(line: str) -> bool:
    no_lower_alpha = len(list(filter(str.islower, line))) == 0
    alpha_present = len(list(filter(str.isalpha, line))) > 0
    return alpha_present and no_lower_alpha


def _is_page_number(line: str) -> bool:
    return re.match(r"\d+\.?", line) is not None


def _num_leading_whitespaces(line: str) -> int: 
    stripped_line = line.lstrip()
    num_leading_chars = len(line) - len(stripped_line)

    return num_leading_chars

def _any_alpha_chars(text: str) -> bool:
    return len(list(filter(str.isalpha, text))) > 0


def _base_indent(lines, title_offset: int = 5):
    min_indent = 1000
    for line_idx, line in enumerate(lines[title_offset:]):
        if len(line) <= 1:
            continue

        indent = _num_leading_whitespaces(line)
        
        min_candidate = min(indent, min_indent)
        if _any_alpha_chars(line[:min_candidate]):
            raise ValueError(f"Rejected indentation in line {line_idx + title_offset + 1} contains alpha characters: {line[:min_candidate]}")

        min_indent = min_candidate
    return min_indent


def normalize_script(script):
    lines = script.split("\n")
    indent = _base_indent(lines)
    normalized_lines = []
    for line in lines:
        line_without_indent = line[indent:]
        
        # ignore empty lines
        stripped_line = line_without_indent.strip()
        if len(stripped_line) == 0:
            continue

        # ignore "page numbers"
        if _is_page_number(stripped_line):
            continue

        if len(line_without_indent) > 1:
            normalized_lines.append(line_without_indent)
    return normalized_lines


def _normalize_role(role: str) -> str:
    role = role.split("(CONT'D)")[0]
    role = role.split("(O.S.)")[0]
    role = role.split("(V.O.)")[0]
    role = role.strip()
    return role


def _normalize_dialogue_line(line: str) -> str:
    return line.strip()


class EScriptLineType(enum.Enum):
    SectionTitle = 1
    Context = 2
    Role = 3
    Dialogue = 4
    Unknown = 5


def _tokenize_normalized_script(normalized_script):
    def is_section_title_line(line: str):
        return _is_all_caps_line(line) and not str.isspace(line[0])

    def is_context_line(line: str):
        return not _is_all_caps_line(line) and not str.isspace(line[0])

    def is_dialogue_start_line(line: str):
        return _is_all_caps_line(line) and str.isspace(line[0])

    def is_dialogue_content_line(line: str):
        return not _is_all_caps_line(line) and str.isspace(line[0])

    for line in normalized_script:
       
        if is_section_title_line(line):
            yield EScriptLineType.SectionTitle, line
        elif is_context_line(line):
            yield EScriptLineType.Context, line
        elif is_dialogue_start_line(line):
            yield EScriptLineType.Role, line
        elif is_dialogue_content_line(line):
            yield EScriptLineType.Dialogue, line
        else:
            yield EScriptLineType.Unknown, line


def split_into_sections(normalized_script):
    section = None
    for token, line in _tokenize_normalized_script(normalized_script):
        if token == EScriptLineType.SectionTitle:
            if section is not None:
                yield section
            section = []
        
        if section is not None:
            section.append(line)

    if section is not None:
        yield section



class _SceneContext:
    def __init__(self) -> None:
        self.lines: List[str] = []

    def add(self, line: str):
        if line:
            self.lines.append(line.strip())

    def __repr__(self):
        return "Context\n" + "\n".join(self.lines)


class _DialogueLine:
    
    def __init__(self, character_name: str) -> None:
        self.character_name = character_name.strip()
        self.lines: List[str] = []

    def add(self, line: str):
        if line:
            self.lines.append(line.strip())

    def __repr__(self):
        return self.character_name + ": " + "\n".join(self.lines)


class _Narrator:
    def __init__(self) -> None:
        self.lines: List[str] = []

    def add(self, line: str):
        if line:
            self.lines.append(line.strip())

    def __repr__(self):
        return "Narrator: " + "\n".join(self.lines)


def parse_section(section_normalized_lines):
    section_elements = []
    current_entry = _SceneContext()

    for line_idx, (token, line) in enumerate(_tokenize_normalized_script(section_normalized_lines)):
        if token == EScriptLineType.Context:
            if not isinstance(current_entry, _SceneContext) and not isinstance(current_entry, _Narrator):
                section_elements.append(current_entry)
                current_entry = _Narrator()
            current_entry.add(line)
        elif token == EScriptLineType.Role:
                section_elements.append(current_entry)
                current_entry = _DialogueLine(character_name=line)
        elif token == EScriptLineType.Dialogue:
            if not isinstance(current_entry, _DialogueLine):
                # This is a new dialogue line
                section_elements.append(current_entry)

                character_name = line
                # check if this might be a continuation of the previous dialogue line
                if len(section_elements) > 1 and isinstance(section_elements[-1], _Narrator) and isinstance(section_elements[-2], _DialogueLine):
                    # this is a continuation
                    character_name = section_elements[-2].character_name
                current_entry = _DialogueLine(character_name=character_name)
            else:
                # Add text to the dialogue line
                current_entry.add(line)
        elif token == EScriptLineType.SectionTitle:
            if not isinstance(current_entry, _SceneContext):
                raise ValueError(f"Line {line_idx + 1}: Section title can only be added to SceneContext entry. The current entry is {type(current_entry)}")
            current_entry.add(line)

        
    section_elements.append(current_entry)
    
    return section_elements


def section_to_scene(section_elements) -> Tuple[dg.Dialogue, dg.DialogueState]:
    scene = dg.Dialogue()
    state = dg.DialogueState()

    for elem in section_elements:
        if isinstance(elem, _SceneContext):
            scene.facts.append("\n".join(elem.lines))
        elif isinstance(elem, _DialogueLine):
            role = _normalize_role(elem.character_name)
            dialogue_line = _normalize_dialogue_line(" ".join(elem.lines))
            if role and dialogue_line:
                state.chat_history.append(f"{role}: {dialogue_line}")
        elif isinstance(elem, _Narrator):
            fact = "".join(elem.lines)
            state.chat_history.append(f"Narrator: {fact}")

    return scene, state


def title_path(genre: str, title: str) -> str:
    title = title.replace(" ", "_").replace("/", "").lower()
    genre = genre.lower()

    return f"{genre}/{title}"


def scene_path(genre: str, title: str, scene_idx: int) -> str:
    title = title.replace(" ", "_").replace("/", "").lower()
    genre = genre.lower()

    folder = title_path(genre=genre, title=title)
    return f"{folder}/{genre}_{title}_scene_{scene_idx}.json"


def num_scenes_in_title(genre: str, title: str) -> int:
    all_files = list(pathlib.Path(title_path(genre=genre, title=title)).glob("*.json"))
    return len(all_files) // 2


def normalize_title(title: str) -> str:
    return title.replace(" ", "_").replace("/", "").replace(".", "").replace(":", "").replace(",", "").replace("(", "").replace(")", "").lower()


def find_workspace_root():
    current_path = os.path.abspath(os.path.dirname(__file__))
    while True:
        if os.path.isdir(os.path.join(current_path, 'benchmark')):
            return current_path
        new_path = os.path.dirname(current_path)
        if new_path == current_path:
            raise FileNotFoundError("Could not find 'benchmark' folder in any parent directory")
        current_path = new_path


def load_scene(genre: str, title: str, scene_idx: int) -> Tuple[dg.Dialogue, dg.DialogueState]:
    title = normalize_title(title)
    genre = genre.lower()

    folder = title_path(genre=genre, title=title)
    workspace_root = find_workspace_root()
    with open(f"{workspace_root}/benchmark/dataset/{folder}/{genre}_{title}_scene_{scene_idx}.json") as f_scene:
        scene = dg.Dialogue.deserialize(json.load(f_scene))

    with open(f"{workspace_root}/benchmark/dataset/{folder}/{genre}_{title}_state_{scene_idx}.json") as f_state:
        state = dg.DialogueState.deserialize(json.load(f_state))

    return scene, state


class Tasks(enum.Enum):
    SCENE_SIZE = "scene_size"
    INTERACTIVITY = "interactivity"
    EMOTIONS = "emotions"
    ADVERSARIAL = "adversarial"


def task_scenes(task: Tasks) -> Generator[Tuple[dg.Dialogue, dg.DialogueState], None, None]:
    workspace_root = find_workspace_root()
    df = pd.read_csv(f"{workspace_root}/benchmark/dataset/task_dataset.csv")

    task_rows = df[df.task == task.value]
    for _, row in task_rows.iterrows():
        genre, title, scene_idx = row.genre, row.title, row.scene_idx
        initial_state, final_state = load_scene(genre=genre, title=title, scene_idx=scene_idx)
        yield initial_state, final_state


def load_subtitles(genre: str, title: str) -> List[str]:
    """Loads subtitles from an .srt file located in benchmark/dataset/{genre} folder.

    The name of the file corresponds to the normalized name of the movie title, 
    eg. Black Rain -> black_rain.srt
    """
    genre_normalized = genre.lower()
    title_normalized = normalize_title(title)
    workspace_root = find_workspace_root()

    subtitles_raw = pathlib.Path(f"{workspace_root}/benchmark/dataset/{genre_normalized}/{title_normalized}.srt").read_text()
    entries = subtitles_raw.split("\n\n")
    subtitles: List[str] = []
    for entry in entries:
        lines = entry.split("\n")
        entry_idx = int(lines[0])
        entry_text = " ".join(lines[2:])

        if entry_idx - 1 != len(subtitles):
            raise RuntimeError(f"We appear to be missing an entry: {entry_idx - 1} != {len(subtitles)}\n{entry}")
        
        subtitles.append(entry_text)

    return subtitles
