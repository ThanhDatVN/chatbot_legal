#!/usr/bin/env python3
"""Inventory missing legal-document types from the official e-Gazette."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

BASE_URL = "https://congbao.chinhphu.vn"
KINDS = {
    "resolution": ("nghi-quyet-l6", "resolution", "Nghị quyết"),
    "consolidated": ("van-ban-hop-nhat-l7", "consolidated", "Văn bản hợp nhất"),
}
DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)")
TOTAL_PAGE_RE = re.compile(r"var\s+totalPageSodo\s*=\s*(\d+)")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value: str) -> str | None:
    match = DATE_RE.search(value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


class GazetteListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.documents: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.item_depth = 0
        self.capture: str | None = None
        self.capture_depth = 0
        self.capture_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.casefold(): value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        if tag == "div" and "item--vb" in classes:
            self.current = {
                "source_item_id": attributes.get("data-id"),
                "attachment_urls": [],
                "text_parts": [],
            }
            self.item_depth = 1
            return
        if self.current is None:
            return
        if tag == "div":
            self.item_depth += 1
        if tag == "span" and "kh" in classes:
            self.capture = "instrument_number"
            self.capture_depth = 1
            self.capture_parts = []
        elif self.capture and tag == "span":
            self.capture_depth += 1
        if tag == "a":
            href = attributes.get("href")
            if "sapo" in classes and href:
                self.current["detail_url"] = urllib.parse.urljoin(BASE_URL, href)
                self.current["title"] = normalize_space(attributes.get("title", ""))
            data_file = urllib.parse.unquote(attributes.get("data-file", ""))
            href_folded = href.casefold() if href else ""
            is_pdf = data_file.casefold().endswith(".pdf") or (
                "file_name=" in href_folded and ".pdf" in href_folded
            )
            if href and is_pdf:
                self.current["attachment_urls"].append(href.replace("&amp;", "&"))

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        cleaned = normalize_space(data)
        if cleaned:
            self.current["text_parts"].append(cleaned)
            if self.capture:
                self.capture_parts.append(cleaned)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if self.capture and tag == "span":
            self.capture_depth -= 1
            if self.capture_depth == 0:
                value = normalize_space(" ".join(self.capture_parts))
                self.current[self.capture] = re.sub(r"^Ký\s+hiệu:\s*", "", value, flags=re.I)
                self.capture = None
                self.capture_parts = []
        if tag == "div":
            self.item_depth -= 1
            if self.item_depth == 0:
                text = normalize_space(" ".join(self.current.pop("text_parts")))
                promulgation = re.search(r"\[Ban\s+hành:\s*([^\]]+)\]", text, re.I)
                effective = re.search(r"\[Hiệu\s+lực:\s*([^\]]+)\]", text, re.I)
                self.current["promulgation_date"] = parse_date(
                    promulgation.group(1) if promulgation else ""
                )
                self.current["effective_date"] = parse_date(
                    effective.group(1) if effective else ""
                )
                self.current["attachment_urls"] = list(
                    dict.fromkeys(self.current["attachment_urls"])
                )
                if self.current.get("instrument_number") and self.current.get("detail_url"):
                    self.documents.append(self.current)
                self.current = None


@dataclass
class GazetteClient:
    user_agent: str
    delay_seconds: float
    timeout_seconds: int
    max_bytes: int
    max_attempts: int = 4

    def __post_init__(self) -> None:
        self.last_request = 0.0

    def fetch(self, url: str) -> tuple[bytes, dict[str, str]]:
        for attempt in range(1, self.max_attempts + 1):
            remaining = self.delay_seconds - (time.monotonic() - self.last_request)
            if remaining > 0:
                time.sleep(remaining)
            self.last_request = time.monotonic()
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml;q=0.9",
                    "Accept-Language": "vi,en;q=0.7",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    if urllib.parse.urlsplit(response.geturl()).hostname != "congbao.chinhphu.vn":
                        raise ValueError(f"Unexpected redirect host: {response.geturl()}")
                    body = response.read(self.max_bytes + 1)
                    if len(body) > self.max_bytes:
                        raise ValueError(f"Listing response exceeds {self.max_bytes} bytes")
                    return body, {key.casefold(): value for key, value in response.headers.items()}
            except urllib.error.HTTPError as exc:
                if not (exc.code == 429 or 500 <= exc.code <= 504) or attempt == self.max_attempts:
                    raise
                time.sleep(min(2**attempt, 30))
        raise RuntimeError("Unreachable retry state")


def decode_html(body: bytes, headers: dict[str, str]) -> str:
    match = re.search(r"charset=([^;\s]+)", headers.get("content-type", ""), re.I)
    return body.decode(match.group(1).strip("\"'") if match else "utf-8", errors="replace")


def listing_url(slug: str, page_number: int) -> str:
    if page_number == 1:
        return f"{BASE_URL}/van-ban-dang-cong-bao/{slug}.htm"
    return f"{BASE_URL}/van-ban-dang-cong-bao/{slug}/trang-{page_number}.htm"


def run(args: argparse.Namespace) -> int:
    slug, type_group, type_label = KINDS[args.kind]
    cutoff = date.fromisoformat(args.cutoff)
    output = Path(args.output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    raw_dir = output / "raw-listing-pages"
    raw_dir.mkdir(parents=True, exist_ok=True)

    first_url = listing_url(slug, 1)
    robots = urllib.robotparser.RobotFileParser(f"{BASE_URL}/robots.txt")
    robots.read()
    if not robots.can_fetch(args.user_agent, first_url):
        raise PermissionError("robots.txt disallows the Gazette listing URL")

    client = GazetteClient(args.user_agent, args.delay, args.timeout, args.max_bytes)
    documents: list[dict[str, Any]] = []
    page_records: list[dict[str, Any]] = []
    stopped_on_cutoff = False
    reported_pages: int | None = None
    for page_number in range(1, args.max_pages + 1):
        url = listing_url(slug, page_number)
        body, headers = client.fetch(url)
        decoded = decode_html(body, headers)
        if reported_pages is None and (match := TOTAL_PAGE_RE.search(decoded)):
            reported_pages = int(match.group(1))
        parser = GazetteListingParser()
        parser.feed(decoded)
        if not parser.documents:
            raise ValueError(f"No document cards parsed on page {page_number}")
        raw_path = raw_dir / f"page-{page_number:03d}.html"
        raw_path.write_bytes(body)
        dated = [item for item in parser.documents if item["promulgation_date"]]
        included = [
            item
            for item in dated
            if date.fromisoformat(item["promulgation_date"]) >= cutoff
        ]
        for item in included:
            item.update(
                {
                    "promulgation_date_display": item["promulgation_date"],
                    "listing_page": page_number,
                    "title_relevance_class": "requires_fulltext_tax_screening",
                }
            )
        documents.extend(included)
        page_records.append(
            {
                "page_number": page_number,
                "row_count": len(parser.documents),
                "included_count": len(included),
                "sha256": hashlib.sha256(body).hexdigest(),
                "stored_path": raw_path.relative_to(output).as_posix(),
            }
        )
        if dated and all(date.fromisoformat(item["promulgation_date"]) < cutoff for item in dated):
            stopped_on_cutoff = True
            break
        if reported_pages is not None and page_number >= reported_pages:
            break

    deduplicated = {item["source_item_id"]: item for item in documents}
    ordered = sorted(
        deduplicated.values(),
        key=lambda item: (item["promulgation_date"], item["source_item_id"]),
        reverse=True,
    )
    payload = {
        "schema_version": "1.0",
        "source_url": first_url,
        "source_role": "authoritative_government_gazette",
        "type_group": type_group,
        "type_label": type_label,
        "cutoff_inclusive": cutoff.isoformat(),
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "portal_reported_total_pages_all_dates": reported_pages,
        "pages_fetched": len(page_records),
        "stopped_on_cutoff": stopped_on_cutoff,
        "document_count_in_window": len(ordered),
        "page_records": page_records,
        "documents": ordered,
    }
    (output / "inventory.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.as_posix(),
                "pages_fetched": len(page_records),
                "documents": len(ordered),
                "stopped_on_cutoff": stopped_on_cutoff,
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(KINDS), required=True)
    parser.add_argument("--cutoff", default="2016-08-11")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pages", type=int, default=300)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--max-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument(
        "--user-agent",
        default="TaxLegalWorkspaceGazetteInventory/0.1 (official Government Gazette)",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
