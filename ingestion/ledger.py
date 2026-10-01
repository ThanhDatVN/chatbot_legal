"""Provision-level currency ledger: which later instrument changed which provision.

data/corpus/currency_ledger.json records, for each corpus document that has been
checked, the amending instruments that were read and every provision they
expire, amend, displace or extend. Each entry carries a verbatim quote from the
official Công báo PDF of the amending instrument; `verify_evidence` re-reads
those PDFs and fails the build when a quote is missing, so an entry can never
point at text that is not in the source.

Entries are AI-assisted extractions until `reviewed_by` names a person.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from enum import Enum
from pathlib import Path

from ingestion.models import Chunk, Section, Strict
from ingestion.structure import CLAUSE_RE, ParsedDocument, _quote_delta


class ChangeType(str, Enum):
    EXPIRED = "expired"  # hết hiệu lực / bãi bỏ
    AMENDED = "amended"  # wording replaced by the amending instrument
    DISPLACED = "displaced"  # temporarily applied as the instrument says (authority, procedure)
    PARTIALLY_AFFECTED = "partially_affected"  # part changed; the changed part cannot be isolated
    ADDED = "added"  # new clause added; the existing text is unchanged


SUPERSEDING = {ChangeType.EXPIRED, ChangeType.AMENDED, ChangeType.DISPLACED}

VERB = {
    ChangeType.EXPIRED: "hết hiệu lực theo",
    ChangeType.AMENDED: "đã được sửa đổi theo",
    ChangeType.DISPLACED: "đang được thực hiện theo",
    ChangeType.PARTIALLY_AFFECTED: "bị thay đổi một phần theo",
    ChangeType.ADDED: "được bổ sung nội dung theo",
}


def instrument_name(number: str) -> str:
    if number.endswith("/NĐ-CP"):
        return f"Nghị định {number}"
    if number.endswith("/NQ-CP"):
        return f"Nghị quyết {number}"
    return number


class AmendingSource(Strict):
    document_number: str
    title: str
    issued_date: date
    congbao_id: int
    source_url: str  # Công báo listing or the official CDN file
    download_url: str
    path: str  # relative to the repository root
    sha256: str
    pages: int
    effective_from: date
    effective_until: date | None = None  # first day the instrument no longer applies
    checked_on: date


class Coverage(Strict):
    document_id: str
    instruments_checked: list[str]
    checked_on: date
    method: str
    limitations: str


class LedgerEntry(Strict):
    entry_id: str
    target_document_id: str
    sections: list[str]  # section labels, e.g. "Điều 4", "Phụ lục III"
    clauses: list[str] = []  # top-level clause numbers; empty = the whole section
    change: ChangeType
    source: str  # document number of the amending instrument
    source_provision: str
    effective_from: date
    effective_until: date | None = None  # first day the change no longer applies
    replacement: str | None = None  # where the applicable wording now lives
    evidence_quote: str
    note: str = ""
    extracted_by: str
    reviewed_by: str | None = None
    reviewed_at: date | None = None

    def applies_on(self, day: date) -> bool:
        return self.effective_from <= day and (self.effective_until is None or day < self.effective_until)

    def target_label(self, section: str | None = None) -> str:
        sections = section if section in self.sections else ", ".join(self.sections)
        if not self.clauses:
            return sections
        return f"khoản {', '.join(self.clauses)} {sections}"

    def describe(self, section: str | None = None) -> str:
        """One sentence for currency_basis; `section` narrows a multi-article entry to the chunk's article."""
        text = f"{self.target_label(section)} {VERB[self.change]} {self.source_provision} {instrument_name(self.source)}"
        text = text[0].upper() + text[1:]
        text += f" (từ {self.effective_from:%d/%m/%Y}"
        if self.effective_until:
            text += f", áp dụng đến trước {self.effective_until:%d/%m/%Y}"
        text += ")"
        if self.replacement:
            text += f"; nội dung áp dụng: {self.replacement}"
        return text


class CurrencyLedger(Strict):
    ledger_version: str
    sources: list[AmendingSource]
    coverage: list[Coverage]
    entries: list[LedgerEntry]

    def coverage_for(self, document_id: str) -> Coverage | None:
        return next((c for c in self.coverage if c.document_id == document_id), None)

    def entries_for(self, document_id: str) -> list[LedgerEntry]:
        return [e for e in self.entries if e.target_document_id == document_id]


def load_ledger(path: Path) -> CurrencyLedger | None:
    if not path.exists():
        return None
    return CurrencyLedger.model_validate_json(path.read_text(encoding="utf-8"))


