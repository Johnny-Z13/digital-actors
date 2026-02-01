"""
OpenAI model wrapper.

This module provides a LangChain-compatible wrapper for OpenAI models.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import PrivateAttr

from llm_prompt_core.models.base import BaseLLMModel


class OpenAIModel(BaseLLMModel):
    """
    LangChain-compatible wrapper for OpenAI models.

    This wrapper supports all OpenAI models including GPT-4, GPT-4o, and GPT-3.5.
    It uses the OpenAI SDK for API calls.

    Attributes:
        model_name: Name of the OpenAI model to use (e.g., "gpt-4o")
        temperature: Controls randomness in generation (0.0 to 2.0)
        max_tokens: Maximum number of tokens to generate
        api_key: Optional API key (defaults to OPENAI_API_KEY env variable)
    """

    model_name: str = "gpt-4o"
    temperature: float = 0.8
    max_tokens: int = 1024
    api_key: str | None = None

    _client: Any = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data: Any):
        super().__init__(**data)
        resolved_api_key = self._get_api_key("OPENAI_API_KEY", "OpenAI")

        from openai import OpenAI

        self._client = self._initialize_client(OpenAI, resolved_api_key, "openai")

    def _call(
        self,
        prompt: str,
        stop: Sequence[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: The input text prompt
            stop: Optional list of stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text response

        Raises:
            RuntimeError: If OpenAI fails to generate a response
        """
        # Override defaults with kwargs if provided
        temperature = kwargs.pop("temperature", self.temperature)
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)

        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                stop=stop,
                **kwargs,
            )

            if not response.choices or len(response.choices) == 0:
                raise RuntimeError("OpenAI response did not contain any choices.")

            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("OpenAI response did not contain any text.")

            return content

        except Exception as e:
            self._handle_api_error(e, "OpenAI")

    @property
    def _llm_type(self) -> str:
        return "openai"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


class GPT4oModel(OpenAIModel):
    """GPT-4o - Fast and capable model with multimodal support."""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        super().__init__(
            model_name="gpt-4o",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class GPT4TurboModel(OpenAIModel):
    """GPT-4 Turbo - High capability model with extended context."""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        super().__init__(
            model_name="gpt-4-turbo",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class GPT35TurboModel(OpenAIModel):
    """GPT-3.5 Turbo - Fast and efficient model for simpler tasks."""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        super().__init__(
            model_name="gpt-3.5-turbo",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
