#!/usr/bin/env python3
"""Build the controlled tax-law register and a crawler allowlist."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def stable_id(instrument_number: str) -> str:
    return "LAW-" + re.sub(r"[^A-Za-z0-9]+", "-", instrument_number).strip("-").upper()


def build_register(inventory: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    inventory_by_number = {item["instrument_number"]: item for item in inventory["documents"]}
    selected: list[dict[str, Any]] = []
    for declaration in scope["mandatory_in_window"]:
        number = declaration["instrument_number"]
        if number not in inventory_by_number:
            raise ValueError(f"Mandatory in-window instrument missing from inventory: {number}")
        source = inventory_by_number[number]
        if not source.get("detail_url"):
            raise ValueError(f"Mandatory instrument has no official detail URL: {number}")
        selected.append(
            {
                "id": stable_id(number),
                "instrument_number": number,
                "title": source["title"],
                "tier": declaration["tier"],
                "topics": declaration["topics"],
                "temporal_role": "in_window",
                "promulgation_date": source["promulgation_date"],
                "effective_date": None,
                "effective_date_status": "requires_content_extraction",
                "official_url": source["detail_url"],
                "official_attachment_urls": source.get("attachment_urls", []),
                "selection_evidence": "official_inventory_and_consolidation_chain",
                "review_status": "pending_human_review",
            }
        )

    for source in scope["historical_dependencies"]:
        selected.append(
            {
                "id": stable_id(source["instrument_number"]),
                "instrument_number": source["instrument_number"],
                "title": source["title"],
                "tier": source["tier"],
                "topics": source["topics"],
                "temporal_role": "historical_dependency",
                "promulgation_date": source["promulgation_date"],
                "effective_date": source.get("effective_date"),
                "effective_date_status": "declared_requires_content_confirmation",
                "official_url": source["official_url"],
                "official_attachment_urls": [],
                "known_source_discrepancy": source.get("known_source_discrepancy"),
                "selection_evidence": "official_consolidation_chain_or_transition_requirement",
                "review_status": "pending_human_review",
            }
        )

    number_counts = Counter(item["instrument_number"] for item in selected)
    duplicates = [number for number, count in number_counts.items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate instrument numbers in register: {duplicates}")
    tier_counts = Counter(item["tier"] for item in selected)
    role_counts = Counter(item["temporal_role"] for item in selected)
    selected_numbers = {
        item["instrument_number"]
        for item in selected
        if item["temporal_role"] == "in_window"
    }
    screening_queue = [
        {
            "instrument_number": item["instrument_number"],
            "promulgation_date": item["promulgation_date"],
            "title": item["title"],
            "detail_url": item["detail_url"],
            "screening_status": "requires_fulltext_tax_screening",
        }
        for item in inventory["documents"]
        if item["instrument_number"] not in selected_numbers
    ]
    return {
        "schema_version": "1.0",
        "as_of_date": scope["as_of_date"],
        "window_start": scope["window_start"],
        "scope_definition": scope["scope_definition"],
        "source_inventory": inventory["source_url"],
        "official_inventory_count_in_window": inventory["document_count_in_window"],
        "selected_count": len(selected),
        "selected_count_by_tier": dict(sorted(tier_counts.items())),
        "selected_count_by_temporal_role": dict(sorted(role_counts.items())),
        "fulltext_screening_queue_count": len(screening_queue),
        "chain_evidence_artifacts": scope["chain_evidence_artifacts"],
        "documents": selected,
        "fulltext_screening_queue": screening_queue,
    }


def build_crawl_config(register: dict[str, Any]) -> dict[str, Any]:
    documents = []
    for item in register["documents"]:
        attachments = [
            {"url": url, "label": f"Bản ký chính thức {item['instrument_number']}"}
            for url in item["official_attachment_urls"][:1]
            if url.casefold().endswith(".pdf")
        ]
        document = {
            "id": item["id"],
            "instrument_number": item["instrument_number"],
            "document_type_expected": "Luật",
            "title_short": item["title"],
            "topic": item["topics"],
            "coverage_class": "dependency_exception"
            if item["temporal_role"] == "historical_dependency"
            else "core_current",
            "selection_rationale": f"Tax-law register tier {item['tier']}",
            "promulgation_date_expected": item["promulgation_date"],
            "official_url": item["official_url"],
            "download_attachments": bool(attachments),
            "relations": [],
        }
        if item.get("effective_date"):
            document["effective_date_expected"] = item["effective_date"]
        if attachments:
            document["official_attachment_urls"] = attachments
        if item.get("known_source_discrepancy"):
            document["known_source_discrepancy"] = item["known_source_discrepancy"]
        documents.append(document)
    return {
        "pilot_id": f"tax-law-register-{register['as_of_date']}",
        "scope": (
            "Tier A/B/C tax-law register with historical dependencies and official signed PDFs "
            "where available"
        ),
        "user_agent": "TaxLegalWorkspacePilot/0.3 (controlled official tax-law register)",
        "request_delay_seconds": 1.5,
        "timeout_seconds": 30,
        "max_redirects": 4,
        "max_html_bytes": 8 * 1024 * 1024,
        "max_attachment_bytes": 40 * 1024 * 1024,
        "max_attachments_per_document": 1,
        "sources": {
            "chinhphu": {
                "role": "authoritative",
                "robots_url": "https://chinhphu.vn/robots.txt",
                "allowed_hosts": [
                    "chinhphu.vn",
                    "vanban.chinhphu.vn",
                    "datafiles.chinhphu.vn",
                ],
                "store_raw_html": True,
                "store_visible_text": True,
                "excerpt_chars": 2000,
                "attribution": "Nguồn: Cổng Thông tin điện tử Chính phủ",
            },
            "thuvienphapluat": {
                "role": "discovery_only",
                "allowed_hosts": ["thuvienphapluat.vn"],
                "store_raw_html": False,
                "store_visible_text": False,
                "excerpt_chars": 0,
            },
        },
        "documents": documents,
    }


def run(args: argparse.Namespace) -> int:
    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    scope = json.loads(Path(args.scope).read_text(encoding="utf-8"))
    register = build_register(inventory, scope)
    crawl_config = build_crawl_config(register)
    output = Path(args.output)
    crawl_output = Path(args.crawl_config_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    crawl_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(register, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    crawl_output.write_text(
        json.dumps(crawl_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "register": str(output),
                "crawl_config": str(crawl_output),
                "selected": register["selected_count"],
                "screening_queue": register["fulltext_screening_queue_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--crawl-config-output", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
