"""Wire the corpus, indexes and models from settings; check they belong to the same snapshot."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.errors import SnapshotUnavailable
from app.retrieval.models import BgeM3Encoder, BgeReranker
from app.retrieval.service import RetrievalService
from app.retrieval.sparse import SparseIndex
from app.storage.corpus import CorpusCatalog
from app.storage.vector_store import VectorStore


@dataclass
class Runtime:
    settings: Settings
    catalog: CorpusCatalog
    store: VectorStore
    retrieval: RetrievalService
    index_manifest: dict

    def readiness(self) -> dict:
        checks = {
            "snapshot_loaded": bool(self.catalog.chunks),
            "snapshot_quality_passed": bool(self.catalog.manifest.get("quality_passed")),
            "index_matches_snapshot": self.index_manifest.get("chunks_sha256") == self.catalog.manifest["chunks_sha256"],
            "vector_store": self.store.healthy() and self.store.count() == len(self.catalog.chunks),
            "bm25": len(self.retrieval.sparse.ids) == len(self.catalog.chunks),
        }
        return {"ready": all(checks.values()), "checks": checks, **self.catalog.stats()}


_lock = threading.Lock()
_runtime: Runtime | None = None


def build_runtime(settings: Settings | None = None) -> Runtime:
    settings = settings or get_settings()
    catalog = CorpusCatalog(settings.snapshot_dir, settings.currency_policy)
    index_dir = settings.index_dir / catalog.snapshot_id
    manifest_path = index_dir / "index_manifest.json"
    if not manifest_path.exists():
        raise SnapshotUnavailable()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    store = VectorStore(settings.collection, url=settings.qdrant_url, api_key=settings.qdrant_api_key,
                        path=settings.index_dir / "qdrant")
    sparse = SparseIndex.load(index_dir / "bm25.json")
    encoder = BgeM3Encoder(settings.embedding_model, settings.model_device, settings.hf_offline)
    reranker = BgeReranker(settings.reranker_model, settings.model_device, settings.hf_offline,
                           settings.reranker_max_length)
    retrieval = RetrievalService(catalog, store, sparse, encoder, reranker, settings.dense_top_k,
                                 settings.sparse_top_k, settings.rrf_k, settings.rerank_candidates,
                                 settings.ineligible_rerank_candidates)
    return Runtime(settings=settings, catalog=catalog, store=store, retrieval=retrieval, index_manifest=manifest)


def get_runtime() -> Runtime:
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = build_runtime()
        return _runtime
