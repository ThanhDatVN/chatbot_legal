"""Build the real snapshot from the official PDFs and check the facts we verified on page images."""

import json
from pathlib import Path

import pytest

from ingestion.build import ROOT, build
from ingestion.models import Registry

REGISTRY = ROOT / "data" / "corpus" / "registry.json"


def _sources_present() -> bool:
    reg = Registry.model_validate_json(REGISTRY.read_text(encoding="utf-8"))
    return all((ROOT / p.path).exists() for d in reg.documents for p in d.source_parts)


pytestmark = pytest.mark.skipif(not _sources_present(), reason="source PDFs not downloaded")


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    out = tmp_path_factory.mktemp("snapshots")
    code = build(REGISTRY, "test-snapshot", out, ROOT / "data" / "review",
                 ROOT / "data" / "corpus" / "regression_fixtures.json")
    base = out / "test-snapshot"
    chunks = [json.loads(line) for line in (base / "chunks.jsonl").open(encoding="utf-8")]
    report = json.loads((base / "quality_report.json").read_text(encoding="utf-8"))
    return code, chunks, report


def test_all_quality_gates_pass(snapshot):
    code, _, report = snapshot
    failed = {d["document_id"]: [k for k, v in d["hard"].items() if not v] for d in report["documents"] if not d["passed"]}
    assert code == 0 and report["passed"], failed


def test_no_gazette_artifacts_in_any_chunk(snapshot):
    _, chunks, _ = snapshot
    for c in chunks:
        assert "CÔNG BÁO/Số" not in c["text"]
        assert "Ký bởi:" not in c["text"] and "Người ký:" not in c["text"]
        assert "iếp theo Công báo số" not in c["text"]


def test_consolidated_footnotes_become_notes_on_the_right_article(snapshot):
    _, chunks, _ = snapshot
    art62 = next(c for c in chunks if c["document_id"] == "18_2026_vbhn_vpqh" and c["section_label"] == "Điều 62")
    assert "Khoản này được sửa đổi" not in art62["text"]
    art61 = next(c for c in chunks if c["document_id"] == "18_2026_vbhn_vpqh" and c["section_label"] == "Điều 61")
    assert [n["target_label"] for n in art61["amendment_notes"]] == ["Điều 61 khoản 3"]
    art139 = next(c for c in chunks if c["document_id"] == "18_2026_vbhn_vpqh" and c["section_label"] == "Điều 139")
    assert art139["text"].startswith("Điều 139. Nghỉ thai sản\n1. Lao động nữ")


def test_currency_policy(snapshot):
    _, chunks, _ = snapshot
    by_doc = {}
    for c in chunks:
        by_doc.setdefault(c["document_id"], set()).add(c["currency_status"])
    assert by_doc["18_2026_vbhn_vpqh"] == {"consolidated_current"}
    assert by_doc["45_2019_qh14"] == {"superseded_by_consolidation"}
    assert by_doc["74_2024_nd_cp"] == {"historical"}
    assert by_doc["293_2025_nd_cp"] == {"presumed_current"}
    assert "verified_current" not in set().union(*by_doc.values())  # needs a human reviewer


def test_wage_table_is_labelled(snapshot):
    _, chunks, _ = snapshot
    art3 = next(c for c in chunks if c["document_id"] == "293_2025_nd_cp" and c["section_label"] == "Điều 3")
    assert "Vùng: Vùng I; Mức lương tối thiểu tháng (Đơn vị: đồng/tháng): 5.310.000" in art3["text"]
    assert art3["contains_table"]
