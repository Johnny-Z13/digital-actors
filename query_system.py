"""
Query System for LLM-based condition evaluation.

Provides a caching, latching query mechanism for scene handlers
to evaluate natural language conditions using Claude Haiku.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm_prompt_core.models.base import BaseLLMModel

logger = logging.getLogger(__name__)


@dataclass
class QueryCache:
    """
    LRU-style cache for query results.

    Caches by (input_hash, query_hash) to avoid redundant LLM calls.
    """

    max_size: int = 500
    _cache: dict[str, bool] = field(default_factory=dict)

    def _make_key(self, input_text: str, query_text: str) -> str:
        """Create cache key from input and query text using MD5 hashing."""
        combined = f"{input_text}|||{query_text}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, input_text: str, query_text: str) -> bool | None:
        """Get cached result or None if not cached."""
        key = self._make_key(input_text, query_text)
        return self._cache.get(key)

    def set(self, input_text: str, query_text: str, result: bool) -> None:
        """Cache a query result. Evicts oldest if at capacity."""
        key = self._make_key(input_text, query_text)

        # Simple eviction: remove first item if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        self._cache[key] = result


class QuerySystem:
    """
    LLM-based condition evaluation with caching and latching.

    Evaluates natural language conditions against dialogue context
    using Claude Haiku for fast, cheap evaluation.

    Features:
    - Caching: Results cached by (input_hash, query_hash)
    - Latching: Once True, stays True for session duration
    - Context injection: Optional additional context for evaluation
    """

    def __init__(
        self,
        model: BaseLLMModel | None = None,
        cache_max_size: int = 500,
    ) -> None:
        """
        Initialize the query system.

        Args:
            model: LLM model to use for evaluation (defaults to ClaudeHaikuModel)
            cache_max_size: Maximum number of cached query results
        """
        self._model = model
        self._cache = QueryCache(max_size=cache_max_size)
        self._latched: dict[str, bool] = {}  # query_hash -> True (once latched)

    def _get_model(self) -> BaseLLMModel:
        """Lazy initialization of model to avoid import at module load."""
        if self._model is None:
            from constants import LLM_MAX_TOKENS_QUERY, LLM_TEMPERATURE_QUERY
            from llm_prompt_core.models.anthropic import ClaudeHaikuModel

            self._model = ClaudeHaikuModel(
                temperature=LLM_TEMPERATURE_QUERY,
                max_tokens=LLM_MAX_TOKENS_QUERY,
            )
        return self._model

    def _make_latch_key(self, query_text: str, session_id: str = "") -> str:
        """Create latch key from query text and optional session ID."""
        combined = f"{session_id}|||{query_text}"
        return hashlib.md5(combined.encode()).hexdigest()

    async def query(
        self,
        input_text: str,
        query_text: str,
        latch: bool = False,
        context: str = "",
        session_id: str = "",
    ) -> bool:
        """
        Evaluate a condition using LLM.

        Args:
            input_text: The dialogue or text to evaluate against
            query_text: The condition to check (e.g., "Player has earned trust")
            latch: If True, once query returns True it stays True for session
            context: Additional context to provide to the LLM
            session_id: Session identifier for latch isolation

        Returns:
            bool: Whether the condition is met

        Example:
            result = await query_system.query(
                dialogue_history,
                "Player has mentioned their family",
                latch=True
            )
        """
        # Check latch first - if already latched True, return immediately
        if latch:
            latch_key = self._make_latch_key(query_text, session_id)
            if self._latched.get(latch_key):
                logger.debug("Query latched True: %s", query_text[:50])
                return True

        # Check cache
        cached = self._cache.get(input_text, query_text)
        if cached is not None:
            logger.debug("Query cache hit: %s -> %s", query_text[:50], cached)
            return cached

        # Build evaluation prompt
        prompt = self._build_prompt(input_text, query_text, context)

        # Call LLM
        try:
            model = self._get_model()
            response = await self._invoke_async(model, prompt)
            result = self._parse_response(response)
        except Exception as e:
            logger.warning("Query evaluation failed: %s - defaulting to False", e)
            result = False

        # Cache result
        self._cache.set(input_text, query_text, result)

        # Latch if requested and result is True
        if latch and result:
            latch_key = self._make_latch_key(query_text, session_id)
            self._latched[latch_key] = True
            logger.debug("Query latched: %s", query_text[:50])

        logger.debug("Query evaluated: %s -> %s", query_text[:50], result)
        return result

    def _build_prompt(self, input_text: str, query_text: str, context: str) -> str:
        """Build the LLM prompt for condition evaluation."""
        prompt_parts = [
            "You are evaluating whether a condition is true based on the given text.",
            "Respond with ONLY 'YES' or 'NO' - nothing else.",
            "",
            "=== TEXT TO EVALUATE ===",
            input_text[-2000:],  # Limit to last 2000 chars
            "",
        ]

        if context:
            prompt_parts.extend([
                "=== ADDITIONAL CONTEXT ===",
                context,
                "",
            ])

        prompt_parts.extend([
            "=== CONDITION TO CHECK ===",
            query_text,
            "",
            "Is this condition TRUE based on the text above? Respond YES or NO:",
        ])

        return "\n".join(prompt_parts)

    async def _invoke_async(self, model: BaseLLMModel, prompt: str) -> str:
        """Invoke model asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: model._call(prompt))

    def _parse_response(self, response: str) -> bool:
        """Parse YES/NO response from LLM."""
        cleaned = response.strip().upper()
        return cleaned.startswith("YES")

    def clear_latches(self, session_id: str = "") -> None:
        """Clear all latched values for a session."""
        if session_id:
            keys_to_remove = [k for k in self._latched if session_id in k]
            for key in keys_to_remove:
                del self._latched[key]
        else:
            self._latched.clear()
        logger.debug("Cleared latches for session: %s", session_id or "(all)")

    def clear_cache(self) -> None:
        """Clear the query cache."""
        self._cache._cache.clear()
        logger.debug("Query cache cleared")


# Module-level singleton for shared use
_query_system: QuerySystem | None = None


def get_query_system(model: BaseLLMModel | None = None) -> QuerySystem:
    """
    Get or create the global QuerySystem instance.

    Args:
        model: Optional model to use (only used on first call)

    Returns:
        Shared QuerySystem instance
    """
    global _query_system
    if _query_system is None:
        _query_system = QuerySystem(model=model)
    return _query_system
