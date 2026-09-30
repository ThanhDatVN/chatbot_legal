"""Integrity checks for the locally collected 10-document pilot."""

from __future__ import annotations

import hashlib
import json

from pilot.collect import OUT, assert_allowed_url


def records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    manifest = records(OUT / "manifest.jsonl")
    assert len(manifest) == 10, f"Expected 10 documents, found {len(manifest)}"
    chunk_ids = set()
    for item in manifest:
        doc_id = item["document_id"]
        assert_allowed_url(item["source_url"])
        assert_allowed_url(item["content_url"])
        html = (OUT / "raw" / f"{doc_id}.html").read_bytes()
        pdf = (OUT / "raw" / f"{doc_id}.pdf").read_bytes()
        assert pdf.startswith(b"%PDF-")
        assert hashlib.sha256(html).hexdigest() == item["html_sha256"]
        assert hashlib.sha256(pdf).hexdigest() == item["content_sha256"]
        assert item["native_status"] == "unsupported_scan"
        assert item["ocr_review_status"] == "unreviewed"
        assert len(records(OUT / "chunks" / f"{doc_id}.jsonl")) == 0
        ocr_pages = records(OUT / "ocr_pages" / f"{doc_id}.jsonl")
        assert len(ocr_pages) == item["pages"] == item["ocr_pages"]
        assert [page["page"] for page in ocr_pages] == list(range(1, item["pages"] + 1))
        chunks = records(OUT / "ocr_chunks" / f"{doc_id}.jsonl")
        assert len(chunks) == item["ocr_chunk_count"]
        for chunk in chunks:
            assert chunk["text"] and chunk["document_id"] == doc_id
            assert 1 <= chunk["page_start"] <= chunk["page_end"] <= item["pages"]
            assert chunk["chunk_id"] not in chunk_ids
            chunk_ids.add(chunk["chunk_id"])
    print(f"Validated {len(manifest)} documents, {sum(x['pages'] for x in manifest)} pages, {len(chunk_ids)} experimental OCR chunks")


if __name__ == "__main__":
    main()
