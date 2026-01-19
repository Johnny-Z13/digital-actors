from typing import Dict, List, NamedTuple

from benchmark import dialogue_graph as dg
from benchmark import dialogue_graph_utils as dg_utils
from langchain_core.language_models.llms import LLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from benchmark.metrics import features
import numpy as np
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm  # type: ignore


class EstimatePrecisionTemplate(BaseModel):
    justification: str = Field(
        description="List the reasons for your response, do not give your judgment before listing individual reasons explainig why. Start your judgement with 'Let's examine...'. Use \" only for the json, use ' instead when quoting."
    )
    response: float = Field(
        description="The float with the value obtained from your justification."
    )


async def precision(
    model: LLM, initial_state: dg.Dialogue, final_state: dg.DialogueState
) -> float:
    # Assumption here - subtext goals are expressed clearly as a goal in the dialogue context
    precision_feature = (
        "Every single goal has been achieved. Goal achievement may be explicit or implicit. Suggestion of achieving the goal is not enough.",
    )

    # Force it to recall the feature
    prompt = ChatPromptTemplate.from_template(
        """Given the following dialogue: {dialogue}\n\n
        and the following feature: \n---\n{feature}\n---\n
        return a binary value 1 or 0, that represents if the feature is entirely present in the dialogue.
        The value of 0 means that the feature is absent in the dialogue state, 1 means that the feature is entirely present.
        After finalising your list of examples, start your global judgement, starting with "From the individual analisis just listed, given that the feature was: {feature}, the conclusion is that..." 
        Do not return any text that is not the JSON. Follow these instructions:\n{output_instructions}
        """
    )
    parser = JsonOutputParser(pydantic_object=EstimatePrecisionTemplate)
    chain = prompt | model | parser

    state_str = dg_utils.dumps_full_state(initial_state, final_state)
    response_dic = chain.invoke(
        {
            "dialogue": state_str,
            "feature": precision_feature,
            "output_instructions": parser.get_format_instructions(),
        }
    )
    return response_dic["response"]


async def synergy(
    model: LLM,
    initial_state: dg.Dialogue,
    final_state: dg.DialogueState,
    evaluated_actor: str,
) -> float:
    metric_features = [
        f"""{evaluated_actor} consistently acknowledges and responds to inputs from other characters, especially when 
            a response is contextually expected, in a manner consistent with their own character.""",
        f"""{evaluated_actor} generally acknowledges and responds to the emotions and intentions expressed by other 
            characters, in a way that aligns with their own character's traits.""",
        f"""{evaluated_actor} tends to ignore or respond to disruptive lines or specific 
            characters when a response would be appropriate, except in cases the lack of 
            response aligns with {evaluated_actor}'s established behavior.
            """,
    ]

    deltas = np.asarray(
        await features.calculate_metric_delta(
            model, initial_state, final_state, metric_features
        )
    )
    deltas[-1] = 1.0 if deltas[-1] == 0.0 else 0.0
    return np.average(deltas)


async def calculate_style_accuracy(
    model: LLM,
    initial_state: dg.Dialogue,
    delta_state: dg.DialogueState,
    evaluated_actor: str,
) -> float:
    # We assume that every element in the description of the character has equal importance
    comm_style = initial_state.comm_style
    if not comm_style:
        return 1.0
    # Divide each line of the str to get a list of strings
    comm_style = comm_style[0].split("\n")
    # Get only those lines that have evaluated_actor
    comm_style = [line for line in comm_style if evaluated_actor in line]
    if not comm_style:
        return 1.0
    traits = []
    for style_feature in comm_style:
        traits.append(
            f"The actor {evaluated_actor} displayed: {style_feature} between <chat_history_start> and <chat_history_start>"
        )

    results = await features.calculate_metric_delta(
        model, initial_state, delta_state, traits
    )
    return float(np.average(results))


