"""Qdrant access: a server when QDRANT_URL is set, otherwise an embedded on-disk store."""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np

from app.errors import VectorStoreUnavailable

NAMESPACE = uuid.UUID("7f0e6b1c-3c55-4d7e-9a57-1d9c0c1e2a11")


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, chunk_id))


class VectorStore:
    def __init__(self, collection: str, url: str | None = None, api_key: str | None = None,
                 path: Path | None = None) -> None:
        from qdrant_client import QdrantClient

        self.collection = collection
        try:
            # query_points needs server >= 1.10; skip the client's minor-version warning
            self.client = QdrantClient(url=url, api_key=api_key, timeout=10, check_compatibility=False) if url \
                else QdrantClient(path=str(path))
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreUnavailable() from exc

    def healthy(self) -> bool:
        try:
            return self.client.collection_exists(self.collection)
        except Exception:  # noqa: BLE001
            return False

    def count(self) -> int:
        return self.client.count(self.collection, exact=True).count

    def recreate(self, dim: int) -> None:
        from qdrant_client import models

        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(self.collection,
                                      vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
        for field in ("document_id", "currency_status", "section_kind"):
            try:
                self.client.create_payload_index(self.collection, field, models.PayloadSchemaType.KEYWORD)
            except Exception:  # noqa: BLE001 - embedded mode ignores payload indexes
                pass

    def upsert(self, chunk_ids: list[str], vectors: np.ndarray, payloads: list[dict], batch: int = 128) -> None:
        from qdrant_client import models

        for i in range(0, len(chunk_ids), batch):
            points = [models.PointStruct(id=point_id(cid), vector=vectors[j].tolist(), payload=payloads[j])
                      for j, cid in enumerate(chunk_ids[i:i + batch], start=i)]
            self.client.upsert(self.collection, points=points, wait=True)

    def search(self, vector: np.ndarray, allowed: list[str], top_k: int) -> list[tuple[str, float]]:
        from qdrant_client import models

        if not allowed:
            return []
        try:
            result = self.client.query_points(
                self.collection, query=vector.tolist(), limit=top_k, with_payload=["chunk_id"],
                query_filter=models.Filter(must=[models.HasIdCondition(has_id=[point_id(c) for c in allowed])]))
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreUnavailable() from exc
        return [(p.payload["chunk_id"], float(p.score)) for p in result.points]
