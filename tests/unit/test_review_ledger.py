"""Ledger review round trip: export a checklist, import decisions, only agreed entries are marked reviewed."""

import csv
import importlib.util
import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("review_ledger", ROOT / "scripts" / "review_ledger.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def test_export_and_import_marks_only_agreed_entries(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.json"
    shutil.copy(ROOT / "data" / "corpus" / "currency_ledger.json", ledger)
    monkeypatch.setattr(review, "LEDGER", ledger)
    monkeypatch.setattr(review, "ROOT", tmp_path)
    out = tmp_path / "review.csv"
    assert review.export(out) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    original = json.loads(ledger.read_text(encoding="utf-8"))
    assert len(rows) == len(original["entries"]) and rows[0]["evidence_quote"]
    rows[0]["decision"], rows[1]["decision"], rows[1]["note"] = "agree", "disagree", "sai khoản"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=review.FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    assert review.import_(out, "Nguyễn Văn A, luật sư", date(2026, 10, 2)) == 0
    after = {e["entry_id"]: e for e in json.loads(ledger.read_text(encoding="utf-8"))["entries"]}
    assert after[rows[0]["entry_id"]]["reviewed_by"] == "Nguyễn Văn A, luật sư"
    assert after[rows[0]["entry_id"]]["reviewed_at"] == "2026-10-02"
    assert after[rows[1]["entry_id"]].get("reviewed_by") is None  # disagreement is reported, not recorded
    before = {e["entry_id"]: e for e in original["entries"]}
    assert after[rows[0]["entry_id"]]["evidence_quote"] == before[rows[0]["entry_id"]]["evidence_quote"]
