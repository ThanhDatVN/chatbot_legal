"""The retrieval pipeline: sparse + dense -> fuse -> rerank -> legal score.

    query
      |-- BM25 (lexical: instrument numbers, "Dieu 9", exact rates)
      |-- dense (semantic: paraphrases, synonyms)
      v
    reciprocal-rank fusion
      v
    temporal filter (valid on the event date)
      v
    cross-encoder rerank
      v
    composite legal score = a*semantic + b*authority + c*temporal
                            + d*specificity + e*citation_quality
      v
    parent expansion (score the Khoan, read the Dieu)

Reciprocal-rank fusion is used rather than score addition because BM25 scores
and cosine similarities are on incomparable scales; RRF only needs the ranks,
so it needs no tuning per corpus.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from virag.index.bm25 import BM25Index
from virag.index.chunk_store import ChunkStore
from virag.index.embedder import Embedder, get_embedder
from virag.index.vector_store import SearchFilters, VectorStore, build_vector_store, to_days
from virag.ingest.chunking import window_parent
from virag.ingest.taxonomy import classify_domains, specificity_score
from virag.legal import authority as authority_mod
from virag.legal import temporal as temporal_mod
from virag.retrieval.rerank import Reranker, get_reranker
from virag.schemas import Chunk, RetrievedChunk, ScoreBreakdown
from virag.settings import RetrievalConfig, Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievalTrace:
    """Per-stage timings and counts, surfaced in the API response."""

    sparse_ms: float = 0.0
    dense_ms: float = 0.0
    rerank_ms: float = 0.0
    n_sparse: int = 0
    n_dense: int = 0
    n_fused: int = 0
    n_after_temporal: int = 0
    n_final: int = 0


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
    weights: list[float] | None = None,
) -> dict[str, float]:
    """RRF: score(d) = sum_i w_i / (k + rank_i(d))."""
    weights = weights or [1.0] * len(ranked_lists)
    fused: dict[str, float] = {}
    for ranked, weight in zip(ranked_lists, weights, strict=True):
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + weight / (k + rank)
    return fused


class Retriever:
    """Owns the index handles and executes one configuration of the pipeline."""

    def __init__(
        self,
        chunk_store: ChunkStore,
        bm25: BM25Index,
        vector_store: VectorStore,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.chunk_store = chunk_store
        self.bm25 = bm25
        self.vector_store = vector_store
        self._embedder = embedder
        self._reranker = reranker

    # -- lazy model handles ----------------------------------------------
    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = get_embedder(self.settings)
        return self._embedder

    @property
    def reranker(self) -> Reranker:
        if self._reranker is None:
            self._reranker = get_reranker(self.settings)
        return self._reranker

    # -- construction -----------------------------------------------------
    @classmethod
    def from_disk(cls, settings: Settings | None = None) -> Retriever:
        settings = settings or get_settings()
        root: Path = settings.index_root

        chunk_store = ChunkStore(root).load()
        bm25_path = root / "bm25.json"
        bm25 = BM25Index.load(bm25_path) if bm25_path.exists() else BM25Index.build([])
        vector_store = build_vector_store(settings.qdrant_url, settings.qdrant_collection, root)
        return cls(chunk_store, bm25, vector_store, settings=settings)

    # -- retrieval --------------------------------------------------------
    def retrieve(
        self,
        query: str,
        *,
        config: RetrievalConfig | None = None,
        as_of: str | None = None,
        tax_domains: list[str] | None = None,
        trace: RetrievalTrace | None = None,
    ) -> list[RetrievedChunk]:
        config = config or self.settings.retrieval
        as_of = as_of or temporal_mod.today_iso()
        trace = trace if trace is not None else RetrievalTrace()
        query_domains = tax_domains if tax_domains is not None else classify_domains(query)

        sparse_hits: list[tuple[str, float]] = []
        dense_hits: list[tuple[str, float]] = []

        if config.mode in {"bm25", "hybrid"}:
            started = time.perf_counter()
            sparse_hits = self.bm25.search(query, top_k=config.top_k_sparse)
            trace.sparse_ms = (time.perf_counter() - started) * 1000
            trace.n_sparse = len(sparse_hits)

        if config.mode in {"dense", "hybrid"}:
            started = time.perf_counter()
            filters = (
                SearchFilters(as_of_days=to_days(as_of, 0)) if config.use_temporal_filter else None
            )
            vector = self.embedder.encode([query], is_query=True)[0]
            dense_hits = self.vector_store.search(vector, config.top_k_dense, filters)
            trace.dense_ms = (time.perf_counter() - started) * 1000
            trace.n_dense = len(dense_hits)

        candidates = self._fuse(sparse_hits, dense_hits, config)
        trace.n_fused = len(candidates)

        # BM25 has no payload filter of its own, so the temporal predicate is
        # re-applied to the fused list to catch sparse-only hits.
        if config.use_temporal_filter:
            candidates = [rc for rc in candidates if self._in_force(rc.chunk, as_of)]
            trace.n_after_temporal = len(candidates)
            if not candidates:
                # Never return nothing purely because dates are unknown - fall
                # back and let the temporal score demote the stale hits.
                candidates = self._fuse(sparse_hits, dense_hits, config)
                logger.info("temporal filter emptied the candidate set for as_of=%s", as_of)

        candidates = candidates[: config.top_k_fused]

        if config.use_reranker and candidates:
            started = time.perf_counter()
            scores = self.reranker.score(query, [rc.chunk.text for rc in candidates])
            for retrieved, score in zip(candidates, scores, strict=True):
                retrieved.rerank_score = score
            candidates = [rc for rc in candidates if (rc.rerank_score or 0) >= config.min_rerank_score]
            candidates.sort(key=lambda rc: rc.rerank_score or 0.0, reverse=True)
            trace.rerank_ms = (time.perf_counter() - started) * 1000

        if config.use_legal_ranking:
            candidates = self._apply_legal_score(candidates, as_of, query_domains, config)

        final = candidates[: config.top_k_final]

        if config.use_parent_expansion:
            for retrieved in final:
                parent = self.chunk_store.parent_of(retrieved.chunk)
                if parent is not None:
                    # Window around the retrieved child rather than slicing from
                    # the head: a head slice would delete the very clause that
                    # retrieval selected (D-03).
                    retrieved.context_text = window_parent(
                        parent.text,
                        retrieved.chunk.text,
                        self.settings.parent_max_tokens,
                    )

        trace.n_final = len(final)
        return final

    # -- helpers ----------------------------------------------------------
    def _fuse(
        self,
        sparse_hits: list[tuple[str, float]],
        dense_hits: list[tuple[str, float]],
        config: RetrievalConfig,
    ) -> list[RetrievedChunk]:
        if config.mode == "bm25":
            fused = {doc_id: score for doc_id, score in sparse_hits}
        elif config.mode == "dense":
            fused = {doc_id: score for doc_id, score in dense_hits}
        else:
            fused = reciprocal_rank_fusion(
                [sparse_hits, dense_hits],
                k=config.rrf_k,
                weights=[1.0 - config.dense_weight, config.dense_weight],
            )

        sparse_scores = dict(sparse_hits)
        dense_scores = dict(dense_hits)
        sparse_ranks = {doc_id: i for i, (doc_id, _) in enumerate(sparse_hits, start=1)}
        dense_ranks = {doc_id: i for i, (doc_id, _) in enumerate(dense_hits, start=1)}

        results: list[RetrievedChunk] = []
        for chunk_id, score in sorted(fused.items(), key=lambda item: item[1], reverse=True):
            chunk = self.chunk_store.get(chunk_id)
            if chunk is None:
                continue
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=float(score),
                    sparse_score=sparse_scores.get(chunk_id),
                    dense_score=dense_scores.get(chunk_id),
                    sparse_rank=sparse_ranks.get(chunk_id),
                    dense_rank=dense_ranks.get(chunk_id),
                )
            )
        return results

    @staticmethod
    def _in_force(chunk: Chunk, as_of: str) -> bool:
        return temporal_mod.in_force(chunk.effective_from, chunk.effective_to, as_of)

    def _apply_legal_score(
        self,
        candidates: list[RetrievedChunk],
        as_of: str,
        query_domains: list[str],
        config: RetrievalConfig,
    ) -> list[RetrievedChunk]:
        if not candidates:
            return candidates

        weights = config.weights.normalised()
        # Relevance arrives on different scales depending on the stage that
        # produced it, so it is min-max normalised within the candidate set
        # before being blended with the legal components.
        raw = [
            rc.rerank_score if rc.rerank_score is not None else rc.score for rc in candidates
        ]
        low, high = min(raw), max(raw)
        span = (high - low) or 1.0

        for retrieved, value in zip(candidates, raw, strict=True):
            chunk = retrieved.chunk
            semantic = (value - low) / span
            authority_component = authority_mod.authority_score(chunk.authority_tier)
            temporal_component = temporal_mod.validity_score(
                chunk.effective_from, chunk.effective_to, as_of
            )
            specificity = specificity_score(chunk.tax_domains, query_domains)
            # A chunk that can be cited down to the clause is more useful as
            # evidence than one that can only be cited to the article.
            citation_quality = 1.0 if chunk.khoan else (0.6 if chunk.dieu else 0.2)

            total = (
                weights.semantic * semantic
                + weights.authority * authority_component
                + weights.temporal * temporal_component
                + weights.specificity * specificity
                + weights.citation_quality * citation_quality
            )
            retrieved.breakdown = ScoreBreakdown(
                semantic=round(semantic, 4),
                authority=round(authority_component, 4),
                temporal=round(temporal_component, 4),
                specificity=round(specificity, 4),
                citation_quality=round(citation_quality, 4),
                total=round(total, 4),
            )
            retrieved.score = total

        candidates.sort(key=lambda rc: rc.score, reverse=True)
        return candidates

    # -- diagnostics ------------------------------------------------------
    def stats(self) -> dict:
        return {
            "chunks": len(self.chunk_store),
            "parents": len(self.chunk_store.parents),
            "bm25_documents": len(self.bm25),
            "vectors": self.vector_store.count(),
            "embedder": getattr(self._embedder, "name", "lazy"),
            "reranker": getattr(self._reranker, "name", "lazy"),
        }
