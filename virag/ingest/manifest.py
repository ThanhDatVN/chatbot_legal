"""Read the crawler's evidence manifests into ingestible source documents.

The acquisition tooling in ``tools/`` writes one ``manifest.jsonl`` per shard
next to the bytes it downloaded.  Each ``source_page`` record carries the portal
metadata (instrument number, dates, issuing authority) and each
``official_attachment`` record carries the signed PDF that is the authoritative
text.  This module joins the two by ``document_id`` and yields one
:class:`SourceDocument` per legal instrument.

Nothing here fetches anything: ingestion reads only what the crawler already
verified and stored, so it is reproducible offline.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from virag.ingest.taxonomy import classify_domains, classify_taxpayers
from virag.legal import authority as authority_mod
from virag.legal.temporal import classify_portal_date
from virag.schemas import DocumentMeta

logger = logging.getLogger(__name__)


@dataclass
class SourceDocument:
    """One legal instrument with every local artefact the crawler kept."""

    meta: DocumentMeta
    #: Signed PDFs / DOCX - the authoritative text, preferred for ingestion.
    attachment_paths: list[Path] = field(default_factory=list)
    #: Portal HTML-to-text side-car, used only when no attachment parsed.
    text_path: Path | None = None
    shard: str | None = None

    def best_paths(self) -> list[Path]:
        if self.attachment_paths:
            return self.attachment_paths
        return [self.text_path] if self.text_path else []


def _iter_manifest_records(manifest: Path) -> Iterator[dict]:
    with manifest.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("%s:%d is not valid JSON: %s", manifest, line_number, exc)


def _meta_from_record(record: dict) -> DocumentMeta:
    portal = record.get("metadata") or {}
    document_type = portal.get("document_type")
    instrument_number = portal.get("instrument_number") or record.get("instrument_number")
    title = record.get("title") or portal.get("summary")

    haystack = " ".join(
        str(value) for value in (title, portal.get("summary"), instrument_number, document_type) if value
    )

    # Portal date fields carry non-date labels on a large minority of records
    # (D-13), so classify rather than trust.
    promulgation, _ = classify_portal_date(portal.get("promulgation_date"))
    effective_from, from_quality = classify_portal_date(portal.get("effective_date"))
    effective_to, to_quality = classify_portal_date(portal.get("expiration_date"))

    return DocumentMeta(
        document_id=record.get("document_id", ""),
        instrument_number=instrument_number,
        document_type=document_type,
        title=title,
        issuing_authority=portal.get("issuing_authority"),
        signer=portal.get("signer"),
        promulgation_date=promulgation,
        effective_from=effective_from,
        effective_to=effective_to,
        source=record.get("source"),
        source_url=record.get("final_url") or record.get("requested_url"),
        source_role=record.get("source_role"),
        sha256=record.get("response_sha256"),
        attribution=record.get("attribution"),
        effective_date_quality=from_quality,
        expiration_date_quality=to_quality,
        authority_tier=authority_mod.resolve_tier(document_type, instrument_number, title),
        tax_domains=classify_domains(haystack),
        taxpayer_types=classify_taxpayers(haystack),
    )


def load_manifest(manifest: Path) -> list[SourceDocument]:
    """Join page and attachment records of one shard manifest."""
    root = manifest.parent
    documents: dict[str, SourceDocument] = {}

    for record in _iter_manifest_records(manifest):
        document_id = record.get("document_id")
        if not document_id or record.get("fetch_status") != "fetched":
            continue

        record_type = record.get("record_type")
        if record_type == "source_page":
            source = documents.get(document_id)
            meta = _meta_from_record(record)
            if source is None:
                documents[document_id] = source = SourceDocument(meta=meta, shard=root.name)
            else:
                # Attachments arrived first; keep their paths, take the metadata.
                source.meta = meta
            for stored in record.get("stored_paths") or []:
                path = root / stored
                if path.suffix.lower() == ".txt" and path.exists():
                    source.text_path = path

        elif record_type == "official_attachment":
            source = documents.get(document_id)
            if source is None:
                documents[document_id] = source = SourceDocument(
                    meta=DocumentMeta(
                        document_id=document_id,
                        instrument_number=record.get("instrument_number"),
                        source=record.get("source"),
                        source_role=record.get("source_role"),
                    ),
                    shard=root.name,
                )
            stored = record.get("stored_path")
            if stored:
                path = root / stored
                if path.exists():
                    source.attachment_paths.append(path)
                    # The authoritative artifact is the signed attachment, so its
                    # hash - not the portal page's - is what a citation must be
                    # traceable to (D-02).  The first attachment wins; later ones
                    # are annexes.
                    if source.meta.artifact_sha256 is None:
                        source.meta.artifact_sha256 = record.get("response_sha256")

    return list(documents.values())


def find_manifests(crawl_root: Path, pattern: str = "**/manifest.jsonl") -> list[Path]:
    if not crawl_root.exists():
        return []
    return sorted(crawl_root.glob(pattern))


def iter_source_documents(
    crawl_root: Path,
    *,
    include: str | None = None,
    limit: int | None = None,
) -> Iterator[SourceDocument]:
    """Yield every ingestible document under ``crawl_root``.

    Duplicate ``document_id`` values across shards are common - a resume run
    re-downloads what a crashed shard missed - so the first complete record
    wins and later ones only contribute missing attachments.
    """
    seen: dict[str, SourceDocument] = {}
    emitted = 0

    for manifest in find_manifests(crawl_root):
        if include and include not in str(manifest):
            continue
        for source in load_manifest(manifest):
            key = source.meta.document_id
            if key in seen:
                existing = seen[key]
                known = {p.name for p in existing.attachment_paths}
                existing.attachment_paths.extend(
                    p for p in source.attachment_paths if p.name not in known
                )
                if existing.text_path is None:
                    existing.text_path = source.text_path
                continue
            seen[key] = source

    for source in seen.values():
        if not source.best_paths():
            continue
        yield source
        emitted += 1
        if limit is not None and emitted >= limit:
            return
