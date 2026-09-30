"""Table detection and row-wise linearisation.

Flattened table text loses which value belongs to which column (for example the
male/female retirement columns in Nghị định 135/2020). Each accepted table row is
rewritten as "column label: value; ..." so the meaning survives chunking.

Tables are processed per document: consecutive page tables without their own
header continue the previous logical table, and vertically merged cells that
straddle a page break are joined before values are filled.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import pymupdf

MAX_HEADER_ROWS = 3
MIN_FILLED_COLUMNS = 2
MIN_COLUMN_FILL = 0.5
MIN_VERTICAL_RULES = 2  # ruled tables only: highlight bands and two-column headers have none

LEFT, UP = "left", "up"


@dataclass
class TableBlock:
    bbox: tuple[float, float, float, float]
    col_count: int
    row_count: int
    raw: list[list[str | None]]
    merge_dir: list[list[str | None]]  # for None cells: "left" or "up"
    page: int = 0
    header_rows: int = 0
    labels: list[str] = field(default_factory=list)
    col_offset: int = 0
    header_source: str = "none"  # own | continued | continued_group | none
    rows_text: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def contains(self, bbox: tuple[float, float, float, float], tol: float = 1.0) -> bool:
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        x0, y0, x1, y1 = self.bbox
        return x0 - tol <= cx <= x1 + tol and y0 - tol <= cy <= y1 + tol


def clean_cell(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(unicodedata.normalize("NFC", value).split())


def is_real_table(rows: list[list[str | None]]) -> bool:
    """Reject paragraphs that the line-based detector split into fake columns."""
    if len(rows) < 2 or len(rows[0]) < 2:
        return False
    cols = len(rows[0])
    filled = 0
    for c in range(cols):
        share = sum(1 for r in rows if r[c] not in (None, "")) / len(rows)
        if share >= MIN_COLUMN_FILL:
            filled += 1
    return filled >= MIN_FILLED_COLUMNS


def vertical_rules(drawings: list[dict], bbox: tuple[float, float, float, float]) -> int:
    """Count distinct x positions of vertical ruling lines crossing the table box."""
    x0, y0, x1, y1 = bbox
    xs: set[int] = set()
    for drawing in drawings:
        for item in drawing["items"]:
            if item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.x - b.x) < 1 and abs(a.y - b.y) > 8 and x0 - 2 <= a.x <= x1 + 2 \
                        and min(a.y, b.y) < y1 and max(a.y, b.y) > y0:
                    xs.add(round(a.x))
            elif item[0] == "re":
                r = item[1]
                if r.width < 2.5 and r.height > 8 and x0 - 2 <= r.x0 <= x1 + 2 and r.y0 < y1 and r.y1 > y0:
                    xs.add(round(r.x0))
    return len(xs)


def merge_directions(cells: list[list[tuple | None]]) -> list[list[str | None]]:
    """For every missing cell decide whether a wider cell on the left or a taller cell above covers it."""
    cols = len(cells[0])
    centers = []
    for c in range(cols):
        boxes = [row[c] for row in cells if row[c] is not None]
        narrow = min(boxes, key=lambda b: b[2] - b[0]) if boxes else None
        centers.append((narrow[0] + narrow[2]) / 2 if narrow else None)
    out: list[list[str | None]] = []
    for r, row in enumerate(cells):
        dirs: list[str | None] = []
        for c, box in enumerate(row):
            if box is not None:
                dirs.append(None)
                continue
            left = next((row[k] for k in range(c - 1, -1, -1) if row[k] is not None), None)
            covered_left = left is not None and centers[c] is not None and left[2] > centers[c]
            dirs.append(LEFT if covered_left else UP)
        out.append(dirs)
    return out


def _has_digit(row: list[str | None]) -> bool:
    return any(cell and re.search(r"\d", cell) for cell in row)


def header_row_count(rows: list[list[str | None]]) -> int:
    for i, row in enumerate(rows[:MAX_HEADER_ROWS + 1]):
        if _has_digit(row):
            return min(i, MAX_HEADER_ROWS)
    first = [c for c in rows[0] if c]
    return 1 if first and all(len(c) <= 60 for c in first) and len(rows) > 1 else 0


def column_labels(rows: list[list[str | None]], dirs: list[list[str | None]]) -> list[str]:
    cols = len(rows[0])
    filled: list[list[str]] = []
    for r, row in enumerate(rows):
        out: list[str] = []
        for c in range(cols):
            value = row[c]
            if value is None:
                if dirs[r][c] == LEFT and c > 0:
                    value = out[c - 1]
                elif r > 0:
                    value = filled[r - 1][c]
            out.append(value or "")
        filled.append(out)
    labels = []
    for c in range(cols):
        parts: list[str] = []
        for row in filled:
            if row[c] and (not parts or parts[-1] != row[c]):
                parts.append(row[c])
        labels.append(" – ".join(parts))
    return labels


def _group_suffixes(labels: list[str], width: int) -> list[list[str]]:
    groups = [labels[i:i + width] for i in range(0, len(labels), width)]
    return [[label.split(" – ", 1)[-1] for label in group] for group in groups]


def resolve_document_tables(tables: list[TableBlock]) -> None:
    """Assign labels, join page-straddling merged cells and build row texts in place."""
    logical: list[dict] = []
    for tb in tables:
        n_header = header_row_count(tb.raw)
        tb.header_rows = n_header
        current = logical[-1] if logical else None
        if n_header:
            tb.labels = column_labels(tb.raw[:n_header], tb.merge_dir[:n_header])
            tb.header_source = "own"
            logical.append({"labels": tb.labels, "width": tb.col_count, "tables": [tb]})
            continue
        if current and current["width"] == tb.col_count:
            tb.col_offset, tb.header_source = 0, "continued"
        elif current and current["width"] % tb.col_count == 0 and current["width"] > tb.col_count \
                and len({tuple(g) for g in _group_suffixes(current["labels"], tb.col_count)}) == 1:
            tb.col_offset, tb.header_source = current["width"] - tb.col_count, "continued_group"
        else:
            logical.append({"labels": [""] * tb.col_count, "width": tb.col_count, "tables": [tb]})
            continue
        tb.labels = current["labels"][tb.col_offset:tb.col_offset + tb.col_count]
        current["tables"].append(tb)
    for group in logical:
        _fill_logical_table(group)


def _fill_logical_table(group: dict) -> None:
    width = group["width"]
    absent = object()
    grid: list[list] = []  # values or None (merged up) or absent
    owners: list[tuple[TableBlock, int, bool]] = []  # (table, data row index, first row of its page)
    for tb in group["tables"]:
        for i, row in enumerate(tb.raw[tb.header_rows:]):
            r = tb.header_rows + i
            full: list = [absent] * width
            for c, value in enumerate(row):
                if value is None and tb.merge_dir[r][c] == LEFT:
                    value = ""  # horizontally covered data cell: nothing of its own
                full[tb.col_offset + c] = value
            grid.append(full)
            owners.append((tb, i, i == 0))
    values: list[list[str]] = [[""] * width for _ in grid]
    for c in range(width):
        blocks: list[list] = []  # [start, end, texts]
        current = None
        for i, row in enumerate(grid):
            v = row[c]
            if v is absent:
                current = None
                continue
            page_start = owners[i][2] and i > 0
            if v is None:
                if current is None:
                    current = [i, i, []]
                    blocks.append(current)
                current[1] = i
                continue
            joins_previous = (page_start and current is not None and current[1] == i - 1
                              and (v == "" or not any(current[2])))
            if joins_previous:
                current[1] = i
                if v:
                    current[2].append(v)
                continue
            current = [i, i, [v] if v else []]
            blocks.append(current)
        for start, end, texts in blocks:
            value = texts[0] if texts else ""
            for i in range(start, end + 1):
                values[i][c] = value
    for tb in group["tables"]:
        tb.rows, tb.rows_text = [], []
    for i, (tb, _, _) in enumerate(owners):
        present = [c for c in range(tb.col_offset, tb.col_offset + tb.col_count)]
        row_values = [values[i][c] for c in present]
        tb.rows.append(row_values)
        labels = tb.labels
        if not any(row_values):
            tb.rows_text.append("")
            continue
        if any(labels):
            parts = [f"{labels[k]}: {v}" if labels[k] else v for k, v in enumerate(row_values) if v]
            tb.rows_text.append("; ".join(parts))
        else:
            tb.rows_text.append(" | ".join(v for v in row_values if v))


def detect_tables(page: pymupdf.Page) -> tuple[list[TableBlock], int]:
    accepted: list[TableBlock] = []
    rejected = 0
    found = page.find_tables().tables
    drawings = page.get_drawings() if found else []
    for table in found:
        rows = [[clean_cell(c) for c in row] for row in table.extract()]
        if vertical_rules(drawings, tuple(table.bbox)) < MIN_VERTICAL_RULES or not is_real_table(rows):
            rejected += 1
            continue
        cells = [list(row.cells) for row in table.rows]
        accepted.append(TableBlock(bbox=tuple(table.bbox), col_count=table.col_count, row_count=table.row_count,
                                   raw=rows, merge_dir=merge_directions(cells)))
    return accepted, rejected
