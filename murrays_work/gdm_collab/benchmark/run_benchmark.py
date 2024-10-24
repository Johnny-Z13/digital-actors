"""
Usage:
python -m benchmark.run_benchmark --model=[gpt4,sonnet,llama3.1:8b] [--baseline]
"""
import argparse
import asyncio
import concurrent
import os
import pathlib
import time
from typing import Optional
import uuid

from benchmark import agent_interface
from benchmark import dataset_utils
from benchmark import task_runner
from benchmark import dialogue_graph as dg
from iconic_tools import langchain   # type: ignore
from langchain_ollama.llms import OllamaLLM
from langchain_core.language_models.llms import LLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd  # type: ignore

_MAX_TOKENS = 4096

class NaiveVirtualActor:

    def __init__(self, model: LLM) -> None:
        parser = JsonOutputParser(pydantic_object=agent_interface.VirtualActorResponse)
        prompt = ChatPromptTemplate.from_template(
"""
Given the following dialogue, predict the next line in that dialogue.

Do not return any text that is not the JSON. Follow these instructions:\n{output_instructions}

Here's the dialogue until now, along with the contextual information:
{dialogue}
"""
        )
        self.chain = prompt | model | parser
        self.output_format = parser.get_format_instructions()

    def generate_next_line(self, dialogue_state: str) -> agent_interface.VirtualActorResponse:
        response_dict = self.chain.invoke({
            "dialogue": dialogue_state,
            "output_instructions": self.output_format,
        })  
        return agent_interface.VirtualActorResponse(**response_dict)


class ResultsFileLock:

    def __init__(self, filepath: pathlib.Path) -> None:
        self._filepath = filepath
        self._lock_file = self._filepath.parent / "benchmark_results.lock"
        self._lock_id = str(uuid.uuid4())

    def __enter__(self) -> Optional[pd.DataFrame]:
        while True:
            if self._lock_file.exists() and self._lock_file.read_text() != self._lock_id:
                time.sleep(0.001)
            else:
                break
        self._lock_file.write_text(self._lock_id)

        return pd.read_csv(str(self._filepath)) if self._filepath.exists() else None
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._lock_file.exists() and self._lock_file.read_text() != self._lock_id:
            raise RuntimeError("Lock file with a wrong ID detected, possible race condition in progress")
        
        self._lock_file.unlink()


class ResultsLog:

    def __init__(self, filename: str) -> None:
        benchmark_root = pathlib.Path(f"{dataset_utils.find_workspace_root()}/benchmark")
        results_folder = benchmark_root / "results"
        # Make sure the folder exists
        os.makedirs(results_folder, exist_ok=True)
        self._results_file = results_folder / filename

    def __len__(self) -> int:
        with ResultsFileLock(self._results_file) as results_df:
            return len(results_df) if results_df is not None else 0

    def add_result(self, task_results: pd.DataFrame) -> None:
        with ResultsFileLock(self._results_file) as results_df:
            if results_df is None:
                results_df = task_results
            else:
                results_df = pd.concat([results_df, task_results])
            results_df.to_csv(str(self._results_file), index=False)

    def __enter__(self) -> 'ResultsLog':
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass


def time_me(async_func):
    async def wrapper(*args, **kwargs):
        start_timestamp = time.time()
        try:
            await async_func(*args, **kwargs)
        finally:
            end_timestamp = time.time()

            elapsed_time = time.gmtime(end_timestamp - start_timestamp)
            print(f"Total runtime: {time.strftime("%H:%M:%S", elapsed_time)}")
    
    return wrapper


def execute_coroutine_in_process(args):
    loop = asyncio.new_event_loop()
    results_log, coroutine, kwargs = args
    task_results = loop.run_until_complete(coroutine(**kwargs))
    results_log.add_result(task_results)


class BaselineAgent:
    def __init__(self, final_state: dg.DialogueState) -> None:
        self.final_state = final_state

    def generate_next_line(self, dialogue_state: str) -> agent_interface.VirtualActorResponse:
        for i, line in enumerate(self.final_state.chat_history):
            role, text = line.split(":", 1)
            text = text.strip()  # Remove any extra spaces
            if text not in dialogue_state:
                is_last = (i == len(self.final_state.chat_history) - 1)
                return agent_interface.VirtualActorResponse(
                    role=role,
                    text=text,
                    is_last=is_last
                )

