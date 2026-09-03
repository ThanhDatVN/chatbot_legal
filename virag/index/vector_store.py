"""Dense vector store: Qdrant in production, NumPy on disk offline.

The temporal filter is applied *inside* the vector search, not after it.
Filtering afterwards silently shrinks top-k - ask for 30 neighbours, get 30
current-law hits, filter to the 2021 event date, and be left with two.  Qdrant
evaluates the payload filter during traversal, so top-k stays top-k.

Dates are stored as integer days-since-epoch (``effective_from_days`` /
``effective_to_days``) because integer range filters are exactly supported on
every backend, with sentinels for "unknown" so open-ended validity still
matches.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from virag.schemas import Chunk

logger = logging.getLogger(__name__)

_EPOCH = date(1970, 1, 1)
#: Sentinels for an unknown bound: "in force since forever / until further notice".
UNKNOWN_FROM = -36500
UNKNOWN_TO = 36500


def to_days(iso_date: str | None, default: int) -> int:
    if not iso_date:
        return default
    try:
        return (date.fromisoformat(iso_date) - _EPOCH).days
    except ValueError:
        return default


@dataclass
class SearchFilters:
    """Payload predicates evaluated during vector traversal."""

    as_of_days: int | None = None
    tax_domains: list[str] | None = None
    max_authority_tier: int | None = None
    document_ids: list[str] | None = None

    def matches(self, payload: dict[str, Any]) -> bool:
        """In-memory equivalent of the Qdrant filter, kept in sync by tests."""
        if self.as_of_days is not None:
            if payload.get("effective_from_days", UNKNOWN_FROM) > self.as_of_days:
                return False
            if payload.get("effective_to_days", UNKNOWN_TO) < self.as_of_days:
                return False
        if self.tax_domains and not set(payload.get("tax_domains") or []) & set(
            self.tax_domains
        ):
            return False
        if (
            self.max_authority_tier is not None
            and int(payload.get("authority_tier", 9)) > self.max_authority_tier
        ):
            return False
        # Kept as a guard clause so every predicate reads the same way.
        if self.document_ids and payload.get("document_id") not in set(  # noqa: SIM103
            self.document_ids
        ):
            return False
        return True


def chunk_payload(chunk: Chunk) -> dict[str, Any]:
    payload = chunk.payload()
    payload["effective_from_days"] = to_days(chunk.effective_from, UNKNOWN_FROM)
    payload["effective_to_days"] = to_days(chunk.effective_to, UNKNOWN_TO)
    # The body is already in the ChunkStore; keeping it out of the vector
    # payload halves Qdrant's memory footprint on a 4 GB corpus.
    payload.pop("text", None)
    return payload


class VectorStore(Protocol):
    def recreate(self, dim: int) -> None: ...
    def upsert(self, chunks: list[Chunk], vectors: np.ndarray) -> None: ...
    def search(
        self, vector: np.ndarray, top_k: int, filters: SearchFilters | None = None
    ) -> list[tuple[str, float]]: ...
    def count(self) -> int: ...


# ---------------------------------------------------------------------------
# NumPy fallback
# ---------------------------------------------------------------------------


class NumpyVectorStore:
    """Exact cosine search over an in-memory matrix, persisted as ``.npz``.

    Linear scan is fine at this corpus size (order 10^5 chunks) and removes a
    service dependency from the test path.
    """

    def __init__(self, root: Path, name: str = "vectors") -> None:
        self.root = root
        self.vectors_path = root / f"{name}.npz"
        self.payloads_path = root / f"{name}.payloads.json"
        self.ids: list[str] = []
        self.payloads: list[dict[str, Any]] = []
        self.matrix: np.ndarray | None = None

    def recreate(self, dim: int) -> None:
        self.ids, self.payloads, self.matrix = [], [], np.zeros((0, dim), dtype=np.float32)

    def upsert(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if not chunks:
            return
        payloads = [chunk_payload(chunk) for chunk in chunks]
        ids = [chunk.chunk_id for chunk in chunks]
        if self.matrix is None or self.matrix.size == 0:
            self.matrix = np.asarray(vectors, dtype=np.float32)
            self.ids, self.payloads = list(ids), payloads
        else:
            self.matrix = np.vstack([self.matrix, np.asarray(vectors, dtype=np.float32)])
            self.ids.extend(ids)
            self.payloads.extend(payloads)

    def search(
        self, vector: np.ndarray, top_k: int, filters: SearchFilters | None = None
    ) -> list[tuple[str, float]]:
        if self.matrix is None or self.matrix.size == 0:
            return []
        query = np.asarray(vector, dtype=np.float32).reshape(-1)
        scores = self.matrix @ query

        if filters is not None:
            mask = np.array([filters.matches(payload) for payload in self.payloads])
            if not mask.any():
                return []
            scores = np.where(mask, scores, -np.inf)

        limit = min(top_k, int(np.isfinite(scores).sum()))
        if limit <= 0:
            return []
        top = np.argpartition(-scores, limit - 1)[:limit]
        top = top[np.argsort(-scores[top])]
        return [(self.ids[i], float(scores[i])) for i in top if np.isfinite(scores[i])]

    def count(self) -> int:
        return len(self.ids)

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(self.vectors_path, matrix=self.matrix if self.matrix is not None else [])
        self.payloads_path.write_text(
            json.dumps({"ids": self.ids, "payloads": self.payloads}, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self) -> NumpyVectorStore:
        if self.vectors_path.exists():
            self.matrix = np.load(self.vectors_path)["matrix"]
        if self.payloads_path.exists():
            payload = json.loads(self.payloads_path.read_text(encoding="utf-8"))
            self.ids = payload["ids"]
            self.payloads = payload["payloads"]
        return self


# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------


class QdrantVectorStore:
    def __init__(self, url: str, collection: str) -> None:
        from qdrant_client import QdrantClient

        self.collection = collection
        self.client = QdrantClient(url=url, timeout=60.0)

    def recreate(self, dim: int) -> None:
        from qdrant_client import models

        self.client.recreate_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        # Indexes on the fields the filter touches; without them Qdrant falls
        # back to a full payload scan per query.
        for field_name, schema in (
            ("effective_from_days", models.PayloadSchemaType.INTEGER),
            ("effective_to_days", models.PayloadSchemaType.INTEGER),
            ("authority_tier", models.PayloadSchemaType.INTEGER),
            ("tax_domains", models.PayloadSchemaType.KEYWORD),
            ("document_id", models.PayloadSchemaType.KEYWORD),
        ):
            try:
                self.client.create_payload_index(self.collection, field_name, field_schema=schema)
            except Exception as exc:  # index may already exist
                logger.debug("payload index %s: %s", field_name, exc)

    def upsert(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        from qdrant_client import models

        if not chunks:
            return
        points = [
            models.PointStruct(
                id=_point_id(chunk.chunk_id),
                vector=np.asarray(vector, dtype=np.float32).tolist(),
                payload=chunk_payload(chunk),
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def _build_filter(self, filters: SearchFilters | None):
        from qdrant_client import models

        if filters is None:
            return None
        must: list[Any] = []
        if filters.as_of_days is not None:
            must.append(
                models.FieldCondition(
                    key="effective_from_days", range=models.Range(lte=filters.as_of_days)
                )
            )
            must.append(
                models.FieldCondition(
                    key="effective_to_days", range=models.Range(gte=filters.as_of_days)
                )
            )
        if filters.tax_domains:
            must.append(
                models.FieldCondition(
                    key="tax_domains", match=models.MatchAny(any=list(filters.tax_domains))
                )
            )
        if filters.max_authority_tier is not None:
            must.append(
                models.FieldCondition(
                    key="authority_tier", range=models.Range(lte=filters.max_authority_tier)
                )
            )
        if filters.document_ids:
            must.append(
                models.FieldCondition(
                    key="document_id", match=models.MatchAny(any=list(filters.document_ids))
                )
            )
        return models.Filter(must=must) if must else None

    def search(
        self, vector: np.ndarray, top_k: int, filters: SearchFilters | None = None
    ) -> list[tuple[str, float]]:
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=np.asarray(vector, dtype=np.float32).tolist(),
            query_filter=self._build_filter(filters),
            limit=top_k,
            with_payload=True,
        )
        return [(hit.payload.get("chunk_id", str(hit.id)), float(hit.score)) for hit in hits]

    def count(self) -> int:
        try:
            return int(self.client.count(self.collection, exact=True).count)
        except Exception:
            return 0


def _point_id(chunk_id: str) -> int:
    """Qdrant point ids must be uint64 or UUID; chunk ids are 16 hex chars."""
    return int(chunk_id[:15], 16)


def build_vector_store(url: str, collection: str, fallback_root: Path) -> VectorStore:
    """Prefer Qdrant; fall back to the NumPy store when it is unreachable."""
    try:
        store = QdrantVectorStore(url, collection)
        store.client.get_collections()
        logger.info("using Qdrant at %s (collection=%s)", url, collection)
        return store
    except Exception as exc:
        logger.warning("Qdrant unavailable at %s (%s); using the NumPy store", url, exc)
        return NumpyVectorStore(fallback_root).load()
