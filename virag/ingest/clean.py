"""Normalisation for Vietnamese legal text coming out of PDF/OCR extraction.

Two problems dominate this corpus:

1.  PDF extractors break a Vietnamese word across lines and drop the diacritic
    context ("thu-\\nnhap"), and OCR inserts spurious spaces inside diacritics.
2.  Every gazette page repeats a header/footer band ("CONG BAO/So 440",
    page numbers, issue dates).  Left in place those bands become the most
    frequent n-grams in the corpus and poison BM25.

``clean_document`` fixes both, page-aware, before any chunking happens.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from virag.schemas import ExtractedDocument, PageText

# Zero-width and control characters that survive PDF extraction.
_INVISIBLE = re.compile(r"[­​‌‍⁠﻿]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# "thu-\nnhap" -> "thunhap"; the hyphen is a line-break artefact, not a real one.
_HYPHEN_LINEBREAK = re.compile(r"(\w)-\s*\n\s*(\w)")

_MULTI_SPACE = re.compile(r"[ \t ]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")

# Page furniture seen across the crawled gazette / portal PDFs.
_PAGE_FURNITURE = (
    re.compile(r"^\s*(?:trang\s*)?\d{1,4}\s*(?:/\s*\d{1,4})?\s*$", re.IGNORECASE),
    re.compile(r"^\s*CÔNG\s*BÁO(?:\s*/\s*Số.*)?$", re.IGNORECASE),
    re.compile(r"^\s*công\s*báo\s*số.*$", re.IGNORECASE),
    re.compile(r"^\s*-{2,}\s*$"),
    re.compile(r"^\s*_{3,}\s*$"),
)

# Boilerplate that the portal HTML-to-text path drags in.
_HTML_BOILERPLATE = (
    "Chia sẻ lên facebook",
    "Chia sẻ lên Zalo",
    "Chia sẻ lên Twiter",
    "Copy link",
    "Copylink",
    "Lược đồ Thuộc tính",
    "Văn bản liên quan",
    "Sơ đồ văn bản",
    "Cơ quan ban hành",
    "Hệ thống văn bản",
)


def normalise_unicode(text: str) -> str:
    """NFC-normalise and drop invisible characters.

    Vietnamese has two valid Unicode spellings for most accented vowels; NFC
    picks one so that BM25 tokens and embeddings agree.
    """
    text = unicodedata.normalize("NFC", text)
    text = _INVISIBLE.sub("", text)
    return _CONTROL.sub(" ", text)


def _strip_html_boilerplate(text: str) -> str:
    for marker in _HTML_BOILERPLATE:
        text = text.replace(marker, " ")
    return text


def _detect_repeated_bands(pages: list[PageText], band: int = 3, min_ratio: float = 0.6) -> set[str]:
    """Find header/footer lines repeated on most pages.

    Only the first and last ``band`` lines of each page are candidates, so a
    genuine sentence that happens to recur mid-page is never removed.
    """
    if len(pages) < 4:
        return set()

    counter: Counter[str] = Counter()
    for page in pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for line in lines[:band] + lines[-band:]:
            if 3 <= len(line) <= 120:
                counter[line] += 1

    threshold = max(3, int(len(pages) * min_ratio))
    return {line for line, count in counter.items() if count >= threshold}


def _clean_page_text(text: str, repeated: set[str]) -> str:
    text = normalise_unicode(text)
    text = _strip_html_boilerplate(text)
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)

    kept: list[str] = []
    for raw_line in text.splitlines():
        line = _MULTI_SPACE.sub(" ", raw_line).strip()
        if not line:
            kept.append("")
            continue
        if line in repeated:
            continue
        if any(pattern.match(line) for pattern in _PAGE_FURNITURE):
            continue
        kept.append(line)

    joined = "\n".join(kept)
    return _MULTI_NEWLINE.sub("\n\n", joined).strip()


def clean_document(document: ExtractedDocument) -> ExtractedDocument:
    """Clean every page in place and return the same document object."""
    repeated = _detect_repeated_bands(document.pages)
    for page in document.pages:
        page.text = _clean_page_text(page.text, repeated)
        page.char_count = len(page.text)
    return document


def clean_text(text: str) -> str:
    """Clean a standalone string (used by tests and the query path)."""
    return _clean_page_text(text, set())


def is_low_quality(document: ExtractedDocument, min_chars: int = 400, min_alpha_ratio: float = 0.5) -> bool:
    """Reject documents that extraction clearly failed on.

    A cover-page-only PDF or an OCR pass that produced mostly punctuation would
    otherwise enter the index as unretrievable noise.
    """
    text = document.text
    if len(text) < min_chars:
        return True
    alpha = sum(1 for ch in text if ch.isalpha() or ch.isspace())
    return (alpha / max(1, len(text))) < min_alpha_ratio
