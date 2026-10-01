"""Build the real snapshot from the official PDFs and check the facts we verified on page images."""

import json
from pathlib import Path

import pytest

from ingestion.build import ROOT, build
from ingestion.ledger import load_ledger
from ingestion.models import Registry

REGISTRY = ROOT / "data" / "corpus" / "registry.json"


LEDGER = ROOT / "data" / "corpus" / "currency_ledger.json"


def _sources_present() -> bool:
    reg = Registry.model_validate_json(REGISTRY.read_text(encoding="utf-8"))
    ledger = load_ledger(LEDGER)
    paths = [p.path for d in reg.documents for p in d.source_parts] + [s.path for s in ledger.sources]
    return all((ROOT / p).exists() for p in paths)


pytestmark = pytest.mark.skipif(not _sources_present(), reason="source PDFs not downloaded")


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    out = tmp_path_factory.mktemp("snapshots")
    code = build(REGISTRY, "test-snapshot", out, ROOT / "data" / "review",
                 ROOT / "data" / "corpus" / "regression_fixtures.json", LEDGER)
    base = out / "test-snapshot"
    chunks = [json.loads(line) for line in (base / "chunks.jsonl").open(encoding="utf-8")]
    report = json.loads((base / "quality_report.json").read_text(encoding="utf-8"))
    return code, chunks, report


def test_all_quality_gates_pass(snapshot):
    code, _, report = snapshot
    failed = {d["document_id"]: [k for k, v in d["hard"].items() if not v] for d in report["documents"] if not d["passed"]}
    assert code == 0 and report["passed"], (failed, report["ledger_problems"])
    assert report["ledger_problems"] == []  # every ledger quote occurs in its official PDF


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


def _status(chunks, doc, section, needle=""):
    hits = [c for c in chunks if c["document_id"] == doc and c["section_label"] == section and needle in c["text"]]
    assert hits, (doc, section, needle)
    return {c["currency_status"] for c in hits}


def test_currency_ledger_is_applied_at_clause_level(snapshot):
    _, chunks, _ = snapshot
    # 158/2025 Điều 44(2)(c): only khoản 2 of 135/2020 Điều 3 expired, khoản 1 and 3 remain
    assert _status(chunks, "135_2020_nd_cp", "Điều 3", "1. Thời điểm nghỉ hưu") == {"presumed_current"}
    assert _status(chunks, "135_2020_nd_cp", "Điều 3", "2. Thời điểm hưởng") == {"superseded_by_amendment"}
    assert _status(chunks, "135_2020_nd_cp", "Phụ lục III") == {"superseded_by_amendment"}
    assert _status(chunks, "135_2020_nd_cp", "Điều 4") == {"presumed_current"}
    # 219/2025 Điều 35(2): foreign-worker content of 152/2020 expired; Chương III stays
    assert _status(chunks, "152_2020_nd_cp", "Điều 9") == {"superseded_by_amendment"}
    assert _status(chunks, "152_2020_nd_cp", "Điều 24") == {"presumed_current"}
    assert _status(chunks, "152_2020_nd_cp", "Điều 30") == {"unverified"}
    # temporary resolutions: outsourcing licences (66.18/2026) and labour-mediator authority (129/2025)
    assert _status(chunks, "145_2020_nd_cp", "Điều 21") == {"superseded_by_amendment"}
    assert _status(chunks, "145_2020_nd_cp", "Điều 95") == {"superseded_by_amendment"}
    assert _status(chunks, "145_2020_nd_cp", "Điều 4", "2. Định kỳ") == {"superseded_by_amendment"}
    assert _status(chunks, "145_2020_nd_cp", "Điều 3") == {"presumed_current"}
    assert _status(chunks, "219_2025_nd_cp", "Điều 27") == {"superseded_by_amendment"}
    assert _status(chunks, "219_2025_nd_cp", "Điều 7") == {"presumed_current"}
    amended = next(c for c in chunks if c["document_id"] == "152_2020_nd_cp" and c["section_label"] == "Điều 9")
    assert amended["currency_entries"] == ["152-219-35-ch2"]
    assert "Nghị định 219/2025/NĐ-CP" in amended["currency_basis"]
