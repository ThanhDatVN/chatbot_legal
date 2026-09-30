"""Validate the isolated Công báo candidate without promoting it to current QA."""

from __future__ import annotations

import hashlib

from pilot.collect import OUT
from pilot.process_local import load_jsonl


def main() -> None:
    base = OUT / "candidate_congbao_all"
    manifest = load_jsonl(base / "manifest.jsonl")
    assert len(manifest) == 10
    assert len({x["document_id"] for x in manifest}) == 10
    seen_chunk_ids = set()
    for document in manifest:
        doc_id = document["document_id"]
        pages = load_jsonl(base / "pages" / f"{doc_id}.jsonl")
        sections = load_jsonl(base / "sections" / f"{doc_id}.jsonl")
        chunks = load_jsonl(base / "chunks" / f"{doc_id}.jsonl")
        assert len(pages) == document["pages"]
        assert [x["page"] for x in pages] == list(range(1, len(pages) + 1))
        assert sum(len(x["normalized_text"].split()) for x in pages) == document["native_words"]
        assert sum(x["word_count"] for x in sections) == document["native_words"]
        assert len(chunks) == document["chunks"]
        assert all(x["exact_full_passage"] for x in document["hand_reference_checks"])
        for part in document["source_parts"]:
            assert hashlib.sha256(open(part["path"], "rb").read()).hexdigest() == part["sha256"]
        for page in pages:
            part = document["source_parts"][page["source_part"] - 1]
            assert 1 <= page["source_part_page"] <= part["pages"]
            assert page["source_pdf_sha256"] == part["sha256"]
        for chunk in chunks:
            assert chunk["chunk_id"] not in seen_chunk_ids
            seen_chunk_ids.add(chunk["chunk_id"])
            assert chunk["document_id"] == doc_id
            assert chunk["text_quality_status"] == "unreviewed"
            assert chunk["currency_status"] == "unverified"
            assert chunk["candidate_sha256"] == document["candidate_sha256"]
            assert 1 <= chunk["page_start"] <= chunk["page_end"] <= len(pages)
            assert chunk["section_kind"] in {"preamble", "main_text", "annex"}
    print(f"PASS: {len(manifest)} official candidate documents, {sum(x['pages'] for x in manifest)} pages, {len(seen_chunk_ids)} quarantined chunks")


if __name__ == "__main__":
    main()
