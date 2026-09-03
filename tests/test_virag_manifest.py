"""Regression tests for manifest reading.

Defect D-02: the document's ``sha256`` was taken from the ``source_page``
record, so it identified the **portal HTML page** rather than the **signed PDF**
that is the authoritative artifact a citation must be traceable to.

Defect D-13: portal date fields carry non-date labels; their quality must be
recorded rather than inferred from truthiness.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from virag.ingest.manifest import _meta_from_record, load_manifest  # noqa: E402

PAGE_HASH = "a" * 64
PDF_HASH = "b" * 64
ANNEX_HASH = "c" * 64


def _write_manifest(tmp_path: Path, records: list[dict]) -> Path:
    root = tmp_path / "shard-0001"
    (root / "quarantine" / "official-attachments").mkdir(parents=True)
    (root / "quarantine" / "official-attachments" / "doc-1.pdf").write_bytes(b"%PDF-1.4")
    (root / "quarantine" / "official-attachments" / "doc-2.pdf").write_bytes(b"%PDF-1.4")
    manifest = root / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8"
    )
    return manifest


def _records() -> list[dict]:
    return [
        {
            "record_type": "source_page",
            "document_id": "DOC-1",
            "fetch_status": "fetched",
            "response_sha256": PAGE_HASH,
            "title": "Nghị định số 123/2020/NĐ-CP của Chính phủ: Quy định về hóa đơn",
            "metadata": {
                "instrument_number": "123/2020/NĐ-CP",
                "document_type": "Nghị định",
                "promulgation_date": "19-10-2020",
                "effective_date": "01-07-2022",
            },
        },
        {
            "record_type": "official_attachment",
            "document_id": "DOC-1",
            "fetch_status": "fetched",
            "response_sha256": PDF_HASH,
            "stored_path": "quarantine/official-attachments/doc-1.pdf",
        },
        {
            "record_type": "official_attachment",
            "document_id": "DOC-1",
            "fetch_status": "fetched",
            "response_sha256": ANNEX_HASH,
            "stored_path": "quarantine/official-attachments/doc-2.pdf",
        },
    ]


class TestArtifactHashBinding:
    def test_artifact_hash_is_the_signed_pdf_not_the_page(self, tmp_path: Path):
        docs = load_manifest(_write_manifest(tmp_path, _records()))
        assert len(docs) == 1
        meta = docs[0].meta
        assert meta.artifact_sha256 == PDF_HASH, "must bind the authoritative artifact"
        assert meta.sha256 == PAGE_HASH, "the page hash is kept as provenance"
        assert meta.artifact_sha256 != meta.sha256

    def test_first_attachment_wins_over_annexes(self, tmp_path: Path):
        docs = load_manifest(_write_manifest(tmp_path, _records()))
        assert docs[0].meta.artifact_sha256 != ANNEX_HASH

    def test_both_attachments_are_still_collected(self, tmp_path: Path):
        docs = load_manifest(_write_manifest(tmp_path, _records()))
        assert len(docs[0].attachment_paths) == 2


class TestDateQualityRecording:
    def test_valid_date_is_parsed_and_marked(self):
        meta = _meta_from_record(
            {"document_id": "X", "metadata": {"effective_date": "18-08-2026"}}
        )
        assert meta.effective_from == "2026-08-18"
        assert meta.effective_date_quality == "valid"

    def test_cong_bao_label_is_rejected_and_marked(self):
        """D-13: the label must not become a date, and must be reportable."""
        meta = _meta_from_record(
            {"document_id": "X", "metadata": {"effective_date": "Công báo"}}
        )
        assert meta.effective_from is None
        assert meta.effective_date_quality == "malformed"

    def test_absent_date_is_marked_absent(self):
        meta = _meta_from_record({"document_id": "X", "metadata": {}})
        assert meta.effective_from is None
        assert meta.effective_date_quality == "absent"

    def test_authority_tier_derived_from_instrument_number(self):
        meta = _meta_from_record(
            {
                "document_id": "X",
                "metadata": {
                    "instrument_number": "48/2024/QH15",
                    "document_type": "Luật",
                },
            }
        )
        assert meta.authority_tier == 2, "a Law must outrank a Circular"
