"""Collect isolated PDF candidates from official Công báo detail pages.

Use the Windows certificate store to validate the official CDN TLS chain.
Re-download on each run and verify every cached file against the trusted bytes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import bs4
import pymupdf
import requests
import truststore

from pilot.collect import OUT
from pilot.process_local import load_jsonl


DETAILS = {
    "45_2019_qh14": "https://congbao.chinhphu.vn/van-ban/nghi-quyet-so-45-2019-qh14-30232.htm",
    "18_2026_vbhn_vpqh": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm",
    "145_2020_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-145-2020-nd-cp-32732.htm",
    "135_2020_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-135-2020-nd-cp-32525.htm",
    "152_2020_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-152-2020-nd-cp-32864.htm",
    "70_2023_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-70-2023-nd-cp-40131.htm",
    "293_2025_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-293-2025-nd-cp-46568.htm",
    "74_2024_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-74-2024-nd-cp-42170.htm",
    "38_2022_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-38-2022-nd-cp-37348.htm",
    "12_2022_nd_cp": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-12-2022-nd-cp-36716.htm",
}

truststore.inject_into_ssl()


def main() -> None:
    output = OUT / "raw_alternates"
    output.mkdir(exist_ok=True)
    manifest = {x["document_id"]: x for x in load_jsonl(OUT / "manifest.jsonl")}
    results = []
    for doc_id, detail in DETAILS.items():
        row = {"document_id": doc_id, "detail_url": detail, "observed_at": datetime.now(timezone.utc).isoformat(), "files": []}
        try:
            response = requests.get(detail, timeout=30)
            response.raise_for_status()
            soup = bs4.BeautifulSoup(response.text, "html.parser")
            title = soup.find("h1")
            row["page_title"] = title.get_text(" ", strip=True) if title else None
            links = [
                a for a in soup.select("a[href]")
                if a.get_text(" ", strip=True).lower().endswith(".pdf")
                and manifest[doc_id]["document_number"].split("/")[0] in a.get_text(" ", strip=True)
            ]
            for index, link in enumerate(links, start=1):
                url = link["href"]
                if urlparse(url).hostname != "g7.cdnchinhphu.vn":
                    raise ValueError(f"Unexpected CDN host: {urlparse(url).hostname}")
                target = output / f"{doc_id}_congbao_part{index}.pdf"
                downloaded = requests.get(url, timeout=120)
                downloaded.raise_for_status()
                if not downloaded.content.startswith(b"%PDF-"):
                    raise ValueError("Download did not contain a PDF")
                fresh_hash = hashlib.sha256(downloaded.content).hexdigest()
                if target.exists():
                    cached_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                    if cached_hash != fresh_hash:
                        raise ValueError(f"Cached source differs from TLS-verified download: {target}")
                else:
                    target.write_bytes(downloaded.content)
                with pymupdf.open(target) as pdf:
                    page_count = len(pdf)
                    native_words = sum(len(p.get_text("words")) for p in pdf)
                row["files"].append({
                    "label": link.get_text(" ", strip=True),
                    "download_url": url,
                    "path": str(target),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "tls_certificate_verified": True,
                    "pages": page_count,
                    "native_words": native_words,
                })
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        results.append(row)
        print(doc_id, [(x["pages"], x["native_words"]) for x in row["files"]], row.get("error", ""), flush=True)
    path = OUT / "congbao_candidate_inventory.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
