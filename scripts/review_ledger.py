"""Human review of the currency ledger: export a checklist, then record the reviewer's decisions.

    python scripts/review_ledger.py export                      # dist/review/ledger_review.csv (opens in Excel)
    python scripts/review_ledger.py import dist/review/ledger_review.csv --reviewer "Họ tên, chức danh"

The CSV has one row per ledger entry with the target provision, the change, the amending provision, its
verbatim quote and a link to the official source. The reviewer fills `decision` with `agree` or `disagree` and
may add `note`. Import writes reviewed_by / reviewed_at for agreed entries only, never edits an entry's
content, and lists the disagreements so the entry can be corrected and re-checked by the build.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "corpus" / "currency_ledger.json"
FIELDS = ["entry_id", "target_document_id", "target", "change", "source", "source_provision", "effective_from",
          "effective_until", "evidence_quote", "source_url", "reviewed_by", "decision", "note"]


def export(out: Path) -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    urls = {s["document_number"]: s["source_url"] for s in ledger["sources"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:  # BOM so Excel reads Vietnamese correctly
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for e in ledger["entries"]:
            target = ", ".join(e["sections"]) + (f" (khoản {', '.join(e['clauses'])})" if e["clauses"] else "")
            writer.writerow({"entry_id": e["entry_id"], "target_document_id": e["target_document_id"],
                             "target": target, "change": e["change"], "source": e["source"],
                             "source_provision": e["source_provision"], "effective_from": e["effective_from"],
                             "effective_until": e.get("effective_until") or "", "evidence_quote": e["evidence_quote"],
                             "source_url": urls.get(e["source"], ""), "reviewed_by": e.get("reviewed_by") or "",
                             "decision": "", "note": ""})
    print(f"wrote {out.relative_to(ROOT)} ({len(ledger['entries'])} entries)")
    return 0


def import_(path: Path, reviewer: str, on: date) -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    by_id = {e["entry_id"]: e for e in ledger["entries"]}
    agreed, disagreed, skipped = [], [], []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            decision = (row.get("decision") or "").strip().lower()
            entry = by_id.get(row["entry_id"])
            if entry is None:
                print(f"unknown entry {row['entry_id']!r}; skipped")
                continue
            if decision == "agree":
                entry["reviewed_by"], entry["reviewed_at"] = reviewer, on.isoformat()
                agreed.append(entry["entry_id"])
            elif decision == "disagree":
                disagreed.append((entry["entry_id"], (row.get("note") or "").strip()))
            else:
                skipped.append(entry["entry_id"])
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"agreed {len(agreed)}, disagreed {len(disagreed)}, not reviewed {len(skipped)}")
    for eid, note in disagreed:
        print(f"  DISAGREE {eid}: {note or '(no note)'}")
    if disagreed:
        print("Correct these entries in data/corpus/currency_ledger.json and rebuild under a new snapshot id.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--out", type=Path, default=ROOT / "dist" / "review" / "ledger_review.csv")
    im = sub.add_parser("import")
    im.add_argument("csv", type=Path)
    im.add_argument("--reviewer", required=True, help="name and role of the person who reviewed the entries")
    im.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    if args.cmd == "export":
        return export(args.out)
    return import_(args.csv, args.reviewer, args.date)


if __name__ == "__main__":
    sys.exit(main())
