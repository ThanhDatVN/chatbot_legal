"""Build an isolated native-text candidate for 18/VBHN-VPQH from Công báo."""

from __future__ import annotations

import hashlib
import json

import pymupdf

from pilot.collect import OUT, make_chunks, write_jsonl
from pilot.process_local import load_jsonl
from pilot.structure_v2 import make_structured_sections


DOC_ID = "18_2026_vbhn_vpqh"


def main() -> None:
    audit = json.loads((OUT / "alternate_source_audit.json").read_text(encoding="utf-8"))
    if audit["printed_page_breaks"] or audit["missing_pdf_articles_1_to_220"]:
        raise RuntimeError("Alternate source fails continuity/heading audit")
    source = OUT / "raw_alternates" / f"{DOC_ID}_congbao.pdf"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != audit["pdf_sha256"]:
        raise RuntimeError("Alternate PDF hash changed")
    with pymupdf.open(source) as pdf:
        pages = [
            {"page": i + 1, "normalized_text": page.get_text("text", sort=True)}
            for i, page in enumerate(pdf)
        ]
    sections, warnings = make_structured_sections(pages, DOC_ID, strict_sequence=True)
    chunks = make_chunks(DOC_ID, digest + "|congbao-native-v1", sections)
    key_to_kind = {(s["section"], s["page_start"]): s["section_kind"] for s in sections}
    for chunk in chunks:
        chunk["section_kind"] = key_to_kind[(chunk["section"], chunk["section_page_start"])]
        chunk["text_quality_status"] = "unreviewed"
        chunk["currency_status"] = "unverified"
        chunk["candidate_source_url"] = audit["source_url"]
        chunk["candidate_pdf_sha256"] = digest
        chunk["page_numbering"] = "PDF page; printed Công báo page differs"
    candidate = OUT / "candidate_congbao_18"
    write_jsonl(candidate / "pages.jsonl", pages)
    write_jsonl(candidate / "sections.jsonl", sections)
    write_jsonl(candidate / "chunks.jsonl", chunks)
    write_jsonl(candidate / "warnings.jsonl", warnings)
    summary = {
        "source_url": audit["source_url"],
        "source_pdf_sha256": digest,
        "page_count": len(pages),
        "native_word_count": sum(len(page["normalized_text"].split()) for page in pages),
        "article_section_count": sum(s["section_kind"] == "main_text" for s in sections),
        "chunk_count": len(chunks),
        "warning_count": len(warnings),
        "warnings": warnings,
        "status": "candidate_only_not_released",
    }
    (OUT / "candidate_congbao_18_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
