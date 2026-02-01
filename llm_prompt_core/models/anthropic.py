"""
Anthropic Claude model wrapper.

This module provides a LangChain-compatible wrapper for Claude models.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import PrivateAttr

from llm_prompt_core.models.base import BaseLLMModel


class ClaudeModel(BaseLLMModel):
    """
    LangChain-compatible wrapper for Anthropic Claude models.

    This wrapper supports all Claude models including Sonnet, Opus, and Haiku.
    It uses the Anthropic SDK for API calls.

    Attributes:
        model_name: Name of the Claude model to use (e.g., "claude-sonnet-4.5")
        temperature: Controls randomness in generation (0.0 to 1.0)
        max_tokens: Maximum number of tokens to generate
        api_key: Optional API key (defaults to ANTHROPIC_API_KEY env variable)
    """

    model_name: str = "claude-sonnet-4.5-20250929"
    temperature: float = 0.8
    max_tokens: int = 1024
    api_key: str | None = None

    _client: Any = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data: Any):
        super().__init__(**data)
        resolved_api_key = self._get_api_key("ANTHROPIC_API_KEY", "Claude")

        from anthropic import Anthropic

        self._client = self._initialize_client(Anthropic, resolved_api_key, "anthropic")

    def _call(
        self,
        prompt: str,
        stop: Sequence[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text using Claude API.

        Args:
            prompt: The input text prompt
            stop: Optional list of stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text response

        Raises:
            RuntimeError: If Claude fails to generate a response
        """
        # Override defaults with kwargs if provided
        temperature = kwargs.pop("temperature", self.temperature)
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)

        try:
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )

            if not response.content or len(response.content) == 0:
                raise RuntimeError("Claude response did not contain any text.")

            return response.content[0].text

        except Exception as e:
            self._handle_api_error(e, "Claude")

    @property
    def _llm_type(self) -> str:
        return "anthropic-claude"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


class ClaudeSonnet45Model(ClaudeModel):
    """Claude Sonnet 4.5 - Balanced performance model (recommended for most use cases)."""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        super().__init__(
            model_name="claude-sonnet-4-20250514",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class ClaudeOpus4Model(ClaudeModel):
    """Claude Opus 4 - Most capable model for complex tasks."""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        super().__init__(
            model_name="claude-opus-4-20250514",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )


class ClaudeHaikuModel(ClaudeModel):
    """Claude Haiku 3.5 - Fast and efficient model for simpler tasks."""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        super().__init__(
            model_name="claude-3-5-haiku-20241022",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
