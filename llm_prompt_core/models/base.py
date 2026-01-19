"""
Base class for LLM model wrappers.

This module defines the abstract interface that all LLM provider wrappers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Sequence
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM


class BaseLLMModel(LLM, ABC):
    """
    Abstract base class for all LLM provider wrappers.

    This class extends LangChain's LLM base class and defines the standard
    interface that all model wrappers (Claude, OpenAI, Gemini) must implement.

    Subclasses must implement:
    - _call(): The main method for generating text
    - _llm_type: Property returning the model type identifier
    - _identifying_params: Property returning model configuration parameters
    """

    @property
    @abstractmethod
    def _llm_type(self) -> str:
        """
        Return the type of LLM.

        Returns:
            String identifier for this LLM type (e.g., "claude", "openai", "gemini")
        """
        pass

    @property
    @abstractmethod
    def _identifying_params(self) -> Dict[str, Any]:
        """
        Return a dictionary of identifying parameters.

        Returns:
            Dictionary containing model configuration (model_name, temperature, etc.)
        """
        pass

    @abstractmethod
    def _call(
        self,
        prompt: str,
        stop: Optional[Sequence[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input text prompt
            stop: Optional list of stop sequences
            run_manager: Optional callback manager for tracking
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response

        Raises:
            RuntimeError: If the model fails to generate a response
        """
        pass
