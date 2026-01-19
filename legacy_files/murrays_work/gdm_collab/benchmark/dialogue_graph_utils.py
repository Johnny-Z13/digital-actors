from typing import List

from benchmark import dialogue_graph as dg
import pydantic


class TokenizedDialogueLine(pydantic.BaseModel):
    role: str
    text: str


def format_dialogue_line(role: str, text: str) -> str:
    """Unified formatter for the dialogue lines.
    
    Creates dialogue lines that can be parsed using tokenize_dialogue_line
    """
    return f"{role}: {text}"


def tokenize_dialogue_line(line: str) -> TokenizedDialogueLine:
    """Tokenizes a dialogue line into its constituent parts - role and the text.
    
    Example:
        input: "Role: some text over here, the text may contain colon characters : such as that one"
        output: role="Role"; text="some text over here, the text may contain colon characters : such as that one"
    """
    role, text = line.split(": ", 1)
    return TokenizedDialogueLine(role=role, text=text)


def is_narrator(role: str) -> bool:
    return role.lower() == "narrator"


def dumps_full_state(dialogue: dg.Dialogue, state: dg.DialogueState) -> str:
    all_facts = "\n".join(dialogue.facts)
    all_styles = "\n".join(dialogue.comm_style)
    all_goals = "\n".join(dialogue.goals)
    chat_history = "\n".join(state.chat_history)
    return f"<dialogue_state_start>\n<facts_start>\n{all_facts}\n<facts_end>\n\n<style_start>\n{all_styles}\n<style_end>\n\n<goals_start>\n{all_goals}\n<goals_end>\n\n<chat_history_start>\n{chat_history}\n<chat_history_end>\n<dialogue_state_end>"


def get_roles(dialogue_state: dg.DialogueState) -> List[str]:
    """Returns a list of roles that participate in a dialogue.
    
    The roles are retrieved from the chat history.
    """
    roles = set()
    for chat_line in dialogue_state.chat_history:
        tokenized_line = tokenize_dialogue_line(line=chat_line)
        if tokenized_line.role and not is_narrator(tokenized_line.role):
            roles.add(tokenized_line.role)

    return list(sorted(roles))
