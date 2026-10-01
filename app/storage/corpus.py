"""Read-only catalog of one corpus snapshot.

The snapshot files are the source of truth for provenance; vector and BM25
indexes are rebuilt from them. Eligibility for answering questions about current
law is decided here, from the snapshot statuses and the configured policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.errors import SnapshotUnavailable, SourceNotFound
from app.schemas import EvidencePreview, SourceEvidence
from ingestion.models import Chunk, CurrencyStatus, SectionKind, TextQualityStatus

POLICIES = {
    "strict": ({CurrencyStatus.VERIFIED_CURRENT}, {TextQualityStatus.VERIFIED}),
    "pilot": ({CurrencyStatus.VERIFIED_CURRENT, CurrencyStatus.CONSOLIDATED_CURRENT, CurrencyStatus.PRESUMED_CURRENT},
              {TextQualityStatus.VERIFIED, TextQualityStatus.MACHINE_CHECKED}),
}
ANSWER_KINDS = {SectionKind.MAIN_TEXT, SectionKind.ANNEX}


@dataclass
class DocumentInfo:
    document_id: str
    document_number: str
    title: str
    short_title: str
    document_type: str
    issuer: str
    issued_date: str
    effective_date: str | None
    source_url: str
    publisher: str
    license: str
    scope: str
    corpus_use: str
    corpus_use_reason: str
    downloaded_at: str
    chunks: int
    main_articles: int
    legal_status_lead: dict | None
    section_scope: list[str] | None = None


class CorpusCatalog:
    def __init__(self, snapshot_dir: Path, policy: str = "pilot") -> None:
        if not (snapshot_dir / "chunks.jsonl").exists():
            raise SnapshotUnavailable()
        self.snapshot_dir = snapshot_dir
        self.manifest = json.loads((snapshot_dir / "snapshot.json").read_text(encoding="utf-8"))
        self.snapshot_id: str = self.manifest["snapshot_id"]
        self.as_of_date: str = self.manifest["as_of_date"]
        self.policy = policy
        self.allowed_currency, self.allowed_quality = POLICIES[policy]
        self.chunks: dict[str, Chunk] = {}
        with (snapshot_dir / "chunks.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                chunk = Chunk.model_validate_json(line)
                self.chunks[chunk.chunk_id] = chunk
        self.order = list(self.chunks)
        self.documents: dict[str, DocumentInfo] = {}
        with (snapshot_dir / "documents.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                self.documents[d["document_id"]] = DocumentInfo(
                    document_id=d["document_id"], document_number=d["document_number"], title=d["title"],
                    short_title=d["short_title"], document_type=d["document_type"], issuer=d["issuer"],
                    issued_date=d["issued_date"], effective_date=d["effective_date"], source_url=d["source_url"],
                    publisher=d["publisher"], license=d["license"], scope=d["scope"], corpus_use=d["corpus_use"],
                    corpus_use_reason=d["corpus_use_reason"], downloaded_at=d["downloaded_at"], chunks=d["chunks"],
                    main_articles=d["main_articles"], legal_status_lead=d.get("legal_status_lead"),
                    section_scope=d.get("section_scope"))

    # -- eligibility ---------------------------------------------------------------------------
    def is_eligible(self, chunk: Chunk) -> bool:
        return (chunk.currency_status in self.allowed_currency and chunk.text_quality_status in self.allowed_quality
                and chunk.section_kind in ANSWER_KINDS)

    def in_scope(self, chunk: Chunk) -> bool:
        return self.documents[chunk.document_id].scope == "in_scope" and chunk.section_kind in ANSWER_KINDS

    def ids(self, subset: str, document_ids: list[str] | None = None) -> list[str]:
        wanted = set(document_ids) if document_ids else None
        out = []
        for cid in self.order:
            c = self.chunks[cid]
            if wanted is not None and c.document_id not in wanted:
                continue
            if subset == "eligible" and not self.is_eligible(c):
                continue
            if subset == "in_scope" and not self.in_scope(c):
                continue
            if subset == "ineligible_in_scope" and (not self.in_scope(c) or self.is_eligible(c)):
                continue
            out.append(cid)
        return out

    # -- lookups -------------------------------------------------------------------------------
    def get(self, chunk_id: str) -> Chunk:
        try:
            return self.chunks[chunk_id]
        except KeyError:
            raise SourceNotFound() from None

    def preview(self, chunk: Chunk, score: float, limit: int = 420) -> EvidencePreview:
        text = chunk.text if len(chunk.text) <= limit else chunk.text[:limit].rsplit(" ", 1)[0] + " …"
        return EvidencePreview(
            chunk_id=chunk.chunk_id, document_id=chunk.document_id, document_number=chunk.document_number,
            short_title=chunk.short_title, section=chunk.section_label, section_path=chunk.section_path,
            page_start=chunk.page_start, page_end=chunk.page_end, text_preview=text,
            retrieval_score=round(float(score), 4), currency_status=chunk.currency_status.value,
            eligible=self.is_eligible(chunk), source_url=chunk.source_url)

    def source(self, chunk_id: str) -> SourceEvidence:
        c = self.get(chunk_id)
        doc = self.documents[c.document_id]
        return SourceEvidence(
            chunk_id=c.chunk_id, corpus_snapshot_id=c.corpus_snapshot_id, document_id=c.document_id,
            document_number=c.document_number, title=c.document_title, short_title=c.short_title,
            document_type=c.document_type, section=c.section_label, section_path=c.section_path,
            page_start=c.page_start, page_end=c.page_end, text=c.text, source_url=c.source_url,
            downloaded_at=doc.downloaded_at, publisher=doc.publisher, currency_status=c.currency_status.value,
            currency_basis=c.currency_basis, text_quality_status=c.text_quality_status.value,
            amendment_notes=c.amendment_notes, eligible=self.is_eligible(c))

    def stats(self) -> dict:
        return {"snapshot_id": self.snapshot_id, "as_of_date": self.as_of_date, "policy": self.policy,
                "chunks": len(self.chunks), "eligible_chunks": len(self.ids("eligible")),
                "documents": len(self.documents)}
