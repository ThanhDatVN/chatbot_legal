"""Tiny hand-checked OCR probe; not a legal-content evaluation set."""

from __future__ import annotations

import json
import re
import unicodedata

import pymupdf

from pilot.collect import OUT


# Manually transcribed from page 42 of the source PDF, covering the heading,
# opening rule, and point a of Article 113. Keep this fixture short and auditable.
REFERENCE = """Điều 113. Nghỉ hằng năm
1. Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động
thì được nghỉ hằng năm, hưởng nguyên lương theo hợp đồng lao động như sau:
a) 12 ngày làm việc đối với người làm công việc trong điều kiện bình thường;"""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def distance(left: list | str, right: list | str) -> int:
    previous = list(range(len(right) + 1))
    for i, first in enumerate(left, 1):
        current = [i]
        for j, second in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (first != second)))
        previous = current
    return previous[-1]


def excerpt(text: str) -> str:
    start = text.find("Điều 113.")
    if start < 0:
        raise ValueError("Article 113 heading not found")
    end = text.find("b)", start)
    if end < 0:
        raise ValueError("Article 113 point b not found")
    return text[start:end]


def main() -> None:
    pdf = OUT / "raw" / "45_2019_qh14.pdf"
    with pymupdf.open(pdf) as document:
        page = document[41]
        results = []
        for model in ("tessdata", "tessdata_best"):
            textpage = page.get_textpage_ocr(
                language="vie", dpi=200, full=True, tessdata=str((OUT / model).resolve())
            )
            raw = page.get_text("text", textpage=textpage, sort=False)
            (OUT / "qa" / f"article113_{model}.txt").write_text(raw, encoding="utf-8")
            gold = normalize(REFERENCE)
            predicted = normalize(excerpt(raw))
            results.append({
                "model": model,
                "source_pdf": "45_2019_qh14.pdf",
                "page": 42,
                "scope": "Article 113 heading, opening paragraph and point a only",
                "normalization": "NFC, lowercase, punctuation removed, whitespace collapsed",
                "reference_chars": len(gold),
                "character_error_rate": round(distance(gold, predicted) / max(len(gold), 1), 4),
                "word_error_rate": round(distance(gold.split(), predicted.split()) / max(len(gold.split()), 1), 4),
            })
    (OUT / "ocr_quality_probe.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
