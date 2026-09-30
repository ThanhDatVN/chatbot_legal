"""Re-OCR pages around article-sequence gaps for reviewer triage."""

from __future__ import annotations

import json
import re

from pilot.benchmark_ocr import ocr_page
from pilot.collect import OUT


CASES = (
    ("45_2019_qh14", 11, [28]),
    ("18_2026_vbhn_vpqh", 15, [35]),
    ("18_2026_vbhn_vpqh", 33, [76, 77, 78, 79]),
    ("18_2026_vbhn_vpqh", 61, [166]),
    ("145_2020_nd_cp", 6, [6]),
    ("145_2020_nd_cp", 72, [97]),
)
HEADING = re.compile(r"^\s*[-–—]?\s*Điều\s+\d+", re.IGNORECASE)


def main() -> None:
    rows = []
    for doc_id, page, missing in CASES:
        variants = {}
        for config in (("fast_200", "tessdata", 200), ("best_200", "tessdata_best", 200)):
            text = ocr_page(doc_id, page, config)
            variants[config[0]] = [line.strip() for line in text.splitlines() if HEADING.match(line)]
        rows.append({
            "document_id": doc_id, "page": page,
            "missing_article_candidates": missing, "headings": variants,
        })
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    (OUT / "heading_gap_benchmark.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
