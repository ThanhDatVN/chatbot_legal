"""Retrieval pipeline: dense + BM25 → RRF → cross-encoder rerank.

`mode` selects the benchmark systems:
    dense   — System A: dense top-k only
    hybrid  — System B: dense top 20 + BM25 top 20 fused with RRF (k=60)
    rerank  — System C/D: hybrid candidates reranked by the cross-encoder

Eligible chunks (usable for current-law answers) and in-scope but ineligible
chunks are searched separately, so outdated duplicates cannot crowd current
evidence out of the top-k, yet the agent still sees what it may not rely on.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from app.retrieval.models import Encoder, Reranker
from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.sparse import SparseIndex
from app.schemas import ScoredChunk
from app.storage.corpus import CorpusCatalog
from app.storage.vector_store import VectorStore

Mode = Literal["dense", "hybrid", "rerank"]


@dataclass
class SearchResult:
    eligible: list[ScoredChunk]
    ineligible: list[ScoredChunk]
    timings_ms: dict[str, float] = field(default_factory=dict)


class RetrievalService:
    def __init__(self, catalog: CorpusCatalog, store: VectorStore, sparse: SparseIndex, encoder: Encoder,
                 reranker: Reranker | None, dense_k: int = 20, sparse_k: int = 20, rrf_k: int = 60) -> None:
        self.catalog = catalog
        self.store = store
        self.sparse = sparse
        self.encoder = encoder
        self.reranker = reranker
        self.dense_k, self.sparse_k, self.rrf_k = dense_k, sparse_k, rrf_k

    def embed(self, query: str) -> np.ndarray:
        return self.encoder.encode([query], batch_size=1, max_length=256)[0]

    def _candidates(self, query: str, vector: np.ndarray, allowed: list[str], mode: Mode,
                    top_k: int) -> tuple[list[ScoredChunk], float]:
        started = time.perf_counter()
        dense = self.store.search(vector, allowed, self.dense_k if mode != "dense" else top_k)
        dense_rank = {cid: r for r, (cid, _) in enumerate(dense, start=1)}
        if mode == "dense":
            out = [ScoredChunk(chunk=self.catalog.get(cid), eligible=self.catalog.is_eligible(self.catalog.get(cid)),
                               dense_rank=r, rrf_score=score) for r, (cid, score) in enumerate(dense, start=1)]
            return out, (time.perf_counter() - started) * 1000
        sparse = self.sparse.search(query, allowed, self.sparse_k)
        sparse_rank = {cid: r for r, (cid, _) in enumerate(sparse, start=1)}
        fused = reciprocal_rank_fusion([[c for c, _ in dense], [c for c, _ in sparse]], k=self.rrf_k)
        out = []
        for cid, score in fused:
            chunk = self.catalog.get(cid)
            out.append(ScoredChunk(chunk=chunk, eligible=self.catalog.is_eligible(chunk), dense_rank=dense_rank.get(cid),
                                   bm25_rank=sparse_rank.get(cid), rrf_score=round(score, 6)))
        return out, (time.perf_counter() - started) * 1000

    def _rerank(self, query: str, items: list[ScoredChunk]) -> list[ScoredChunk]:
        if not items or self.reranker is None:
            return items
        scores = self.reranker.score(query, [s.chunk.embedding_text for s in items])
        for item, score in zip(items, scores):
            item.reranker_score = round(float(score), 6)
        return sorted(items, key=lambda s: -(s.reranker_score or 0.0))

    def search(self, query: str, top_k: int = 5, mode: Mode = "rerank", document_ids: list[str] | None = None,
               include_ineligible: bool = True, ineligible_k: int = 3, subset: str = "eligible") -> SearchResult:
        timings: dict[str, float] = {}
        started = time.perf_counter()
        vector = self.embed(query)
        timings["embed_ms"] = (time.perf_counter() - started) * 1000

        eligible, t1 = self._candidates(query, vector, self.catalog.ids(subset, document_ids), mode, top_k)
        other: list[ScoredChunk] = []
        t2 = 0.0
        if include_ineligible and subset == "eligible":
            other, t2 = self._candidates(query, vector, self.catalog.ids("ineligible_in_scope", document_ids), mode,
                                         ineligible_k)
        timings["retrieval_ms"] = timings["embed_ms"] + t1 + t2

        if mode == "rerank":
            started = time.perf_counter()
            eligible = self._rerank(query, eligible)
            other = self._rerank(query, other[: max(ineligible_k * 3, 10)])
            timings["rerank_ms"] = (time.perf_counter() - started) * 1000
        return SearchResult(eligible=eligible[:top_k], ineligible=other[:ineligible_k], timings_ms=timings)
