"""Small, repeatable source/parse pilot. This does not publish a current-law corpus."""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pymupdf
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pilot" / "2026-09-24"
ALLOWED_HOSTS = {"vanban.chinhphu.vn", "datafiles.chinhphu.vn"}
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
ARTICLE_RE = re.compile(r"^\s*Điều\s+(\d+[a-zA-Z]?)(?:[.:]\s*|\s*$)(.*)$", re.IGNORECASE)

# Deliberate diagnostic set: includes consolidated, implementing, amending,
# historical and boundary-scope texts. Inclusion here is NOT legal-current review.
SAMPLES = [
    ("45_2019_qh14", "https://vanban.chinhphu.vn/?classid=1&docid=198540&pageid=27160&typegroupid=3"),
    ("18_2026_vbhn_vpqh", "https://vanban.chinhphu.vn/?classid=2629&docid=217002&pageid=27160"),
    ("145_2020_nd_cp", "https://vanban.chinhphu.vn/default.aspx?docid=201967&pageid=27160"),
    ("135_2020_nd_cp", "https://vanban.chinhphu.vn/default.aspx?docid=201650&pageid=27160"),
    ("152_2020_nd_cp", "https://vanban.chinhphu.vn/?classid=1&docid=202215&orggroupid=2&pageid=27160"),
    ("70_2023_nd_cp", "https://vanban.chinhphu.vn/?classid=1&docid=208673&orggroupid=2&pageid=27160"),
    ("293_2025_nd_cp", "https://vanban.chinhphu.vn/?classid=1&docid=215832&orggroupid=2&pageid=27160"),
    ("74_2024_nd_cp", "https://vanban.chinhphu.vn/?classid=1&docid=210536&orggroupid=2&pageid=27160"),
    ("38_2022_nd_cp", "https://vanban.chinhphu.vn/?classid=1&docid=205950&pageid=27160&typegroupid=5"),
    ("12_2022_nd_cp", "https://vanban.chinhphu.vn/?classid=1&docid=205182&orggroupid=2&pageid=27160"),
]


def assert_allowed_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"URL outside pilot allowlist: {url}")


def fetch(session: requests.Session, url: str) -> tuple[bytes, str, str]:
    """Fetch once plus two retries; reject cross-domain redirects and oversize content."""
    assert_allowed_url(url)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            current_url = url
            for _ in range(6):
                with session.get(current_url, timeout=(10, 45), allow_redirects=False, stream=True) as response:
                    if response.is_redirect:
                        location = response.headers.get("Location")
                        if not location:
                            raise ValueError("Redirect without Location")
                        current_url = requests.compat.urljoin(response.url, location)
                        assert_allowed_url(current_url)
                        continue
                    response.raise_for_status()
                    declared_size = int(response.headers.get("Content-Length", "0"))
                    if declared_size > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Source exceeds pilot size limit")
                    data = bytearray()
                    for chunk in response.iter_content(chunk_size=256 * 1024):
                        data.extend(chunk)
                        if len(data) > MAX_DOWNLOAD_BYTES:
                            raise ValueError("Source exceeds pilot size limit")
                    return bytes(data), response.url, response.headers.get("Content-Type", "")
            raise ValueError("Too many redirects")
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"Fetch failed for {url}: {last_error}")


