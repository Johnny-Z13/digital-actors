import time

from benchmark import agent_interface
from benchmark import dialogue_graph as dg
from benchmark import dialogue_graph_utils as dgu
from benchmark import dataset_utils
from benchmark import eval_methods
from benchmark.metrics import metrics
from langchain_core.language_models.llms import LLM
import pandas as pd  # type: ignore


_DEFAULT_MAX_DIALOGUE_LINES = 10


async def eval_final_state(
    task_idx: int,
    task: dataset_utils.Tasks,
    initial_state: dg.Dialogue,
    final_state: dg.DialogueState,
    metric_calc_llm: LLM,
) -> pd.DataFrame:
    start_timestamp = time.time()

    evaluated_roles = dgu.get_roles(final_state)

    results = await metrics.calculate_scores(
        model=metric_calc_llm,
        initial_state=initial_state,
        final_state=final_state,
        evaluated_roles=evaluated_roles,
    )

    end_timestamp = time.time()

    task_results = {
        "task_idx": [task_idx],
        "task": [task.value],
        "score": [results.overall],
        "exec_seconds": [end_timestamp - start_timestamp],
    }
    for metric_id, metric_val in results.partial.items():
        task_results[metric_id] = [metric_val]

    return pd.DataFrame(task_results)


async def eval_agent(
    task_idx: int,
    task: dataset_utils.Tasks,
    initial_state: dg.Dialogue,
    agent: agent_interface.VirtualActor,
    metric_calc_llm: LLM,
    max_lines: int = _DEFAULT_MAX_DIALOGUE_LINES,
) -> pd.DataFrame:
    start_timestamp = time.time()

    if task == dataset_utils.Tasks.ADVERSARIAL:
        dialogue_for_eval = eval_methods.adversarial_evaluation(
            initial_state=initial_state, agent=agent, max_lines=max_lines
        )
    else:
        dialogue_for_eval = eval_methods.feed_forward_evaluation(
            initial_state=initial_state, agent=agent, max_lines=max_lines
        )

    results = await metrics.calculate_scores(
        model=metric_calc_llm,
        initial_state=dialogue_for_eval.initial_state,
        final_state=dialogue_for_eval.final_state,
        evaluated_roles=dialogue_for_eval.evaluated_roles,
    )

    end_timestamp = time.time()

    task_results = {
        "task_idx": [task_idx],
        "task": [task.value],
        "score": [results.overall],
        "synergy_impersonation_score": [results.s_i],
        "exec_seconds": [end_timestamp - start_timestamp],
    }
    for metric_id, metric_val in results.partial.items():
        task_results[metric_id] = [metric_val]

    return pd.DataFrame(task_results)
