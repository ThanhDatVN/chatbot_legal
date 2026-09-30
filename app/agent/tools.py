"""The agent's only two business tools: search_evidence and get_source.

Inputs are validated with Pydantic, call counts are capped per request, and every
call is traced. get_source only accepts chunk IDs that search_evidence returned
in the same request, so the model cannot open arbitrary sources or URLs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.errors import SourceNotFound
from app.retrieval.service import Mode, RetrievalService
from app.schemas import EvidencePreview, GetSourceInput, ScoredChunk, SearchEvidenceInput, SourceEvidence
from app.storage.corpus import CorpusCatalog

TOOL_DEFINITIONS = [
    {
        "name": "search_evidence",
        "description": (
            "Search the official Vietnamese labour-law corpus (hybrid dense + BM25 retrieval with reranking). "
            "Returns short previews with chunk_id, document, article (section), pages, a relevance score and "
            "`eligible`: only eligible=true evidence may support statements about the law currently in force. "
            "Use Vietnamese queries. Call get_source before relying on any preview."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query in Vietnamese, 1-1000 characters."},
                "top_k": {"type": "integer", "description": "Number of eligible results, 1-8.",
                          "enum": [1, 2, 3, 4, 5, 6, 7, 8]},
                "document_ids": {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}],
                                 "description": "Optional filter: document_id values seen in earlier results, "
                                                "or null for the whole corpus."},
            },
            "required": ["query", "top_k", "document_ids"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_source",
        "description": (
            "Fetch the full original text and provenance of one chunk returned by search_evidence in this "
            "conversation. Only fetched sources can be cited."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"chunk_id": {"type": "string", "description": "A chunk_id from search_evidence."}},
            "required": ["chunk_id"],
            "additionalProperties": False,
        },
    },
]


class ToolLimitExceeded(Exception):
    pass


@dataclass
class ToolBox:
    catalog: CorpusCatalog
    retrieval: RetrievalService
    mode: Mode = "rerank"
    max_search_calls: int = 3
    max_source_calls: int = 8
    search_calls: int = 0
    source_calls: int = 0
    retrieved: dict[str, ScoredChunk] = field(default_factory=dict)
    fetched: dict[str, SourceEvidence] = field(default_factory=dict)
    trace: list[dict] = field(default_factory=list)
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    last_result: object | None = None  # SearchResult of the latest search_evidence call

    def search_evidence(self, raw: dict) -> list[EvidencePreview]:
        args = SearchEvidenceInput.model_validate(raw)
        if self.search_calls >= self.max_search_calls:
            raise ToolLimitExceeded(f"search_evidence limit of {self.max_search_calls} calls reached")
        self.search_calls += 1
        known = set(self.catalog.documents)
        doc_filter = [d for d in (args.document_ids or []) if d in known] or None
        result = self.retrieval.search(args.query, top_k=args.top_k, mode=self.mode, document_ids=doc_filter)
        self.last_result = result
        self.retrieval_ms += result.timings_ms.get("retrieval_ms", 0.0)
        self.rerank_ms += result.timings_ms.get("rerank_ms", 0.0)
        previews = []
        for item in result.eligible + result.ineligible:
            previous = self.retrieved.get(item.chunk.chunk_id)
            if previous is None or item.score > previous.score:
                self.retrieved[item.chunk.chunk_id] = item
            previews.append(self.catalog.preview(item.chunk, item.score))
        self.trace.append({"tool": "search_evidence", "query": args.query, "top_k": args.top_k,
                           "document_ids": doc_filter, "timings_ms": {k: round(v, 1) for k, v in result.timings_ms.items()},
                           "results": [{"chunk_id": s.chunk.chunk_id, "section": s.chunk.section_label,
                                        "document_id": s.chunk.document_id, "eligible": s.eligible,
                                        "dense_rank": s.dense_rank, "bm25_rank": s.bm25_rank,
                                        "rrf_score": s.rrf_score, "reranker_score": s.reranker_score}
                                       for s in result.eligible + result.ineligible]})
        return previews

    def get_source(self, raw: dict) -> SourceEvidence:
        args = GetSourceInput.model_validate(raw)
        if args.chunk_id not in self.retrieved:
            raise SourceNotFound()  # only evidence retrieved in this request may be opened
        if args.chunk_id in self.fetched:
            return self.fetched[args.chunk_id]
        if self.source_calls >= self.max_source_calls:
            raise ToolLimitExceeded(f"get_source limit of {self.max_source_calls} calls reached")
        self.source_calls += 1
        started = time.perf_counter()
        source = self.catalog.source(args.chunk_id)
        self.fetched[args.chunk_id] = source
        self.trace.append({"tool": "get_source", "chunk_id": args.chunk_id, "section": source.section,
                           "eligible": source.eligible, "ms": round((time.perf_counter() - started) * 1000, 2)})
        return source

    def call(self, name: str, raw: dict) -> tuple[str, bool]:
        """Run a tool for the LLM loop; returns (JSON text, is_error)."""
        import json

        try:
            if name == "search_evidence":
                return json.dumps([p.model_dump() for p in self.search_evidence(raw)], ensure_ascii=False), False
            if name == "get_source":
                return self.get_source(raw).model_dump_json(), False
            return json.dumps({"error": f"unknown tool {name!r}; only search_evidence and get_source exist"}), True
        except ValidationError as exc:
            return json.dumps({"error": "invalid_input", "detail": exc.errors(include_url=False)},
                              ensure_ascii=False, default=str), True
        except SourceNotFound:
            return json.dumps({"error": "source_not_found",
                               "detail": "chunk_id was not returned by search_evidence in this request"}), True
        except ToolLimitExceeded as exc:
            return json.dumps({"error": "tool_limit", "detail": str(exc)}), True

    def score_of(self, chunk_id: str) -> float:
        item = self.retrieved.get(chunk_id)
        return item.score if item else 0.0
