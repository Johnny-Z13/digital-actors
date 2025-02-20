from typing import Any
import os
import asyncio
import json
from itertools import combinations
import matplotlib.pyplot as plt
from generate_dialogue import load_prompts
from langchain_core.language_models.llms import LLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from pydantic import BaseModel, Field


def load_dialogues_for_variant(scene: str, variant_name: str) -> str:
    """Load and concatenate all dialogue text from the variant's folders for a specific scene.
       Expects 'scene' to be the scene folder name (e.g. "describe_the_failures").
       Assumes dialogues are stored in: <cwd>/dialogues/<act_folder>/<scene>/<variant_name>/*.txt.
    """
    import os, glob
    dialogues = []
    base_path = os.path.join(os.getcwd(), "dialogues")
    # The '*' matches any act folder like "act_1", "act_2", etc.
    pattern = os.path.join(base_path, scene, variant_name, "*.txt")
    for filename in glob.glob(pattern):
        with open(filename, "r", encoding="utf-8") as f:
            dialogues.append(f.read())
    return "\n\n ** new play, same actors ** \n\n".join(dialogues)


def get_scene_context(scene_link: str) -> str:
    """Load the complete scene information using load_prompts (as in sim_mini_scene)
       and compose a context string with back story, scene description, scene supplement and queries.
       Expects scene_link in the format "act/scene".
    """
    act, scene = scene_link.split("/", 1)
    # load_prompts signature: load_prompts(scene, game, supplement_version=-1)
    back_story, _, scene_description, scene_supplement, _, queries, _ = load_prompts(scene, act)
    # Assuming queries is a list of strings (or convertible to strings)
    query_texts = "\n\n".join(str(q) for q in queries)
    scene_context = (
        f"Back Story:\n\n{back_story}\n\n-----\n\n"
        f"Scene Description:\n\n{scene_description}\n\n-----\n\n"
        f"Scene Supplement:\n\n{scene_supplement}\n\n-----\n\n"
        f"Queries, these are the objectives of the scene, a scene is not considered succesful unless all of these statement are satisfied in the dialogue:\n\n{query_texts}"
    )
    return scene_context


class GenerateEmbeddingTemplate(BaseModel):
    review: str = Field(
        description="Your critic review structured in three parts detailed above."
    )
    value: int = Field(
        description="""The int with the value obtained from your justification.
                    1 if the first set of actors performed better, 2 if the second set performed better, 
                    0 if they performed equally well."""
    )


async def contrast_set_actors(
    model: LLM, set_actor_1: str, set_actor_2: str, scene: str, evaluated_actors: str,
) -> dict[str, Any]:
    eval_prompt = ChatPromptTemplate.from_template(
        """You are evaluating and contrasting the quality of the dialogues of a set of actors in the middle of a
         computer videogame. Here is the contextual information of the game and the scene: \n---\n {scene}\n---\n
         Your review focuses on the quality of the dialogues of the actors {evaluated_actors} in the scene.
         Since the actors need to improv and adap to what players might say, you are to evaluate the actors
         across several instances. Below are the dialogues of the first set of actors:
        \n---\n {set_actor_1}\n---\n
        And below are the dialogues of the second set of actors:
        \n---\n {set_actor_2}\n---\n
        Your output is in json format. It starts with a "review" field, where you write your review.
        Your review is structured in the following format: First, it lists the most relevant good and bad points of the
        dialogues of each set of actors; following a format like this: "Good points for the first set of actors...
        Good points for the second set of actors... Bad points for the first set... Good points for the second set...".
        Second, your review continues by contrasting the good and bad points of each set of actors. Third, your
        review ends with a global judgement of which set of actors performed better.
        The output json will have a "value" field, which will be 1 if the first set of actors performed better,
        2 if the second set of actors performed better, and 0 if they performed equally.
        Do not return any text that is not the JSON. Format your output according to these instructions:
        \n{output_instructions}
        """
    )
    parser = JsonOutputParser(pydantic_object=GenerateEmbeddingTemplate)
    chain = eval_prompt | model | parser

    response = chain.invoke(
        {
            "scene": scene,
            "evaluated_actors": evaluated_actors,
            "set_actor_1": set_actor_1,
            "set_actor_2": set_actor_2,
            "output_instructions": parser.get_format_instructions(),
        }
    )

    return response


#TODO: This should be moved to a test file
async def dummy_contrast_set_actors(evaluation_model, dialogue1, dialogue2, scene_context, evaluated_actors):
    # Simulate an asynchronous I/O-bound call (e.g., a network request)
    await asyncio.sleep(0.1)
    # Dummy implementation: randomly choose a winner or tie.
    import random
    return random.choice([{ "value": 1 }, { "value": 2 }, { "value": 0 }])


# -----------------------------------------------------------------------------
# Elo update helper.
# -----------------------------------------------------------------------------
def elo_update(rating1, rating2, score1, score2, k):
    expected1 = 1 / (1 + 10 ** ((rating2 - rating1) / 400))
    expected2 = 1 / (1 + 10 ** ((rating1 - rating2) / 400))
    new_rating1 = rating1 + k * (score1 - expected1)
    new_rating2 = rating2 + k * (score2 - expected2)
    return new_rating1, new_rating2


