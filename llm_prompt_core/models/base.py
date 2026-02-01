"""
Base class for LLM model wrappers.

This module defines the abstract interface that all LLM provider wrappers must implement.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

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

    Provides shared functionality:
    - _get_api_key(): Resolve API key from instance or environment
    - _initialize_client(): Initialize SDK client with error handling
    - _handle_api_error(): Standardized error handling and exception chaining
    """

    def _get_api_key(
        self, env_var_name: str, provider_name: str, required: bool = True
    ) -> str | None:
        """
        Resolve API key from instance attribute or environment variable.

        Args:
            env_var_name: Name of environment variable to check (e.g., "ANTHROPIC_API_KEY")
            provider_name: Human-readable provider name for error messages (e.g., "Claude")
            required: If True, raises EnvironmentError when key not found

        Returns:
            Resolved API key or None if not required and not found

        Raises:
            EnvironmentError: If required=True and API key not found
        """
        api_key = getattr(self, "api_key", None)
        resolved_key = api_key or os.getenv(env_var_name)

        if required and not resolved_key:
            raise OSError(
                f"{env_var_name} environment variable must be set for {provider_name} models."
            )

        return resolved_key

    def _initialize_client(
        self, client_class: type[Any], api_key: str, package_name: str, **client_kwargs: Any
    ) -> Any:
        """
        Initialize an SDK client with standardized error handling.

        Args:
            client_class: The client class to instantiate (e.g., Anthropic, OpenAI)
            api_key: The API key to pass to the client
            package_name: Package name for import error messages (e.g., "anthropic")
            **client_kwargs: Additional keyword arguments to pass to client constructor

        Returns:
            Initialized client instance

        Raises:
            ImportError: If the SDK package is not installed
        """
        try:
            return client_class(api_key=api_key, **client_kwargs)
        except (ImportError, NameError):
            raise ImportError(
                f"{package_name} package not installed. Install it with: pip install {package_name}"
            )

    def _handle_api_error(self, exception: Exception, provider_name: str) -> None:
        """
        Handle API errors with standardized exception chaining.

        This method provides consistent error handling across all providers:
        - Re-raises RuntimeError without wrapping (to preserve specific error messages)
        - Wraps ConnectionError, TimeoutError, ValueError with provider context
        - Catches all other exceptions and wraps them in RuntimeError with provider context

        Args:
            exception: The caught exception to handle
            provider_name: Human-readable provider name for error messages (e.g., "Claude", "OpenAI")

        Raises:
            RuntimeError: For unhandled exceptions or validation errors
            ConnectionError: For network connection failures
            TimeoutError: For request timeouts
            ValueError: For invalid request parameters
        """
        # Re-raise our own RuntimeErrors without wrapping
        if isinstance(exception, RuntimeError):
            raise exception

        # Handle specific exception types with provider context
        if isinstance(exception, ConnectionError):
            raise ConnectionError(
                f"{provider_name} API connection failed: {exception}"
            ) from exception
        if isinstance(exception, TimeoutError):
            raise TimeoutError(f"{provider_name} API request timed out: {exception}") from exception
        if isinstance(exception, ValueError):
            raise ValueError(f"Invalid request parameters: {exception}") from exception

        # Catch-all for SDK-specific errors (APIError, AuthenticationError, etc.)
        # Preserve exception chain for debugging
        raise RuntimeError(
            f"{provider_name} API call failed: {exception.__class__.__name__}: {exception}"
        ) from exception

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
    def _identifying_params(self) -> dict[str, Any]:
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
        stop: Sequence[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
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
