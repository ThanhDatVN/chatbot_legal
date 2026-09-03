"""Dense encoders.

Two backends behind one interface:

*   ``SentenceTransformerEmbedder`` - the real model (BGE-M3 by default, strong
    on Vietnamese and trained for retrieval).
*   ``HashingEmbedder`` - a deterministic character-n-gram encoder with no
    downloads.  It exists so that the test suite, CI and a first
    ``docker compose up`` on a machine with no model cache still produce a
    working, if weaker, system instead of an import error.  Every benchmark
    reports which backend produced it.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Protocol

import numpy as np

from virag.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Models that were trained with an explicit query/passage instruction prefix.
_E5_FAMILY = ("e5", "multilingual-e5")


class Embedder(Protocol):
    dim: int
    name: str

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray: ...


def _l2_normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class HashingEmbedder:
    """Deterministic, dependency-free encoder.

    Hashes word unigrams, word bigrams and character 4-grams into a fixed
    vector with sub-linear term weighting.  It is a bag-of-n-grams model, so it
    captures lexical similarity only - which is exactly the honest floor to
    compare a real semantic encoder against.
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim
        self.name = f"hashing-{dim}"

    @staticmethod
    def _features(text: str) -> list[str]:
        lowered = text.lower()
        words = re.findall(r"[0-9a-zà-ỹ%/]+", lowered)
        features = list(words)
        features += [f"{a}_{b}" for a, b in zip(words, words[1:], strict=False)]
        compact = re.sub(r"\s+", " ", lowered)
        features += [compact[i : i + 4] for i in range(0, max(0, len(compact) - 3), 2)]
        return features

    def _encode_one(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        # Sub-linear damping, mirroring the log term-frequency of BM25.
        return np.sign(vector) * np.log1p(np.abs(vector))

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        matrix = np.vstack([self._encode_one(text) for text in texts])
        return _l2_normalise(matrix)


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, dim: int) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        detected = self.model.get_sentence_embedding_dimension()
        if detected and detected != dim:
            logger.info("embedding dim from model is %d (config said %d)", detected, dim)
        self.dim = detected or dim
        self.name = model_name
        self._needs_prefix = any(token in model_name.lower() for token in _E5_FAMILY)

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        prepared = texts
        if self._needs_prefix:
            prefix = "query: " if is_query else "passage: "
            prepared = [prefix + text for text in texts]
        vectors = self.model.encode(
            prepared,
            batch_size=16,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


_EMBEDDER: Embedder | None = None


def build_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    backend = settings.embedding_backend.lower()

    if backend == "hashing":
        return HashingEmbedder(settings.embedding_dim)

    if backend in {"auto", "sentence-transformers", "st"}:
        try:
            return SentenceTransformerEmbedder(settings.embedding_model, settings.embedding_dim)
        except Exception as exc:
            if backend != "auto":
                raise
            logger.warning(
                "falling back to the hashing embedder (%s unavailable: %s)",
                settings.embedding_model,
                exc,
            )
            return HashingEmbedder(settings.embedding_dim)

    raise ValueError(f"unknown embedding backend: {settings.embedding_backend}")


def get_embedder(settings: Settings | None = None) -> Embedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = build_embedder(settings)
    return _EMBEDDER


def reset_embedder() -> None:
    """Drop the cached encoder - used by tests that switch backends."""
    global _EMBEDDER
    _EMBEDDER = None
