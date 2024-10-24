from typing import List, Dict, Any, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json

from benchmark import dataset_utils
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.language_models.llms import LLM
import benchmark.dialogue_graph as dg
import benchmark.dialogue_graph_utils as dg_utils


class SummarizeHistoryTemplate(BaseModel):
    summary: str = Field(description="Your summary of the previous scenes. We want this summary to be sentence based, add an \n after each sentence.")


class ExtractGoalsTemplate(BaseModel):
    goals: list[str] = Field(description="Your list of goals. Should be something like ['X does ..., 'Y and X do ...', 'Z tries to ...']")


class ExtractStyleTemplate(BaseModel):
    style: list[str] = Field(description="The list of statements that describe the character")


def summarize_history(model: LLM, scene_history: str, next_scene: str,) -> str:
    prompt = ChatPromptTemplate.from_template(
        """Given this history of scenes: {history}\n\n
        and the following information about a new_scene: \n---\n{next_scene}\n---\n
        Summarize the relevant history of information from the history of scenes.\n
        Focus your summary in providing the relevant information for the new scene, for example the background of the characters participating, general lore, encounters that are relevant for the new scene...\n
        Be concise and avoid irrelevant details.\n
        Do not return any text that is not the JSON. Follow these instructions to format your json output:\n{output_instructions}
        """)
    parser = JsonOutputParser(pydantic_object=SummarizeHistoryTemplate)
    chain = prompt | model | parser

    response = chain.invoke({"history": scene_history, "next_scene": next_scene, "output_instructions":parser.get_format_instructions()})

    return response['summary']


def summarize_character_traits(model: LLM, description: str):
    prompt = ChatPromptTemplate.from_template(
        """Given the following description of a character: \n---\n{description}\n---\n
        Return a list with the traits of the character and the key relationships they have.\n
        Bear in mind that your output will be used to guide the actor interpreting this character, any other information from the description is irrelevant.
        Include any main drivers/desires of the character.
        Avoid irrelevant details.
        The traits should be universal, avoid listing things that may change in different scenes.
        Your output should be a JSON with the field a list of statements that describe the character, for example: "<Name of character> is ...", "<Name of character> cares/loves/hates/etc X", "<Name of character> is driven by A",  "<Name of character> driver is B" etc.\n
        Do not return any text that is not the JSON. Follow these instructions to format your json output:\n{output_instructions}
        """)
    parser = JsonOutputParser(pydantic_object=ExtractStyleTemplate)
    chain = prompt | model | parser

    response = chain.invoke({"description": description, "output_instructions":parser.get_format_instructions()})

    return response['style']


def get_goals(model: LLM, next_scene: str,) -> list[str]:
    prompt = ChatPromptTemplate.from_template(
        """Given the following scene: \n---\n{next_scene}\n---\n
        Return a list with the goals of the scene.\n
        Focus on the main goals of the scene, what the characters are trying to achieve, the main objectives...\n
        Keep the list concise and avoid irrelevant details. The order of your list should describe the order in which goals are meant to be achieved.\n
        Do not return any text that is not the JSON. Follow these instructions to format your json output:\n{output_instructions}
        """)
    parser = JsonOutputParser(pydantic_object=ExtractGoalsTemplate)
    chain = prompt | model | parser

    response = chain.invoke({"next_scene": next_scene, "output_instructions":parser.get_format_instructions()})

    return response['goals']


def get_character_description(movie: str, character: str, model: LLM) -> str:
    # Set up Chrome options to run in headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    # Set up the Chrome WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Construct the search URL
    base_url = "https://search.brave.com"
    query = f"Character description of {character} in {movie}, including key relationships and antagonisms, character traits, character drivers and comunication style"
    search_url = f"{base_url}/search?q={query}&source=llmSuggest&summary=1"

    i = 0
    max_attempts = 10
    while i < max_attempts:
        try:
            # Navigate to the search page
            driver.get(search_url)

            # Use WebDriverWait to wait for the AI response to be fully loaded
            wait = WebDriverWait(driver, 30)  # Wait up to 30 seconds
            ai_response_element = wait.until(EC.presence_of_element_located((By.ID, "chatllm-content")))

            # Check if a "Show More" button or link is present and click it
            try:
                show_more_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Show more")]')))
                show_more_button.click()
            except:
                # If the button isn't found, it may not be needed
                pass

            # Give it a bit of time to load the expanded content
            wait.until(EC.presence_of_element_located((By.ID, "chatllm-content")))

            # Scroll the element into view to ensure all content is loaded
            driver.execute_script("arguments[0].scrollIntoView(true);", ai_response_element)

            # Retrieve the inner HTML of the element
            ai_response_html = ai_response_element.get_attribute('innerHTML')

            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(ai_response_html, 'html.parser')

            # Extract all text content, including bullet points and other elements
            text_parts = []
            for element in soup.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em']):
                text_parts.append(element.get_text(strip=True))

            # Join all parts together with line breaks
            ai_response = "\n".join(text_parts)
            character_description = summarize_character_traits(model, ai_response)
            return character_description
        except Exception as e:
            i += 1
            print(f"Attempt {i} failed: {str(e)}")
            time.sleep(2)  # Wait for 2 seconds before retrying
            if i == 10:
                raise e
        finally:
            # Close the browser
            driver.quit()

    # If all attempts fail, return an error message
    return f"An error occurred after {max_attempts} attempts."


