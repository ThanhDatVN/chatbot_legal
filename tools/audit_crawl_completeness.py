#!/usr/bin/env python3
"""Audit crawl coverage and PDF transport integrity across canonical shards."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import warnings
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        record["_artifact_root"] = path.parent.as_posix()
        record["_manifest"] = path.as_posix()
        record["_line_number"] = line_number
        records.append(record)
    return records


def choose_recovered_records(
    records: list[dict[str, Any]], record_type: str, identity_field: str
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("record_type") == record_type:
            grouped[str(record.get(identity_field, ""))].append(record)
    selected: dict[str, dict[str, Any]] = {}
    for identity, candidates in grouped.items():
        fetched = [item for item in candidates if item.get("fetch_status") == "fetched"]
        selected[identity] = (fetched or candidates)[-1]
    return selected


def expected_attachment_urls(page_records: dict[str, dict[str, Any]]) -> set[str]:
    return {
        str(link["url"])
        for page in page_records.values()
        if page.get("fetch_status") == "fetched"
        for link in page.get("attachment_links", [])
    }


def stored_file(record: dict[str, Any]) -> Path | None:
    stored = record.get("stored_path")
    if not stored:
        return None
    return Path(record["_artifact_root"]) / stored


def audit_transport(record: dict[str, Any], path: Path) -> list[str]:
    issues: list[str] = []
    if not path.exists():
        return ["stored_file_missing"]
    expected_length = record.get("content_length")
    if expected_length is not None and path.stat().st_size != int(expected_length):
        issues.append("content_length_mismatch")
    expected_hash = record.get("response_sha256")
    if expected_hash and sha256_file(path) != expected_hash:
        issues.append("sha256_mismatch")
    return issues


def audit_pdf(record: dict[str, Any], path: Path) -> dict[str, Any]:
    issues = audit_transport(record, path)
    page_count: int | None = None
    encrypted = False
    if path.exists():
        with path.open("rb") as stream:
            head = stream.read(5)
            stream.seek(max(0, path.stat().st_size - 8192))
            tail = stream.read()
        if head != b"%PDF-":
            issues.append("pdf_magic_missing")
        if b"%%EOF" not in tail:
            issues.append("pdf_eof_missing")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                reader = PdfReader(path, strict=False)
                encrypted = reader.is_encrypted
                if not encrypted:
                    page_count = len(reader.pages)
                    if page_count == 0:
                        issues.append("pdf_has_zero_pages")
        except Exception as exc:  # pypdf exposes several parser-specific exceptions
            issues.append(f"pdf_parse_error:{type(exc).__name__}")
    return {
        "document_id": record.get("document_id"),
        "instrument_number": record.get("instrument_number"),
        "requested_url": record.get("requested_url"),
        "stored_path": path.as_posix(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "page_count": page_count,
        "encrypted": encrypted,
        "issues": issues,
    }


def artifact_manifests(crawl_root: Path, shard_name: str) -> list[Path]:
    paths = [crawl_root / shard_name / "manifest.jsonl"]
    paths.extend(
        item / "manifest.jsonl"
        for item in sorted(crawl_root.glob(f"{shard_name}-resume*"))
        if item.is_dir()
    )
    return paths


def run(args: argparse.Namespace) -> int:
    shards_dir = Path(args.shards_dir)
    crawl_root = Path(args.crawl_root)
    all_pdf_results: list[dict[str, Any]] = []
    shard_results: list[dict[str, Any]] = []

    for number in range(args.start_shard, args.end_shard + 1):
        shard_name = f"shard-{number:04d}"
        config_path = shards_dir / f"{shard_name}.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        records = [
            record
            for manifest in artifact_manifests(crawl_root, shard_name)
            for record in read_manifest(manifest)
        ]
        pages = choose_recovered_records(records, "source_page", "document_id")
        attachments = choose_recovered_records(records, "official_attachment", "requested_url")
        configured_ids = {str(item["id"]) for item in config["documents"]}
        fetched_page_ids = {
            identity for identity, item in pages.items() if item.get("fetch_status") == "fetched"
        }
        expected_urls = expected_attachment_urls(pages)
        fetched_attachment_urls = {
            identity
            for identity, item in attachments.items()
            if item.get("fetch_status") == "fetched"
        }

        page_artifact_issues: list[dict[str, Any]] = []
        for document_id, page in pages.items():
            if page.get("fetch_status") != "fetched":
                continue
            html_paths = [
                Path(page["_artifact_root"]) / item
                for item in page.get("stored_paths", [])
                if "official-html" in item
            ]
            if not html_paths:
                page_artifact_issues.append(
                    {"document_id": document_id, "issues": ["official_html_path_missing"]}
                )
                continue
            issues = audit_transport(page, html_paths[0])
            if issues:
                page_artifact_issues.append({"document_id": document_id, "issues": issues})

        shard_pdf_results: list[dict[str, Any]] = []
        for url in sorted(fetched_attachment_urls):
            attachment = attachments[url]
            path = stored_file(attachment)
            if path is None:
                shard_pdf_results.append(
                    {
                        "document_id": attachment.get("document_id"),
                        "requested_url": url,
                        "stored_path": None,
                        "page_count": None,
                        "issues": ["stored_path_missing"],
                    }
                )
            else:
                shard_pdf_results.append(audit_pdf(attachment, path))
        all_pdf_results.extend(shard_pdf_results)
        shard_results.append(
            {
                "shard": shard_name,
                "configured_documents": len(configured_ids),
                "fetched_source_pages": len(fetched_page_ids & configured_ids),
                "missing_source_page_ids": sorted(configured_ids - fetched_page_ids),
                "unexpected_source_page_ids": sorted(fetched_page_ids - configured_ids),
                "expected_attachment_urls": len(expected_urls),
                "fetched_attachment_urls": len(fetched_attachment_urls & expected_urls),
                "missing_attachment_urls": sorted(expected_urls - fetched_attachment_urls),
                "unexpected_attachment_urls": sorted(fetched_attachment_urls - expected_urls),
                "page_artifact_issues": page_artifact_issues,
                "pdf_file_count": len(shard_pdf_results),
                "pdf_page_count": sum(item.get("page_count") or 0 for item in shard_pdf_results),
                "pdf_integrity_issue_count": sum(bool(item.get("issues")) for item in shard_pdf_results),
            }
        )

    pdf_issues = [item for item in all_pdf_results if item.get("issues")]
    output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": {
            "start_shard": args.start_shard,
            "end_shard": args.end_shard,
            "transport_completeness_only": True,
        },
        "limitations": [
            (
                "Hash/length/EOF/page-tree checks prove the downloaded response is internally complete; "
                "they cannot prove the publisher's scan omitted no physical page."
            ),
            (
                "Printed page-number sequence cannot be checked reliably for image-only PDFs without OCR "
                "and a document-boundary model."
            ),
            (
                "One Official Gazette PDF can contain several legal instruments, so PDF page count is not an "
                "instrument page count."
            ),
        ],
        "summary": {
            "shard_count": len(shard_results),
            "configured_documents": sum(item["configured_documents"] for item in shard_results),
            "fetched_source_pages": sum(item["fetched_source_pages"] for item in shard_results),
            "missing_source_pages": sum(len(item["missing_source_page_ids"]) for item in shard_results),
            "expected_attachment_urls": sum(item["expected_attachment_urls"] for item in shard_results),
            "fetched_attachment_urls": sum(item["fetched_attachment_urls"] for item in shard_results),
            "missing_attachment_urls": sum(len(item["missing_attachment_urls"]) for item in shard_results),
            "page_artifact_issue_count": sum(len(item["page_artifact_issues"]) for item in shard_results),
            "pdf_file_count": len(all_pdf_results),
            "pdf_page_count": sum(item.get("page_count") or 0 for item in all_pdf_results),
            "encrypted_pdf_count": sum(bool(item.get("encrypted")) for item in all_pdf_results),
            "pdf_integrity_issue_count": len(pdf_issues),
        },
        "shards": shard_results,
        "pdf_integrity_issues": pdf_issues,
    }
    Path(args.output).write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output["summary"], ensure_ascii=False))
    return 1 if any(
        (
            output["summary"]["missing_source_pages"],
            output["summary"]["missing_attachment_urls"],
            output["summary"]["page_artifact_issue_count"],
            output["summary"]["pdf_integrity_issue_count"],
        )
    ) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards-dir", required=True)
    parser.add_argument("--crawl-root", required=True)
    parser.add_argument("--start-shard", type=int, required=True)
    parser.add_argument("--end-shard", type=int, required=True)
    parser.add_argument("--output", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
