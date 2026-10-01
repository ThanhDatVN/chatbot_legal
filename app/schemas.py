"""Pydantic contracts shared by the API, the agent tools and the UI."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ingestion.models import Chunk, Footnote


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(str, Enum):
    ANSWER = "ANSWER"
    PARTIAL = "PARTIAL"
    REFUSE = "REFUSE"


class RefusalReason(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    OUT_OF_SCOPE = "out_of_scope"
    CONFLICTING_SOURCES = "conflicting_sources"
    UNSUPPORTED_PREDICTION = "unsupported_prediction"
    SOURCE_UNAVAILABLE = "source_unavailable"
    CURRENCY_UNVERIFIED = "currency_unverified"
    HISTORICAL_NOT_SUPPORTED = "historical_not_supported"
    SUPERSEDED_BY_AMENDMENT = "superseded_by_amendment"


class ScoredChunk(BaseModel):
    chunk: Chunk
    eligible: bool  # may support an answer about current law under the active policy
    dense_rank: int | None = None
    bm25_rank: int | None = None
    rrf_score: float | None = None
    reranker_score: float | None = None

    @property
    def score(self) -> float:
        if self.reranker_score is not None:
            return self.reranker_score
        return self.rrf_score or 0.0


class SearchEvidenceInput(Strict):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=8)
    document_ids: list[str] | None = Field(None, max_length=20)

    @field_validator("query")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be blank")
        return v


class GetSourceInput(Strict):
    chunk_id: str = Field(pattern=r"^[0-9a-f]{24}$")


class EvidencePreview(Strict):
    chunk_id: str
    document_id: str
    document_number: str
    short_title: str
    section: str
    section_path: list[str]
    page_start: int
    page_end: int
    text_preview: str
    retrieval_score: float
    currency_status: str
    eligible: bool
    source_url: str


class SourceEvidence(Strict):
    chunk_id: str
    corpus_snapshot_id: str
    document_id: str
    document_number: str
    title: str
    short_title: str
    document_type: str
    section: str
    section_path: list[str]
    page_start: int
    page_end: int
    text: str
    source_url: str
    downloaded_at: str
    publisher: str
    currency_status: str
    currency_basis: str
    text_quality_status: str
    amendment_notes: list[Footnote] = Field(default_factory=list)
    eligible: bool


class Citation(Strict):
    citation_id: int
    chunk_id: str
    document_id: str
    document_number: str
    title: str
    section: str
    page_start: int
    page_end: int
    source_url: str
    quote: str
    currency_status: str


class Claim(Strict):
    claim_id: str
    text: str
    citation_ids: list[int]


class StageMetrics(Strict):
    total_ms: float = 0
    retrieval_ms: float = 0
    rerank_ms: float = 0
    generation_ms: float = 0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_cost_usd: float = 0
    search_calls: int = 0
    source_calls: int = 0


class AnswerResult(Strict):
    query_id: str
    session_id: str | None = None
    corpus_snapshot_id: str
    decision: Decision
    reason: RefusalReason | None = None
    answer: str
    claims: list[Claim] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    notices: list[str] = Field(default_factory=list)
    related_sources: list[EvidencePreview] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    mode: str
    metrics: StageMetrics = Field(default_factory=StageMetrics)
    trace: list[dict] = Field(default_factory=list)


class ChatRequest(Strict):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(None, max_length=64)
    debug: bool = False


class SearchRequest(Strict):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(8, ge=1, le=20)
    document_ids: list[str] | None = Field(None, max_length=20)
    include_non_current: bool = True


class FeedbackRequest(Strict):
    query_id: str = Field(min_length=4, max_length=64)
    rating: int = Field(ge=-1, le=1)
    reason: str | None = Field(None, pattern=r"^(wrong_content|citation_wrong|missing_source|unclear|other)$")
    comment: str | None = Field(None, max_length=1000)


class ErrorBody(Strict):
    error: str
    message: str
    query_id: str | None = None
