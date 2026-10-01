"""Turn classified layout lines into a legal document tree.

Main articles are accepted only in sequence (Điều 1, 2, 3 ...) and never inside
quoted amendment text, so "Điều 55" quoted from another law or a form's
"Điều 1" cannot become an article of the host document.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from ingestion.layout import DocumentLayout, Line
from ingestion.models import Footnote, Section, SectionKind

ARTICLE_RE = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
CHAPTER_RE = re.compile(r"^(?:Chương|CHƯƠNG)\s+([IVXLCDM]+|\d+)\b\.?\s*(.*)$")
PART_RE = re.compile(r"^Mục\s+(\d+)\.?\s*(.*)$")
CLOSING_RE = re.compile(r"^(Bộ luật|Luật|Nghị quyết) này (đã )?được Quốc hội")
SIGNATURE_RE = re.compile(
    r"^((TM|KT|Q)\.\s.+|THỦ TƯỚNG|PHÓ THỦ TƯỚNG|CHỦ TỊCH QUỐC HỘI|VĂN PHÒNG QUỐC HỘI|XÁC THỰC VĂN BẢN HỢP NHẤT"
    r"|CHỦ NHIỆM|BỘ TRƯỞNG|Nơi nhận:?)$")
ANNEX_RE = re.compile(r"^(PHỤ LỤC|Phụ lục)(\s+[IVXLC\d]+[a-z]?)?\s*:?\s*(?=$|\()")
ANNEX_TITLE_END_RE = re.compile(r"^\((Ban hành )?[Kk]èm theo")
CLAUSE_RE = re.compile(r"^(\d+[a-z]?)\.\s")
POINT_RE = re.compile(r"^([a-zđ])\)\s")
EFFECTIVE_RE = re.compile(r"có hiệu lực (?:thi hành )?kể từ ngày (\d{1,2}) tháng (\d{1,2}) năm (\d{4})")
INSTRUMENT_RE = re.compile(r"((?:Bộ luật|Luật|Nghị định|Nghị quyết)[^,;“”]*?số\s+(?:số\s+)?\d+/\d{4}/[A-ZĐ0-9\-]+)")
INDENT = 12.0
CENTERED = 60.0
SHORT_LINE = 40.0


@dataclass
class Paragraph:
    start: int
    end: int
    lines: list[Line]
    text: str  # lines joined with single spaces

    @property
    def page_start(self) -> int:
        return self.lines[0].page

    @property
    def page_end(self) -> int:
        return self.lines[-1].page

    @property
    def x0(self) -> float:
        return self.lines[0].x0

    @property
    def is_table(self) -> bool:
        return self.lines[0].is_table


@dataclass
class ParsedDocument:
    document_id: str
    text: str
    line_spans: list[tuple[int, int]]
    lines: list[Line]
    paragraphs: list[Paragraph]
    sections: list[Section]
    footnotes: list[Footnote]
    structural_paragraphs: list[int]  # paragraph indexes of Chương/Mục headings
    warnings: list[str] = field(default_factory=list)

    def section_text(self, section: Section) -> str:
        return self.text[section.start:section.end]


def page_margins(lines: list[Line]) -> dict[int, float]:
    by_page: dict[int, Counter] = {}
    for line in lines:
        if not line.is_table:
            by_page.setdefault(line.page, Counter())[round(line.x0)] += 1
    margins = {}
    for page, counts in by_page.items():
        floor = max(2, counts.most_common(1)[0][1] // 4)
        frequent = [x for x, n in counts.items() if n >= floor]
        margins[page] = float(min(frequent or counts))
    return margins


def right_margins(lines: list[Line]) -> dict[int, float]:
    by_page: dict[int, list[float]] = {}
    for line in lines:
        if not line.is_table:
            by_page.setdefault(line.page, []).append(line.x1)
    return {page: sorted(xs)[int(0.9 * (len(xs) - 1))] for page, xs in by_page.items()}


def build_paragraphs(lines: list[Line]) -> tuple[str, list[tuple[int, int]], list[Paragraph]]:
    margins = page_margins(lines)
    rights = right_margins(lines)
    parts: list[str] = []
    spans: list[tuple[int, int]] = []
    pos = 0
    for line in lines:
        spans.append((pos, pos + len(line.text)))
        parts.append(line.text)
        pos += len(line.text) + 1
    text = "\n".join(parts)
    paragraphs: list[Paragraph] = []
    current: list[int] = []
    for i, line in enumerate(lines):
        prev = lines[i - 1] if i else None
        margin = margins.get(line.page, line.x0)
        # justified text: a line that stops well short of the right margin ends its paragraph
        prev_short = prev is not None and prev.x1 < rights.get(prev.page, prev.x1) - SHORT_LINE
        new = (prev is None or line.is_table or prev.is_table or line.force_break
               or line.x0 - margin > INDENT or prev_short
               or (prev.page == line.page and abs(prev.y0 - line.y0) < 2))
        if new and current:
            paragraphs.append(_paragraph(text, spans, lines, current))
            current = []
        current.append(i)
    if current:
        paragraphs.append(_paragraph(text, spans, lines, current))
    return text, spans, paragraphs


def _paragraph(text: str, spans: list[tuple[int, int]], lines: list[Line], idx: list[int]) -> Paragraph:
    start, end = spans[idx[0]][0], spans[idx[-1]][1]
    joined = " ".join(" ".join(lines[i].text.split()) for i in idx).strip()
    return Paragraph(start=start, end=end, lines=[lines[i] for i in idx], text=joined)


def _quote_delta(text: str) -> int:
    return text.count("“") - text.count("”")


CHANGE_RE = re.compile(r"^(Điều|Khoản|Điểm|Cụm từ|Đoạn|Tên|Chương|Mục)\b[^.“]{0,40}?(được|bị)\s+"
                       r"(sửa đổi|bổ sung|bãi bỏ|thay thế)")


def parse_footnote_text(text: str) -> tuple[str, str | None, date | None]:
    m = CHANGE_RE.match(text)
    if not m:
        change = "note"  # e.g. the enacting clauses of the amending laws
    elif m.group(3) == "bãi bỏ":
        change = "repealed"
    elif m.group(3) == "bổ sung" and "sửa đổi" not in text[:m.end() + 12]:
        change = "added"
    else:
        change = "amended"
    instrument = INSTRUMENT_RE.search(text)
    effective = EFFECTIVE_RE.search(text)
    eff = date(int(effective.group(3)), int(effective.group(2)), int(effective.group(1))) if effective else None
    return change, (" ".join(instrument.group(1).split()) if instrument else None), eff


def parse_document(layout: DocumentLayout) -> ParsedDocument:
    doc_id = layout.document_id
    text, line_spans, paragraphs = build_paragraphs(layout.lines)
    margins = page_margins(layout.lines)
    sections: list[Section] = []
    structural: list[int] = []
    warnings: list[str] = []

    state = "preamble"
    depth = 0
    last_article = 0
    chapter: str | None = None
    part: str | None = None
    current: dict | None = None
    annex_count = 0

    def open_section(kind: SectionKind, label: str, title: str | None, number: int | None, path: list[str],
                     first: int) -> dict:
        nonlocal current
        close_section()
        current = {"kind": kind, "label": label, "title": title, "number": number, "path": path, "paras": [first],
                   "quoted": False}
        return current

    def close_section() -> None:
        nonlocal current
        if current is None:
            return
        paras = [paragraphs[i] for i in current["paras"]]
        kind: SectionKind = current["kind"]
        slug = {SectionKind.MAIN_TEXT: f"art{current['number']}", SectionKind.ANNEX: f"annex{annex_count}",
                SectionKind.PREAMBLE: "preamble", SectionKind.CLOSING: "closing",
                SectionKind.SIGNATURE: f"signature{len(sections)}"}[kind]
        sections.append(Section(
            section_id=f"{doc_id}:{slug}", document_id=doc_id, kind=kind, label=current["label"],
            title=current["title"], article_number=current["number"], path=current["path"],
            start=paras[0].start, end=paras[-1].end, page_start=paras[0].page_start, page_end=paras[-1].page_end,
            paragraph_spans=[(p.start, p.end) for p in paras],
            contains_quoted_amendment=current["quoted"], contains_table=any(p.is_table for p in paras)))
        current = None

    i = 0
    pending_title_for: str | None = None  # "chapter" / "part" when the title sits on the next paragraph
    while i < len(paragraphs):
        para = paragraphs[i]
        t = para.text
        margin = margins.get(para.page_start, para.x0)
        at_top_level = depth == 0 and not t.startswith("“")
        delta = _quote_delta(t)

        if pending_title_for and at_top_level and state == "main" and not ARTICLE_RE.match(t) \
                and not CHAPTER_RE.match(t) and not PART_RE.match(t):
            continuation = pending_title_for.endswith("+")
            kind = pending_title_for.rstrip("+")
            joiner = " " if continuation else ". "
            if kind == "chapter":
                chapter = f"{chapter}{joiner}{t}"
            else:
                part = f"{part}{joiner}{t}"
            structural.append(i)
            # a long centred title wraps onto further centred upper-case lines
            nxt = paragraphs[i + 1] if i + 1 < len(paragraphs) else None
            wraps = (nxt is not None and not nxt.is_table and _is_title_line(nxt, margins)
                     and not ARTICLE_RE.match(nxt.text))
            pending_title_for = f"{kind}+" if wraps else None
            i += 1
            continue
        pending_title_for = None

        if state in ("preamble", "main") and at_top_level and not para.is_table:
            m = ARTICLE_RE.match(t)
            if m and int(m.group(1)) == last_article + 1:
                last_article = int(m.group(1))
                state = "main"
                title = m.group(2).strip() or None
                label = f"Điều {last_article}"
                path = [p for p in (chapter, part) if p] + [f"{label}. {title}" if title else label]
                open_section(SectionKind.MAIN_TEXT, label, title, last_article, path, i)
                depth = max(0, depth + delta)
                i += 1
                continue
            if m and state == "main":
                warnings.append(f"non-sequential article heading ignored: {t[:60]!r} after Điều {last_article}")
            cm = CHAPTER_RE.match(t)
            if cm and state in ("preamble", "main") and para.x0 - margin > INDENT and last_article >= 0:
                if state == "preamble" and last_article == 0 and not _next_is_article(paragraphs, i):
                    pass  # e.g. a "Chương" word inside the preamble; stay put
                else:
                    close_section()
                    chapter = f"Chương {cm.group(1)}" + (f". {cm.group(2).strip()}" if cm.group(2).strip() else "")
                    part = None
                    pending_title_for = None if cm.group(2).strip() else "chapter"
                    structural.append(i)
                    state = "main"
                    i += 1
                    continue
            pm = PART_RE.match(t)
            if pm and state == "main" and para.x0 - margin > INDENT:
                close_section()
                part = f"Mục {pm.group(1)}" + (f". {pm.group(2).strip()}" if pm.group(2).strip() else "")
                pending_title_for = None if pm.group(2).strip() else "part"
                structural.append(i)
                i += 1
                continue
            if state == "main" and CLOSING_RE.match(t):
                open_section(SectionKind.CLOSING, "Lời kết", None, None, ["Lời kết"], i)
                state = "closing"
                i += 1
                continue

        if state in ("main", "closing") and at_top_level and SIGNATURE_RE.match(t.split("  ")[0].strip()) \
                and len(t) < 80:
            open_section(SectionKind.SIGNATURE, "Chữ ký", None, None, ["Chữ ký"], i)
            state = "signature"
            i += 1
            continue

        if state in ("signature", "annex", "main", "closing") and at_top_level and ANNEX_RE.match(t) \
                and (state != "main" or para.x0 - margin > CENTERED):
            annex_count += 1
            label = " ".join(ANNEX_RE.match(t).group(0).rstrip(": ").split())
            title_parts: list[str] = []
            j = i + 1
            while j < len(paragraphs) and j <= i + 5:
                nxt = paragraphs[j].text
                if ANNEX_TITLE_END_RE.match(nxt):
                    j += 1
                    break
                if paragraphs[j].is_table:
                    break
                title_parts.append(nxt)
                j += 1
            title = " ".join(title_parts) or None
            open_section(SectionKind.ANNEX, label, title, None, [f"{label}. {title}" if title else label], i)
            state = "annex"
            depth = 0
            i += 1
            continue

        if current is None:
            open_section(SectionKind.PREAMBLE, "Phần mở đầu", None, None, ["Phần mở đầu"], i)
        else:
            current["paras"].append(i)
        if depth > 0 or t.startswith("“"):
            current["quoted"] = True
        depth = max(0, depth + delta)
        i += 1
    close_section()

    footnotes = _attach_footnotes(layout, text, line_spans, paragraphs, sections, structural)
    for fn in footnotes:
        for s in sections:
            if s.section_id == fn.section_id:
                s.footnote_numbers.append(fn.number)
    return ParsedDocument(document_id=doc_id, text=text, line_spans=line_spans, lines=layout.lines,
                          paragraphs=paragraphs, sections=sections, footnotes=footnotes,
                          structural_paragraphs=structural, warnings=warnings)


def _is_title_line(p: Paragraph, margins: dict[int, float]) -> bool:
    letters = [c for c in p.text if c.isalpha()]
    upper = bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.9
    return upper and p.x0 - margins.get(p.page_start, p.x0) > INDENT


def _next_is_article(paragraphs: list[Paragraph], i: int) -> bool:
    for p in paragraphs[i + 1:i + 4]:
        if ARTICLE_RE.match(p.text):
            return True
    return False


def _attach_footnotes(layout: DocumentLayout, text: str, line_spans: list[tuple[int, int]],
                      paragraphs: list[Paragraph], sections: list[Section], structural: list[int]) -> list[Footnote]:
    raw = {fn.number: fn for fn in layout.footnotes}
    out: list[Footnote] = []
    for li, line in enumerate(layout.lines):
        for offset, number in line.markers:
            fn = raw.get(number)
            if fn is None:
                continue
            pos = line_spans[li][0] + offset
            para_index = next(k for k, p in enumerate(paragraphs) if p.start <= pos <= p.end)
            section = next((s for s in sections if s.start <= pos <= s.end), None)
            target = None
            if para_index in structural:
                # note on a chapter heading: attach to the first section after it
                section = next((s for s in sections if s.start > paragraphs[para_index].end), section)
                target = section.path[0] if section and section.path and section.path[0].startswith(("Chương", "Mục")) \
                    else paragraphs[para_index].text
            elif section is not None and section.kind == SectionKind.MAIN_TEXT:
                target = _provision_label(section, paragraphs, para_index)
            elif section is not None:
                target = section.label
            change, instrument, effective = parse_footnote_text(fn.text)
            out.append(Footnote(document_id=layout.document_id, number=number, page=fn.page, text=fn.text,
                                marker_offset=pos, section_id=section.section_id if section else None,
                                target_label=target, change_type=change, amending_instrument=instrument,
                                effective_from=effective))
    return out


def _provision_label(section: Section, paragraphs: list[Paragraph], para_index: int) -> str:
    label = section.label
    clause = point = None
    for k in range(para_index, -1, -1):
        p = paragraphs[k]
        if p.start < section.start:
            break
        if point is None and clause is None and POINT_RE.match(p.text):
            point = POINT_RE.match(p.text).group(1)
            continue
        m = CLAUSE_RE.match(p.text)
        if m:
            clause = m.group(1)
            break
    if clause:
        label += f" khoản {clause}"
    if point:
        label += f" điểm {point}"
    return label
