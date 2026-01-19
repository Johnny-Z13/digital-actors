"""
Data types for the LLM prompt system.

This module defines the core data structures used throughout the prompt system:
- Line: A single line of dialogue with timing information
- StateChange: Represents a change in game/application state
- Query: A conditional check that triggers state changes
- SceneData: Container for all scene-related context and configuration
"""

from dataclasses import dataclass, field
from typing import List, Callable, Optional, Tuple
from llm_prompt_core.prompts.templates import (
    preamble_template,
    preamble_plus_template,
    query_preamble_template,
    merge_preamble_template,
)
from llm_prompt_core.utils import list_to_conjunction


@dataclass
class Line:
    """
    Represents a single line of dialogue.

    Attributes:
        text: The dialogue text
        delay: Delay in seconds before displaying this line
    """

    text: str
    delay: float


@dataclass
class StateChange:
    """
    Represents a state change in the application/game.

    Attributes:
        name: The name/identifier of the state variable
        value: The new value to set
    """

    name: str
    value: str


@dataclass
class Query:
    """
    Represents a conditional query that checks dialogue state.

    A query evaluates a statement against the dialogue history. If the statement
    is true, it triggers associated state changes and marks itself as handled.

    Attributes:
        text: The statement to evaluate (true/false question)
        state_changes: List of state changes to trigger if query passes
        handled: Whether this query has already been handled
        query_printed: Whether a message should be printed when evaluated
        query_printed_text_true: Message to print if query evaluates to true
        query_printed_text_false: Message to print if query evaluates to false
    """

    text: str
    state_changes: List[StateChange]
    handled: bool = False
    query_printed: bool = False
    query_printed_text_true: str = ""
    query_printed_text_false: str = ""


@dataclass
class SceneData:
    """
    Container for all scene-related context and configuration.

    This class holds all the information needed to generate dialogue for a scene,
    including scene descriptions, backstory, opening speeches, queries, and
    pre-built preambles for different types of prompts.

    Attributes:
        scene_name: Unique identifier for this scene
        scene_description: Description of what's happening in this scene
        previous_scenes_description: Summary of previous scenes
        steer_back_instructions: Instructions to keep dialogue on track
        scene_supplement: Additional scene context
        back_story: Background story context
        dialogue_instruction_prefix: Prefix for dialogue generation prompts
        summary_instruction_prefix: Prefix for summary generation prompts
        merge_instruction_prefix: Prefix for summary merging prompts
        opening_speech: Lines to speak when scene starts
        queries: List of queries to evaluate during the scene
        actors: List of character names in the dialogue
        dialogue_preamble: Pre-built preamble for dialogue generation
        query_preamble: Pre-built preamble for query evaluation
        dialogue_summary: Summary of dialogue from previous scenes
    """

    scene_name: str
    scene_description: str
    previous_scenes_description: str
    steer_back_instructions: str
    scene_supplement: str
    back_story: str
    dialogue_instruction_prefix: str
    summary_instruction_prefix: str
    merge_instruction_prefix: str
    opening_speech: List[Line]
    queries: List[Query]
    actors: List[str] = field(default_factory=lambda: ["NPC", "Player"])

    dialogue_preamble: str = ""
    query_preamble: str = ""
    dialogue_summary: str = ""
    summary_preamble: str = ""
    merge_preamble: str = ""

    def __post_init__(self):
        """Build preambles after initialization."""
        if self.dialogue_summary:
            self.dialogue_preamble = preamble_plus_template.format(
                instruction_prefix=self.dialogue_instruction_prefix,
                back_story=self.back_story,
                dialogue_summary=self.dialogue_summary,
                scene_description=self.scene_description,
                steer_back_instructions=self.steer_back_instructions,
                scene_supplement=self.scene_supplement,
                actors=list_to_conjunction(self.actors),
                previous_scenes_description=self.previous_scenes_description,
            )
        else:
            self.dialogue_preamble = preamble_template.format(
                instruction_prefix=self.dialogue_instruction_prefix,
                back_story=self.back_story,
                scene_description=self.scene_description,
                steer_back_instructions=self.steer_back_instructions,
                scene_supplement=self.scene_supplement,
                actors=list_to_conjunction(self.actors),
                previous_scenes_description=self.previous_scenes_description,
            )

        self.query_preamble = query_preamble_template.format(
            instruction_prefix="You are going to answer a single question about the current state of the dialogue in a scene in the middle of a computer game.\n",
            back_story=self.back_story,
            actors=list_to_conjunction(self.actors),
            previous_scenes_description=self.previous_scenes_description,
        )

        self.summary_preamble = preamble_template.format(
            instruction_prefix=self.summary_instruction_prefix,
            back_story=self.back_story,
            scene_description="",
            steer_back_instructions="",
            scene_supplement="",
            actors=list_to_conjunction(self.actors),
            previous_scenes_description=self.previous_scenes_description,
        )

        self.merge_preamble = merge_preamble_template.format(
            instruction_prefix=self.merge_instruction_prefix,
            back_story=self.back_story,
            previous_scenes_description=self.previous_scenes_description,
        )

    def all_queries_handled(self) -> bool:
        """
        Check if all queries in this scene have been handled.

        Returns:
            True if all queries are handled, False otherwise
        """
        return all(query.handled for query in self.queries)

    def get_initial_dialog(self, print_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Get the initial dialogue for this scene (opening speech).

        Args:
            print_callback: Optional function to call for each line (for logging/display)

        Returns:
            Formatted dialogue string
        """
        from llm_prompt_core.prompts.templates import speech_template

        dialogue = ""
        for line in self.opening_speech:
            response = speech_template.format(actor=self.actors[0], speech=line.text)
            dialogue += response + "\n"
            if print_callback:
                print_callback(response)

        return dialogue

    def run_queries(
        self,
        dialogue: str,
        query_model,
        print_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[List[StateChange], str]:
        """
        Evaluate all unhandled queries against the current dialogue.

        Args:
            dialogue: The dialogue history to evaluate against
            query_model: The LLM model to use for evaluation
            print_callback: Optional function to call for logging

        Returns:
            Tuple of (state_changes, text_to_print)
        """
        from llm_prompt_core.prompts.templates import (
            query_instruction_suffix_template,
            instruction_template,
        )
        from llm_prompt_core.utils import prompt_llm

        state_changes = []
        to_print = ""

        for query in self.queries:
            if query.handled == False:
                instruction = query_instruction_suffix_template.format(
                    statement=query.text
                )
                prompt = instruction_template.format(
                    preamble=self.query_preamble,
                    dialogue=dialogue,
                    instruction_suffix=instruction,
                )
                chain = prompt_llm(prompt, query_model)
                response = chain.invoke({})

                if print_callback:
                    print_callback(f'Query for "{query.text}" - response: "{response}"')
                    print_callback(f"To print: {to_print}")

                if response[0:4].lower() == "true":
                    query.handled = True
                    if print_callback:
                        print_callback(
                            f'Query passed for "{query.text}" - returning state_id "{query.state_changes}"'
                        )
                    if query.query_printed_text_true:
                        query.query_printed = True
                        to_print = query.query_printed_text_true
                    state_changes.extend(query.state_changes)
                else:
                    if query.query_printed_text_true and not query.query_printed:
                        to_print = query.query_printed_text_false
                    break
        return state_changes, to_print
