"""Typed records shared by the offline corpus pipeline."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SectionKind(str, Enum):
    PREAMBLE = "preamble"
    MAIN_TEXT = "main_text"
    ANNEX = "annex"
    CLOSING = "closing"
    SIGNATURE = "signature"


INDEXABLE_KINDS = {SectionKind.PREAMBLE, SectionKind.MAIN_TEXT, SectionKind.ANNEX}


class CorpusUse(str, Enum):
    CURRENT = "current"
    HISTORICAL = "historical"
    OUT_OF_SCOPE = "out_of_scope"


class CurrencyStatus(str, Enum):
    VERIFIED_CURRENT = "verified_current"  # confirmed by a named human reviewer
    CONSOLIDATED_CURRENT = "consolidated_current"  # official consolidated text, no later change known
    PRESUMED_CURRENT = "presumed_current"  # document listed in force, no provision-level change known
    PENDING_AMENDMENT = "pending_amendment"  # consolidated wording not yet in force at as_of_date
    SUPERSEDED_BY_CONSOLIDATION = "superseded_by_consolidation"
    SUPERSEDED_BY_AMENDMENT = "superseded_by_amendment"  # a ledger entry expires, amends or displaces it
    HISTORICAL = "historical"
    UNVERIFIED = "unverified"


class TextQualityStatus(str, Enum):
    VERIFIED = "verified"  # compared against the source image by a named human reviewer
    MACHINE_CHECKED = "machine_checked"  # passed every automated gate in quality.py
    UNREVIEWED = "unreviewed"
    REJECTED = "rejected"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourcePart(Strict):
    label: str
    download_url: str
    path: str  # relative to the repository root
    sha256: str
    pages: int


class StatusLead(Strict):
    status: str
    source_url: str
    checked_on: date
    note: str


class RegistryDocument(Strict):
    document_id: str
    document_number: str
    title: str
    short_title: str
    document_type: str
    issuer: str
    issued_date: date
    effective_date: date | None
    source_url: str
    publisher: str
    license: str
    source_parts: list[SourcePart]
    scope: str
    corpus_use: CorpusUse
    corpus_use_reason: str
    consolidates: list[str] = Field(default_factory=list)
    legal_status_lead: StatusLead | None = None
    expected_main_articles: int
    downloaded_at: str


class Registry(Strict):
    registry_version: str
    as_of_date: date
    documents: list[RegistryDocument]


class Footnote(Strict):
    document_id: str
    number: str
    page: int
    text: str
    marker_offset: int | None = None  # offset of the marker in the document text
    section_id: str | None = None
    target_label: str | None = None  # e.g. "Điều 61 khoản 3"
    change_type: str | None = None  # amended | added | repealed | note
    amending_instrument: str | None = None
    effective_from: date | None = None


class Section(Strict):
    section_id: str
    document_id: str
    kind: SectionKind
    label: str
    title: str | None
    article_number: int | None
    path: list[str]
    start: int
    end: int
    page_start: int
    page_end: int
    paragraph_spans: list[tuple[int, int]]
    contains_quoted_amendment: bool = False
    contains_table: bool = False
    footnote_numbers: list[str] = Field(default_factory=list)


class Chunk(Strict):
    chunk_id: str
    corpus_snapshot_id: str
    document_id: str
    document_number: str
    document_title: str
    short_title: str
    document_type: str
    issuer: str
    section_id: str
    section_kind: SectionKind
    section_label: str
    section_title: str | None
    section_path: list[str]
    article_number: int | None
    ordinal: int  # position of this chunk inside its section, 0-based
    part_count: int
    page_start: int
    page_end: int
    source_start_char: int
    source_end_char: int
    raw_text: str
    text: str
    context_header: str
    embedding_text: str
    token_count: int
    embedding_token_count: int
    source_url: str
    source_sha256: list[str]
    content_sha256: str
    source_text_method: str = "native_pdf_text_layer"
    contains_quoted_amendment: bool
    contains_table: bool
    amendment_notes: list[Footnote] = Field(default_factory=list)
    currency_status: CurrencyStatus
    currency_basis: str
    currency_entries: list[str] = Field(default_factory=list)  # currency_ledger.json entry ids
    text_quality_status: TextQualityStatus
