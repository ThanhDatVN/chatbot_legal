#!/usr/bin/env python3
"""Build a crawl config for the tax-priority slice of the screening queue.

The full-text screening queue holds 13,058 records and only 819 have been
crawled (6.3%).  Crawling all of it is a multi-day job against government
servers; crawling the slice whose **title already carries a direct tax or
invoice term** is a few hundred documents and targets the v1 scope directly.

Prioritisation classes come from the queue itself, built by
``build_tax_document_inventory.py``:

    direct_tax_title                 807  <- this tool's default
    adjacent_legal_domain            829
    requires_fulltext_tax_screening  11422

**This is scheduling, not exclusion.** The corpus rule is that a title keyword
may only order the work; no record is dropped before full-text screening. The
remaining classes stay in the queue for later passes.

Documents already fetched are skipped, so re-running after a partial crawl
produces a config for exactly what is left.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Ordered by precision of the title signal.
PRIORITY_CLASSES = ("direct_tax_title", "adjacent_legal_domain", "requires_fulltext_tax_screening")

#: Keys that belong to a shard, not to a parent config.
SHARD_ONLY_KEYS = ("shard_number", "shard_start_index", "parent_pilot_id")


def load_crawled_ids(crawl_root: Path) -> set[str]:
    """Document ids already fetched, so a re-run only covers the remainder."""
    crawled: set[str] = set()
    for manifest in crawl_root.glob("**/manifest.jsonl"):
        with manifest.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    record.get("record_type") == "source_page"
                    and record.get("fetch_status") == "fetched"
                    and record.get("document_id")
                ):
                    crawled.add(record["document_id"])
    return crawled


def queue_to_document(record: dict[str, Any]) -> dict[str, Any]:
    """Map one queue record onto the crawler's document schema."""
    instrument = record.get("instrument_number")
    return {
        "id": record["document_key"],
        "instrument_number": instrument,
        "document_type_expected": record.get("document_type_label"),
        "title_short": record.get("title"),
        "promulgation_date_expected": record.get("promulgation_date"),
        "official_url": record["detail_url"],
        "selection_rationale": ",".join(record.get("screening_reasons") or [])
        or record.get("title_relevance_class", "unspecified"),
        "download_attachments": True,
        "relations": [],
        "official_attachment_urls": [
            {"url": url, "label": f"Tệp chính thức {instrument or record['document_key']}"}
            for url in (record.get("attachment_urls") or [])
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue",
        default=str(
            REPO_ROOT / "data" / "analysis" / "tax-document-fulltext-screening-queue-2026-08-11.jsonl"
        ),
    )
    parser.add_argument(
        "--template",
        default=str(REPO_ROOT / "config" / "tax-document-all-fulltext-shards-v4" / "shard-0001.json"),
        help="an existing shard config, used for source/limit settings",
    )
    parser.add_argument("--out", default=str(REPO_ROOT / "config" / "tax-priority-crawl.json"))
    parser.add_argument(
        "--classes",
        nargs="+",
        default=["direct_tax_title"],
        choices=list(PRIORITY_CLASSES),
    )
    parser.add_argument("--limit", type=int, default=None, help="cap the document count (smoke tests)")
    parser.add_argument(
        "--include-crawled",
        action="store_true",
        help="do not skip documents already fetched",
    )
    parser.add_argument("--pilot-id", default="tax-priority-2026-09-03")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    if not queue_path.exists():
        print(f"queue not found: {queue_path}", file=sys.stderr)
        return 2

    records = [
        json.loads(line)
        for line in queue_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    crawled = set() if args.include_crawled else load_crawled_ids(REPO_ROOT / "data" / "crawl")

    wanted = set(args.classes)
    selected = [
        record
        for record in records
        if record.get("title_relevance_class") in wanted
        and record.get("document_key") not in crawled
        and record.get("detail_url")
    ]
    # Keep the queue's own order: it is deterministic and audit-friendly.
    if args.limit is not None:
        selected = selected[: args.limit]

    if not selected:
        print("nothing to crawl - the selected classes are fully covered")
        return 1

    template = json.loads(Path(args.template).read_text(encoding="utf-8"))
    config = {key: value for key, value in template.items() if key not in SHARD_ONLY_KEYS}
    config["pilot_id"] = args.pilot_id
    config["scope"] = (
        "Tax-priority slice of the full-text screening queue: classes "
        + ", ".join(sorted(wanted))
        + ". Title terms schedule the work only; no record is excluded from the "
        "queue before full-text screening."
    )
    config["documents"] = [queue_to_document(record) for record in selected]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    attachments = sum(len(d["official_attachment_urls"]) for d in config["documents"])
    by_type: dict[str, int] = {}
    for document in config["documents"]:
        key = document.get("document_type_expected") or "?"
        by_type[key] = by_type.get(key, 0) + 1

    print(f"classes selected     : {', '.join(sorted(wanted))}")
    print(f"already crawled      : {len(crawled)} (skipped)")
    print(f"documents in config  : {len(config['documents'])}")
    print(f"attachment URLs      : {attachments}")
    print(f"by document type     : {by_type}")
    print(f"request delay        : {config.get('request_delay_seconds')}s")
    print(f"config -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
