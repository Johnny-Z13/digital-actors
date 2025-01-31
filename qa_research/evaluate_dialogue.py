from typing import Any

from langchain_core.language_models.llms import LLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from pydantic import BaseModel, Field


EVALUATION_CONTEXT_TEMPLATE = """Back Story:
{back_story}

Scene Description:
{scene_description}

Scene Supplement:
{scene_supplement}
"""


class GenerateEmbeddingTemplate(BaseModel):
    review: str = Field(
        description="Your critic review structured in three parts detailed above."
    )
    value: int = Field(
        description="""The int with the value obtained from your justification.
                    1 if the first set of actors performed better, 2 if the second set performed better, 
                    0 if they performed equally well."""
    )


def scene_info_generation(back_story: str, scene_description: str, scene_supplement: str) -> str:
    return EVALUATION_CONTEXT_TEMPLATE.format(
        back_story=back_story, scene_description=scene_description, scene_supplement=scene_supplement
    )


def general_comparison(
    model: LLM, set_actor_1: str, set_actor_2: str, scene: str, evaluated_actors: str,
) -> dict[str, Any]:
    eval_prompt = ChatPromptTemplate.from_template(
        """You are evaluating and contrasting the quality of the dialogues of a set of actors in the middle of a 
         computer videogame. Here is the contextual information of the game and the scene: \n---\n {scene}\n---\n
         Your review focuses on the quality of the dialogues of the actors {evaluated_actors} in the scene.
         Since the actors need to improv and adap to what players might say, you are to evaluate the actors
         across several instances of the same scene with different players. Here are the dialogues of the 
         first set of actors:
        \n---\n {set_actor_1}\n---\n
        And here are the dialogues of the second set of actors:
        \n---\n {set_actor_2}\n---\n
        Your output is in json format. It starts with a "review" field, where you write your review.
        Your review is structured in the following format: First, it lists the most relevant good and bad points of the
        dialogues of each set of actors. Second, it contrasts the good and bad points of each set of actors. Third, your 
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
