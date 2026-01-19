"""
Utility functions for the LLM prompt system.

This module contains generic utilities for string formatting, file loading,
and LangChain chain building.
"""

import os
import sys
from typing import List
from langchain_core.prompts import ChatPromptTemplate


# Color constants for CLI output
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
WHITE = "\033[0m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BRIGHT_WHITE = "\033[97m"
BLACK = "\033[90m"
ORANGE = "\033[33m"


def list_to_conjunction(L: List[str]) -> str:
    """
    Takes a list of strings and returns a string with every element in the list
    separated by commas, with 'and' before the last element.

    Args:
        L: List of strings to join

    Returns:
        Formatted string with proper conjunction

    Examples:
        >>> list_to_conjunction(["Alice"])
        "Alice"
        >>> list_to_conjunction(["Alice", "Bob"])
        "Alice and Bob"
        >>> list_to_conjunction(["Alice", "Bob", "Charlie"])
        "Alice, Bob, and Charlie"
    """
    if L == "":
        return ""
    elif len(L) == 1:
        return L[0]
    elif len(L) == 2:
        return f"{L[0]} and {L[1]}"
    else:
        return ", ".join(L[:-1]) + f", and {L[-1]}"


def prompt_llm(prompt: str, model):
    """
    Build a LangChain chain from a prompt template and model.

    Args:
        prompt: The prompt template string
        model: The LLM model to use

    Returns:
        A LangChain chain ready for invocation
    """
    prompt = ChatPromptTemplate.from_template(template=prompt)
    chain = prompt | model
    return chain


def resource_path(base_path: str = None) -> str:
    """
    Get the absolute path to resource files.

    Args:
        base_path: Optional base directory path. If not provided, uses current working directory.

    Returns:
        Absolute path to resources directory
    """
    if base_path is None:
        base_path = os.path.abspath(os.getcwd())
    return base_path


def load_file(file_path: str) -> str:
    """
    Load a text file from the given path.

    Args:
        file_path: Path to the file to load

    Returns:
        Contents of the file as a string, or empty string if file not found
    """
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        print(RED + f'File "{file_path}" not found' + WHITE)
        return ""
