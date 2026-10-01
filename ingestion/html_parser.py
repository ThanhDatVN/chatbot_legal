"""Read an official full-text HTML page into the same layout model as a PDF.

Navigation, headers, footers, scripts and advertising are removed; headings,
paragraphs, list items and table rows are kept in document order. Each block
becomes its own paragraph; centred or heading elements are marked so the
structure parser recognises chapter titles. Tables use the same labelled-row
linearisation as PDFs. HTML has no pages, so every line is on page 1.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ingestion.layout import DocumentLayout, Line, PageStats
from ingestion.tables import TableBlock, clean_cell, resolve_document_tables

DROP_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "iframe", "button", "svg"]
NOISE_RE = re.compile(r"nav|menu|footer|header|breadcrumb|share|social|banner|advert|ads|sidebar|related|comment|login",
                      re.IGNORECASE)
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "table", "div"}
BODY_X, HEADING_X, LINE_HEIGHT = 70.0, 200.0, 18.0


def _is_noise(tag: Tag) -> bool:
    ident = " ".join(tag.get("class", [])) + " " + (tag.get("id") or "")
    return bool(ident.strip()) and bool(NOISE_RE.search(ident))


def _centered(tag: Tag) -> bool:
    style = (tag.get("style") or "").replace(" ", "").lower()
    return tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"} or tag.get("align") == "center" \
        or "text-align:center" in style


def _text(tag: Tag) -> str:
    return " ".join(unicodedata.normalize("NFC", tag.get_text(" ", strip=True)).split())


def _main_container(soup: BeautifulSoup) -> Tag:
    """The element holding the act: the smallest block that contains 'Điều 1.' and most of the text."""
    body = soup.body or soup
    candidates = [t for t in body.find_all(["article", "main", "div", "section"]) if "Điều 1." in t.get_text()]
    if not candidates:
        return body
    total = len(body.get_text())
    sized = [t for t in candidates if len(t.get_text()) >= 0.5 * total] or candidates
    return min(sized, key=lambda t: len(t.get_text()))


def _table_rows(table: Tag) -> tuple[list[list[str | None]], list[list[str | None]]]:
    """Cell grid plus, for each covered cell, whether a colspan ("left") or a rowspan ("up") covers it."""
    rows: list[list[str | None]] = []
    dirs: list[list[str | None]] = []
    spans: dict[int, int] = {}  # column -> rows still covered by a rowspan from above
    for tr in table.find_all("tr"):
        row: list[str | None] = []
        drow: list[str | None] = []
        cells = iter(tr.find_all(["td", "th"]))
        col = 0
        while True:
            if spans.get(col, 0) > 0:
                row.append(None)
                drow.append("up")
                spans[col] -= 1
                col += 1
                continue
            cell = next(cells, None)
            if cell is None:
                break
            row.append(clean_cell(cell.get_text(" ", strip=True)))
            drow.append(None)
            rowspan = int(cell.get("rowspan", 1) or 1)
            colspan = int(cell.get("colspan", 1) or 1)
            if rowspan > 1:
                spans[col] = rowspan - 1
            for k in range(1, colspan):
                row.append(None)
                drow.append("left")
                if rowspan > 1:
                    spans[col + k] = rowspan - 1
            col += colspan
        if row:
            rows.append(row)
            dirs.append(drow)
    width = max((len(r) for r in rows), default=0)
    return ([r + [""] * (width - len(r)) for r in rows], [d + [None] * (width - len(d)) for d in dirs])


def read_html_layout(document_id: str, path: Path) -> DocumentLayout:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()
    for tag in [t for t in soup.find_all(True) if isinstance(t, Tag) and t.attrs is not None and _is_noise(t)]:
        if not tag.decomposed:
            tag.decompose()
    root = _main_container(soup)
    lines: list[Line] = []
    tables: list[TableBlock] = []
    y = 0.0

    def emit(text: str, x0: float, bold: bool = False, table: TableBlock | None = None, row: int | None = None):
        nonlocal y
        y += LINE_HEIGHT
        lines.append(Line(page=1, part=1, part_page=1, x0=x0, y0=y, x1=x0 + 400, y1=y + 14, text=text, size=14,
                          bold=bold, is_table=table is not None, table_row=row, table=table, force_break=True))

    def walk(node: Tag) -> None:
        for child in node.children:
            if not isinstance(child, Tag):
                continue
            if child.name == "table":
                rows, dirs = _table_rows(child)
                if rows and len(rows[0]) >= 2:
                    block = TableBlock(bbox=(0, y, 0, y), col_count=len(rows[0]), row_count=len(rows), raw=rows,
                                       merge_dir=dirs, page=1)
                    tables.append(block)
                    for r in range(len(rows)):
                        emit("", BODY_X, table=block, row=r)
                else:
                    for r in rows:
                        emit(" ".join(v for v in r if v), BODY_X)
                continue
            has_blocks = any(isinstance(c, Tag) and c.name in BLOCK_TAGS for c in child.children)
            if child.name in BLOCK_TAGS and not has_blocks:
                text = _text(child)
                if text:
                    emit(text, HEADING_X if _centered(child) else BODY_X,
                         bold=child.name.startswith("h") or child.find(["b", "strong"]) is not None)
            else:
                walk(child)

    walk(root)
    resolve_document_tables(tables)
    kept: list[Line] = []
    for line in lines:
        if line.table is not None:
            index = line.table_row - line.table.header_rows
            if index < 0 or not line.table.rows_text[index]:
                continue
            line.text, line.table_row = line.table.rows_text[index], index
        kept.append(line)
    return DocumentLayout(document_id=document_id, body_size=14, lines=kept, footnotes=[],
                          pages=[PageStats(page=1, part=1, part_page=1, body_lines=len(kept),
                                           table_count=len(tables))],
                          tables=tables, blank_pages=[])
