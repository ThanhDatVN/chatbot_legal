#!/usr/bin/env python3
"""Inventory a document-type group from the official Government portal.

The command snapshots each listing page, preserves response hashes, and stops
when it crosses the requested promulgation-date cutoff. Results are an inventory
for later full-text screening, not a claim that title keywords prove relevance.
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
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

PORTAL_URL_TEMPLATE = (
    "https://chinhphu.vn/he-thong-van-ban?classid=1&mode=1&typegroupid={type_group}"
)
PORTAL_HOST = "chinhphu.vn"
TYPE_GROUPS = {
    3: "law_or_ordinance",
    4: "decree",
    5: "decision",
    6: "circular",
}
GRID_EVENT_TARGET = "ctrl_191017_163$grvDocument"
DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)")
TOTAL_RE = re.compile(r"(?:tổng\s+số\s*:?)?\s*([\d.,]+)\s+văn\s+bản", re.IGNORECASE)
DIRECT_TAX_RE = re.compile(
    r"(?:\bthuế\b|hóa\s+đơn|chứng\s+từ\s+điện\s+tử|"
    r"(?<!kinh\s)\bphí\b|lệ\s+phí)",
    re.IGNORECASE,
)
ADJACENT_RE = re.compile(
    r"(?:hải\s+quan|ngân\s+sách\s+nhà\s+nước|quản\s+lý\s+nợ\s+công|"
    r"giá\s+chuyển\s+nhượng|doanh\s+nghiệp|đất\s+đai|đầu\s+tư)",
    re.IGNORECASE,
)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_date(value: str) -> str | None:
    match = DATE_RE.search(value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


class ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden: dict[str, str] = {}
        self.rows: list[dict[str, Any]] = []
        self.text_parts: list[str] = []
        self._row: dict[str, Any] | None = None
        self._field: str | None = None
        self._field_parts: list[str] = []
        self._in_grid = False
        self._grid_table_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag == "input" and attributes.get("type", "").lower() == "hidden":
            name = attributes.get("name")
            if name:
                self.hidden[name] = attributes.get("value", "")
        if tag == "table":
            if attributes.get("id") == "ctrl_191017_163_grvDocument":
                self._in_grid = True
                self._grid_table_depth = 1
            elif self._in_grid:
                self._grid_table_depth += 1
        if self._in_grid and tag == "tr":
            self._row = {"anchors": []}
        if self._row is None:
            return
        if tag == "span":
            classes = set(attributes.get("class", "").split())
            field = next((item for item in ("code", "issue-v2", "substract") if item in classes), None)
            if field:
                self._field = field
                self._field_parts = []
        elif tag == "a" and attributes.get("href"):
            self._row["anchors"].append(attributes["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._in_grid:
            self._grid_table_depth -= 1
            if self._grid_table_depth == 0:
                self._in_grid = False
            return
        if self._row is None:
            return
        if tag == "span" and self._field:
            self._row[self._field] = normalize_space(" ".join(self._field_parts))
            self._field = None
            self._field_parts = []
        elif tag == "tr":
            if self._row.get("code") and self._row.get("substract"):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        cleaned = normalize_space(data)
        if cleaned:
            self.text_parts.append(cleaned)
            if self._field:
                self._field_parts.append(cleaned)


@dataclass
class PortalClient:
    portal_url: str
    user_agent: str
    delay_seconds: float
    timeout_seconds: int
    max_bytes: int
    max_attempts: int = 4

    def __post_init__(self) -> None:
        cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        self.last_request = 0.0

    def _wait(self) -> None:
        remaining = self.delay_seconds - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)
        self.last_request = time.monotonic()

    def fetch(self, data: bytes | None = None) -> tuple[bytes, dict[str, str]]:
        for attempt in range(1, self.max_attempts + 1):
            self._wait()
            request = urllib.request.Request(
                self.portal_url,
                data=data,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml;q=0.9",
                    "Accept-Language": "vi,en;q=0.7",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST" if data is not None else "GET",
            )
            try:
                with self.opener.open(request, timeout=self.timeout_seconds) as response:
                    if urllib.parse.urlsplit(response.geturl()).hostname != PORTAL_HOST:
                        raise ValueError(f"Unexpected redirect host: {response.geturl()}")
                    body = response.read(self.max_bytes + 1)
                    if len(body) > self.max_bytes:
                        raise ValueError(f"Listing response exceeds {self.max_bytes} bytes")
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    return body, headers
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code <= 504
                if not retryable or attempt == self.max_attempts:
                    raise
                retry_after = exc.headers.get("Retry-After")
                wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(min(wait_seconds, 30.0))
        raise RuntimeError("Unreachable retry state")


def decode_html(body: bytes, headers: dict[str, str]) -> str:
    match = re.search(r"charset=([^;\s]+)", headers.get("content-type", ""), re.I)
    encoding = match.group(1).strip("\"'") if match else "utf-8"
    return body.decode(encoding, errors="replace")


def parse_listing(body: bytes, headers: dict[str, str]) -> tuple[ListingParser, str]:
    decoded = decode_html(body, headers)
    parser = ListingParser()
    parser.feed(decoded)
    return parser, decoded


def absolute_url(href: str, portal_url: str = PORTAL_URL_TEMPLATE.format(type_group=3)) -> str:
    url = urllib.parse.urljoin(portal_url, href)
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "chinhphu.vn",
        "vanban.chinhphu.vn",
        "datafiles.chinhphu.vn",
        "congbaocdn.chinhphu.vn",
    }:
        raise ValueError(f"Unexpected listing link: {url}")
    return url


def normalize_row(
    row: dict[str, Any], page_number: int, portal_url: str = PORTAL_URL_TEMPLATE.format(type_group=3)
) -> dict[str, Any]:
    anchors = []
    for href in row.get("anchors", []):
        try:
            anchors.append(absolute_url(href, portal_url))
        except ValueError:
            continue
    detail = next((url for url in anchors if "docid=" in url.casefold()), None)
    attachments = [url for url in anchors if url.casefold().endswith((".pdf", ".doc", ".docx"))]
    title = row.get("substract", "")
    if DIRECT_TAX_RE.search(title):
        relevance = "direct_tax_title"
    elif ADJACENT_RE.search(title):
        relevance = "adjacent_legal_domain"
    else:
        relevance = "requires_fulltext_tax_screening"
    return {
        "instrument_number": row.get("code"),
        "promulgation_date": parse_date(row.get("issue-v2", "")),
        "promulgation_date_display": row.get("issue-v2"),
        "title": title,
        "detail_url": detail,
        "attachment_urls": attachments,
        "listing_page": page_number,
        "title_relevance_class": relevance,
    }


def postback_data(hidden: dict[str, str], page_number: int) -> bytes:
    payload = dict(hidden)
    payload["__EVENTTARGET"] = GRID_EVENT_TARGET
    payload["__EVENTARGUMENT"] = f"Page${page_number}"
    payload.setdefault("__LASTFOCUS", "")
    return urllib.parse.urlencode(payload).encode("ascii")


def check_robots(user_agent: str, portal_url: str) -> None:
    parser = urllib.robotparser.RobotFileParser("https://chinhphu.vn/robots.txt")
    parser.read()
    if not parser.can_fetch(user_agent, portal_url):
        raise PermissionError("robots.txt disallows the official listing URL")


def run(args: argparse.Namespace) -> int:
    cutoff = date.fromisoformat(args.cutoff)
    type_group = int(args.type_group)
    portal_url = PORTAL_URL_TEMPLATE.format(type_group=type_group)
    output = Path(args.output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    raw_dir = output / "raw-listing-pages"
    raw_dir.mkdir()

    check_robots(args.user_agent, portal_url)
    client = PortalClient(portal_url, args.user_agent, args.delay, args.timeout, args.max_bytes)
    inventory: list[dict[str, Any]] = []
    page_records = []
    hidden: dict[str, str] | None = None
    reported_total: int | None = None
    stopped_on_cutoff = False

    for page_number in range(1, args.max_pages + 1):
        data = None if page_number == 1 else postback_data(hidden or {}, page_number)
        body, headers = client.fetch(data)
        parser, decoded = parse_listing(body, headers)
        if not parser.rows:
            raise ValueError(f"No document rows parsed on listing page {page_number}")
        hidden = parser.hidden
        if reported_total is None:
            total_match = TOTAL_RE.search(" ".join(parser.text_parts))
            if total_match:
                total_digits = re.sub(r"\D", "", total_match.group(1))
                if total_digits:
                    reported_total = int(total_digits)

        raw_path = raw_dir / f"page-{page_number:03d}.html"
        raw_path.write_bytes(body)
        normalized = [normalize_row(row, page_number, portal_url) for row in parser.rows]
        dated_rows = [item for item in normalized if item["promulgation_date"]]
        included = [item for item in dated_rows if date.fromisoformat(item["promulgation_date"]) >= cutoff]
        inventory.extend(included)
        page_records.append(
            {
                "page_number": page_number,
                "row_count": len(normalized),
                "included_count": len(included),
                "sha256": sha256_bytes(body),
                "stored_path": raw_path.relative_to(output).as_posix(),
            }
        )
        if dated_rows and all(date.fromisoformat(item["promulgation_date"]) < cutoff for item in dated_rows):
            stopped_on_cutoff = True
            break
        if "Page$Next" not in decoded and len(parser.rows) < 50:
            break

    deduplicated: dict[tuple[str, str | None], dict[str, Any]] = {}
    for item in inventory:
        deduplicated[(item["instrument_number"], item["promulgation_date"])] = item
    documents = sorted(
        deduplicated.values(),
        key=lambda item: (item["promulgation_date"] or "", item["instrument_number"] or ""),
        reverse=True,
    )
    classification_counts: dict[str, int] = {}
    for item in documents:
        key = item["title_relevance_class"]
        classification_counts[key] = classification_counts.get(key, 0) + 1
    result = {
        "schema_version": "1.0",
        "source_url": portal_url,
        "source_role": "authoritative_government_portal",
        "type_group_id": type_group,
        "type_group": TYPE_GROUPS[type_group],
        "cutoff_inclusive": cutoff.isoformat(),
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "portal_reported_total_all_dates": reported_total,
        "pages_fetched": len(page_records),
        "stopped_on_cutoff": stopped_on_cutoff,
        "document_count_in_window": len(documents),
        "classification_counts": classification_counts,
        "page_records": page_records,
        "documents": documents,
    }
    (output / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "pages_fetched": len(page_records),
                "documents": len(documents),
                "classification_counts": classification_counts,
                "stopped_on_cutoff": stopped_on_cutoff,
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", default="2016-08-11")
    parser.add_argument("--type-group", type=int, choices=sorted(TYPE_GROUPS), default=3)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument(
        "--user-agent",
        default="TaxLegalWorkspaceInventory/0.1 (official Government portal inventory)",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
