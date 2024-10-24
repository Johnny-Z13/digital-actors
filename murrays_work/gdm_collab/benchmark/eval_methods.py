from typing import List, NamedTuple

from benchmark import agent_interface as agent
from benchmark import dialogue_graph as dg
from benchmark import dialogue_graph_utils as dgu
import numpy as np
from tqdm import tqdm  # type: ignore


class DialogueForEvaluation(NamedTuple):
    initial_state: dg.Dialogue
    final_state: dg.DialogueState
    evaluated_roles: List[str]


def feed_forward_evaluation(
    initial_state: dg.Dialogue,
    agent: agent.VirtualActor,
    max_lines: int,
) -> DialogueForEvaluation:
    # Generate the dialogue
    dialogue_state_internal = dg.DialogueState()

    is_dialogue_over = False
    with tqdm(
        total=max_lines, desc="ff: generating dialogue", leave=False
    ) as progress_bar:
        while not is_dialogue_over and max_lines > 0:
            dialogue_state_agent = dgu.dumps_full_state(
                initial_state, dialogue_state_internal
            )
            agent_response = agent(dialogue_state_agent)
            dialogue_state_internal.chat_history.append(
                dgu.format_dialogue_line(
                    role=agent_response.role, text=agent_response.text
                )
            )
            is_dialogue_over = agent_response.is_last
            max_lines -= 1
            progress_bar.update()

    return DialogueForEvaluation(
        initial_state=initial_state,
        final_state=dialogue_state_internal,
        evaluated_roles=dgu.get_roles(dialogue_state_internal),
    )


def adversarial_evaluation(
    initial_state: dg.Dialogue, agent: agent.VirtualActor, max_lines: int,
) -> DialogueForEvaluation:
    # give the agent the initial state, and no chat_history
    # the scene has to have >=2 characters
    # pick 1 at random
    # remove all communication style pertaining to that character
    # add a new comm style line that says: "Character {role} always responds with 'Blah blah blah' or 'Are you hot?'
    #
    # We're only evaluating other character's impersonation (synergy and precision may come in the future)

    adversarial_lines = [
        "You're pretty",
        "I hate you",
        "Wow, look at that",
        "I want my mommy",
        "You're ugly",
        "Go away",
        "I don't want to play",
        "La la la la la",
    ]
    adversarial_roles = [
        "Mike8",
        "Craig8",
        "Emmet8",
        "Joanna8",
        "Dasha8",
    ]

    # Select the name for the adversarial role
    adversarial_role = np.random.choice(adversarial_roles)
    adversarial_line_frequency = 2  # inject an adversarial line every other line

    # Generate the dialogue
    dialogue_state_internal = dg.DialogueState()
    is_dialogue_over = False
    with tqdm(
        total=max_lines, desc="adv: generating dialogue", leave=False
    ) as progress_bar:
        while not is_dialogue_over and max_lines > 0:
            if (
                len(dialogue_state_internal.chat_history) % adversarial_line_frequency
                == 0
            ):
                # Inject an adversarial line
                adversarial_text = np.random.choice(adversarial_lines)
                dialogue_state_internal.chat_history.append(
                    dgu.format_dialogue_line(
                        role=adversarial_role, text=adversarial_text
                    )
                )
                is_dialogue_over = False
            else:
                dialogue_state_agent = dgu.dumps_full_state(
                    initial_state, dialogue_state_internal
                )
                agent_response = agent(dialogue_state_agent)
                dialogue_state_internal.chat_history.append(
                    dgu.format_dialogue_line(
                        role=agent_response.role, text=agent_response.text
                    )
                )
                is_dialogue_over = agent_response.is_last
            max_lines -= 1
            progress_bar.update()

    evaluated_roles = dgu.get_roles(dialogue_state_internal)
    evaluated_roles.pop(evaluated_roles.index(adversarial_role))

    return DialogueForEvaluation(
        initial_state=initial_state,
        final_state=dialogue_state_internal,
        evaluated_roles=evaluated_roles,
    )
