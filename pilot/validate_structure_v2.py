"""Validate losslessness and confirmed structural regressions in the pilot."""

from __future__ import annotations

from pilot.collect import OUT
from pilot.process_local import load_jsonl


EXPECTED_ANNEX_START = {
    "145_2020_nd_cp": 90,
    "135_2020_nd_cp": 7,
    "152_2020_nd_cp": 27,
    "70_2023_nd_cp": 10,
    "293_2025_nd_cp": 5,
    "74_2024_nd_cp": 5,
    "38_2022_nd_cp": 5,
}


def main() -> None:
    manifest = load_jsonl(OUT / "manifest.jsonl")
    total_chunks = 0
    for document in manifest:
        doc_id = document["document_id"]
        sections = load_jsonl(OUT / "structured_sections_v2" / f"{doc_id}.jsonl")
        chunks = load_jsonl(OUT / "structured_chunks_v2" / f"{doc_id}.jsonl")
        assert sum(section["word_count"] for section in sections) == document["ocr_word_count"], doc_id
        assert all(chunk["text_quality_status"] == "unreviewed" for chunk in chunks), doc_id
        assert all(chunk["currency_status"] == "unverified" for chunk in chunks), doc_id
        assert all(chunk["page_start"] <= chunk["page_end"] for chunk in chunks), doc_id
        main = [s for s in sections if s["section_kind"] == "main_text"]
        assert len({s["section"] for s in main}) == len(main), doc_id
        annex = [s for s in sections if s["section_kind"] == "annex"]
        expected = EXPECTED_ANNEX_START.get(doc_id)
        assert (annex[0]["page_start"] if annex else None) == expected, doc_id
        total_chunks += len(chunks)
    law = load_jsonl(OUT / "structured_sections_v2" / "45_2019_qh14.jsonl")
    assert any(s["section"] == "Điều 219" and s["contains_quoted_amendment"] for s in law)
    assert sum(s["section"] == "Điều 55" for s in law) == 1
    print(f"Validated {len(manifest)} documents, {total_chunks} unreviewed structured chunks, "
          f"{len(EXPECTED_ANNEX_START)} confirmed annex boundaries")


if __name__ == "__main__":
    main()