async def impersonation(
    model: LLM,
    initial_state: dg.Dialogue,
    final_state: dg.DialogueState,
    evaluated_actor: str,
) -> float:
    metric_features_0 = [
        f"{evaluated_actor} makes references to the facts between <facts_start> and <facts_end>",
        f"{evaluated_actor} makes references to things said in previous lines of the chat history between <chat_history_start> and <chat_history_start>",
        f"We find one instance where {evaluated_actor} references to things that are not consistent with the information between <facts_start> and <facts_end> or earlier in the chat history between <chat_history_start> and <chat_history_start>",
    ]

    style_score, deltas = await tqdm.gather(
        *[
            calculate_style_accuracy(
                model, initial_state, final_state, evaluated_actor
            ),
            features.calculate_metric_delta(
                model, initial_state, final_state, metric_features_0
            ),
        ]
    )

    deltas[-1] = 0.0 if deltas[-1] == 1.0 else 1.0
    if deltas[0] == 0.0 and deltas[1] == 0.0:
        style_score /= 2
    if deltas[2] == 0.0:
        style_score /= 2
    return style_score


def overall_agent_performance(
    precision: float, synergy: List[float], impersonations: List[float]
) -> float:
    """Calculates the overall Virtual Actor agent performance based on all the metrics.

    Args:
        precision: Precision score for the dialogue the agent generated
        synergy: Synergy score for the dialogue the agent generated
        impersonations: Impersonation scores for those of the roles in the play that
            the agent generated dialogue lines for

    Note:
        If the graded dialogue contained dialogue lines not generated by the agent, do not include
        the impersonation metric values for those roles in the `impersonations` mapping.

    Returns:
        A scalar, either 0 or 1, where 0 indicates the performance was bad, and 1 indicates that it was good.
    """
    p = round(precision)
    s = np.mean(synergy)
    i = np.mean(impersonations)

    # if p == 1 and s == 1 and i >= 0.75:
    #     return 1
    # elif p == 0 and s == 0 and i <= 0.5:
    #     return 0
    # elif p == 0 and s <= 0.5 and i <= 0.25:
    #     return 0
    # else:
    #     return 0
    return float(np.mean([p, s, i]))
    # raise ValueError(f"The overall actor performance is undefined. Partial scores: precision={precision} synergy={synergy} impersonations={impersonations}")


def impersonation_and_synergy_performance(
        synergies: List[float], impersonations: List[float]
    ) -> float:
    s = np.mean(synergies)
    i = np.mean(impersonations)
    return float(np.mean([s, i]))


class EvaluationScores(NamedTuple):
    overall: float
    s_i: float
    partial: Dict[str, float]


async def calculate_scores(
    model: LLM,
    initial_state: dg.Dialogue,
    final_state: dg.DialogueState,
    evaluated_roles: List[str],
):
    """Calculates all relevant scores for a dialogue"""
    # Evaluate the dialogue, for now we are not evaluating precision
    metric_tasks = [
        precision(model=model, initial_state=initial_state, final_state=final_state),
    ]
    for role in evaluated_roles:
        metric_tasks.append(
            synergy(
                model=model,
                initial_state=initial_state,
                final_state=final_state,
                evaluated_actor=role,
            )
        )
        metric_tasks.append(
            impersonation(
                model=model,
                initial_state=initial_state,
                final_state=final_state,
                evaluated_actor=role,
            )
        )

    metric_values = await tqdm.gather(*metric_tasks)

    # calculate the overall score
    overall = overall_agent_performance(
        precision=metric_values[0],
        synergy=metric_values[1: len(evaluated_roles) + 1],
        impersonations=metric_values[len(evaluated_roles) + 1:],
    )

    s_i = impersonation_and_synergy_performance(
        synergies=metric_values[1:len(evaluated_roles)+1],
        impersonations=metric_values[len(evaluated_roles)+1:],
    )

    # prepare partial results
    partial = {
        "precision": metric_values[0],
    }
    for role, synergy_score, impersonation_score in zip(
        evaluated_roles,
        metric_values[:len(evaluated_roles)],
        metric_values[len(evaluated_roles):],
    ):
        partial[f"synergy_{role}"] = synergy_score
        partial[f"impersonation_{role}"] = impersonation_score

    return EvaluationScores(overall=overall, partial=partial, s_i=s_i)
