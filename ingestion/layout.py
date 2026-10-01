"""Layout-aware reading of Công báo PDFs.

Each PDF line is classified before any text is joined, so running headers, the
digital-signature stamp and consolidated-text footnotes never reach the legal
body text. Footnote markers are removed from body lines and their positions are
kept so notes can be attached to the provision that carries the marker.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from ingestion.tables import TableBlock, detect_tables, resolve_document_tables

HEADER_RE = re.compile(r"^\s*(\d{1,4}\s+)?CÔNG BÁO/Số\s+\d+(\s*\+\s*\d+)?/Ngày\s+\d{1,2}-\d{1,2}-\d{4}(\s+\d{1,4})?\s*$")
# a signature-stamp field has a value; the same label followed by dots is a blank field of a form in an annex
STAMP_RE = re.compile(r"^(Ký bởi|Người ký|Ngày ký|Email|Cơ quan|Thời gian ký)\s*:(?!\s*[.…_]{3,})")
GAZETTE_BANNER = "VĂN BẢN QUY PHẠM PHÁP LUẬT"  # Công báo section banner, not part of the act
CONTINUATION_RE = re.compile(r"^\((Xem )?[Tt]iếp theo Công báo số .*\)$")
HEADER_ZONE = 75.0  # points from the top edge; Công báo headers sit at y≈29–69
FOOTNOTE_ID_RE = re.compile(r"^\d{1,3}$")
MARKER_SIZE_GAP = 3.0  # markers are at least 3pt smaller than the body font


@dataclass
class Line:
    page: int  # 1-based page number across all source parts, blank pages excluded
    part: int
    part_page: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    size: float
    bold: bool
    is_table: bool = False
    table_row: int | None = None
    table: TableBlock | None = None
    markers: list[tuple[int, str]] = field(default_factory=list)  # (offset in text, footnote number)
    force_break: bool = False  # HTML blocks: the line always starts a new paragraph


@dataclass
class RawFootnote:
    number: str
    page: int
    lines: list[str]

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.lines).split())


@dataclass
class PageStats:
    page: int
    part: int
    part_page: int
    header_lines: int = 0
    stamp_lines: int = 0
    footnote_lines: int = 0
    body_lines: int = 0
    table_count: int = 0
    rejected_table_count: int = 0


@dataclass
class DocumentLayout:
    document_id: str
    body_size: float
    lines: list[Line]
    footnotes: list[RawFootnote]
    pages: list[PageStats]
    tables: list[TableBlock]
    blank_pages: list[tuple[int, int]]


def _span_is_marker(span: dict, body_size: float) -> bool:
    return span["size"] <= body_size - MARKER_SIZE_GAP and bool(FOOTNOTE_ID_RE.match(span["text"].strip()))


def _is_body_sized(line: dict, body_size: float) -> bool:
    return max((s["size"] for s in line["spans"] if s["text"].strip()), default=0.0) >= body_size - 0.5


def _line_record(line: dict) -> tuple[str, float, bool]:
    text = "".join(s["text"] for s in line["spans"])
    size = max((s["size"] for s in line["spans"] if s["text"].strip()), default=0.0)
    bold = any((s["flags"] & 16) or "Bold" in s["font"] for s in line["spans"] if s["text"].strip())
    return unicodedata.normalize("NFC", text), size, bold


def _body_size(pdfs: list[pymupdf.Document]) -> float:
    weights: dict[float, int] = {}
    for pdf in pdfs:
        for page in pdf:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        key = round(span["size"])
                        weights[key] = weights.get(key, 0) + len(span["text"].strip())
    return float(max(weights, key=weights.get))


def _strip_markers(line: dict, body_size: float) -> tuple[str, list[tuple[int, str]]]:
    """Join spans, dropping footnote-marker spans and remembering where they were."""
    text = ""
    markers: list[tuple[int, str]] = []
    spans = line["spans"]
    last_marker: str | None = None
    for i, span in enumerate(spans):
        if _span_is_marker(span, body_size):
            number = span["text"].strip()
            if number != last_marker:  # the Công báo PDF draws each marker twice
                markers.append((len(text.rstrip()), number))
            last_marker = number
            nxt = next((s["text"] for s in spans[i + 1:] if not _span_is_marker(s, body_size)), "")
            if text and not text[-1].isspace() and nxt[:1].isalnum():
                text += " "
            continue
        if span["text"].strip():
            last_marker = None
        text += span["text"]
    return unicodedata.normalize("NFC", text), markers


def _page_lines(page: pymupdf.Page) -> list[dict]:
    lines = [line for block in page.get_text("dict")["blocks"] for line in block.get("lines", [])]
    lines = [line for line in lines if "".join(s["text"] for s in line["spans"]).strip()]
    return sorted(lines, key=lambda line: (round(line["bbox"][1], 1), line["bbox"][0]))


def _footnote_start(line: dict, body_size: float) -> str | None:
    spans = [s for s in line["spans"] if s["text"].strip()]
    if len(spans) < 2 or not _span_is_marker(spans[0], body_size):
        return None
    rest = [s for s in spans if not _span_is_marker(s, body_size)]
    if rest and max(s["size"] for s in rest) < body_size - 1:
        return spans[0]["text"].strip()
    return None


def _gazette_block(raw: list[dict]) -> set[int]:
    """Line indexes of the Công báo banner block on the first page of a PDF part.

    The first part carries the banner and the issuer heading; later parts repeat
    the banner, issuer and act title down to "(Tiếp theo Công báo số ...)".
    """
    texts = ["".join(s["text"] for s in line["spans"]).strip() for line in raw]
    if GAZETTE_BANNER not in texts:
        return set()
    start = texts.index(GAZETTE_BANNER)
    end = next((i for i in range(start + 1, min(len(texts), start + 12)) if CONTINUATION_RE.match(texts[i])), None)
    if end is None:
        end = start + 1  # banner + issuer heading
    return set(range(start, end + 1))


def read_layout(document_id: str, pdf_paths: list[Path]) -> DocumentLayout:
    pdfs = [pymupdf.open(path) for path in pdf_paths]
    try:
        body_size = _body_size(pdfs)
        lines: list[Line] = []
        footnotes: list[RawFootnote] = []
        stats: list[PageStats] = []
        tables: list[TableBlock] = []
        blank: list[tuple[int, int]] = []
        page_no = 0
        seen_markers: set[str] = set()
        for part_no, pdf in enumerate(pdfs, start=1):
            for index, page in enumerate(pdf):
                raw = _page_lines(page)
                if not raw:
                    blank.append((part_no, index + 1))
                    continue
                page_no += 1
                st = PageStats(page=page_no, part=part_no, part_page=index + 1)
                accepted, rejected = detect_tables(page)
                st.table_count, st.rejected_table_count = len(accepted), rejected
                for table in accepted:
                    table.page = page_no
                tables.extend(accepted)
                in_footnote: RawFootnote | None = None
                page_body: list[Line] = []
                gazette = _gazette_block(raw) if index == 0 else set()
                for li, line in enumerate(raw):
                    text, size, bold = _line_record(line)
                    if li in gazette or CONTINUATION_RE.match(text.strip()):
                        st.stamp_lines += 1
                        continue
                    x0, y0, x1, y1 = line["bbox"]
                    stripped = text.strip()
                    if y0 < HEADER_ZONE and (HEADER_RE.match(stripped) or stripped.isdigit()):
                        st.header_lines += 1
                        continue
                    if size <= 9 and STAMP_RE.match(stripped):
                        st.stamp_lines += 1
                        continue
                    number = _footnote_start(line, body_size)
                    if number is not None and number in seen_markers and y0 > page.rect.height * 0.25:
                        rest = "".join(s["text"] for s in line["spans"] if not _span_is_marker(s, body_size))
                        in_footnote = RawFootnote(number=number, page=page_no, lines=[rest.strip()])
                        footnotes.append(in_footnote)
                        st.footnote_lines += 1
                        continue
                    if in_footnote is not None and size < body_size - 1:
                        in_footnote.lines.append(stripped)
                        st.footnote_lines += 1
                        continue
                    in_footnote = None
                    if any(t.contains(line["bbox"]) for t in accepted):
                        continue  # replaced by the linearised table rows below
                    if _is_body_sized(line, body_size):
                        clean, markers = _strip_markers(line, body_size)
                        seen_markers.update(number for _, number in markers)
                    else:
                        clean, markers = text, []
                    page_body.append(Line(page=page_no, part=part_no, part_page=index + 1, x0=x0, y0=y0, x1=x1,
                                          y1=y1, text=clean.rstrip(), size=size, bold=bold, markers=markers))
                for table in accepted:
                    for r in range(len(table.raw)):  # placeholders, filled once the document is read
                        page_body.append(Line(page=page_no, part=part_no, part_page=index + 1, x0=table.bbox[0],
                                              y0=table.bbox[1] + r * 0.01, x1=table.bbox[2], y1=table.bbox[3],
                                              text="", size=body_size, bold=False, is_table=True, table_row=r,
                                              table=table))
                page_body.sort(key=lambda ln: (round(ln.y0, 2), ln.x0))
                lines.extend(page_body)
                stats.append(st)
        resolve_document_tables(tables)
        kept: list[Line] = []
        for line in lines:
            if line.table is not None:
                data_index = line.table_row - line.table.header_rows
                if data_index < 0 or not line.table.rows_text[data_index]:
                    continue
                line.text = line.table.rows_text[data_index]
                line.table_row = data_index
            kept.append(line)
        lines = kept
        for st in stats:
            st.body_lines = sum(1 for line in lines if line.page == st.page)
        return DocumentLayout(document_id=document_id, body_size=body_size, lines=lines, footnotes=footnotes,
                              pages=stats, tables=tables, blank_pages=blank)
    finally:
        for pdf in pdfs:
            pdf.close()
