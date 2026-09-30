"""Structural and identifier checks for the 10 official Công báo candidates."""

from __future__ import annotations

import json
import re

import pymupdf

from pilot.collect import OUT
from pilot.process_local import load_jsonl
from pilot.structure_v2 import make_structured_sections


def main() -> None:
    inventory = json.loads((OUT / "congbao_candidate_inventory.json").read_text(encoding="utf-8"))
    manifest = {x["document_id"]: x for x in load_jsonl(OUT / "manifest.jsonl")}
    rows = []
    for item in inventory:
        doc_id = item["document_id"]
        pages = []
        excluded_blank_pages = []
        for part_index, part in enumerate(item["files"], start=1):
            with pymupdf.open(part["path"]) as pdf:
                for part_page, page in enumerate(pdf, start=1):
                    raw = page.get_text("text", sort=True)
                    if not raw.strip() and not page.get_images():
                        excluded_blank_pages.append({"source_part": part_index, "source_part_page": part_page})
                        continue
                    pages.append({"page": len(pages) + 1, "normalized_text": raw})
        if not pages:
            rows.append({"document_id": doc_id, "error": item.get("error", "no files")})
            continue
        full_text = "\n".join(x["normalized_text"] for x in pages)
        flexible_text = re.sub(r"\s*/\s*", "/", full_text)
        sections, warnings = make_structured_sections(pages, doc_id, strict_sequence=True)
        article_numbers = [
            int(re.search(r"\d+", x["section"]).group())
            for x in sections if x["section_kind"] == "main_text"
        ]
        row = {
            "document_id": doc_id,
            "document_number": manifest[doc_id]["document_number"],
            "file_count": len(item["files"]),
            "page_count": len(pages),
            "blank_pdf_pages_excluded": excluded_blank_pages,
            "native_word_count": sum(len(x["normalized_text"].split()) for x in pages),
            "exact_document_number_in_text": manifest[doc_id]["document_number"] in full_text,
            "space_tolerant_document_number_in_text": manifest[doc_id]["document_number"] in flexible_text,
            "article_section_count": len(article_numbers),
            "article_number_min": min(article_numbers) if article_numbers else None,
            "article_number_max": max(article_numbers) if article_numbers else None,
            "article_sequence_gaps": [
                {"previous": a, "next": b} for a, b in zip(article_numbers, article_numbers[1:])
                if b != a + 1
            ],
            "annex_page_count": sum(x["section_kind"] == "annex" for x in sections),
            "warning_count": len(warnings),
            "warnings": warnings[:20],
            "full_text_preserved": sum(x["word_count"] for x in sections) == sum(len(x["normalized_text"].split()) for x in pages),
            "status": "candidate_only_not_released",
        }
        rows.append(row)
        print(doc_id, row["page_count"], row["native_word_count"], row["article_section_count"], row["article_number_max"], len(row["article_sequence_gaps"]), row["exact_document_number_in_text"], flush=True)
    path = OUT / "congbao_candidate_audit.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
