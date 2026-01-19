"""
Google Gemini model wrapper.

This module provides a LangChain-compatible wrapper for Google Gemini models.
Moved from project_one_demo/model_utils.py
"""

import os
from typing import Any, Dict, Optional, Sequence

from google import genai
from google.genai import types as genai_types
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field, PrivateAttr

from llm_prompt_core.models.base import BaseLLMModel


class GoogleGeminiModel(BaseLLMModel):
    """Minimal LangChain-compatible adapter for the official Google GenAI SDK."""

    model_name: str
    temperature: float = 0.8
    max_tokens: int = 1024
    thinking_budget: Optional[int] = None
    include_thoughts: Optional[bool] = None
    api_key: Optional[str] = None
    generation_config: Dict[str, Any] = Field(default_factory=dict)

    _client: genai.Client = PrivateAttr()

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data: Any):
        super().__init__(**data)
        resolved_api_key = self.api_key or os.getenv("GOOGLE_API_KEY")
        if not resolved_api_key:
            raise EnvironmentError(
                "GOOGLE_API_KEY environment variable must be set for Google Gemini models."
            )
        self._client = genai.Client(api_key=resolved_api_key)

    def _build_generation_config(
        self,
        stop: Optional[Sequence[str]],
        overrides: Dict[str, Any],
    ) -> genai_types.GenerateContentConfig:
        config_kwargs: Dict[str, Any] = {
            "temperature": overrides.pop("temperature", self.temperature),
            "max_output_tokens": overrides.pop(
                "max_output_tokens",
                overrides.pop("max_tokens", self.max_tokens),
            ),
        }

        # Respect stop sequences passed at invocation time (LangChain's `stop` arg).
        stop_sequences = overrides.pop("stop_sequences", None)
        if not stop_sequences and stop:
            stop_sequences = list(stop)
        if stop_sequences:
            config_kwargs["stop_sequences"] = stop_sequences

        if self.generation_config:
            config_kwargs.update(self.generation_config)
        config_kwargs.update(overrides)

        thinking_kwargs: Dict[str, Any] = {}
        if self.thinking_budget is not None:
            thinking_kwargs["thinking_budget"] = self.thinking_budget
        if self.include_thoughts is not None:
            thinking_kwargs["include_thoughts"] = self.include_thoughts
        if thinking_kwargs:
            config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
                **thinking_kwargs
            )

        return genai_types.GenerateContentConfig(**config_kwargs)

    def _call(
        self,
        prompt: str,
        stop: Optional[Sequence[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        config = self._build_generation_config(stop=stop, overrides=dict(kwargs))
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        text_response = response.text
        if text_response is None:
            raise RuntimeError("Google Gemini response did not contain any text.")
        return text_response

    @property
    def _llm_type(self) -> str:
        return "google-genai"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "thinking_budget": self.thinking_budget,
            "include_thoughts": self.include_thoughts,
        }


class GeminiFlash25NoThinking(GoogleGeminiModel):
    """Gemini 2.5 Flash with thinking explicitly disabled."""

    def __init__(
        self,
        temperature: float = 0.8,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        super().__init__(
            model_name="gemini-2.5-flash",
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=0,
            include_thoughts=False,
            **kwargs,
        )
