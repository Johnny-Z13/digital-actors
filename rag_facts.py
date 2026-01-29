"""
RAG Facts Engine for lightweight fact retrieval.

Provides embedding-based fact retrieval using sentence-transformers,
with a keyword fallback when the library is not installed.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Try to import numpy and sentence-transformers, fall back to keyword matching if unavailable
_numpy_available = False
_sentence_transformer_available = False
_embedding_model: Any = None
np: Any = None

try:
    import numpy as _np
    np = _np
    _numpy_available = True
except ImportError:
    logger.warning("numpy not installed, embedding-based retrieval disabled")

try:
    from sentence_transformers import SentenceTransformer

    if _numpy_available:
        _sentence_transformer_available = True
        logger.info("sentence-transformers available, using embedding-based retrieval")
    else:
        logger.warning("sentence-transformers requires numpy, falling back to keyword matching")
except ImportError:
    logger.warning(
        "sentence-transformers not installed, falling back to keyword matching. "
        "Install with: pip install sentence-transformers"
    )


@dataclass
class RAGResult:
    """Result of a fact retrieval query."""

    facts: list[str]
    scores: list[float]
    method: str  # "embedding" or "keyword"


@dataclass
class FactIndex:
    """Indexed facts for a single scene."""

    scene_id: str
    facts: list[str]
    embeddings: Any = None  # np.ndarray | None, Shape: (num_facts, embedding_dim)


class RAGFactsEngine:
    """
    Lightweight fact retrieval using sentence-transformers.

    Indexes facts per scene at load time, then retrieves relevant facts
    via cosine similarity when queried.

    Features:
    - Fast embedding computation at scene load
    - Instant retrieval via vector similarity
    - Keyword fallback when sentence-transformers unavailable
    - Configurable similarity threshold
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.3,
    ) -> None:
        """
        Initialize the RAG engine.

        Args:
            model_name: Sentence transformer model to use (384-dim, fast)
            similarity_threshold: Minimum cosine similarity for inclusion
        """
        self._model_name = model_name
        self._similarity_threshold = similarity_threshold
        self._indices: dict[str, FactIndex] = {}  # scene_id -> FactIndex
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazy load the sentence transformer model."""
        global _embedding_model

        if not _sentence_transformer_available:
            return None

        if _embedding_model is None:
            logger.info("Loading sentence transformer model: %s", self._model_name)
            from sentence_transformers import SentenceTransformer

            _embedding_model = SentenceTransformer(self._model_name)
            logger.info("Model loaded successfully")

        return _embedding_model

    def set_facts(self, scene_id: str, facts: list[str]) -> None:
        """
        Index facts for a scene.

        Computes embeddings at scene load time for fast retrieval.

        Args:
            scene_id: Scene identifier
            facts: List of fact strings to index
        """
        if not facts:
            logger.debug("No facts to index for scene: %s", scene_id)
            return

        model = self._get_model()
        embeddings = None

        if model is not None:
            try:
                # Compute embeddings for all facts
                embeddings = model.encode(facts, convert_to_numpy=True)
                logger.info(
                    "Indexed %d facts for scene %s using embeddings",
                    len(facts),
                    scene_id,
                )
            except Exception as e:
                logger.warning("Failed to compute embeddings: %s", e)
                embeddings = None

        if embeddings is None:
            logger.info(
                "Indexed %d facts for scene %s using keyword fallback",
                len(facts),
                scene_id,
            )

        self._indices[scene_id] = FactIndex(
            scene_id=scene_id,
            facts=facts,
            embeddings=embeddings,
        )

    def retrieve(
        self,
        query: str,
        scene_id: str | None = None,
        top_k: int = 3,
    ) -> RAGResult:
        """
        Retrieve relevant facts for a query.

        Uses embedding similarity if available, otherwise keyword matching.

        Args:
            query: Query string to match against facts
            scene_id: Specific scene to search (None = search all)
            top_k: Maximum number of facts to return

        Returns:
            RAGResult with matching facts and scores
        """
        # Gather facts from relevant scenes
        if scene_id and scene_id in self._indices:
            indices_to_search = [self._indices[scene_id]]
        else:
            indices_to_search = list(self._indices.values())

        if not indices_to_search:
            return RAGResult(facts=[], scores=[], method="none")

        # Try embedding-based retrieval
        model = self._get_model()
        if model is not None and all(idx.embeddings is not None for idx in indices_to_search):
            return self._retrieve_by_embedding(query, indices_to_search, top_k, model)

        # Fall back to keyword matching
        return self._retrieve_by_keyword(query, indices_to_search, top_k)

    def _retrieve_by_embedding(
        self,
        query: str,
        indices: list[FactIndex],
        top_k: int,
        model: Any,
    ) -> RAGResult:
        """Retrieve using cosine similarity."""
        # Encode query
        query_embedding = model.encode([query], convert_to_numpy=True)[0]

        # Collect all facts and embeddings
        all_facts: list[str] = []
        all_embeddings: list[np.ndarray] = []

        for idx in indices:
            if idx.embeddings is not None:
                all_facts.extend(idx.facts)
                for i in range(len(idx.facts)):
                    all_embeddings.append(idx.embeddings[i])

        if not all_facts:
            return RAGResult(facts=[], scores=[], method="embedding")

        # Compute cosine similarities
        embeddings_matrix = np.stack(all_embeddings)
        similarities = self._cosine_similarity(query_embedding, embeddings_matrix)

        # Filter by threshold and get top-k
        ranked_indices = np.argsort(similarities)[::-1]

        results_facts: list[str] = []
        results_scores: list[float] = []

        for idx in ranked_indices[:top_k]:
            score = float(similarities[idx])
            if score >= self._similarity_threshold:
                results_facts.append(all_facts[idx])
                results_scores.append(score)

        return RAGResult(facts=results_facts, scores=results_scores, method="embedding")

    def _retrieve_by_keyword(
        self,
        query: str,
        indices: list[FactIndex],
        top_k: int,
    ) -> RAGResult:
        """Retrieve using keyword matching as fallback."""
        # Extract keywords from query (lowercase, remove punctuation)
        query_lower = query.lower()
        query_words = set(re.findall(r"\b\w+\b", query_lower))

        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "can",
            "of", "in", "to", "for", "with", "on", "at", "by", "from",
            "as", "into", "about", "like", "through", "after", "over",
            "between", "out", "against", "during", "without", "before",
            "under", "around", "among", "and", "or", "but", "if", "then",
            "so", "that", "this", "what", "which", "who", "whom", "whose",
            "when", "where", "why", "how", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "no", "not",
            "only", "same", "than", "too", "very", "just", "also", "now",
        }
        query_words = query_words - stop_words

        if not query_words:
            return RAGResult(facts=[], scores=[], method="keyword")

        # Score facts by keyword overlap
        scored_facts: list[tuple[str, float]] = []

        for idx in indices:
            for fact in idx.facts:
                fact_lower = fact.lower()
                fact_words = set(re.findall(r"\b\w+\b", fact_lower))

                # Calculate Jaccard-like overlap score
                overlap = len(query_words & fact_words)
                if overlap > 0:
                    score = overlap / max(len(query_words), 1)
                    scored_facts.append((fact, score))

        # Sort by score descending
        scored_facts.sort(key=lambda x: x[1], reverse=True)

        # Take top-k above threshold
        results_facts: list[str] = []
        results_scores: list[float] = []

        for fact, score in scored_facts[:top_k]:
            if score >= self._similarity_threshold:
                results_facts.append(fact)
                results_scores.append(score)

        return RAGResult(facts=results_facts, scores=results_scores, method="keyword")

    def _cosine_similarity(
        self,
        query_vec: np.ndarray,
        fact_vecs: np.ndarray,
    ) -> np.ndarray:
        """Compute cosine similarity between query and all facts."""
        # Normalize vectors
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
        fact_norms = fact_vecs / (np.linalg.norm(fact_vecs, axis=1, keepdims=True) + 1e-9)

        # Dot product = cosine similarity for normalized vectors
        return np.dot(fact_norms, query_norm)

    def clear(self, scene_id: str | None = None) -> None:
        """
        Clear indexed facts.

        Args:
            scene_id: Specific scene to clear (None = clear all)
        """
        if scene_id:
            self._indices.pop(scene_id, None)
            logger.debug("Cleared facts for scene: %s", scene_id)
        else:
            self._indices.clear()
            logger.debug("Cleared all fact indices")

    def get_fact_count(self, scene_id: str | None = None) -> int:
        """Get number of indexed facts."""
        if scene_id:
            idx = self._indices.get(scene_id)
            return len(idx.facts) if idx else 0
        return sum(len(idx.facts) for idx in self._indices.values())


# Module-level singleton for shared use
_rag_engine: RAGFactsEngine | None = None


def get_rag_engine(
    model_name: str = "all-MiniLM-L6-v2",
    similarity_threshold: float = 0.3,
) -> RAGFactsEngine:
    """
    Get or create the global RAGFactsEngine instance.

    Args:
        model_name: Sentence transformer model (only used on first call)
        similarity_threshold: Minimum similarity (only used on first call)

    Returns:
        Shared RAGFactsEngine instance
    """
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGFactsEngine(
            model_name=model_name,
            similarity_threshold=similarity_threshold,
        )
    return _rag_engine