def parse_portal_page(page: bytes) -> dict:
    soup = BeautifulSoup(page, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    fields: dict[str, str] = {}
    for cell in soup.select("td.col1"):
        sibling = cell.find_next_sibling("td")
        if sibling:
            fields[cell.get_text(" ", strip=True)] = sibling.get_text(" ", strip=True)
    attachments = []
    for anchor in soup.select("a[href]"):
        href = requests.compat.urljoin("https://vanban.chinhphu.vn/", anchor["href"])
        if urlparse(href).path.lower().endswith(".pdf"):
            try:
                assert_allowed_url(href)
            except ValueError:
                continue
            attachments.append({"name": anchor.get_text(" ", strip=True), "url": href})
    return {"title": title, "fields": fields, "pdf_attachments": attachments}


def normalize_text(text: str) -> str:
    # NFC and whitespace only. Never rewrite legal wording.
    return "\n".join(
        re.sub(r"[\t\u00a0 ]+", " ", line).strip()
        for line in unicodedata.normalize("NFC", text).splitlines()
        if line.strip()
    )


def extract_pdf(pdf_bytes: bytes) -> tuple[list[dict], dict]:
    pages = []
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for index, page in enumerate(doc, start=1):
            raw = page.get_text("text", sort=True)
            normalized = normalize_text(raw)
            page_area = page.rect.width * page.rect.height
            max_image_fraction = max(
                ((image["bbox"][2] - image["bbox"][0])
                 * (image["bbox"][3] - image["bbox"][1]) / page_area
                 for image in page.get_image_info()),
                default=0.0,
            )
            pages.append(
                {"page": index, "raw_text": raw, "normalized_text": normalized,
                 "word_count": len(normalized.split()), "replacement_chars": raw.count("\ufffd"),
                 "full_page_image": max_image_fraction >= 0.8}
            )
    stats = {
        "pages": len(pages),
        "empty_pages": sum(not p["normalized_text"] for p in pages),
        "word_count": sum(p["word_count"] for p in pages),
        "replacement_chars": sum(p["replacement_chars"] for p in pages),
        "substantial_text_pages": sum(p["word_count"] >= 50 for p in pages),
        "full_page_image_pages": sum(p["full_page_image"] for p in pages),
    }
    return pages, stats


def scan_like(stats: dict) -> bool:
    """Ignore a token footer if the PDF is overwhelmingly full-page images."""
    return (
        stats["substantial_text_pages"] / max(stats["pages"], 1) < 0.2
        and stats["full_page_image_pages"] / max(stats["pages"], 1) >= 0.8
    )


def make_sections(pages: list[dict]) -> list[dict]:
    sections: list[dict] = []
    current = {"section": "preamble", "page_start": 1, "page_end": 1, "lines": []}
    for page in pages:
        for line in page["normalized_text"].splitlines():
            match = ARTICLE_RE.match(line)
            if match:
                if current["lines"]:
                    sections.append(current)
                current = {
                    "section": f"Điều {match.group(1)}",
                    "page_start": page["page"], "page_end": page["page"], "lines": [],
                }
            current["lines"].append((page["page"], line))
            current["page_end"] = page["page"]
    if current["lines"]:
        sections.append(current)
    for section in sections:
        located_lines = section.pop("lines")
        page_blocks = []
        for page_no, line in located_lines:
            if not page_blocks or page_blocks[-1]["page"] != page_no:
                page_blocks.append({"page": page_no, "lines": []})
            page_blocks[-1]["lines"].append(line)
        section["page_blocks"] = [
            {"page": block["page"], "text": "\n".join(block["lines"])}
            for block in page_blocks
        ]
        section["text"] = "\n".join(line for _, line in located_lines)
        section["word_count"] = len(section["text"].split())
    return sections


def make_chunks(doc_id: str, pdf_hash: str, sections: list[dict]) -> list[dict]:
    chunks = []
    for section_index, section in enumerate(sections):
        located_words = [
            (word, block["page"])
            for block in section["page_blocks"]
            for word in block["text"].split()
        ]
        if not located_words:
            continue
        starts = [0] if len(located_words) <= 600 else range(0, len(located_words), 520)
        for part_index, start in enumerate(starts):
            part = located_words[start : start + 600]
            if not part:
                continue
            text = " ".join(word for word, _ in part)
            identity = f"{doc_id}|{pdf_hash}|{section_index}|{part_index}|{hashlib.sha256(text.encode()).hexdigest()}"
            chunks.append({
                "chunk_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                "document_id": doc_id,
                "section": section["section"],
                "page_start": part[0][1],
                "page_end": part[-1][1],
                "section_page_start": section["page_start"],
                "section_page_end": section["page_end"],
                "page_span_coarse": False,
                "part": part_index + 1,
                "word_count": len(part),
                "text": text,
            })
    return chunks


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    if (OUT / "manifest.jsonl").exists():
        raise FileExistsError(f"Pilot manifest already exists: {OUT / 'manifest.jsonl'}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw").mkdir(exist_ok=True)
    (OUT / "pages").mkdir(exist_ok=True)
    (OUT / "chunks").mkdir(exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "CiteAgentVN-ResearchPilot/0.1 (+public document evaluation)"})
    manifest = []
    for doc_id, page_url in SAMPLES:
        record = {
            "document_id": doc_id, "source_url": page_url,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "source_type": "pdf", "language": "vi",
            "license": "publicly_accessible_unknown_license",
            "legal_status": "unverified", "review_status": "pilot_only",
        }
        try:
            html, final_url, html_type = fetch(session, page_url)
            if "html" not in html_type.lower():
                raise ValueError(f"Unexpected metadata content type: {html_type}")
            parsed = parse_portal_page(html)
            if not parsed["fields"].get("Số ký hiệu") or not parsed["pdf_attachments"]:
                raise ValueError("Missing document number or PDF attachment")
            (OUT / "raw" / f"{doc_id}.html").write_bytes(html)
            attachment = parsed["pdf_attachments"][0]
            pdf, pdf_url, pdf_type = fetch(session, attachment["url"])
            if not pdf.startswith(b"%PDF-"):
                raise ValueError(f"Attachment is not PDF: {pdf_type}")
            (OUT / "raw" / f"{doc_id}.pdf").write_bytes(pdf)
            pages, stats = extract_pdf(pdf)
            is_scan = scan_like(stats)
            sections = [] if is_scan else make_sections(pages)
            pdf_hash = hashlib.sha256(pdf).hexdigest()
            chunks = make_chunks(doc_id, pdf_hash, sections)
            write_jsonl(OUT / "pages" / f"{doc_id}.jsonl", pages)
            write_jsonl(OUT / "chunks" / f"{doc_id}.jsonl", chunks)
            article_sections = [s for s in sections if s["section"] != "preamble"]
            record.update({
                "status": "unsupported_scan" if is_scan else "processed",
                "source_url": final_url, "html_sha256": hashlib.sha256(html).hexdigest(),
                "html_bytes": len(html), "content_url": pdf_url,
                "content_sha256": pdf_hash, "pdf_bytes": len(pdf),
                "attachment_count": len(parsed["pdf_attachments"]),
                "attachment_names": [x["name"] for x in parsed["pdf_attachments"]],
                "title": parsed["title"],
                "document_number": parsed["fields"].get("Số ký hiệu"),
                "issued_date_raw": parsed["fields"].get("Ngày ban hành"),
                "effective_date_raw": parsed["fields"].get("Ngày có hiệu lực"),
                "document_type": parsed["fields"].get("Loại văn bản"),
                "publisher": parsed["fields"].get("Cơ quan ban hành"),
                "summary": parsed["fields"].get("Trích yếu"),
                **stats, "article_sections": len(article_sections),
                "max_section_words": max((s["word_count"] for s in sections), default=0),
                "chunk_count": len(chunks),
                "coarse_page_chunks": sum(c["page_span_coarse"] for c in chunks),
            })
            print(f"OK {doc_id}: {stats['pages']} pages, {stats['word_count']} words, {len(chunks)} chunks", flush=True)
        except Exception as exc:  # keep the rest of the pilot running
            record.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            print(f"FAIL {doc_id}: {exc}", flush=True)
        manifest.append(record)
        write_jsonl(OUT / "manifest.jsonl", manifest)
        time.sleep(1)
    summary = {
        "sample_count": len(manifest),
        "processed": sum(x["status"] == "processed" for x in manifest),
        "unsupported_scan": sum(x["status"] == "unsupported_scan" for x in manifest),
        "failed": sum(x["status"] == "failed" for x in manifest),
        "total_pages": sum(x.get("pages", 0) for x in manifest),
        "total_words": sum(x.get("word_count", 0) for x in manifest),
        "total_chunks": sum(x.get("chunk_count", 0) for x in manifest),
        "total_empty_pages": sum(x.get("empty_pages", 0) for x in manifest),
        "total_coarse_page_chunks": sum(x.get("coarse_page_chunks", 0) for x in manifest),
        "multiple_attachment_documents": [x["document_id"] for x in manifest if x.get("attachment_count", 0) > 1],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
