"""
LLM Prompt Core - A generic prompt-based character dialogue system.

This module provides a flexible framework for building interactive NPC dialogue systems
using large language models (LLMs). It supports multiple LLM providers (Claude, OpenAI, Gemini)
and provides tools for managing multi-scene conversations with context.
"""

from llm_prompt_core.types import Line, Query, StateChange, SceneData
from llm_prompt_core.prompts.builder import PromptBuilder
from llm_prompt_core.models.base import BaseLLMModel

__all__ = [
    "Line",
    "Query",
    "StateChange",
    "SceneData",
    "PromptBuilder",
    "BaseLLMModel",
]

__version__ = "0.1.0"
