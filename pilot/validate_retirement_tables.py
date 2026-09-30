"""Check structure and a few rows read directly from the source page image."""

from __future__ import annotations

import json

from pilot.collect import OUT
from pilot.process_local import load_jsonl


def main() -> None:
    base = OUT / "candidate_retirement_tables_135"
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    rows = load_jsonl(base / "rows.jsonl")
    assert len(rows) == 354
    assert summary["schedule_rows"] == 350
    assert summary["threshold_rows"] == 4
    assert summary["issue_count"] == 0
    assert all(x["retirement_age_months"] is not None for x in rows)
    expected = [
        ("I", "male", 1, 1961, 60 * 12 + 3, 5, 2021),
        ("I", "female", 1, 1966, 55 * 12 + 4, 6, 2021),
        ("I", "male", 9, 1961, 60 * 12 + 3, 1, 2022),
        ("I", "female", 8, 1966, 55 * 12 + 4, 1, 2022),
    ]
    for appendix, gender, birth_month, birth_year, age, pension_month, pension_year in expected:
        matches = [x for x in rows if x["appendix"] == appendix and x["gender"] == gender and x["birth_month"] == birth_month and x["birth_year"] == birth_year]
        assert len(matches) == 1
        row = matches[0]
        assert (row["retirement_age_months"], row["pension_month"], row["pension_year"]) == (age, pension_month, pension_year)
    assert all(x["text_quality_status"] == "unreviewed" and x["currency_status"] == "unverified" for x in rows)
    print("PASS: 350 schedule rows, 4 thresholds, 4 source-image fixtures; candidate remains unreviewed")


if __name__ == "__main__":
    main()