def clause_spans(parsed: ParsedDocument, section: Section) -> dict[str, tuple[int, int]]:
    """Top-level clause (khoản) spans of an article, skipping numbered text inside quotes."""
    paras = [p for p in parsed.paragraphs if p.start >= section.start and p.end <= section.end]
    starts: list[tuple[str, int]] = []
    depth = 0
    for p in paras:
        m = CLAUSE_RE.match(p.text)
        if m and depth == 0 and not p.text.startswith("“") and not p.is_table:
            starts.append((m.group(1), p.start))
        depth = max(0, depth + _quote_delta(p.text))
    spans: dict[str, tuple[int, int]] = {}
    for i, (label, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else section.end
        spans.setdefault(label, (start, end))
    return spans


def _sections_by_label(parsed: ParsedDocument) -> dict[str, Section]:
    return {s.label: s for s in parsed.sections}


def resolve_targets(parsed: ParsedDocument, entries: list[LedgerEntry]) -> tuple[dict[str, list[tuple[int, int]]],
                                                                               list[str]]:
    """Map each entry to character spans in the parsed document; report targets that do not exist."""
    by_label = _sections_by_label(parsed)
    spans: dict[str, list[tuple[int, int]]] = {}
    problems: list[str] = []
    for entry in entries:
        for label in entry.sections:
            section = by_label.get(label)
            if section is None:
                problems.append(f"{entry.entry_id}: {entry.target_document_id} has no section {label!r}")
                continue
            if not entry.clauses:
                spans.setdefault(entry.entry_id, []).append((section.start, section.end))
                continue
            clauses = clause_spans(parsed, section)
            for clause in entry.clauses:
                if clause not in clauses:
                    problems.append(f"{entry.entry_id}: {label} has no top-level khoản {clause}")
                    continue
                spans.setdefault(entry.entry_id, []).append(clauses[clause])
    return spans, problems


def chunk_breaks(parsed: ParsedDocument, entries: list[LedgerEntry]) -> dict[str, set[int]]:
    """Offsets where the chunker must cut so that each clause-level target gets its own chunk."""
    by_label = _sections_by_label(parsed)
    breaks: dict[str, set[int]] = {}
    for entry in entries:
        if not entry.clauses:
            continue
        for label in entry.sections:
            section = by_label.get(label)
            if section is None:
                continue
            clauses = clause_spans(parsed, section)
            first = min((start for start, _ in clauses.values()), default=None)
            for clause in entry.clauses:
                if clause not in clauses:
                    continue
                start, end = clauses[clause]
                cuts = breaks.setdefault(section.section_id, set())
                if start != first:  # the heading stays with the first clause
                    cuts.add(start)
                if end < section.end:
                    cuts.add(end)
    return breaks


def entries_for_chunk(chunk: Chunk, entries: list[LedgerEntry],
                      spans: dict[str, list[tuple[int, int]]]) -> list[LedgerEntry]:
    hits = []
    for entry in entries:
        if entry.target_document_id != chunk.document_id:
            continue
        if any(start < chunk.source_end_char and chunk.source_start_char < end
               for start, end in spans.get(entry.entry_id, [])):
            hits.append(entry)
    return hits


GAZETTE_LINE_RE = re.compile(r"^(CÔNG BÁO/Số .*|\d{1,4}|(Ký bởi|Cơ quan|Ngày ký|Email|Thời gian ký)\s*:.*)$")


def normalized_pdf_text(path: Path) -> str:
    """Plain text of a Công báo PDF with gazette headers, page numbers and signature stamps removed."""
    import pymupdf

    lines: list[str] = []
    with pymupdf.open(path) as doc:
        for page in doc:
            for line in page.get_text().splitlines():
                line = line.strip()
                if line and not GAZETTE_LINE_RE.match(line):
                    lines.append(line)
    return normalize(" ".join(lines))


def normalize(text: str) -> str:
    return " ".join(text.split())


def verify_evidence(ledger: CurrencyLedger, root: Path) -> list[str]:
    """Every source file must match its hash and every evidence quote must occur in its source."""
    problems: list[str] = []
    texts: dict[str, str] = {}
    for source in ledger.sources:
        path = root / source.path
        if not path.exists():
            problems.append(f"{source.document_number}: missing {source.path} (run scripts/download_sources.py)")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != source.sha256:
            problems.append(f"{source.document_number}: {source.path} does not match the ledger sha256")
            continue
        texts[source.document_number] = normalized_pdf_text(path)
    known = {s.document_number for s in ledger.sources}
    for entry in ledger.entries:
        if entry.source not in known:
            problems.append(f"{entry.entry_id}: source {entry.source} is not listed in ledger sources")
            continue
        text = texts.get(entry.source)
        if text is not None and normalize(entry.evidence_quote) not in text:
            problems.append(f"{entry.entry_id}: evidence quote not found in {entry.source}")
    for cov in ledger.coverage:
        for number in cov.instruments_checked:
            if number not in known:
                problems.append(f"coverage {cov.document_id}: {number} is not listed in ledger sources")
    return problems
