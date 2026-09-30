"""Paired OCR experiment on the hand-checked pilot excerpts and critical IDs.

This diagnostic set is selected for failures; it is not a corpus-wide estimate.
All candidate outputs are kept separate from the original OCR snapshot.
"""

from __future__ import annotations

import hashlib
import json

import pymupdf

from pilot.collect import OUT
from pilot.evaluate_data_quality import SAMPLES, excerpt
from pilot.evaluate_ocr import distance, normalize


CONFIGS = (
    ("fast_200", "tessdata", 200),
    ("best_200", "tessdata_best", 200),
    ("best_300", "tessdata_best", 300),
)
CRITICAL_PAGES = (
    ("145_2020_nd_cp", 1, "145/2020/NĐ-CP"),
    ("135_2020_nd_cp", 1, "135/2020/NĐ-CP"),
    ("152_2020_nd_cp", 1, "152/2020/NĐ-CP"),
    ("293_2025_nd_cp", 5, "293/2025/NĐ-CP"),
)


def ocr_page(doc_id: str, page_number: int, config: tuple[str, str, int]) -> str:
    name, model_dir, dpi = config
    cache = OUT / "qa" / f"benchmark_{doc_id}_p{page_number}_{name}.txt"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    pdf = OUT / "raw" / f"{doc_id}.pdf"
    with pymupdf.open(pdf) as document:
        page = document[page_number - 1]
        textpage = page.get_textpage_ocr(
            language="vie", dpi=dpi, full=True,
            tessdata=str((OUT / model_dir).resolve()),
        )
        raw = page.get_text("text", textpage=textpage, sort=False)
    cache.write_text(raw, encoding="utf-8")
    return raw


def prediction_excerpt(raw: str, sample: dict) -> str:
    if sample["document_id"] == "152_2020_nd_cp":
        start = raw.find(sample["start"])
        if start < 0:
            raise ValueError(f"Start marker missing: {sample['start']}")
        point_b = raw.find("b)", start)
        if point_b < 0:
            raise ValueError("Point b marker missing")
        line_end = raw.find("\n", point_b)
        return raw[start:line_end if line_end >= 0 else len(raw)]
    return excerpt(raw, sample["start"], sample["end"])


def main() -> None:
    result = {"scope": "selected diagnostic excerpts and identifiers, not a representative sample", "configs": {}}
    for config in CONFIGS:
        name, model_dir, dpi = config
        model_hash = hashlib.sha256((OUT / model_dir / "vie.traineddata").read_bytes()).hexdigest()
        rows = []
        char_count = char_errors = word_count = word_errors = 0
        for sample in SAMPLES:
            raw = ocr_page(sample["document_id"], sample["page"], config)
            gold = normalize(sample["reference"])
            try:
                predicted = normalize(prediction_excerpt(raw, sample))
                c_error = distance(gold, predicted)
                w_error = distance(gold.split(), predicted.split())
                char_count += len(gold)
                char_errors += c_error
                word_count += len(gold.split())
                word_errors += w_error
                rows.append({
                    "document_id": sample["document_id"], "page": sample["page"],
                    "character_error_rate": round(c_error / len(gold), 4),
                    "word_error_rate": round(w_error / len(gold.split()), 4),
                })
            except ValueError as exc:
                rows.append({"document_id": sample["document_id"], "page": sample["page"], "error": str(exc)})
        critical = []
        for doc_id, page, number in CRITICAL_PAGES:
            raw = ocr_page(doc_id, page, config)
            critical.append({
                "document_id": doc_id, "page": page,
                "expected_number": number,
                "exact_present": number in raw,
                "ocr_number_lines": [line.strip() for line in raw.splitlines() if "NĐ-CP" in line][:5],
            })
        result["configs"][name] = {
            "model_sha256": model_hash, "dpi": dpi,
            "excerpts": rows,
            "scored_excerpt_count": sum("error" not in row for row in rows),
            "pooled_character_error_rate": round(char_errors / char_count, 4) if char_count else None,
            "pooled_word_error_rate": round(word_errors / word_count, 4) if word_count else None,
            "critical_exact_count": sum(row["exact_present"] for row in critical),
            "critical_pages": critical,
        }
        print(f"{name}: WER={result['configs'][name]['pooled_word_error_rate']}, "
              f"critical IDs={result['configs'][name]['critical_exact_count']}/{len(critical)}", flush=True)
    path = OUT / "ocr_benchmark.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