@time_me
async def bechmark_run(model: LLM, agent: agent_interface.VirtualActor, eval_llm_id: str, agent_llm_id: str):
    with ResultsLog(f"benchmark_results_{agent_llm_id}_eval_by_{eval_llm_id}.csv") as results_log:
        skip_tasks = len(results_log)
        if skip_tasks > 0:
            print(f"Found a previous checkpoint and skipping {skip_tasks} tasks")

        task_args = []
        task_idx = -1
        for task in dataset_utils.Tasks:
            for initial_state, _ in dataset_utils.task_scenes(task):
                task_idx += 1
                if task_idx < skip_tasks:
                    continue

                task_args.append((
                    results_log,
                    task_runner.eval_agent, 
                    dict(
                        task_idx=task_idx, 
                        task=task, 
                        initial_state=initial_state, 
                        agent=agent, 
                        metric_calc_llm=model
                    )
                ))


        # wait for all of the tasks to be processed
        with concurrent.futures.ProcessPoolExecutor() as executor:
            executor.map(execute_coroutine_in_process, task_args)


@time_me
async def baseline_run(model: LLM, llm_id: str):
    with ResultsLog(f"baseline_results_{llm_id}.csv") as results_log:
        skip_tasks = len(results_log)
        if skip_tasks > 0:
            print(f"Found a previous checkpoint and skipping {skip_tasks} tasks")

        task_args = []
        task_idx = -1
        for task in dataset_utils.Tasks:
            for initial_state, final_state in dataset_utils.task_scenes(task):
                task_idx += 1
                if task_idx < skip_tasks:
                    continue

                agent = BaselineAgent(final_state)

                task_args.append((
                    results_log,
                    task_runner.eval_agent,
                    dict(
                        task_idx=task_idx, 
                        task=task, 
                        initial_state=initial_state,
                        agent=agent.generate_next_line,
                        metric_calc_llm=model,
                        max_lines=200
                    )
                ))

        # wait for all of the tasks to be processed
        with concurrent.futures.ProcessPoolExecutor() as executor:
            executor.map(execute_coroutine_in_process, task_args)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run benchmark with specified model.")
    parser.add_argument('--model', type=str, choices=['gpt4', 'sonnet', 'llama', 'gemini'], required=True, help='Model to use for benchmarking')
    parser.add_argument('--agent_model', type=str, choices=['gpt4', 'sonnet', 'llama', 'gemini'], default='gpt4',
                        help='Model to use for benchmarking')
    parser.add_argument('--baseline', action='store_true', help='If True, evaluate human baseline. Otherwise evaluate an agent.')
    return parser.parse_args()
   

async def main():
    args = parse_arguments()
    if args.model == 'gpt4':
        print("Using GPT4")
        model = langchain.InstructGPT4(temperature=0, max_tokens=_MAX_TOKENS)
    elif args.model == 'sonnet':
        print("Using Sonnet")
        model = langchain.InstructSonnet(temperature=0, max_tokens=_MAX_TOKENS)
    elif args.model == 'gemini':
        print("Using Gemini 1.5")
        model = langchain.InstructGeminiPro(temperature=0, max_tokens=_MAX_TOKENS)
    elif args.model == 'llama':
        print("Using LLAMA 3.1:70B")
        model = OllamaLLM(model='llama3.1:70b')


    if args.baseline:
        await baseline_run(model, args.model)
    else:
        if args.agent_model == 'gpt4':
            print("Using GPT4 agent")
            agent_model = langchain.InstructGPT4(temperature=0.5, max_tokens=_MAX_TOKENS)
        elif args.agent_model == 'sonnet':
            print("Using Sonnet agent")
            agent_model = langchain.InstructSonnet(temperature=0.5, max_tokens=_MAX_TOKENS)
        elif args.agent_model == 'gemini':
            print("Using Gemini 1.5 agent")
            agent_model = langchain.InstructGeminiPro(temperature=0.5, max_tokens=_MAX_TOKENS)
        elif args.agent_model == 'llama':
            print("Using LLAMA 3.1:70B agent")
            agent_model = OllamaLLM(model='llama3.1:70b')
        agent = NaiveVirtualActor(agent_model)
        await bechmark_run(model, agent.generate_next_line, args.model, args.agent_model)


if __name__ == "__main__":  
    asyncio.run(main())

