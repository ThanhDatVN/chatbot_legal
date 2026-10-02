"""Pack the official source PDFs (and optionally the embedding cache) into one zip for a private Kaggle dataset.

    python scripts/pack_sources.py                     # dist/citeagent_sources.zip (corpus + ledger PDFs)
    python scripts/pack_sources.py --with-embeddings   # + data/indexes/embedding_cache (skips re-embedding)

Kaggle notebooks may not reach the Vietnamese government CDNs; upload the zip as a private dataset and point
SOURCES_ZIP at it (see kaggle/README.md). Every PDF is checked against its SHA-256 before it is packed, and
scripts/download_sources.py verifies them again after unzipping. The PDFs are official public documents; keep
the dataset private, as the repository itself does not redistribute them.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.ledger import load_ledger  # noqa: E402
from ingestion.models import Registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-embeddings", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "citeagent_sources.zip")
    args = parser.parse_args()
    registry = Registry.model_validate_json((ROOT / "data" / "corpus" / "registry.json").read_text(encoding="utf-8"))
    files = {p.path: p.sha256 for d in registry.documents for p in d.source_parts}
    ledger = load_ledger(ROOT / "data" / "corpus" / "currency_ledger.json")
    if ledger:
        files.update({s.path: s.sha256 for s in ledger.sources})
    missing = [p for p, digest in files.items()
               if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    if missing:
        print("missing or changed (run scripts/download_sources.py first):", *missing, sep="\n  ")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(files):
            zf.write(ROOT / path, path)
        if args.with_embeddings:
            for f in sorted((ROOT / "data" / "indexes" / "embedding_cache").glob("*")):
                zf.write(f, f.relative_to(ROOT).as_posix())
    size = args.out.stat().st_size / 1e6
    print(f"wrote {args.out.relative_to(ROOT)} ({len(files)} PDFs, {size:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
