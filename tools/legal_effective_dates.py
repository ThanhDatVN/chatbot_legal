#!/usr/bin/env python3
"""Extract reviewable effective-date evidence from official Gazette PDFs.

The extractor deliberately keeps instrument-level effectiveness separate from
provision-level dates and policy application periods. It never treats a date in
portal metadata as if it had been found in the signed text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pypdf import PdfReader

SPACE_RE = re.compile(r"\s+")
FORMAL_NUMBER_RE = re.compile(
    r"(?:luật|nghị\s+quyết)\s+số\s*:?\s*(\d{1,4}/\d{4}/[a-zđ0-9-]+)"
    r"|\bsố\s*:\s*(\d{1,4}/(?:\d{4}/)?[a-zđ0-9-]+)",
    re.IGNORECASE,
)
ARTICLE_RE = re.compile(r"(?=\bĐi[eêề]u\s+\d+[a-z]?\s*[.:])", re.IGNORECASE)
EFFECTIVE_HEADING_RE = re.compile(
    r"\bĐi[eêề]u\s+\d+[a-z]?\s*[.:]\s*"
    r"(?:Hi[eêệ]u\s+l[uưự]c\s+thi\s+h[aà]nh|Đi[eêề]u\s+kho[aả]n\s+thi\s+h[aà]nh)",
    re.IGNORECASE,
)
NUMERIC_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)")
TEXT_DATE_RE = re.compile(
    r"ng[aà]y\s+(\d{1,2})\s+th[aá]ng\s+(\d{1,2})\s+n[aă]m\s+(\d{4})",
    re.IGNORECASE,
)
DATE_TOKEN = (
    r"(?:ng[aà]y\s+\d{1,2}\s+th[aá]ng\s+\d{1,2}\s+n[aă]m\s+\d{4}"
    r"|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})"
)
APPLICATION_RANGE_RE = re.compile(
    rf"từ\s+({DATE_TOKEN})\s+đ[eế]n\s+(?:h[eế]t\s+)?({DATE_TOKEN})",
    re.IGNORECASE,
)
GENERAL_EFFECTIVE_RE = re.compile(
    r"(?:Luật|Nghị\s+quyết|Nghị\s+định|Thông\s+tư)\s+này\s+có\s+hiệu\s+lực"
    r"(?:\s+thi\s+hành)?\s+(?:từ|kể\s+từ)\s+"
    rf"({DATE_TOKEN}|ngày\s+ký\s+ban\s+hành|ngày\s+được(?:\s+Quốc\s+hội)?\s+thông\s+qua)",
    re.IGNORECASE,
)
PROVISION_EFFECTIVE_RE = re.compile(
    r"(?:quy\s+định\s+tại\s+)?"
    r"(?:Đi[eêề]u\s+\d+[a-z]?|các\s+đi[eêề]u\s+[\d,\s]+|khoản\s+\d+|điểm\s+[a-zđ])"
    r"(?:\s+[^.;]{0,180}?)?\s+có\s+hiệu\s+lực"
    r"(?:\s+thi\s+hành)?\s+(?:từ|kể\s+từ)\s+"
    rf"({DATE_TOKEN}|ngày\s+ký\s+ban\s+hành|ngày\s+được(?:\s+Quốc\s+hội)?\s+thông\s+qua)",
    re.IGNORECASE,
)
APPLICATION_CONTEXT_RE = re.compile(
    r"(?:áp\s+dụng|chính\s+sách|giảm\s+thuế|hiệu\s+lực|trong\s+thời\s+gian|thực\s+hiện)",
    re.IGNORECASE,
)


def normalize_space(value: str) -> str:
    normalized = SPACE_RE.sub(" ", unicodedata.normalize("NFC", value)).strip()
    # pypdf occasionally exposes a stray space inside a Vietnamese word.
    for pattern, replacement in (
        (r"\bhi\s+ệu\b", "hiệu"),
        (r"\bt\s+ừ\b", "từ"),
        (r"\bđ\s+ịnh\b", "định"),
        (r"\bc\s+ủa\b", "của"),
        (r"\bthi\s+hà\s+nh\b", "thi hành"),
        (r"\bkinh\s+doa\s+nh\b", "kinh doanh"),
        (r"\bn\s+ăm\b", "năm"),
    ):
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def normalize_identifier(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_date_token(value: str) -> str | None:
    match = NUMERIC_DATE_RE.search(value) or TEXT_DATE_RE.search(value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def formal_numbers(prefix: str) -> list[str]:
    return [normalize_identifier(a or b) for a, b in FORMAL_NUMBER_RE.findall(prefix)]


@dataclass(frozen=True)
class DocumentSpan:
    start_page: int
    end_page: int
    location_confidence: str
    candidate_pages: tuple[int, ...]


def _start_score(text: str, target: str) -> int:
    prefix = normalize_space(text[:2500])
    if target not in normalize_identifier(prefix):
        return -100
    score = 2
    if target in formal_numbers(prefix):
        score += 8
    folded = prefix.casefold()
    if "cộng hòa xã hội chủ nghĩa việt nam" in folded:
        score += 5
    if "độc lập - tự do - hạnh phúc" in folded:
        score += 3
    if "mục lục" in folded:
        score -= 10
    return score


def find_document_span(page_texts: list[str], instrument_number: str) -> DocumentSpan:
    """Locate one instrument inside a PDF that may be a complete Gazette issue."""

    target = normalize_identifier(instrument_number)
    candidates = [index for index, text in enumerate(page_texts) if target in normalize_identifier(text)]
    if not candidates:
        raise ValueError(f"Instrument number not found in PDF: {instrument_number}")
    ranked = sorted(((_start_score(page_texts[index], target), index) for index in candidates), reverse=True)
    best_score, start = ranked[0]
    if best_score < 2:
        raise ValueError(f"Could not identify instrument start page: {instrument_number}")

    end = len(page_texts) - 1
    for index in range(start + 1, len(page_texts)):
        prefix = normalize_space(page_texts[index][:1800])
        header_prefix = normalize_space(page_texts[index][:700])
        folded = prefix.casefold()
        if "văn phòng chính phủ xuất bản" in folded:
            end = index - 1
            break
        numbers = formal_numbers(prefix)
        is_formal_header = (
            "cộng hòa xã hội chủ nghĩa việt nam" in header_prefix.casefold()
        )
        if is_formal_header and any(number != target for number in numbers):
            end = index - 1
            break

    confidence = "high" if best_score >= 15 else "medium"
    return DocumentSpan(start + 1, end + 1, confidence, tuple(index + 1 for index in candidates))


def _clause_windows(text: str) -> list[str]:
    normalized = normalize_space(text)
    matches = list(EFFECTIVE_HEADING_RE.finditer(normalized))
    windows: list[str] = []
    for match in matches:
        following = normalized[match.start() : match.start() + 2400]
        boundary = ARTICLE_RE.search(following, match.end() - match.start() + 1)
        windows.append(following[: boundary.start() if boundary else 1800])
    return windows


def _sentence_around(text: str, start: int, end: int, radius: int = 420) -> str:
    left = max(text.rfind(".", max(0, start - radius), start), text.rfind(";", max(0, start - radius), start))
    right_candidates = [position for token in (".", ";") if (position := text.find(token, end)) >= 0]
    right = min(right_candidates) + 1 if right_candidates else min(len(text), end + radius)
    return normalize_space(text[left + 1 : right])


def extract_temporal_evidence(
    page_texts: list[str], span: DocumentSpan, promulgation_date: str | None
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for page_number in range(span.start_page, span.end_page + 1):
        text = normalize_space(page_texts[page_number - 1])
        candidates = _clause_windows(text)
        for match in APPLICATION_RANGE_RE.finditer(text):
            sentence = _sentence_around(text, match.start(), match.end())
            if APPLICATION_CONTEXT_RE.search(sentence):
                candidates.append(sentence)
        for candidate in candidates:
            matches: list[tuple[str, re.Match[str]]] = []
            matches.extend(("general_effective", item) for item in GENERAL_EFFECTIVE_RE.finditer(candidate))
            matches.extend(
                ("provision_effective", item)
                for item in PROVISION_EFFECTIVE_RE.finditer(candidate)
            )
            if APPLICATION_CONTEXT_RE.search(candidate):
                matches.extend(
                    ("application_period", item)
                    for item in APPLICATION_RANGE_RE.finditer(candidate)
                )
            if not matches and EFFECTIVE_HEADING_RE.search(candidate):
                matches.append(("temporal_clause_unparsed", EFFECTIVE_HEADING_RE.search(candidate)))  # type: ignore[arg-type]
            for kind, match in matches:
                excerpt = candidate[:1800]
                key = (kind, page_number, excerpt)
                if key in seen:
                    continue
                seen.add(key)
                item: dict[str, Any] = {
                    "kind": kind,
                    "pdf_page": page_number,
                    "clause_text": excerpt,
                    "content_match_status": "found_in_pdf_text",
                    "confidence": "high" if kind != "temporal_clause_unparsed" else "medium",
                    "review_status": "pending_human_review",
                }
                if kind == "application_period":
                    item["start_date"] = normalize_date_token(match.group(1))
                    item["end_date"] = normalize_date_token(match.group(2))
                elif kind in {"general_effective", "provision_effective"}:
                    token = match.group(1)
                    normalized = normalize_date_token(token)
                    if normalized:
                        item["effective_date"] = normalized
                        item["date_resolution"] = "explicit_content_date"
                    elif re.search(
                        r"ngày\s+(?:ký\s+ban\s+hành|được(?:\s+Quốc\s+hội)?\s+thông\s+qua)",
                        token,
                        re.I,
                    ):
                        item["effective_date"] = promulgation_date
                        item["date_resolution"] = "relative_content_clause_plus_promulgation_date"
                evidence.append(item)
    return evidence


def extract_document(
    pdf_path: Path,
    document_id: str,
    instrument_number: str,
    promulgation_date: str | None,
    metadata_effective_date: str | None,
) -> dict[str, Any]:
    return extract_document_parts(
        [pdf_path],
        document_id,
        instrument_number,
        promulgation_date,
        metadata_effective_date,
    )


def extract_document_parts(
    pdf_paths: list[Path],
    document_id: str,
    instrument_number: str,
    promulgation_date: str | None,
    metadata_effective_date: str | None,
    source_page_url: str | None = None,
) -> dict[str, Any]:
    """Extract one instrument after concatenating all ordered Gazette parts."""

    if not pdf_paths:
        raise ValueError(f"No PDF parts supplied: {instrument_number}")
    page_texts: list[str] = []
    page_provenance: list[dict[str, Any]] = []
    pdf_parts: list[dict[str, Any]] = []
    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        part_texts = [page.extract_text() or "" for page in reader.pages]
        pdf_parts.append(
            {
                "pdf_path": pdf_path.as_posix(),
                "pdf_sha256": sha256_file(pdf_path),
                "pdf_page_count": len(part_texts),
            }
        )
        for page_in_file, text in enumerate(part_texts, start=1):
            page_texts.append(text)
            page_provenance.append(
                {"pdf_path": pdf_path.as_posix(), "page_in_file": page_in_file}
            )
    substantive_text_pages = sum(len(normalize_space(text)) >= 200 for text in page_texts)
    text_layer_coverage_ratio = (
        round(substantive_text_pages / len(page_texts), 4) if page_texts else 0.0
    )
    span = find_document_span(page_texts, instrument_number)
    evidence = extract_temporal_evidence(page_texts, span, promulgation_date)
    for item in evidence:
        provenance = page_provenance[item["pdf_page"] - 1]
        item["source_pdf_path"] = provenance["pdf_path"]
        item["source_pdf_page"] = provenance["page_in_file"]
    general = [item for item in evidence if item["kind"] == "general_effective"]
    resolved_general = [item for item in general if item.get("effective_date")]
    application = [item for item in evidence if item["kind"] == "application_period"]
    if resolved_general:
        content_status = "general_effective_clause_found"
        effective_date = resolved_general[0]["effective_date"]
        effective_source = "content_clause"
    elif evidence:
        content_status = "temporal_clauses_found_but_general_effective_unresolved"
        effective_date = None
        effective_source = "unresolved"
    else:
        content_status = (
            "insufficient_text_layer_for_temporal_clause"
            if text_layer_coverage_ratio < 0.9
            else "no_temporal_clause_extracted"
        )
        effective_date = None
        effective_source = "unresolved"
    extraction_status = (
        "requires_ocr_or_manual_review"
        if content_status == "insufficient_text_layer_for_temporal_clause"
        else "extracted"
    )
    return {
        "extraction_status": extraction_status,
        "document_id": document_id,
        "instrument_number": instrument_number,
        "source_page_url": source_page_url,
        "pdf_parts": pdf_parts,
        "pdf_path": pdf_paths[0].as_posix(),
        "pdf_sha256": pdf_parts[0]["pdf_sha256"],
        "pdf_page_count": len(page_texts),
        "substantive_text_page_count": substantive_text_pages,
        "text_layer_coverage_ratio": text_layer_coverage_ratio,
        "document_span": {
            "start_pdf_page": span.start_page,
            "end_pdf_page": span.end_page,
            "candidate_pages": list(span.candidate_pages),
            "location_confidence": span.location_confidence,
        },
        "metadata_effective_date": metadata_effective_date,
        "effective_date_value": effective_date,
        "effective_date_source": effective_source,
        "content_match_status": content_status,
        "metadata_content_conflict": bool(
            metadata_effective_date and effective_date and metadata_effective_date != effective_date
        ),
        "metadata_content_status": (
            "confirmed"
            if metadata_effective_date and effective_date == metadata_effective_date
            else "conflicts"
            if metadata_effective_date and effective_date
            else "not_confirmed_by_content"
            if metadata_effective_date
            else "metadata_absent"
        ),
        "application_period_count": len(application),
        "temporal_evidence": evidence,
        "temporal_review_status": (
            "requires_ocr_or_manual_review"
            if extraction_status == "requires_ocr_or_manual_review"
            else "pending_human_review"
        ),
    }


def load_attachment_records(manifest_path: Path) -> list[dict[str, Any]]:
    records = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("record_type") == "official_attachment" and item.get("fetch_status") == "fetched":
            records.append(item)
    return records


def load_source_page_records(manifest_path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("record_type") == "source_page" and item.get("fetch_status") == "fetched":
            records[item["document_id"]] = item
    return records


def normalize_manifest_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def run(args: argparse.Namespace) -> int:
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    config_by_id = {item["id"]: item for item in config["documents"]}
    crawl_root = Path(args.crawl_root).resolve()
    manifest_path = crawl_root / "manifest.jsonl"
    source_pages = load_source_page_records(manifest_path)
    attachments_by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in load_attachment_records(manifest_path):
        attachments_by_document[record["document_id"]].append(record)
    results = []
    for document_id, records in attachments_by_document.items():
        document = config_by_id[document_id]
        pdf_paths = [crawl_root / record["stored_path"] for record in records]
        source_page = source_pages.get(document_id, {})
        source_metadata = source_page.get("metadata", {})
        metadata_effective_date = normalize_manifest_date(source_metadata.get("effective_date"))
        metadata_effective_date = metadata_effective_date or document.get("effective_date_expected")
        try:
            results.append(
                extract_document_parts(
                    pdf_paths,
                    document["id"],
                    document["instrument_number"],
                    document.get("promulgation_date_expected"),
                    metadata_effective_date,
                    source_page.get("final_url") or source_page.get("requested_url"),
                )
            )
        except Exception as exc:
            try:
                page_count = sum(len(PdfReader(pdf_path).pages) for pdf_path in pdf_paths)
            except Exception:
                page_count = None
            results.append(
                {
                    "extraction_status": "requires_ocr_or_manual_review",
                    "document_id": document["id"],
                    "instrument_number": document["instrument_number"],
                    "source_page_url": source_page.get("final_url")
                    or source_page.get("requested_url"),
                    "pdf_parts": [
                        {
                            "pdf_path": pdf_path.as_posix(),
                            "pdf_sha256": sha256_file(pdf_path),
                        }
                        for pdf_path in pdf_paths
                    ],
                    "pdf_page_count": page_count,
                    "metadata_effective_date": metadata_effective_date,
                    "metadata_content_status": (
                        "not_confirmed_by_content" if metadata_effective_date else "metadata_absent"
                    ),
                    "effective_date_value": None,
                    "effective_date_source": "unresolved",
                    "content_match_status": "instrument_not_located_in_pdf_text_layer",
                    "error": f"{type(exc).__name__}: {exc}",
                    "temporal_review_status": "requires_ocr_or_manual_review",
                }
            )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "source_manifest": str((crawl_root / "manifest.jsonl").as_posix()),
        "document_count": len(results),
        "documents": results,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "document_count": len(results)}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--crawl-root", required=True)
    parser.add_argument("--output", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
