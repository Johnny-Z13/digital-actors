"""
Prompt builder for composing context-aware prompts.

This module provides the PromptBuilder class for constructing prompts
from scene data, dialogue history, and other context.
"""

from typing import List
from llm_prompt_core.prompts.templates import (
    preamble_template,
    preamble_plus_template,
    query_preamble_template,
    merge_preamble_template,
    instruction_template,
    query_instruction_suffix_template,
    dialogue_instruction_suffix,
    summary_instruction_suffix,
    merge_instruction_template,
    merge_instruction_suffix,
    query_instruction_prefix,
)
from llm_prompt_core.utils import list_to_conjunction


class PromptBuilder:
    """
    Builder class for constructing prompts for different types of LLM operations.

    This class provides methods to build prompts for:
    - Dialogue generation
    - Query evaluation
    - Summary generation
    - Summary merging
    """

    @staticmethod
    def build_preamble(
        instruction_prefix: str,
        back_story: str,
        scene_description: str,
        previous_scenes_description: str,
        steer_back_instructions: str,
        scene_supplement: str,
        actors: List[str],
        dialogue_summary: str = "",
    ) -> str:
        """
        Build a preamble for dialogue generation.

        Args:
            instruction_prefix: Instruction text to start the prompt
            back_story: Background story context
            scene_description: Description of current scene
            previous_scenes_description: Summary of previous scenes
            steer_back_instructions: Instructions to keep dialogue on track
            scene_supplement: Additional scene information
            actors: List of character names in the dialogue
            dialogue_summary: Optional summary of previous dialogue

        Returns:
            Formatted preamble string
        """
        if dialogue_summary:
            return preamble_plus_template.format(
                instruction_prefix=instruction_prefix,
                back_story=back_story,
                dialogue_summary=dialogue_summary,
                scene_description=scene_description,
                steer_back_instructions=steer_back_instructions,
                scene_supplement=scene_supplement,
                actors=list_to_conjunction(actors),
                previous_scenes_description=previous_scenes_description,
            )
        else:
            return preamble_template.format(
                instruction_prefix=instruction_prefix,
                back_story=back_story,
                scene_description=scene_description,
                steer_back_instructions=steer_back_instructions,
                scene_supplement=scene_supplement,
                actors=list_to_conjunction(actors),
                previous_scenes_description=previous_scenes_description,
            )

    @staticmethod
    def build_query_preamble(
        back_story: str,
        actors: List[str],
        previous_scenes_description: str = "",
    ) -> str:
        """
        Build a preamble for query evaluation.

        Args:
            back_story: Background story context
            actors: List of character names in the dialogue
            previous_scenes_description: Summary of previous scenes

        Returns:
            Formatted query preamble string
        """
        return query_preamble_template.format(
            instruction_prefix=query_instruction_prefix,
            back_story=back_story,
            actors=list_to_conjunction(actors),
            previous_scenes_description=previous_scenes_description,
        )

    @staticmethod
    def build_merge_preamble(
        back_story: str,
        previous_scenes_description: str,
        merge_instruction_prefix: str,
    ) -> str:
        """
        Build a preamble for merging summaries.

        Args:
            back_story: Background story context
            previous_scenes_description: Summary of previous scenes
            merge_instruction_prefix: Instruction prefix for merging

        Returns:
            Formatted merge preamble string
        """
        return merge_preamble_template.format(
            instruction_prefix=merge_instruction_prefix,
            back_story=back_story,
            previous_scenes_description=previous_scenes_description,
        )

    @staticmethod
    def build_dialogue_prompt(preamble: str, dialogue: str) -> str:
        """
        Build a complete prompt for dialogue generation.

        Args:
            preamble: The preamble containing context
            dialogue: The dialogue history so far

        Returns:
            Complete prompt for generating the next dialogue line
        """
        return instruction_template.format(
            preamble=preamble,
            dialogue=dialogue,
            instruction_suffix=dialogue_instruction_suffix,
        )

    @staticmethod
    def build_query_prompt(preamble: str, dialogue: str, statement: str) -> str:
        """
        Build a complete prompt for query evaluation.

        Args:
            preamble: The query preamble containing context
            dialogue: The dialogue history so far
            statement: The statement to evaluate (true/false)

        Returns:
            Complete prompt for evaluating the query
        """
        instruction = query_instruction_suffix_template.format(statement=statement)
        return instruction_template.format(
            preamble=preamble,
            dialogue=dialogue,
            instruction_suffix=instruction,
        )

    @staticmethod
    def build_summary_prompt(preamble: str, dialogue: str) -> str:
        """
        Build a complete prompt for summary generation.

        Args:
            preamble: The preamble containing context
            dialogue: The dialogue to summarize

        Returns:
            Complete prompt for generating a dialogue summary
        """
        return instruction_template.format(
            preamble=preamble,
            dialogue=dialogue,
            instruction_suffix=summary_instruction_suffix,
        )

    @staticmethod
    def build_merge_prompt(
        preamble: str, prev_summary: str, new_summary: str
    ) -> str:
        """
        Build a complete prompt for merging two summaries.

        Args:
            preamble: The merge preamble containing context
            prev_summary: The previous summary
            new_summary: The new summary to merge with the previous one

        Returns:
            Complete prompt for merging summaries
        """
        return merge_instruction_template.format(
            preamble=preamble,
            prev_summary=prev_summary,
            new_summary=new_summary,
            instruction_suffix=merge_instruction_suffix,
        )
