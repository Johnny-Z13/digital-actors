"""
Prompt templates and builders for character dialogue generation.

This module contains the prompt templates and utilities for building
context-aware prompts for LLM-based character dialogue.
"""

from llm_prompt_core.prompts.builder import PromptBuilder
from llm_prompt_core.prompts.templates import (
    preamble_template,
    query_preamble_template,
    preamble_plus_template,
    merge_preamble_template,
    merge_instruction_template,
    speech_template,
    instruction_template,
    dialogue_instruction_suffix,
    query_instruction_suffix_template,
    summary_instruction_suffix,
    query_instruction_prefix,
    merge_instruction_suffix,
)

__all__ = [
    "PromptBuilder",
    "preamble_template",
    "query_preamble_template",
    "preamble_plus_template",
    "merge_preamble_template",
    "merge_instruction_template",
    "speech_template",
    "instruction_template",
    "dialogue_instruction_suffix",
    "query_instruction_suffix_template",
    "summary_instruction_suffix",
    "query_instruction_prefix",
    "merge_instruction_suffix",
]
