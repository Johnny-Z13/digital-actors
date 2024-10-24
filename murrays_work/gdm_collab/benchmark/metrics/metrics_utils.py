from typing import Dict, Tuple, Optional

from benchmark import dialogue_graph as dg
from langchain_core.language_models import llms
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats  # type: ignore


FullDialogueState = Tuple[dg.Dialogue, dg.DialogueState]


def graph_metric_stats(
    dataset: Dict[str, FullDialogueState],
    model: llms.LLM,
    metric_fn,
    n_samples: int = 5,
    evaluated_actor: Optional[str] = None,
) -> None:
    def metric_normal_distr(*metric_args, **metric_kwargs):
        values = [metric_fn(*metric_args, **metric_kwargs) for _ in range(n_samples)]
        mean = np.mean(values)
        ci = stats.sem(values) * stats.t.ppf((1 + 0.95) / 2.0, len(values) - 1)

        return mean, ci

    if evaluated_actor is None:
        precision_scores = [
            (scenario, *metric_normal_distr(model, initial_state, final_state))
            for scenario, (initial_state, final_state) in dataset.items()
        ]
    else:
        precision_scores = [
            (scenario, *metric_normal_distr(model, initial_state, final_state, evaluated_actor))
            for scenario, (initial_state, final_state) in dataset.items()
        ]
    labels, means, cis = zip(*precision_scores)
    plt.figure(figsize=(10, 6))
    plt.bar(labels, means, yerr=cis, capsize=5)
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Scenarios")
    plt.ylabel("Score")
    plt.title("Scores for Different Scenarios")
    plt.tight_layout()
