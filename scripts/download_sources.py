"""Download the official Công báo PDFs and verify their SHA-256.

    python scripts/download_sources.py

Covers the corpus documents in data/corpus/registry.json and the amending
instruments cited by data/corpus/currency_ledger.json. Existing files are kept
when their hash matches. A mismatch is an error: the official file changed and
the registry (and snapshot) must be reviewed.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.ledger import load_ledger  # noqa: E402
from ingestion.models import Registry  # noqa: E402

ALLOWED_HOSTS = {"g7.cdnchinhphu.vn", "congbao.chinhphu.vn", "congbaocdn.chinhphu.vn", "datafiles.chinhphu.vn"}

try:  # the government CDN chain validates against the OS store on Windows
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(path: str, url: str, expected: str) -> bool:
    target = ROOT / path
    if target.exists() and sha256(target.read_bytes()) == expected:
        print(f"ok      {path}")
        return True
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        print(f"refused {url} (host {host} not in allowlist)")
        return False
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    data = response.content
    if not data.startswith(b"%PDF") or sha256(data) != expected:
        print(f"MISMATCH {path}: downloaded bytes differ from the recorded hash")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(f"fetched {path}")
    return True


def main() -> int:
    registry = Registry.model_validate_json((ROOT / "data" / "corpus" / "registry.json").read_text(encoding="utf-8"))
    files = {part.path: (part.download_url, part.sha256) for doc in registry.documents for part in doc.source_parts}
    ledger = load_ledger(ROOT / "data" / "corpus" / "currency_ledger.json")
    if ledger is not None:
        for source in ledger.sources:
            files.setdefault(source.path, (source.download_url, source.sha256))
    failures = sum(not fetch(path, url, digest) for path, (url, digest) in files.items())
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
