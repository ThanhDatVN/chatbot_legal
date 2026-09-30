"""Render the same eight diagnostic source pages for another OCR engine."""

from __future__ import annotations

import pymupdf

from pilot.benchmark_ocr import CRITICAL_PAGES
from pilot.collect import OUT
from pilot.evaluate_data_quality import SAMPLES


def main() -> None:
    pairs = {(s["document_id"], s["page"]) for s in SAMPLES}
    pairs.update((doc_id, page) for doc_id, page, _ in CRITICAL_PAGES)
    folder = OUT / "qa" / "paddle_inputs"
    folder.mkdir(parents=True, exist_ok=True)
    for doc_id, page_number in sorted(pairs):
        path = folder / f"{doc_id}_p{page_number}.png"
        if path.exists():
            continue
        with pymupdf.open(OUT / "raw" / f"{doc_id}.pdf") as document:
            document[page_number - 1].get_pixmap(dpi=200).save(path)
        print(path, flush=True)
    print(f"Rendered {len(pairs)} distinct source pages at 200 DPI")


if __name__ == "__main__":
    main()
