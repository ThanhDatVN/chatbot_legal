"""Parse Vietnamese legal documents into a Phan / Chuong / Muc / Dieu / Khoan / Diem tree.

Pin-point citation is the product requirement that drives this module: an answer
must be able to say "Dieu 9 khoan 2 diem a" and point at the exact span that
supports it.  Chunking on a token window alone destroys that, so the structure
is recovered first and the chunker works on the tree.

The parser is line-based and deliberately conservative.  When a line cannot be
classified it is appended to the current node's body rather than dropped, so no
text is ever lost - the worst case degrades to article-level citation instead of
clause-level.
"""

from __future__ import annotations

import re

from virag.schemas import LegalNode

# --- headings --------------------------------------------------------------

_RE_PHAN = re.compile(
    r"^\s*PHẦN\s+(?:THỨ\s+)?([IVXLCDM]+|\d+|[A-ZĐ]{1,15})\b\s*[.:\-]?\s*(.*)$",
    re.IGNORECASE,
)
_RE_CHUONG = re.compile(
    r"^\s*CHƯƠNG\s+([IVXLCDM]+|\d+)\b\s*[.:\-]?\s*(.*)$",
    re.IGNORECASE,
)
_RE_MUC = re.compile(
    r"^\s*MỤC\s+(\d+|[IVXLCDM]+)\b\s*[.:\-]?\s*(.*)$",
    re.IGNORECASE,
)
# "Dieu 9.", "Dieu 9a:", "Dieu 12 - Doi tuong chiu thue"
_RE_DIEU = re.compile(
    r"^\s*Điều\s+(\d{1,3}[a-zđ]?)\s*[.:\-–]?\s*(.*)$",
    re.IGNORECASE,
)
# Khoan: "1. ..." / "2) ..."
_RE_KHOAN = re.compile(r"^\s*(\d{1,2})\s*[.)]\s+(\S.*)$")
# Diem: "a) ..." / "dd) ..."
_RE_DIEM = re.compile(r"^\s*([a-zđ]{1,2})\s*\)\s+(\S.*)$")

# Lines that mark the end of the operative text.
_RE_SIGNATURE = re.compile(
    r"^\s*(?:TM\.|T/M|KT\.|TL\.)\s|"
    r"^\s*(?:CHỦ TỊCH|THỦ TƯỚNG|BỘ TRƯỞNG|TỔNG CỤC TRƯỞNG)\s*$",
    re.IGNORECASE,
)


def _looks_like_heading_only(text: str) -> bool:
    """A Chuong/Muc heading is usually on its own line, in caps."""
    stripped = text.strip()
    return bool(stripped) and stripped == stripped.upper() and len(stripped) < 200


class _Builder:
    def __init__(self) -> None:
        self.root: list[LegalNode] = []
        self.phan: LegalNode | None = None
        self.chuong: LegalNode | None = None
        self.muc: LegalNode | None = None
        self.dieu: LegalNode | None = None
        self.khoan: LegalNode | None = None
        self.diem: LegalNode | None = None
        self.preamble: LegalNode | None = None

    # -- container helpers ------------------------------------------------
    def _attach_container(self, node: LegalNode) -> None:
        if node.kind == "phan":
            self.root.append(node)
            self.phan, self.chuong, self.muc = node, None, None
        elif node.kind == "chuong":
            (self.phan.children if self.phan else self.root).append(node)
            self.chuong, self.muc = node, None
        elif node.kind == "muc":
            parent = self.chuong or self.phan
            (parent.children if parent else self.root).append(node)
            self.muc = node
        self.dieu = self.khoan = self.diem = None

    def start_dieu(self, number: str, heading: str, page: int | None) -> None:
        node = LegalNode(kind="dieu", number=number, heading=heading or None, text="", page_number=page)
        parent = self.muc or self.chuong or self.phan
        (parent.children if parent else self.root).append(node)
        self.dieu = node
        self.khoan = self.diem = None

    def start_khoan(self, number: str, text: str, page: int | None) -> None:
        node = LegalNode(kind="khoan", number=number, heading=None, text=text, page_number=page)
        if self.dieu is None:
            self.start_dieu(number="?", heading=None, page=page)
        assert self.dieu is not None
        self.dieu.children.append(node)
        self.khoan = node
        self.diem = None

    def start_diem(self, letter: str, text: str, page: int | None) -> None:
        node = LegalNode(kind="diem", number=letter, heading=None, text=text, page_number=page)
        if self.khoan is None:
            self.start_khoan(number="?", text="", page=page)
        assert self.khoan is not None
        self.khoan.children.append(node)
        self.diem = node

    def append_text(self, line: str, page: int | None) -> None:
        target = self.diem or self.khoan or self.dieu
        if target is None:
            if self.preamble is None:
                self.preamble = LegalNode(
                    kind="preamble", number=None, heading=None, text="", page_number=page
                )
                self.root.insert(0, self.preamble)
            target = self.preamble
        target.text = f"{target.text}\n{line}".strip() if target.text else line


