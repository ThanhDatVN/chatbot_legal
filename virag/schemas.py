"""Data contracts shared by ingest, retrieval, generation and evaluation.

The contracts encode the two facts that separate a legal assistant from a
generic RAG bot:

*   A rule is only correct **relative to a date**.  Every chunk therefore
    carries a validity interval and a version id, and every answer carries the
    ``as_of`` date it was computed for.
*   A rule is only correct **relative to the hierarchy**.  Every chunk carries
    an authority tier so a Cong van can never silently outrank the Luat it
    interprets.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Legal vocabulary
# ---------------------------------------------------------------------------

#: Status is tracked per clause, not per document: a Thong tu whose Khoan 2
#: Dieu 3 was amended is PARTIALLY_AMENDED as a document while its Dieu 1 is
#: still plain ACTIVE.
LegalStatus = Literal[
    "ACTIVE",
    "PARTIALLY_AMENDED",
    "PARTIALLY_REPEALED",
    "REPLACED",
    "EXPIRED",
    "SUSPENDED",
    "NOT_YET_EFFECTIVE",
    "SUPERSEDED",
    "UNKNOWN",
]

#: Lower number = higher legal force.  Used by the authority component of the
#: composite ranking score and by conflict resolution.
AuthorityTier = int

RelationType = Literal[
    "AMENDS",
    "REPLACES",
    "REPEALS",
    "DETAILS",
    "GUIDES",
    "REFERS_TO",
    "OVERRIDES",
    "CONFLICTS_WITH",
    "INTERPRETS",
    "CONSOLIDATES",
]

TaxDomain = Literal[
    "gtgt",
    "tndn",
    "tncn",
    "ttdb",
    "xnk",
    "tnmt",
    "sdd",
    "hoa_don",
    "quan_ly_thue",
    "khac",
]


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


@dataclass
class PageText:
    page_number: int
    text: str
    #: "text" when the PDF text layer was usable, "ocr" when Tesseract produced it.
    extraction_method: Literal["text", "ocr", "docx", "html"] = "text"
    char_count: int = 0

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


@dataclass
class DocumentMeta:
    """Bitemporal metadata for one legal instrument.

    ``effective_from`` / ``effective_to`` carry the *validity* interval used to
    answer "which rule applied on the date of the taxable event".
    """

    document_id: str
    instrument_number: str | None = None
    document_type: str | None = None
    title: str | None = None
    issuing_authority: str | None = None
    signer: str | None = None
    promulgation_date: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    source: str | None = None
    source_url: str | None = None
    source_role: str | None = None
    sha256: str | None = None
    #: SHA-256 of the authoritative attachment (signed PDF), distinct from the
    #: portal page hash above.  See D-02.
    artifact_sha256: str | None = None
    attribution: str | None = None
    #: "valid" | "malformed" | "absent" - never infer this from truthiness (D-13).
    effective_date_quality: str = "absent"
    expiration_date_quality: str = "absent"

    # --- version-awareness -----------------------------------------------
    legal_status: LegalStatus = "UNKNOWN"
    authority_tier: AuthorityTier = 9
    #: Identifies one *version* of an instrument, e.g. "LUAT-48-2024#v2".
    version_id: str | None = None
    tax_domains: list[str] = field(default_factory=list)
    taxpayer_types: list[str] = field(default_factory=list)

    # --- dependency graph edges ------------------------------------------
    supersedes: list[str] = field(default_factory=list)
    amends: list[str] = field(default_factory=list)
    repeals: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedDocument:
    meta: DocumentMeta
    pages: list[PageText] = field(default_factory=list)
    ocr_page_count: int = 0
    source_path: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


# ---------------------------------------------------------------------------
# Legal structure
# ---------------------------------------------------------------------------

NodeKind = Literal["phan", "chuong", "muc", "dieu", "khoan", "diem", "preamble", "block"]


@dataclass
class LegalNode:
    """A node of the Phan / Chuong / Muc / Dieu / Khoan / Diem tree."""

    kind: NodeKind
    number: str | None
    heading: str | None
    text: str
    page_number: int | None = None
    children: list[LegalNode] = field(default_factory=list)

    def label(self) -> str:
        prefixes = {
            "phan": "Phần",
            "chuong": "Chương",
            "muc": "Mục",
            "dieu": "Điều",
            "khoan": "Khoản",
            "diem": "Điểm",
        }
        prefix = prefixes.get(self.kind)
        if prefix and self.number:
            return f"{prefix} {self.number}"
        return prefix or self.kind


@dataclass
class LegalRelation:
    """One edge of the legal dependency graph."""

    source_document_id: str
    relation: RelationType
    target_instrument: str
    target_document_id: str | None = None
    target_dieu: str | None = None
    target_khoan: str | None = None
    #: Normalised subject name when the target is cited by name rather than by
    #: number - the majority case in Vietnamese instruments (D-14).
    target_subject: str | None = None
    #: "number" | "name" | None - how the target was resolved, for auditing.
    matched_by: str | None = None
    evidence: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Chunks
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    """A child chunk: the unit that is embedded and retrieved."""

    chunk_id: str
    document_id: str
    parent_id: str
    text: str
    #: Human readable pin-point citation, e.g. "Dieu 9 khoan 2 - Luat 48/2024/QH15".
    citation_label: str
    dieu: str | None = None
    khoan: str | None = None
    diem: str | None = None
    chuong: str | None = None
    muc: str | None = None
    page_number: int | None = None
    token_count: int = 0
    # Denormalised from DocumentMeta so Qdrant can filter without a join.
    legal_status: LegalStatus = "UNKNOWN"
    authority_tier: AuthorityTier = 9
    version_id: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    tax_domains: list[str] = field(default_factory=list)
    meta: DocumentMeta | None = None

    def payload(self) -> dict[str, Any]:
        base = {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "parent_id": self.parent_id,
            "text": self.text,
            "citation_label": self.citation_label,
            "dieu": self.dieu,
            "khoan": self.khoan,
            "diem": self.diem,
            "chuong": self.chuong,
            "muc": self.muc,
            "page_number": self.page_number,
            "token_count": self.token_count,
            "legal_status": self.legal_status,
            "authority_tier": self.authority_tier,
            "version_id": self.version_id,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "tax_domains": self.tax_domains,
        }
        if self.meta is not None:
            meta = self.meta.to_dict()
            for key in ("document_id", "legal_status", "authority_tier", "version_id"):
                meta.pop(key, None)
            base.update(meta)
        return base

    @property
    def article_key(self) -> str:
        """Identity of the article across versions - used to detect version mixing."""
        return f"{self.document_id}#{self.dieu or '?'}"


@dataclass
class ParentChunk:
    """A parent chunk (normally one Dieu) returned as generation context."""

    parent_id: str
    document_id: str
    text: str
    citation_label: str
    dieu: str | None = None
    chuong: str | None = None
    page_number: int | None = None
    child_ids: list[str] = field(default_factory=list)
    meta: DocumentMeta | None = None


@dataclass
class ScoreBreakdown:
    """Components of the composite legal relevance score, kept for explainability."""

    semantic: float = 0.0
    authority: float = 0.0
    temporal: float = 0.0
    specificity: float = 0.0
    citation_quality: float = 0.0
    total: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    sparse_score: float | None = None
    dense_score: float | None = None
    rerank_score: float | None = None
    sparse_rank: int | None = None
    dense_rank: int | None = None
    breakdown: ScoreBreakdown | None = None
    #: Text actually handed to the LLM - the parent when expansion is enabled.
    context_text: str | None = None

    @property
    def text_for_context(self) -> str:
        return self.context_text or self.chunk.text


# ---------------------------------------------------------------------------
# Temporal reasoning
# ---------------------------------------------------------------------------


@dataclass
class TemporalContext:
    """What the system believes about *when* the question is about."""

    as_of_date: str
    #: "explicit" - user gave a date; "inferred" - parsed from phrasing such as
    #: "nam ngoai"; "default" - fell back to today, which is a risk signal.
    source: Literal["explicit", "inferred", "default"] = "default"
    raw_expression: str | None = None
    #: True when the question is date-sensitive but no date could be established.
    needs_clarification: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------

ConflictKind = Literal[
    "temporal",
    "hierarchical",
    "amendment",
    "partial_amendment",
    "implicit_repeal",
    "general_vs_special",
    "formal_vs_guidance",
]


@dataclass
class ConflictFinding:
    kind: ConflictKind
    left_chunk_id: str
    right_chunk_id: str
    left_label: str
    right_label: str
    #: chunk_id of the provision that prevails, or None when undecidable.
    winner_chunk_id: str | None
    rule: str
    explanation: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


@dataclass
class Citation:
    marker: str
    chunk_id: str
    document_id: str
    citation_label: str
    source_url: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    legal_status: LegalStatus = "UNKNOWN"
    version_id: str | None = None
    quote: str | None = None
    #: Lexical support of the citing sentence in the cited chunk, in [0, 1].
    support: float = 0.0


@dataclass
class GuardrailReport:
    input_blocked: bool = False
    input_reasons: list[str] = field(default_factory=list)
    injection_score: float = 0.0
    injection_categories: list[str] = field(default_factory=list)
    output_modified: bool = False
    output_reasons: list[str] = field(default_factory=list)
    citation_coverage: float = 0.0
    grounding_score: float = 0.0
    version_mixing_detected: bool = False
    refused: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnswerResult:
    question: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    contexts: list[RetrievedChunk] = field(default_factory=list)
    conflicts: list[ConflictFinding] = field(default_factory=list)
    guardrails: GuardrailReport = field(default_factory=GuardrailReport)
    temporal: TemporalContext | None = None
    cache_hit: bool = False
    cache_kind: str | None = None
    latency_ms: float = 0.0
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    generation_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str | None = None
    config_name: str | None = None
    as_of_date: str | None = None
    refused: bool = False
    needs_clarification: bool = False
    #: Self-reported confidence in [0, 1]; shown in the UI next to the answer.
    confidence: float = 0.0

    def context_texts(self) -> list[str]:
        return [ctx.text_for_context for ctx in self.contexts]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": [asdict(c) for c in self.citations],
            "contexts": [
                {
                    "chunk_id": c.chunk.chunk_id,
                    "citation_label": c.chunk.citation_label,
                    "document_id": c.chunk.document_id,
                    "version_id": c.chunk.version_id,
                    "legal_status": c.chunk.legal_status,
                    "authority_tier": c.chunk.authority_tier,
                    "effective_from": c.chunk.effective_from,
                    "effective_to": c.chunk.effective_to,
                    "score": c.score,
                    "rerank_score": c.rerank_score,
                    "breakdown": c.breakdown.to_dict() if c.breakdown else None,
                    "text": c.text_for_context,
                }
                for c in self.contexts
            ],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "guardrails": self.guardrails.to_dict(),
            "temporal": self.temporal.to_dict() if self.temporal else None,
            "cache_hit": self.cache_hit,
            "cache_kind": self.cache_kind,
            "latency_ms": self.latency_ms,
            "retrieval_ms": self.retrieval_ms,
            "rerank_ms": self.rerank_ms,
            "generation_ms": self.generation_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model": self.model,
            "config_name": self.config_name,
            "as_of_date": self.as_of_date,
            "refused": self.refused,
            "needs_clarification": self.needs_clarification,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# Evaluation - VietTaxBench
# ---------------------------------------------------------------------------

#: The five task families of VietTaxBench.
EvalTask = Literal["taxqa", "taxrag", "taxtime", "taxchange", "taxconflict"]

EvalCategory = Literal[
    "factoid",
    "rate_lookup",
    "procedure",
    "deadline",
    "definition",
    "multi_hop",
    "temporal",
    "version_selection",
    "change_detection",
    "conflict_resolution",
    "authority_hierarchy",
    "unanswerable",
    "out_of_scope",
]


@dataclass
class EvalItem:
    question_id: str
    question: str
    ground_truth: str
    category: EvalCategory
    task: EvalTask = "taxqa"
    #: chunk ids / parent ids that must be retrieved for the answer to be possible.
    gold_chunk_ids: list[str] = field(default_factory=list)
    gold_document_ids: list[str] = field(default_factory=list)
    gold_citation_labels: list[str] = field(default_factory=list)
    #: Article-level gold, e.g. ["DOC-123#Dieu 9"] - used for Article Recall@K.
    gold_article_keys: list[str] = field(default_factory=list)
    #: The version that must be selected for TVA to score 1.
    gold_version_id: str | None = None
    as_of_date: str | None = None
    should_refuse: bool = False
    #: Correct behaviour is to ask for the taxable-event date first.
    expects_clarification: bool = False
    provenance: str = "generated"
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stable_id(*parts: str) -> str:
    digest = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]
