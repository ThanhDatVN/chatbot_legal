"""Cross-encoder reranking.

Bi-encoders score the query and the passage independently, so they cannot see
that "thue suat 10%" in a passage answers "thue suat bao nhieu" while "thue
suat 0%" does not.  A cross-encoder reads the pair jointly and reorders the
fused candidate list, which is where most of the precision gain in the ablation
comes from.

As everywhere else, the real model has a dependency-free stand-in so the system
degrades instead of failing.
"""

from __future__ import annotations

import logging
import math
from typing import Protocol

from virag.index.bm25 import tokenize
from virag.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class Reranker(Protocol):
    name: str

    def score(self, query: str, passages: list[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name, max_length=512)
        self.name = model_name

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        pairs = [(query, passage) for passage in passages]
        scores = self.model.predict(pairs, batch_size=16, show_progress_bar=False)
        return [float(score) for score in scores]


class LexicalReranker:
    """Fallback reranker: IDF-free lexical containment with a coverage bonus.

    It is not a cross-encoder and is not claimed to be one - it exists so the
    ``use_reranker`` code path is exercised without a model download.  Scores
    are shifted into roughly the same range as a cross-encoder logit so the
    ``min_rerank_score`` threshold keeps its meaning.
    """

    name = "lexical-fallback"

    def score(self, query: str, passages: list[str]) -> list[float]:
        query_terms = set(tokenize(query))
        if not query_terms:
            return [0.0] * len(passages)

        scores: list[float] = []
        for passage in passages:
            passage_terms = set(tokenize(passage))
            if not passage_terms:
                scores.append(-10.0)
                continue
            overlap = query_terms & passage_terms
            coverage = len(overlap) / len(query_terms)
            density = len(overlap) / math.sqrt(len(passage_terms))
            # Map [0, ~1.4] onto roughly [-8, +6], the usual cross-encoder range.
            scores.append(round(-8.0 + 10.0 * coverage + 2.0 * density, 4))
        return scores


_RERANKER: Reranker | None = None


def build_reranker(settings: Settings | None = None) -> Reranker:
    settings = settings or get_settings()
    backend = settings.reranker_backend.lower()

    if backend in {"lexical", "none", "fallback"}:
        return LexicalReranker()

    if backend in {"auto", "cross-encoder", "ce"}:
        try:
            return CrossEncoderReranker(settings.reranker_model)
        except Exception as exc:
            if backend != "auto":
                raise
            logger.warning(
                "falling back to the lexical reranker (%s unavailable: %s)",
                settings.reranker_model,
                exc,
            )
            return LexicalReranker()

    raise ValueError(f"unknown reranker backend: {settings.reranker_backend}")


def get_reranker(settings: Settings | None = None) -> Reranker:
    global _RERANKER
    if _RERANKER is None:
        _RERANKER = build_reranker(settings)
    return _RERANKER


def reset_reranker() -> None:
    global _RERANKER
    _RERANKER = None