def parse_structure(pages: list[tuple[int, str]]) -> list[LegalNode]:
    """Parse ``(page_number, page_text)`` pairs into a legal node tree."""
    builder = _Builder()
    in_signature_block = False

    for page_number, page_text in pages:
        for raw_line in page_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if _RE_SIGNATURE.match(line):
                in_signature_block = True
            if in_signature_block and not _RE_DIEU.match(line):
                # Annexes often restart article numbering after the signature;
                # a new "Dieu" line pulls us back into operative text.
                continue
            in_signature_block = False

            match = _RE_PHAN.match(line)
            if match and _looks_like_heading_only(line):
                builder._attach_container(
                    LegalNode("phan", match.group(1), match.group(2).strip() or None, "", page_number)
                )
                continue

            match = _RE_CHUONG.match(line)
            if match:
                builder._attach_container(
                    LegalNode("chuong", match.group(1), match.group(2).strip() or None, "", page_number)
                )
                continue

            match = _RE_MUC.match(line)
            if match and _looks_like_heading_only(line):
                builder._attach_container(
                    LegalNode("muc", match.group(1), match.group(2).strip() or None, "", page_number)
                )
                continue

            match = _RE_DIEU.match(line)
            if match:
                builder.start_dieu(match.group(1), match.group(2).strip(), page_number)
                continue

            match = _RE_DIEM.match(line)
            if match and builder.khoan is not None:
                builder.start_diem(match.group(1), match.group(2).strip(), page_number)
                continue

            match = _RE_KHOAN.match(line)
            if match and builder.dieu is not None:
                builder.start_khoan(match.group(1), match.group(2).strip(), page_number)
                continue

            builder.append_text(line, page_number)

    # A heading with no body carries no citable text; drop the empties.
    return [node for node in builder.root if _has_text(node)]


def _has_text(node: LegalNode) -> bool:
    if node.text.strip():
        return True
    return any(_has_text(child) for child in node.children)


def iter_articles(nodes: list[LegalNode]) -> list[tuple[LegalNode, dict[str, str | None]]]:
    """Flatten the tree to ``(dieu_node, ancestry)`` pairs.

    ``ancestry`` carries the Chuong/Muc numbers that a citation label needs.
    """
    out: list[tuple[LegalNode, dict[str, str | None]]] = []

    def walk(node: LegalNode, ancestry: dict[str, str | None]) -> None:
        if node.kind == "dieu":
            out.append((node, dict(ancestry)))
            return
        next_ancestry = dict(ancestry)
        if node.kind in {"phan", "chuong", "muc"}:
            next_ancestry[node.kind] = node.number
        for child in node.children:
            walk(child, next_ancestry)

    for node in nodes:
        walk(node, {"phan": None, "chuong": None, "muc": None})
    return out


def node_full_text(node: LegalNode) -> str:
    """Render a node and its descendants back to readable text."""
    parts: list[str] = []
    if node.kind == "dieu":
        header = f"Điều {node.number}."
        if node.heading:
            header = f"{header} {node.heading}"
        parts.append(header)
    elif node.kind == "khoan" and node.number and node.number != "?":
        parts.append(f"{node.number}. {node.text}".strip())
    elif node.kind == "diem" and node.number and node.number != "?":
        parts.append(f"{node.number}) {node.text}".strip())
    elif node.text:
        parts.append(node.text)

    if node.kind == "dieu" and node.text:
        parts.append(node.text)

    for child in node.children:
        rendered = node_full_text(child)
        if rendered:
            parts.append(rendered)
    return "\n".join(part for part in parts if part).strip()
