#!/usr/bin/env python3
"""Selective, provenance-first crawler for the legal-data pilot.

The crawler only fetches URLs declared in the allowlist. Official pages may be
snapshotted for review; discovery sources are reduced to reference metadata and
are never persisted as full page content.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import truststore

LABELS = {
    "Số ký hiệu": "instrument_number",
    "Số, ký hiệu": "instrument_number",
    "Ngày ban hành": "promulgation_date",
    "Ngày có hiệu lực": "effective_date",
    "Ngày hiệu lực": "effective_date",
    "Loại văn bản": "document_type",
    "Cơ quan ban hành": "issuing_authority",
    "Người ký": "signer",
    "Trích yếu": "summary",
}
HTML_TYPES = {"text/html", "application/xhtml+xml"}
PDF_TYPES = {"application/pdf", "application/octet-stream"}
COVERAGE_CLASSES = {
    "core_current",
    "historical_temporal",
    "direct_implementation",
    "time_bounded_policy",
    "dependency_exception",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def content_type(headers: dict[str, str]) -> str:
    return headers.get("content-type", "").split(";", 1)[0].strip().lower()


def charset_from_headers(headers: dict[str, str]) -> str:
    match = re.search(r"charset=([^;\s]+)", headers.get("content-type", ""), re.I)
    return match.group(1).strip("\"'") if match else "utf-8"


def is_allowed_host(host: str, allowed_hosts: Iterable[str]) -> bool:
    host = host.rstrip(".").lower()
    return host in {item.rstrip(".").lower() for item in allowed_hosts}


def validate_url(url: str, allowed_hosts: Iterable[str], resolve_dns: bool = True) -> str:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise ValueError(f"URL must be credential-free HTTPS: {url}")
    if not is_allowed_host(host, allowed_hosts):
        raise ValueError(f"Host is not allowlisted: {host}")
    if resolve_dns:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses:
            raise ValueError(f"Host did not resolve: {host}")
        for address in addresses:
            ip = ipaddress.ip_address(address.split("%", 1)[0])
            if not ip.is_global:
                raise ValueError(f"Host resolved to non-public address: {host} -> {ip}")
    return host


class LegalHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.text_parts: list[str] = []
        self.anchors: list[dict[str, str]] = []
        self._skip_depth = 0
        self._in_title = False
        self._active_anchor: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and attributes.get("name", "").lower() == "description":
            self.description = normalize_space(attributes.get("content", ""))
        elif tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonical = attributes.get("href", "")
        elif tag == "a" and attributes.get("href"):
            self._active_anchor = {"href": attributes["href"], "parts": []}

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._active_anchor:
            self.anchors.append(
                {
                    "href": self._active_anchor["href"],
                    "text": normalize_space(" ".join(self._active_anchor["parts"])),
                }
            )
            self._active_anchor = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = normalize_space(data)
        if not cleaned:
            return
        if self._in_title:
            self.title = normalize_space(f"{self.title} {cleaned}")
        self.text_parts.append(cleaned)
        if self._active_anchor is not None:
            self._active_anchor["parts"].append(cleaned)


def extract_labeled_metadata(parts: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    normalized_labels = {normalize_space(label).casefold(): key for label, key in LABELS.items()}
    for index, part in enumerate(parts):
        field = normalized_labels.get(normalize_space(part).casefold())
        if not field or field in result:
            continue
        for candidate in parts[index + 1 : index + 6]:
            candidate_clean = normalize_space(candidate)
            if not candidate_clean or candidate_clean.casefold() in normalized_labels:
                continue
            result[field] = candidate_clean
            break
    return result


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)", value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return None


def parse_content_signals(robots_text: str) -> dict[str, str]:
    signals: dict[str, str] = {}
    for line in robots_text.splitlines():
        match = re.match(r"\s*Content-Signal\s*:\s*(.+)$", line, re.I)
        if not match:
            continue
        for item in match.group(1).split(","):
            if "=" in item:
                key, value = item.split("=", 1)
                signals[key.strip().lower()] = value.strip().lower()
    return signals


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _parse_curl_headers(header_text: str) -> tuple[int, dict[str, str]]:
    """Parse curl's --dump-header output into (status, headers).

    curl appends one block per response, so the final block is the one that
    produced the body.
    """
    blocks = [block for block in re.split(r"\r?\n\r?\n", header_text) if block.strip()]
    if not blocks:
        raise RuntimeError("curl fallback returned no response headers")
    lines = blocks[-1].splitlines()
    status_match = re.match(r"HTTP/\S+\s+(\d{3})", lines[0])
    if not status_match:
        raise RuntimeError(f"Unexpected curl status line: {lines[0]}")
    headers = {
        key.strip().lower(): value.strip()
        for line in lines[1:]
        if ":" in line
        for key, value in [line.split(":", 1)]
    }
    return int(status_match.group(1)), headers


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    fetched_at: str
    status: int
    headers: dict[str, str]
    body: bytes
    redirects: list[str]


@dataclass
class StreamedFile:
    """A response written straight to disk, never held whole in memory.

    Large attachments are streamed, hashed incrementally and atomically renamed
    into place, so a crash mid-download can never leave a truncated file that
    looks complete.  See docs/large-data-processing-plan.md.
    """

    requested_url: str
    final_url: str
    fetched_at: str
    status: int
    headers: dict[str, str]
    redirects: list[str]
    path: Path
    sha256: str
    size: int


#: The large-data plan specifies 1-8 MiB streaming blocks.
STREAM_BLOCK_BYTES = 1024 * 1024


def verify_pdf(path: Path) -> None:
    """Structural check before a downloaded PDF is accepted.

    Checks the magic bytes and the trailer.  A truncated download usually keeps
    a valid header while losing ``%%EOF``, which is exactly the corruption an
    atomic rename is meant to make impossible - this is the belt to that braces.
    """
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ValueError("not a PDF: bad magic bytes")
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - 2048))
        if b"%%EOF" not in handle.read():
            raise ValueError("truncated PDF: no %%EOF trailer")


class SafeFetcher:
    def __init__(self, user_agent: str, delay_seconds: float, timeout_seconds: int, max_redirects: int):
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.max_redirects = max_redirects
        self.last_request_by_host: dict[str, float] = {}
        tls_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=tls_context),
            NoRedirect(),
        )

    def _fetch_datafiles_with_curl(
        self,
        requested_url: str,
        max_bytes: int,
        headers: dict[str, str],
    ) -> FetchResult:
        """Use the OS TLS stack for the Government CDN's urllib-specific 403."""

        with tempfile.NamedTemporaryFile(suffix=".headers", delete=False) as header_file:
            header_path = Path(header_file.name)
        try:
            command = [
                "curl.exe",
                "--fail",
                "--silent",
                "--show-error",
                "--proto",
                "=https",
                "--max-time",
                str(self.timeout_seconds),
                "--max-filesize",
                str(max_bytes),
                "--dump-header",
                str(header_path),
            ]
            for key, value in headers.items():
                command.extend(["--header", f"{key}: {value}"])
            command.append(requested_url)
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=self.timeout_seconds + 5,
            )
            if completed.returncode:
                error = completed.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"curl fallback failed ({completed.returncode}): {error}")
            if len(completed.stdout) > max_bytes:
                raise ValueError(f"Response exceeds {max_bytes} bytes: {requested_url}")
            header_text = header_path.read_text(encoding="iso-8859-1", errors="replace")
        finally:
            header_path.unlink(missing_ok=True)
        blocks = [block for block in re.split(r"\r?\n\r?\n", header_text) if block.strip()]
        if not blocks:
            raise RuntimeError("curl fallback returned no response headers")
        lines = blocks[-1].splitlines()
        status_match = re.match(r"HTTP/\S+\s+(\d{3})", lines[0])
        if not status_match:
            raise RuntimeError(f"Unexpected curl status line: {lines[0]}")
        response_headers = {
            key.strip().lower(): value.strip()
            for line in lines[1:]
            if ":" in line
            for key, value in [line.split(":", 1)]
        }
        return FetchResult(
            requested_url=requested_url,
            final_url=requested_url,
            fetched_at=utc_now(),
            status=int(status_match.group(1)),
            headers=response_headers,
            body=completed.stdout,
            redirects=[],
        )

    def _stream_body(
        self,
        reader,
        target: Path,
        max_bytes: int,
        declared_length: int | None,
    ) -> tuple[str, int]:
        """Write a response body to ``target`` atomically; return (sha256, size).

        The body never exists whole in memory: blocks go straight to a
        ``.partial`` sibling while the digest and byte count advance, then the
        file is fsynced and renamed into place.
        """
        if declared_length is not None and declared_length > max_bytes:
            raise ValueError(f"Content-Length {declared_length} exceeds {max_bytes} bytes")

        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".partial")
        digest = hashlib.sha256()
        total = 0
        try:
            with partial.open("wb") as handle:
                while True:
                    block = reader.read(STREAM_BLOCK_BYTES)
                    if not block:
                        break
                    total += len(block)
                    if total > max_bytes:
                        raise ValueError(f"Response exceeds {max_bytes} bytes")
                    digest.update(block)
                    handle.write(block)
                handle.flush()
                os.fsync(handle.fileno())
            if declared_length is not None and total != declared_length:
                raise ValueError(f"Short read: got {total}, Content-Length said {declared_length}")
            os.replace(partial, target)  # atomic within a filesystem
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        return digest.hexdigest(), total

    def fetch_to_file(
        self,
        url: str,
        allowed_hosts: Iterable[str],
        max_bytes: int,
        accept: str,
        target: Path,
        resolve_dns: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> StreamedFile:
        """Fetch a large artefact straight to disk (D-12).

        Mirrors :meth:`fetch` for redirects and host validation, but never
        accumulates the payload in memory.
        """
        requested_url = url
        redirects: list[str] = []
        for _ in range(self.max_redirects + 1):
            host = validate_url(url, allowed_hosts, resolve_dns=resolve_dns)
            self._wait(host)
            headers = {
                "User-Agent": self.user_agent,
                "Accept": accept,
                "Accept-Language": "vi,en;q=0.7",
                "Cache-Control": "no-cache",
            }
            headers.update(extra_headers or {})
            request = urllib.request.Request(url, headers=headers)
            try:
                response = self.opener.open(request, timeout=self.timeout_seconds)
            except urllib.error.HTTPError as exc:
                if (
                    exc.code == 403
                    and host == "datafiles.chinhphu.vn"
                    and "application/pdf" in accept
                ):
                    return self._fetch_datafiles_with_curl_to_file(
                        requested_url, max_bytes, headers, target
                    )
                if exc.code not in {301, 302, 303, 307, 308}:
                    raise
                location = exc.headers.get("Location")
                if not location:
                    raise RuntimeError(f"Redirect without Location: {url}") from exc
                next_url = urllib.parse.urljoin(url, location)
                validate_url(next_url, allowed_hosts, resolve_dns=resolve_dns)
                redirects.append(next_url)
                url = next_url
                continue
            with response:
                response_headers = {key.lower(): value for key, value in response.headers.items()}
                declared = response_headers.get("content-length")
                declared_length = int(declared) if declared and declared.isdigit() else None
                digest, size = self._stream_body(response, target, max_bytes, declared_length)
                return StreamedFile(
                    requested_url=requested_url,
                    final_url=response.geturl(),
                    fetched_at=utc_now(),
                    status=response.status,
                    headers=response_headers,
                    redirects=redirects,
                    path=target,
                    sha256=digest,
                    size=size,
                )
        raise RuntimeError(f"Too many redirects: {requested_url}")

    def _fetch_datafiles_with_curl_to_file(
        self,
        requested_url: str,
        max_bytes: int,
        headers: dict[str, str],
        target: Path,
    ) -> StreamedFile:
        """Streaming variant of the curl fallback.

        ``--output`` writes to a ``.partial`` file instead of stdout, so the
        payload is not buffered in the parent process (D-12).
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".partial")
        with tempfile.NamedTemporaryFile(suffix=".headers", delete=False) as header_file:
            header_path = Path(header_file.name)
        try:
            command = [
                "curl.exe",
                "--fail",
                "--silent",
                "--show-error",
                "--proto",
                "=https",
                "--max-time",
                str(self.timeout_seconds),
                "--max-filesize",
                str(max_bytes),
                "--dump-header",
                str(header_path),
                "--output",
                str(partial),
            ]
            for key, value in headers.items():
                command.extend(["--header", f"{key}: {value}"])
            command.append(requested_url)
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=self.timeout_seconds + 5,
            )
            if completed.returncode:
                error = completed.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"curl fallback failed ({completed.returncode}): {error}")

            size = partial.stat().st_size
            if size > max_bytes:
                raise ValueError(f"Response exceeds {max_bytes} bytes: {requested_url}")

            digest = hashlib.sha256()
            with partial.open("rb") as handle:
                while True:
                    block = handle.read(STREAM_BLOCK_BYTES)
                    if not block:
                        break
                    digest.update(block)

            header_text = header_path.read_text(encoding="iso-8859-1", errors="replace")
            status, response_headers = _parse_curl_headers(header_text)
            os.replace(partial, target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        finally:
            header_path.unlink(missing_ok=True)

        return StreamedFile(
            requested_url=requested_url,
            final_url=requested_url,
            fetched_at=utc_now(),
            status=status,
            headers=response_headers,
            redirects=[],
            path=target,
            sha256=digest.hexdigest(),
            size=size,
        )

    def _wait(self, host: str) -> None:
        last = self.last_request_by_host.get(host)
        if last is not None:
            remaining = self.delay_seconds - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)
        self.last_request_by_host[host] = time.monotonic()

    def fetch(
        self,
        url: str,
        allowed_hosts: Iterable[str],
        max_bytes: int,
        accept: str,
        resolve_dns: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> FetchResult:
        requested_url = url
        redirects: list[str] = []
        for _ in range(self.max_redirects + 1):
            host = validate_url(url, allowed_hosts, resolve_dns=resolve_dns)
            self._wait(host)
            headers = {
                "User-Agent": self.user_agent,
                "Accept": accept,
                "Accept-Language": "vi,en;q=0.7",
                "Cache-Control": "no-cache",
            }
            headers.update(extra_headers or {})
            request = urllib.request.Request(url, headers=headers)
            try:
                response = self.opener.open(request, timeout=self.timeout_seconds)
            except urllib.error.HTTPError as exc:
                if (
                    exc.code == 403
                    and host == "datafiles.chinhphu.vn"
                    and "application/pdf" in accept
                ):
                    return self._fetch_datafiles_with_curl(requested_url, max_bytes, headers)
                if exc.code not in {301, 302, 303, 307, 308}:
                    raise
                location = exc.headers.get("Location")
                if not location:
                    raise RuntimeError(f"Redirect without Location: {url}") from exc
                next_url = urllib.parse.urljoin(url, location)
                validate_url(next_url, allowed_hosts, resolve_dns=resolve_dns)
                redirects.append(next_url)
                url = next_url
                continue
            with response:
                headers = {key.lower(): value for key, value in response.headers.items()}
                chunks: list[bytes] = []
                total = 0
                while True:
                    chunk = response.read(min(65536, max_bytes + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"Response exceeds {max_bytes} bytes: {url}")
                    chunks.append(chunk)
                return FetchResult(
                    requested_url=requested_url,
                    final_url=response.geturl(),
                    fetched_at=utc_now(),
                    status=response.status,
                    headers=headers,
                    body=b"".join(chunks),
                    redirects=redirects,
                )
        raise RuntimeError(f"Too many redirects: {requested_url}")


class RobotsCache:
    def __init__(self, fetcher: SafeFetcher):
        self.fetcher = fetcher
        self.cache: dict[str, dict[str, Any]] = {}

    def inspect(self, url: str, allowed_hosts: Iterable[str]) -> dict[str, Any]:
        parsed = urllib.parse.urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{origin}/robots.txt"
        if robots_url not in self.cache:
            try:
                result = self.fetcher.fetch(
                    robots_url,
                    allowed_hosts,
                    max_bytes=1024 * 1024,
                    accept="text/plain,*/*;q=0.1",
                )
                text = result.body.decode(charset_from_headers(result.headers), errors="replace")
                parser = urllib.robotparser.RobotFileParser()
                parser.set_url(robots_url)
                parser.parse(text.splitlines())
                self.cache[robots_url] = {
                    "status": result.status,
                    "url": robots_url,
                    "parser": parser,
                    "content_signals": parse_content_signals(text),
                    "sha256": sha256_bytes(result.body),
                }
            except urllib.error.HTTPError as exc:
                # RFC 9309 treats 4xx robots responses as "unavailable".
                if exc.code not in {401, 403, 404}:
                    raise
                self.cache[robots_url] = {
                    "status": exc.code,
                    "url": robots_url,
                    "parser": None,
                    "content_signals": {},
                    "sha256": None,
                }
        item = self.cache[robots_url]
        parser = item["parser"]
        allowed = True if parser is None else parser.can_fetch(self.fetcher.user_agent, url)
        return {
            "url": item["url"],
            "status": item["status"],
            "allowed": allowed,
            "content_signals": item["content_signals"],
            "sha256": item["sha256"],
        }


def parse_page(result: FetchResult) -> tuple[LegalHTMLParser, str]:
    mime = content_type(result.headers)
    if mime not in HTML_TYPES:
        raise ValueError(f"Expected HTML but received {mime or 'unknown'}")
    decoded = result.body.decode(charset_from_headers(result.headers), errors="replace")
    parser = LegalHTMLParser()
    parser.feed(decoded)
    return parser, decoded


def find_pdf_links(
    parser: LegalHTMLParser, base_url: str, allowed_hosts: Iterable[str]
) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in parser.anchors:
        target = urllib.parse.urljoin(base_url, anchor["href"])
        parsed = urllib.parse.urlsplit(target)
        looks_like_pdf = parsed.path.lower().endswith(".pdf") or ".pdf" in anchor["text"].lower()
        if not looks_like_pdf or target in seen:
            continue
        try:
            validate_url(target, allowed_hosts, resolve_dns=False)
        except ValueError:
            continue
        seen.add(target)
        found.append({"url": target, "label": anchor["text"]})
    return found


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an ISO date: {value}") from exc


def validate_config(config: dict[str, Any]) -> None:
    documents = config.get("documents", [])
    if not documents:
        raise ValueError("Allowlist must contain at least one document")

    selection_window = config.get("selection_window")
    window_start: date | None = None
    window_end: date | None = None
    if selection_window:
        if selection_window.get("date_basis") != "promulgation_date":
            raise ValueError("selection_window.date_basis must be promulgation_date")
        window_start = parse_iso_date(selection_window.get("start"), "selection_window.start")
        window_end = parse_iso_date(selection_window.get("end"), "selection_window.end")
        if window_start > window_end:
            raise ValueError("selection_window.start must not be after selection_window.end")

    document_ids: set[str] = set()
    for document in documents:
        document_id = document["id"]
        if document_id in document_ids:
            raise ValueError(f"Duplicate document id: {document_id}")
        document_ids.add(document_id)
        promulgation_date = parse_iso_date(
            document["promulgation_date_expected"],
            f"{document_id}.promulgation_date_expected",
        )
        if document.get("effective_date_expected"):
            parse_iso_date(
                document["effective_date_expected"],
                f"{document_id}.effective_date_expected",
            )
        if selection_window:
            coverage_class = document.get("coverage_class")
            if coverage_class not in COVERAGE_CLASSES:
                raise ValueError(f"Unknown coverage_class {coverage_class!r} in {document_id}")
            assert window_start is not None and window_end is not None
            outside_window = not window_start <= promulgation_date <= window_end
            exception_reason = normalize_space(document.get("dependency_exception_reason", ""))
            if outside_window and coverage_class != "dependency_exception":
                raise ValueError(f"Out-of-window document must be a dependency_exception: {document_id}")
            if outside_window and not exception_reason:
                raise ValueError(f"Out-of-window document requires a dependency reason: {document_id}")
            if not outside_window and coverage_class == "dependency_exception":
                raise ValueError(f"In-window document cannot be a dependency_exception: {document_id}")
            if not normalize_space(document.get("selection_rationale", "")):
                raise ValueError(f"Missing selection_rationale in {document_id}")
        validate_url(document["official_url"], config["sources"]["chinhphu"]["allowed_hosts"], False)
        if document.get("discovery_url"):
            validate_url(
                document["discovery_url"],
                config["sources"]["thuvienphapluat"]["allowed_hosts"],
                False,
            )
        for attachment in document.get("official_attachment_urls", []):
            validate_url(
                attachment["url"],
                config["sources"]["chinhphu"]["allowed_hosts"],
                False,
            )
    for document in documents:
        for relation in document.get("relations", []):
            if relation["target"] not in document_ids:
                raise ValueError(f"Unknown relation target {relation['target']} in {document['id']}")


def validate_expected_metadata(document: dict[str, Any], metadata: dict[str, str], title: str) -> list[str]:
    issues: list[str] = []
    haystack = normalize_space(f"{title} {metadata.get('instrument_number', '')}").casefold()
    if normalize_space(document["instrument_number"]).casefold() not in haystack:
        issues.append("instrument_number_not_found")
    for field in ("promulgation_date", "effective_date"):
        expected = document.get(f"{field}_expected")
        actual = normalize_date(metadata.get(field))
        if expected and actual and actual != expected:
            issues.append(f"{field}_mismatch:{actual}!={expected}")
        elif expected and not actual:
            issues.append(f"{field}_not_extracted")
    expected_type = document.get("document_type_expected")
    actual_type = metadata.get("document_type")
    if expected_type and not actual_type:
        issues.append("document_type_not_extracted")
    elif expected_type and (
        normalize_space(actual_type).casefold() != normalize_space(expected_type).casefold()
    ):
        issues.append(f"document_type_mismatch:{actual_type}!={expected_type}")
    return issues


def content_signal_allows_reference(
    source: dict[str, Any], robots: dict[str, Any]
) -> tuple[bool, str | None]:
    policy = source.get("content_signal_policy")
    if not policy:
        return True, None
    signals = robots.get("content_signals", {})
    required_search = policy.get("required_search")
    if required_search and signals.get("search") not in {None, required_search}:
        return False, "content_signal_search_disallows"
    if signals.get("use") not in {None, policy.get("maximum_use")}:
        return False, "content_signal_use_exceeds_policy"
    return True, None


def crawl_page(
    document: dict[str, Any],
    source_name: str,
    source: dict[str, Any],
    url: str,
    config: dict[str, Any],
    output: Path,
    fetcher: SafeFetcher,
    robots_cache: RobotsCache,
    download_attachments: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    base_record: dict[str, Any] = {
        "record_type": "source_page",
        "pilot_id": config["pilot_id"],
        "document_id": document["id"],
        "instrument_number": document["instrument_number"],
        "coverage_class": document.get("coverage_class"),
        "selection_rationale": document.get("selection_rationale"),
        "dependency_exception_reason": document.get("dependency_exception_reason"),
        "known_source_discrepancy": document.get("known_source_discrepancy"),
        "source": source_name,
        "source_role": source["role"],
        "requested_url": url,
        "quarantine_status": "pending_human_review",
    }
    try:
        robots = robots_cache.inspect(url, source["allowed_hosts"])
        base_record["robots"] = robots
        if not robots["allowed"]:
            raise PermissionError("robots_disallowed")
        signal_allowed, signal_reason = content_signal_allows_reference(source, robots)
        if not signal_allowed:
            raise PermissionError(signal_reason or "content_signal_disallowed")
        result = fetcher.fetch(
            url,
            source["allowed_hosts"],
            config["max_html_bytes"],
            accept="text/html,application/xhtml+xml;q=0.9",
        )
        parser, decoded = parse_page(result)
        metadata = extract_labeled_metadata(parser.text_parts)
        visible_text = normalize_space("\n".join(parser.text_parts))
        issues = validate_expected_metadata(document, metadata, parser.title)
        page_record = {
            **base_record,
            "fetch_status": "fetched",
            "fetched_at": result.fetched_at,
            "http_status": result.status,
            "final_url": result.final_url,
            "redirects": result.redirects,
            "content_type": content_type(result.headers),
            "content_length": len(result.body),
            "response_sha256": sha256_bytes(result.body),
            "title": parser.title,
            "description": parser.description,
            "canonical_url": urllib.parse.urljoin(result.final_url, parser.canonical)
            if parser.canonical
            else None,
            "metadata": metadata,
            "validation_issues": issues,
            "attribution": source.get("attribution"),
            "stored_paths": [],
        }
        slug = safe_slug(document["id"])
        if source.get("store_raw_html"):
            raw_path = output / "quarantine" / "official-html" / f"{slug}.html"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(result.body)
            page_record["stored_paths"].append(raw_path.relative_to(output).as_posix())
        if source.get("store_visible_text"):
            text_path = output / "quarantine" / "official-text" / f"{slug}.txt"
            text_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.write_text(visible_text + "\n", encoding="utf-8")
            page_record["stored_paths"].append(text_path.relative_to(output).as_posix())
        else:
            excerpt_source = parser.description or visible_text
            page_record["reference_excerpt"] = excerpt_source[: int(source.get("excerpt_chars", 500))]
            reference_path = output / "reference" / f"{slug}.json"
            write_json(reference_path, page_record)
            page_record["stored_paths"].append(reference_path.relative_to(output).as_posix())

        extracted_links = find_pdf_links(
            parser,
            result.final_url,
            config["sources"]["chinhphu"]["allowed_hosts"],
        )
        pdf_links: list[dict[str, str]] = []
        seen_pdf_urls: set[str] = set()
        for link in [*document.get("official_attachment_urls", []), *extracted_links]:
            if link["url"] not in seen_pdf_urls:
                pdf_links.append(link)
                seen_pdf_urls.add(link["url"])
        page_record["attachment_links"] = pdf_links
        records.append(page_record)

        should_download = (
            source["role"] == "authoritative"
            and download_attachments
            and document.get("download_attachments", False)
        )
        if should_download:
            max_count = int(config["max_attachments_per_document"])
            for position, attachment in enumerate(pdf_links[:max_count], start=1):
                attachment_record: dict[str, Any] = {
                    "record_type": "official_attachment",
                    "pilot_id": config["pilot_id"],
                    "document_id": document["id"],
                    "instrument_number": document["instrument_number"],
                    "source": source_name,
                    "source_role": source["role"],
                    "requested_url": attachment["url"],
                    "label": attachment["label"],
                    "quarantine_status": "pending_human_review",
                }
                try:
                    attachment_robots = robots_cache.inspect(
                        attachment["url"], config["sources"]["chinhphu"]["allowed_hosts"]
                    )
                    attachment_record["robots"] = attachment_robots
                    if not attachment_robots["allowed"]:
                        raise PermissionError("robots_disallowed")
                    attachment_path = (
                        output / "quarantine" / "official-attachments" / f"{slug}-{position}.pdf"
                    )
                    # Streamed to disk, hashed on the way, atomically renamed:
                    # a multi-megabyte PDF is never held whole in memory and a
                    # crash cannot leave a truncated file in place.
                    attachment_result = fetcher.fetch_to_file(
                        attachment["url"],
                        config["sources"]["chinhphu"]["allowed_hosts"],
                        config["max_attachment_bytes"],
                        accept="application/pdf",
                        target=attachment_path,
                        extra_headers={"Referer": result.final_url},
                    )
                    mime = content_type(attachment_result.headers)
                    try:
                        if mime not in PDF_TYPES:
                            raise ValueError(f"Attachment is not a PDF: {mime or 'unknown'}")
                        verify_pdf(attachment_path)
                    except Exception:
                        attachment_path.unlink(missing_ok=True)
                        raise
                    attachment_record.update(
                        {
                            "fetch_status": "fetched",
                            "fetched_at": attachment_result.fetched_at,
                            "http_status": attachment_result.status,
                            "final_url": attachment_result.final_url,
                            "redirects": attachment_result.redirects,
                            "content_type": mime,
                            "content_length": attachment_result.size,
                            "response_sha256": attachment_result.sha256,
                            "stored_path": attachment_path.relative_to(output).as_posix(),
                        }
                    )
                except Exception as exc:  # Each attachment is isolated and auditable.
                    attachment_record.update(
                        {
                            "fetch_status": "failed",
                            "failed_at": utc_now(),
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                records.append(attachment_record)
    except Exception as exc:  # A bad source must not stop the remaining allowlist.
        base_record.update(
            {"fetch_status": "failed", "failed_at": utc_now(), "error": f"{type(exc).__name__}: {exc}"}
        )
        records.append(base_record)
    return records


def run(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    output = Path(args.output).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    if args.dry_run:
        print(f"Valid allowlist: {len(config['documents'])} documents")
        return 0
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.jsonl"
    fetcher = SafeFetcher(
        config["user_agent"],
        float(config["request_delay_seconds"]),
        int(config["timeout_seconds"]),
        int(config["max_redirects"]),
    )
    robots_cache = RobotsCache(fetcher)
    documents = config["documents"][: args.limit or None]
    all_records: list[dict[str, Any]] = []
    source_circuit: dict[str, str] = {}
    for document in documents:
        source_requests = [("chinhphu", document["official_url"])]
        if document.get("discovery_url"):
            source_requests.append(("thuvienphapluat", document["discovery_url"]))
        for source_name, url in source_requests:
            if args.only_source and args.only_source != source_name:
                continue
            print(f"[{document['id']}] {source_name}: {url}", flush=True)
            if source_name in source_circuit:
                records = [
                    {
                        "record_type": "source_page",
                        "pilot_id": config["pilot_id"],
                        "document_id": document["id"],
                        "instrument_number": document["instrument_number"],
                        "source": source_name,
                        "source_role": config["sources"][source_name]["role"],
                        "requested_url": url,
                        "quarantine_status": "not_fetched",
                        "fetch_status": "skipped",
                        "skipped_at": utc_now(),
                        "error": source_circuit[source_name],
                    }
                ]
            else:
                records = crawl_page(
                    document,
                    source_name,
                    config["sources"][source_name],
                    url,
                    config,
                    output,
                    fetcher,
                    robots_cache,
                    args.download_official_pdfs,
                )
                if source_name == "thuvienphapluat" and any(
                    item.get("fetch_status") == "failed" and "HTTP Error 403" in item.get("error", "")
                    for item in records
                ):
                    source_circuit[source_name] = "source_circuit_open_after_http_403"
            for record in records:
                append_jsonl(manifest_path, record)
            all_records.extend(records)

    pages = [item for item in all_records if item["record_type"] == "source_page"]
    attachments = [item for item in all_records if item["record_type"] == "official_attachment"]
    summary = {
        "schema_version": "1.0",
        "pilot_id": config["pilot_id"],
        "generated_at": utc_now(),
        "config_path": str(config_path),
        "scope": config["scope"],
        "selection_window": config.get("selection_window"),
        "document_count": len(documents),
        "documents_by_coverage_class": dict(
            sorted(Counter(item.get("coverage_class", "unspecified") for item in documents).items())
        ),
        "documents_by_topic": dict(
            sorted(Counter(topic for item in documents for topic in item.get("topic", [])).items())
        ),
        "known_source_discrepancy_count": sum(
            bool(item.get("known_source_discrepancy")) for item in documents
        ),
        "page_fetches": {
            "attempted": len(pages),
            "succeeded": sum(item["fetch_status"] == "fetched" for item in pages),
            "failed": sum(item["fetch_status"] == "failed" for item in pages),
            "skipped": sum(item["fetch_status"] == "skipped" for item in pages),
        },
        "official_pages_succeeded": sum(
            item["fetch_status"] == "fetched" and item["source_role"] == "authoritative" for item in pages
        ),
        "discovery_pages_succeeded": sum(
            item["fetch_status"] == "fetched" and item["source_role"] == "discovery_reference"
            for item in pages
        ),
        "attachments": {
            "attempted": len(attachments),
            "succeeded": sum(item["fetch_status"] == "fetched" for item in attachments),
            "failed": sum(item["fetch_status"] == "failed" for item in attachments),
        },
        "validation_issue_count": sum(len(item.get("validation_issues", [])) for item in pages),
        "quarantine_notice": (
            "Không index vào RAG trước khi reviewer xác nhận số hiệu, ngày, checksum "
            "và quan hệ hiệu lực."
        ),
    }
    write_json(output / "summary.json", summary)
    write_json(output / "config.snapshot.json", config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["official_pages_succeeded"] > 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/legal-crawl-allowlist.json")
    parser.add_argument("--output", default="data/crawl/pilot")
    parser.add_argument("--limit", type=int, help="Process only the first N configured documents")
    parser.add_argument("--only-source", choices=["chinhphu", "thuvienphapluat"])
    parser.add_argument("--download-official-pdfs", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        sys.exit(run(build_parser().parse_args()))
    except (ValueError, FileNotFoundError, FileExistsError, json.JSONDecodeError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(64)