def generate_context_string(history_summary: str, goals: List[str], character_descriptions: Dict[str, str]) -> str:
    context_string = f"History summary:\n{history_summary}\n\n"

    context_string += "Goals:\n"
    for i, goal in enumerate(goals, start=1):
        context_string += f"Goal {i}: {goal}\n"
    context_string += "\n"

    context_string += "Character descriptions:\n"
    for character, descriptions in character_descriptions.items():
        descriptions_str = ',\n'.join(descriptions)
        context_string += f"{character}:\n{descriptions_str}\n\n"

    return context_string


def load_scene(genre: str, title: str, scene_idx: int) -> Tuple[dg.Dialogue, dg.DialogueState]:
    # This function assumes the presence of the raw_dataset in the workspace.
    title = dataset_utils.normalize_title(title)
    genre = genre.lower()

    folder = dataset_utils.title_path(genre=genre, title=title)
    workspace_root = dataset_utils.find_workspace_root()
    with open(f"{workspace_root}/benchmark/raw_dataset/{folder}/{genre}_{title}_scene_{scene_idx}.json") as f_scene:
        scene = dg.Dialogue.deserialize(json.load(f_scene))

    with open(f"{workspace_root}/benchmark/raw_dataset/{folder}/{genre}_{title}_state_{scene_idx}.json") as f_state:
        state = dg.DialogueState.deserialize(json.load(f_state))

    return scene, state


def gather_movie_info(genre: str, title: str, index: int) -> str:
    title = dataset_utils.normalize_title(title)
    genre = genre.lower()

    info = ""

    for i in range(index):
        scene, state = load_scene(genre, title, i)

        # Add facts from the scene
        if scene.facts:
            info += "Facts from scene_{}:\n".format(i)
            info += "\n".join(scene.facts) + "\n\n"

        # Add chat history from the state
        if hasattr(state, 'chat_history') and state.chat_history:
            info += "Chat history from scene_{}:\n".format(i)
            info += "\n".join(state.chat_history) + "\n\n"

    return info


def extract_characters(chat_history: list) -> set:
    characters = set()
    for entry in chat_history:
        if ':' in entry:
            tokenized_line = dg_utils.tokenize_dialogue_line(entry)
            if tokenized_line.role != "Narrator":
                characters.add(tokenized_line.role)
    return characters


def format_characters_in_scene(chat_histories: list) -> str:
    characters = extract_characters(chat_histories)
    characters_list = sorted(characters)
    characters_str = ", ".join(characters_list)
    return f"characters in the scene: {characters_str}"


def get_context_for_scene(model: LLM, genre: str, title: str, scene_idx: int) -> [str, str]:
    # Gather movie info up to the given scene index
    scene_history = gather_movie_info(genre, title, scene_idx)

    # Load the next scene
    next_scene, next_state = load_scene(genre, title, scene_idx)
    formatted_characters = format_characters_in_scene(next_state.chat_history)

    # Summarize the history using the model
    next_scene_info = "" + "\n".join(next_scene.facts) + "\n\n" + formatted_characters
    history_summary = summarize_history(model, scene_history, next_scene_info)
    history_summary += "\n".join(next_scene.facts)

    # Extract goals from the next scene using the model
    next_scene_info = history_summary + "\n".join(next_scene.facts) + "\n\n" + "\n".join(next_state.chat_history)
    goals = get_goals(model, next_scene_info)

    # Extract character descriptions
    characters = extract_characters(next_state.chat_history)
    character_descriptions = {}
    for character in characters:
        description = get_character_description(title, character, model)
        character_descriptions[character] = description

    return generate_context_string(history_summary, goals, character_descriptions), [history_summary, goals,
                                                                                     character_descriptions]