# -----------------------------------------------------------------------------
# Async function to process a single match between two models.
# -----------------------------------------------------------------------------
async def process_match(evaluation_model, model1, model2, dialogues_by_model, scene_context,
                        evaluated_actors, elo_ratings, k_factor, elo_lock):
    result = await contrast_set_actors(
        evaluation_model,
        dialogues_by_model[model1],
        dialogues_by_model[model2],
        scene_context,
        evaluated_actors
    )
    vote = result.get("value")
    if vote == 1:
        score1, score2 = 1, 0
    elif vote == 2:
        score1, score2 = 0, 1
    else:
        score1, score2 = 0.5, 0.5

    async with elo_lock:
        new_rating1, new_rating2 = elo_update(
            elo_ratings[model1],
            elo_ratings[model2],
            score1,
            score2,
            k_factor
        )
        elo_ratings[model1] = new_rating1
        elo_ratings[model2] = new_rating2


# -----------------------------------------------------------------------------
# Async function to process all matches for a given scene.
# -----------------------------------------------------------------------------
async def process_scene(evaluation_model, act, scene, models, repetitions,
                        evaluated_actors, elo_ratings, k_factor, elo_lock):
    scene_link = f"{act}/{scene}"
    scene_context = get_scene_context(scene_link)
    dialogues_by_model = {
        model: load_dialogues_for_variant(scene_link, model)
        for model in models
    }
    tasks = []
    for _ in range(repetitions):
        for model1, model2 in combinations(models, 2):
            tasks.append(
                process_match(
                    evaluation_model, model1, model2, dialogues_by_model,
                    scene_context, evaluated_actors, elo_ratings, k_factor, elo_lock
                )
            )
    await asyncio.gather(*tasks)


# -----------------------------------------------------------------------------
# Main async function to run the Elo rating evaluation.
#
# Parameters:
#   - evaluation_model: your instantiated evaluation model.
#   - models: list of model names (default list is provided if None).
#   - repetitions: number of comparisons per scene.
#   - evaluated_actors: string passed to contrast_set_actors.
#   - elo_ratings: (optional) dict of initial Elo ratings.
#   - k_factor: (optional) K factor for Elo updates.
#
# Returns:
#   - The final elo_ratings dictionary.
# -----------------------------------------------------------------------------
async def run_elo_rating_evaluation(evaluation_model, models=None, repetitions=3,
                                    evaluated_actors="Eliza", elo_ratings=None, k_factor=None):
    # Set defaults if not provided.
    if models is None:
        models = [
            "InstructSonnet",
            "InstructGPT4",
            "InstructGPT35",
            "InstructGeminiFlash",
            "InstructGeminiFlash2"
        ]
    if elo_ratings is None:
        elo_ratings = {model: 1500 for model in models}
    if k_factor is None:
        k_factor = 32

    # Create an asyncio lock for protecting shared state.
    elo_lock = asyncio.Lock()

    # Assume your dialogues are stored under: <cwd>/dialogues/<act>/<scene>/...
    dialogues_dir = os.path.join(os.getcwd(), "dialogues")
    acts = [d for d in os.listdir(dialogues_dir)
            if os.path.isdir(os.path.join(dialogues_dir, d))]

    scene_tasks = []
    for act in acts:
        act_folder = os.path.join(dialogues_dir, act)
        scenes = [d for d in os.listdir(act_folder)
                  if os.path.isdir(os.path.join(act_folder, d))]
        for scene in scenes:
            scene_tasks.append(
                process_scene(
                    evaluation_model, act, scene, models, repetitions,
                    evaluated_actors, elo_ratings, k_factor, elo_lock
                )
            )

    await asyncio.gather(*scene_tasks)
    return elo_ratings


# -----------------------------------------------------------------------------
# Helper function to save the Elo ratings to a JSON file.
# -----------------------------------------------------------------------------
def save_ratings_to_file(elo_ratings, filename):
    with open(filename, 'w') as f:
        json.dump(elo_ratings, f)


# -----------------------------------------------------------------------------
# Helper function to load Elo ratings from a JSON file and plot them.
# -----------------------------------------------------------------------------
def plot_ratings_from_file(filename):
    with open(filename, 'r') as f:
        elo_ratings = json.load(f)

    sorted_ratings = sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
    print("Final Elo Ratings:")
    for model, rating in sorted_ratings:
        print(f"{model}: {rating:.2f}")

    model_names = [model for model, rating in sorted_ratings]
    elo_values = [rating for model, rating in sorted_ratings]

    plt.figure(figsize=(10, 6))
    plt.bar(model_names, elo_values, color='skyblue')
    plt.xlabel("Models")
    plt.ylabel("Elo Rating")
    plt.title("Async Elo-Based Ranking of Models")
    plt.ylim(min(elo_values) - 50, max(elo_values) + 50)
    plt.show()