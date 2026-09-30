"""Download the registry's official Công báo PDFs and verify their SHA-256.

    python scripts/download_sources.py

Existing files are kept when their hash matches. A mismatch is an error: the
official file changed and the registry (and snapshot) must be reviewed.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.models import Registry  # noqa: E402

ALLOWED_HOSTS = {"g7.cdnchinhphu.vn", "congbao.chinhphu.vn", "datafiles.chinhphu.vn"}

try:  # the government CDN chain validates against the OS store on Windows
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    registry = Registry.model_validate_json((ROOT / "data" / "corpus" / "registry.json").read_text(encoding="utf-8"))
    failures = 0
    for doc in registry.documents:
        for part in doc.source_parts:
            target = ROOT / part.path
            if target.exists() and sha256(target.read_bytes()) == part.sha256:
                print(f"ok      {part.path}")
                continue
            host = urlparse(part.download_url).hostname
            if host not in ALLOWED_HOSTS:
                print(f"refused {part.download_url} (host {host} not in allowlist)")
                failures += 1
                continue
            response = requests.get(part.download_url, timeout=60)
            response.raise_for_status()
            data = response.content
            if not data.startswith(b"%PDF") or sha256(data) != part.sha256:
                print(f"MISMATCH {part.path}: downloaded bytes differ from the registry hash")
                failures += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            print(f"fetched {part.path}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
