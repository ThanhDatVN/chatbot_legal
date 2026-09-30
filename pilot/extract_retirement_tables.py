"""Recover merged-cell retirement schedules from Công báo 135/2020 annex tables.

This is a layout-aware candidate, not an approved legal data table.
"""

from __future__ import annotations

import json
import re

import pymupdf

from pilot.collect import OUT, write_jsonl


PDF = OUT / "raw_alternates" / "135_2020_nd_cp_congbao_part1.pdf"
APPENDIX_PAGES = {"I": range(7, 12), "II": range(12, 17)}


def parse_age(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d+)\s*tuổi(?:\s*(\d+)\s*tháng)?", value.replace("\n", " "))
    if not match:
        return None
    return int(match.group(1)) * 12 + int(match.group(2) or 0)


def main() -> None:
    records = []
    issues = []
    with pymupdf.open(PDF) as pdf:
        for appendix, page_numbers in APPENDIX_PAGES.items():
            last_age = {"male": None, "female": None}
            age_origin = {"male": None, "female": None}
            previous_birth = {"male": None, "female": None}
            for source_page in page_numbers:
                tables = pdf[source_page - 1].find_tables().tables
                if len(tables) != 1 or tables[0].col_count not in {5, 10}:
                    raise RuntimeError(f"Unexpected table geometry on PDF page {source_page}")
                table = tables[0]
                for row_number, cells in enumerate(table.extract(), start=1):
                    groups = {"male": cells[:5], "female": cells[5:]} if table.col_count == 10 else {"female": cells}
                    for gender, values in groups.items():
                        birth_month, birth_year, age, pension_month, pension_year = values
                        if not birth_month or not (birth_month.strip().isdigit() or birth_month.startswith("Từ tháng")):
                            continue
                        is_threshold = not birth_month.strip().isdigit()
                        if age and parse_age(age) is not None:
                            last_age[gender] = parse_age(age)
                            age_origin[gender] = {"pdf_page": source_page, "table_row": row_number}
                        if not is_threshold:
                            if not all(v and v.strip().isdigit() for v in (birth_month, birth_year, pension_month, pension_year)):
                                issues.append({"issue": "non_numeric_schedule_cell", "appendix": appendix, "pdf_page": source_page, "row": row_number, "gender": gender, "cells": values})
                                continue
                            birth_key = int(birth_year) * 12 + int(birth_month)
                            if previous_birth[gender] is not None and birth_key != previous_birth[gender] + 1:
                                issues.append({"issue": "birth_month_sequence_gap", "appendix": appendix, "pdf_page": source_page, "row": row_number, "gender": gender, "previous": previous_birth[gender], "observed": birth_key})
                            previous_birth[gender] = birth_key
                        if last_age[gender] is None:
                            issues.append({"issue": "missing_age_for_merged_cell", "appendix": appendix, "pdf_page": source_page, "row": row_number, "gender": gender})
                        records.append({
                            "document_id": "135_2020_nd_cp",
                            "appendix": appendix,
                            "gender": gender,
                            "row_kind": "threshold" if is_threshold else "schedule",
                            "source_pdf_page": source_page,
                            "source_table_row": row_number,
                            "birth_month": int(birth_month) if not is_threshold else None,
                            "birth_year": int(birth_year) if not is_threshold else None,
                            "birth_threshold_text": birth_month if is_threshold else None,
                            "retirement_age_months": last_age[gender],
                            "age_cell_source": age_origin[gender],
                            "age_filled_from_merged_cell": not bool(age and parse_age(age) is not None),
                            "pension_month": int(pension_month) if not is_threshold else None,
                            "pension_year": int(pension_year) if not is_threshold else None,
                            "pension_threshold_text": pension_month if is_threshold else None,
                            "raw_cells": values,
                            "text_quality_status": "unreviewed",
                            "currency_status": "unverified",
                        })
    target = OUT / "candidate_retirement_tables_135"
    write_jsonl(target / "rows.jsonl", records)
    inventory = json.loads((OUT / "congbao_candidate_inventory.json").read_text(encoding="utf-8"))
    source_item = next(item for item in inventory if item["document_id"] == "135_2020_nd_cp")
    summary = {
        "document_id": "135_2020_nd_cp",
        "source_pdf_sha256": source_item["files"][0]["sha256"],
        "schedule_rows": sum(x["row_kind"] == "schedule" for x in records),
        "threshold_rows": sum(x["row_kind"] == "threshold" for x in records),
        "merged_age_rows": sum(x["age_filled_from_merged_cell"] for x in records),
        "issue_count": len(issues),
        "issues": issues,
        "status": "layout_aware_candidate_unreviewed",
    }
    (target / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
