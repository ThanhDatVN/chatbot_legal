#!/usr/bin/env python3
"""Merge official inventories and build auditable tax-screening queues."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DIRECT_TAX_RE = re.compile(r"(?:\bthuế\b|hóa\s+đơn|chứng\s+từ\s+điện\s+tử)", re.I)
FEE_RE = re.compile(
    r"(?:lệ\s+phí|phí\s+(?:bảo\s+vệ|sử\s+dụng|thẩm\s+định|khai\s+thác|hải\s+quan)|"
    r"(?:mức\s+thu|chế\s+độ\s+thu|miễn|giảm|quản\s+lý).{0,80}\bphí\b)",
    re.I,
)
CUSTOMS_RE = re.compile(
    r"(?:hải\s+quan|biểu.{0,40}(?:xuất\s+khẩu|nhập\s+khẩu)|"
    r"hàng\s+hóa.{0,40}(?:xuất\s+khẩu|nhập\s+khẩu))",
    re.I,
)
ADJACENT_RE = re.compile(
    r"(?:ngân\s+sách\s+nhà\s+nước|quản\s+lý\s+nợ\s+công|đất\s+đai|"
    r"đầu\s+tư|doanh\s+nghiệp|kế\s+toán|kiểm\s+toán)",
    re.I,
)
TYPE_LABELS = {
    "law_or_ordinance": "Luật - Pháp lệnh",
    "decree": "Nghị định",
    "decision": "Quyết định",
    "circular": "Thông tư",
    "resolution": "Nghị quyết",
    "consolidated": "Văn bản hợp nhất",
}
TYPE_GROUP_IDS = {3: "law_or_ordinance", 4: "decree", 5: "decision", 6: "circular"}


def source_doc_id(detail_url: str | None) -> str | None:
    if not detail_url:
        return None
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(detail_url).query).get("docid", [])
    return values[0] if values else None


def stable_document_key(type_group: str, document: dict[str, Any]) -> str:
    doc_id = source_doc_id(document.get("detail_url"))
    if doc_id:
        return f"GOV-{type_group.upper()}-{doc_id}"
    if document.get("source_item_id"):
        return f"GAZETTE-{type_group.upper()}-{document['source_item_id']}"
    identity = "|".join(
        [
            type_group,
            document.get("instrument_number") or "",
            document.get("promulgation_date") or "",
            document.get("title") or "",
        ]
    )
    return "GOV-FALLBACK-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20].upper()


def semantic_document_key(type_group: str, document: dict[str, Any]) -> str:
    identity = "|".join(
        [
            type_group,
            document.get("instrument_number") or "",
            document.get("promulgation_date") or "",
            document.get("title") or "",
        ]
    )
    return "LEGAL-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24].upper()


def classify_title(title: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if DIRECT_TAX_RE.search(title):
        reasons.append("direct_tax_or_invoice_term")
    if FEE_RE.search(title):
        reasons.append("fee_or_charge_term")
    if CUSTOMS_RE.search(title):
        reasons.append("customs_or_tariff_term")
    if reasons:
        return "priority_fulltext_fetch", reasons
    if ADJACENT_RE.search(title):
        return "adjacent_fulltext_screening", ["adjacent_legal_domain_term"]
    return "fulltext_screening_pending", ["no_high_precision_title_term"]


def load_inventory(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload, payload["documents"]


def inventory_type_group(payload: dict[str, Any]) -> str:
    if payload.get("type_group"):
        return payload["type_group"]
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(payload["source_url"]).query).get(
        "typegroupid", []
    )
    if not values or int(values[0]) not in TYPE_GROUP_IDS:
        raise ValueError(f"Cannot infer type group from {payload['source_url']}")
    return TYPE_GROUP_IDS[int(values[0])]


def is_pdf_attachment_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    if parsed.path.casefold().endswith(".pdf"):
        return True
    query = urllib.parse.unquote(parsed.query).casefold()
    return "file_name=" in query and ".pdf" in query


def build_crawl_config(documents: list[dict[str, Any]], pilot_id: str) -> dict[str, Any]:
    crawl_documents: list[dict[str, Any]] = []
    for item in documents:
        pdf_urls = [
            url
            for url in item.get("attachment_urls", [])
            if is_pdf_attachment_url(url)
        ]
        document = {
            "id": item["document_key"],
            "instrument_number": item["instrument_number"],
            "document_type_expected": item["document_type_label"],
            "title_short": item["title"],
            "promulgation_date_expected": item["promulgation_date"],
            "official_url": item["detail_url"],
            "selection_rationale": ", ".join(item["screening_reasons"]),
            "download_attachments": True,
            "relations": [],
        }
        if pdf_urls:
            document["official_attachment_urls"] = [
                {"url": url, "label": f"Tệp chính thức {item['instrument_number']}"}
                for url in pdf_urls
            ]
        crawl_documents.append(document)
    return {
        "pilot_id": pilot_id,
        "scope": (
            "Toàn bộ source record trong sáu nhóm văn bản chính thức của cửa sổ 10 năm; "
            "từ khóa tiêu đề chỉ xếp lịch, mọi record đều chờ sàng lọc toàn văn"
        ),
        "user_agent": "TaxLegalWorkspaceFullInventory/0.1 (official tax document screening)",
        "request_delay_seconds": 1.5,
        "timeout_seconds": 45,
        "max_redirects": 4,
        "max_html_bytes": 5 * 1024 * 1024,
        "max_attachment_bytes": 256 * 1024 * 1024,
        "max_attachments_per_document": 256,
        "sources": {
            "chinhphu": {
                "role": "authoritative",
                "robots_url": "https://chinhphu.vn/robots.txt",
                "allowed_hosts": [
                    "chinhphu.vn",
                    "vanban.chinhphu.vn",
                    "datafiles.chinhphu.vn",
                    "congbao.chinhphu.vn",
                    "congbaocdn.chinhphu.vn",
                    "g7.cdnchinhphu.vn",
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
        "documents": crawl_documents,
    }


def run(args: argparse.Namespace) -> int:
    merged: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for value in args.inventory:
        path = Path(value)
        payload, documents = load_inventory(path)
        type_group = inventory_type_group(payload)
        sources.append(
            {
                "path": path.as_posix(),
                "source_url": payload["source_url"],
                "type_group": type_group,
                "document_count": len(documents),
                "pages_fetched": payload["pages_fetched"],
                "stopped_on_cutoff": payload["stopped_on_cutoff"],
            }
        )
        for source in documents:
            item = dict(source)
            item["document_key"] = stable_document_key(type_group, item)
            if item["document_key"] in seen_keys:
                raise ValueError(f"Duplicate source identity: {item['document_key']}")
            seen_keys.add(item["document_key"])
            item["type_group"] = type_group
            item["semantic_document_key"] = semantic_document_key(type_group, item)
            item["document_type_label"] = TYPE_LABELS[type_group]
            item["source_docid"] = source_doc_id(item.get("detail_url"))
            item["screening_status"], item["screening_reasons"] = classify_title(item["title"])
            merged.append(item)

    merged.sort(
        key=lambda item: (item.get("promulgation_date") or "", item["document_key"]),
        reverse=True,
    )
    duplicate_numbers: dict[str, list[str]] = defaultdict(list)
    for item in merged:
        duplicate_numbers[item["instrument_number"]].append(item["document_key"])
    collisions = {
        number: keys for number, keys in duplicate_numbers.items() if len(keys) > 1
    }
    status_counts = Counter(item["screening_status"] for item in merged)
    type_counts = Counter(item["type_group"] for item in merged)
    semantic_counts = Counter(item["semantic_document_key"] for item in merged)
    semantic_duplicate_groups = {
        key: count for key, count in semantic_counts.items() if count > 1
    }
    priority = [item for item in merged if item["screening_status"] == "priority_fulltext_fetch"]
    payload = {
        "schema_version": "1.0",
        "scope_status": "metadata_complete_fulltext_screening_in_progress",
        "completeness_rule": (
            "No record may be excluded solely because its title lacks a tax keyword; "
            "all non-priority records remain in a full-text screening queue."
        ),
        "sources": sources,
        "source_record_count": len(merged),
        "semantic_document_count": len(semantic_counts),
        "semantic_duplicate_group_count": len(semantic_duplicate_groups),
        "semantic_duplicate_groups": semantic_duplicate_groups,
        "type_counts": dict(type_counts),
        "screening_status_counts": dict(status_counts),
        "instrument_number_collision_count": len(collisions),
        "instrument_number_collisions": collisions,
        "documents": merged,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    queue_path = Path(args.queue_output)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in merged:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    crawl_config = build_crawl_config(priority, args.pilot_id)
    config_path = Path(args.crawl_config_output)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(crawl_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.all_crawl_config_output:
        all_crawl_config = build_crawl_config(merged, args.all_pilot_id)
        all_config_path = Path(args.all_crawl_config_output)
        all_config_path.parent.mkdir(parents=True, exist_ok=True)
        all_config_path.write_text(
            json.dumps(all_crawl_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "source_records": len(merged),
                "semantic_documents": len(semantic_counts),
                "priority_fulltext_fetch": len(priority),
                "screening_status_counts": dict(status_counts),
                "instrument_number_collisions": len(collisions),
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--queue-output", required=True)
    parser.add_argument("--crawl-config-output", required=True)
    parser.add_argument("--all-crawl-config-output")
    parser.add_argument("--pilot-id", default="tax-document-priority-fulltext-2026-08-11")
    parser.add_argument("--all-pilot-id", default="tax-document-all-fulltext-2026-08-11")
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
