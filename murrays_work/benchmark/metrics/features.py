from typing import List

from benchmark import dialogue_graph as dg
from benchmark import dialogue_graph_utils as dg_utils
from langchain_core.language_models.llms import LLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm  # type: ignore


class GenerateEmbeddingTemplate(BaseModel):
    justification: str = Field(
        description="List the reasons for your response, do not give your judgment before listing individual reasons explainig why. Start your judgement with 'Let's examine...'.  Use \" only for the json, use ' instead when quoting"
    )
    response: float = Field(
        description="The float with the value obtained from your justification. Can only be 1.0 or 0.0"
    )


async def feature_presence(model: LLM, initial_state: dg.Dialogue, delta_state: dg.DialogueState, feature: str) -> float:
    prompt = ChatPromptTemplate.from_template(
        """Given the following dialogue: {dialogue}\n\n
        and the following feature: \n---\n{feature}\n---\n
        return a binary value 1.0 or 0.0, that represents if the feature is present in the dialogue.
        The value of 0.0 means that the feature is absent in the dialogue state, 1.0 means that the feature is present, no intermediate responses are allowed.
        First list relevant points form the dialogue and analize them individually, do not cast global judgements before listing individual reasons. Start your judgement with 'Let's examine the important points in the dialogue:' and start quoting.  Use \" only for the json, use ' instead when quoting
        After finalising your list of examples, start your global judgement, starting with "From the individual analisis just listed, given that the feature was: {feature}, the conclusion is that..." 
        Do not return any text that is not the JSON. Follow these instructions:\n{output_instructions}
        """
    )
    parser = JsonOutputParser(pydantic_object=GenerateEmbeddingTemplate)
    chain = prompt | model | parser

    state_str = dg_utils.dumps_full_state(initial_state, delta_state)
    point_str = chain.invoke(
        {"dialogue": state_str, "feature": feature, "output_instructions": parser.get_format_instructions()}
    )
    return point_str["response"]


async def calculate_metric_delta(
    model: LLM, initial_state: dg.Dialogue, delta_state: dg.DialogueState, features: List[str]
) -> List[float]:
    return await tqdm.gather(*[feature_presence(model, initial_state, delta_state, feature) for feature in features])
