"""Diagnostic OCR of the number block on three problematic first pages."""

from __future__ import annotations

import json

import pymupdf

from pilot.collect import OUT


CASES = (
    ("145_2020_nd_cp", "145/2020/NĐ-CP", (105, 108, 255, 145)),
    ("135_2020_nd_cp", "135/2020/NĐ-CP", (105, 125, 255, 165)),
    ("152_2020_nd_cp", "152/2020/NĐ-CP", (105, 112, 255, 153)),
)


def main() -> None:
    rows = []
    for doc_id, expected, coordinates in CASES:
        with pymupdf.open(OUT / "raw" / f"{doc_id}.pdf") as source:
            page = source[0]
            # Source PDF coordinates. Includes generous white border around the ID.
            clip = pymupdf.Rect(*coordinates) & page.rect
            for model in ("tessdata", "tessdata_best"):
                for dpi in (300, 400):
                    pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
                    with pymupdf.open("png", pix.tobytes("png")) as ocr_doc:
                        image_page = ocr_doc[0]
                        textpage = image_page.get_textpage_ocr(
                            language="vie", dpi=dpi, full=True,
                            tessdata=str((OUT / model).resolve()),
                        )
                        text = image_page.get_text("text", textpage=textpage, sort=False)
                    rows.append({
                        "document_id": doc_id, "model": model, "dpi": dpi,
                        "expected_number": expected, "exact_present": expected in text,
                        "ocr_text": text.strip(),
                    })
                    print(f"{doc_id} {model} {dpi}: {expected in text} {text.strip()!r}", flush=True)
    path = OUT / "id_crop_benchmark.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
