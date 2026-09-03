#!/usr/bin/env python3
"""Collect every PDF that needs OCR into one auditable hand-off package.

Blocker B-1: 54% of corpus documents carry no extractable text layer, and no
software workaround exists (Official Gazette substitution overlaps 0.2%;
PyMuPDF rescued 0 of 26). OCR must be run externally.

This tool scans **every** PDF in the corpus - not a sample - classifies each
page by whether it has usable text, and writes a work package that can be
handed to an OCR operator and later re-ingested without losing provenance.

Classification per document:

    text_ok    every page carries usable text            -> not queued
    mixed      some pages need OCR, others do not        -> queued, pages listed
    image_only no page carries usable text               -> queued

De-duplication is by content SHA-256: the same instrument is often crawled into
several run directories, and OCR-ing it more than once wastes the operator's
time. One entry per distinct file; every path it appears at is recorded.

Outputs
-------
    data/ocr-queue/manifest.jsonl     one record per distinct PDF
    data/ocr-queue/README.md          the return-format contract
    data/ocr-queue/pdfs/              the files themselves (with --copy)
    reports/ocr-queue-summary.json    aggregate statistics
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from virag.settings import get_settings  # noqa: E402


def rel_to_repo(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise (output may live anywhere)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path, block: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(block)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def page_text_lengths(path: Path) -> list[int] | None:
    """Characters of extractable text per page, or None if the PDF is unreadable."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        lengths = []
        for page in reader.pages:
            try:
                lengths.append(len((page.extract_text() or "").strip()))
            except Exception:
                lengths.append(0)
        return lengths
    except Exception:
        return None


def load_document_metadata(crawl_root: Path) -> dict[str, dict]:
    """Map a stored attachment filename to its document metadata.

    The OCR operator gets meaningless filenames otherwise; the reintegration
    step needs document_id to put the text back where it belongs.
    """
    by_filename: dict[str, dict] = {}
    meta_by_doc: dict[str, dict] = {}

    for manifest in crawl_root.glob("**/manifest.jsonl"):
        with manifest.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                document_id = record.get("document_id")
                if not document_id:
                    continue
                if record.get("record_type") == "source_page":
                    portal = record.get("metadata") or {}
                    meta_by_doc.setdefault(
                        document_id,
                        {
                            "document_id": document_id,
                            "instrument_number": portal.get("instrument_number")
                            or record.get("instrument_number"),
                            "document_type": portal.get("document_type"),
                            "title": record.get("title") or portal.get("summary"),
                            "promulgation_date": portal.get("promulgation_date"),
                            "effective_date": portal.get("effective_date"),
                            "source_url": record.get("final_url") or record.get("requested_url"),
                        },
                    )
                elif record.get("record_type") == "official_attachment":
                    stored = record.get("stored_path")
                    if stored:
                        by_filename.setdefault(
                            Path(stored).name,
                            {
                                "document_id": document_id,
                                "attachment_sha256": record.get("response_sha256"),
                            },
                        )

    for entry in by_filename.values():
        entry.update(meta_by_doc.get(entry["document_id"], {}))
    return by_filename


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crawl-root", default=str(REPO_ROOT / "data" / "crawl"))
    parser.add_argument("--out", default=str(REPO_ROOT / "data" / "ocr-queue"))
    parser.add_argument(
        "--summary", default=str(REPO_ROOT / "reports" / "ocr-queue-summary.json")
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="copy the PDFs into the package (otherwise only paths are recorded)",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    logging.getLogger("pypdf").setLevel(logging.ERROR)

    settings = get_settings()
    threshold = settings.ocr_min_chars_per_page
    crawl_root = Path(args.crawl_root)
    out_root = Path(args.out)

    pdfs = sorted(crawl_root.glob("**/official-attachments/*.pdf"))
    if args.limit:
        pdfs = pdfs[: args.limit]
    if not pdfs:
        print("no PDFs found", file=sys.stderr)
        return 2

    print(f"scanning {len(pdfs)} PDFs (threshold {threshold} chars/page)...\n")
    metadata = load_document_metadata(crawl_root)

    by_hash: dict[str, dict] = {}
    unreadable: list[str] = []
    counts = defaultdict(int)
    pages_total = pages_needing = 0

    for index, path in enumerate(pdfs, 1):
        if index % 200 == 0:
            print(f"  ...{index}/{len(pdfs)}")
        lengths = page_text_lengths(path)
        if lengths is None:
            unreadable.append(rel_to_repo(path))
            counts["unreadable"] += 1
            continue

        need = [i + 1 for i, n in enumerate(lengths) if n < threshold]
        pages_total += len(lengths)
        pages_needing += len(need)

        if not need:
            classification = "text_ok"
        elif len(need) == len(lengths):
            classification = "image_only"
        else:
            classification = "mixed"
        counts[classification] += 1

        if classification == "text_ok":
            continue

        digest = sha256_file(path)
        rel = rel_to_repo(path)
        existing = by_hash.get(digest)
        if existing is not None:
            existing["duplicate_paths"].append(rel)
            continue

        info = metadata.get(path.name, {})
        by_hash[digest] = {
            "sha256": digest,
            "filename": path.name,
            "source_path": rel,
            "duplicate_paths": [],
            "size_bytes": path.stat().st_size,
            "pages": len(lengths),
            "pages_needing_ocr": need,
            "classification": classification,
            "document_id": info.get("document_id"),
            "instrument_number": info.get("instrument_number"),
            "document_type": info.get("document_type"),
            "title": info.get("title"),
            "promulgation_date": info.get("promulgation_date"),
            "effective_date": info.get("effective_date"),
            "source_url": info.get("source_url"),
            # What the operator must return.  Per-page files are preferred
            # because OCR quality varies page to page and extract.py works
            # per page; a single whole-document file is accepted as a fallback.
            "expected_output": {
                "preferred": f"{path.stem}/page-{{n:04d}}.txt",
                "fallback": f"{path.stem}.txt",
                "encoding": "utf-8",
            },
        }

    queue = sorted(by_hash.values(), key=lambda r: (-r["pages"], r["filename"]))
    out_root.mkdir(parents=True, exist_ok=True)
    manifest_path = out_root / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as handle:
        for record in queue:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    copied = 0
    if args.copy:
        pdf_dir = out_root / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        for record in queue:
            target = pdf_dir / record["filename"]
            if not target.exists():
                shutil.copy2(REPO_ROOT / record["source_path"], target)
                copied += 1

    queued_bytes = sum(r["size_bytes"] for r in queue)
    queued_pages = sum(len(r["pages_needing_ocr"]) for r in queue)
    duplicates = sum(len(r["duplicate_paths"]) for r in queue)

    summary = {
        "threshold_chars_per_page": threshold,
        "pdfs_scanned": len(pdfs),
        "documents": dict(counts),
        "pages_total": pages_total,
        "pages_needing_ocr": pages_needing,
        "pct_pages_needing_ocr": round(100 * pages_needing / max(1, pages_total), 1),
        "queue": {
            "distinct_files": len(queue),
            "duplicate_copies_skipped": duplicates,
            "pages_to_ocr": queued_pages,
            "bytes": queued_bytes,
            "gib": round(queued_bytes / 1024**3, 2),
            "with_document_id": sum(1 for r in queue if r.get("document_id")),
        },
        "unreadable": unreadable,
        "manifest": rel_to_repo(manifest_path),
        "copied_into_package": copied if args.copy else 0,
    }
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    (out_root / "README.md").write_text(_readme(summary, threshold), encoding="utf-8")

    print("\n" + "=" * 64)
    print(f"scanned                     : {len(pdfs)} PDFs, {pages_total} pages")
    print(f"  text_ok                   : {counts['text_ok']}")
    print(f"  mixed (some pages)        : {counts['mixed']}")
    print(f"  image_only                : {counts['image_only']}")
    print(f"  unreadable                : {counts['unreadable']}")
    print(f"pages needing OCR           : {pages_needing}/{pages_total} "
          f"({summary['pct_pages_needing_ocr']}%)")
    print("\nQUEUE (de-duplicated by content hash)")
    print(f"  distinct files            : {len(queue)}")
    print(f"  duplicate copies skipped  : {duplicates}")
    print(f"  pages to OCR              : {queued_pages}")
    print(f"  size                      : {summary['queue']['gib']} GiB")
    print(f"  with document metadata    : {summary['queue']['with_document_id']}/{len(queue)}")
    if args.copy:
        print(f"  copied into package       : {copied}")
    print(f"\nmanifest -> {manifest_path}")
    print(f"summary  -> {summary_path}")
    return 0


def _readme(summary: dict, threshold: int) -> str:
    q = summary["queue"]
    return f"""# OCR work package

{q['distinct_files']} PDF files, {q['pages_to_ocr']} pages, {q['gib']} GiB.

These are the corpus documents with **no extractable text layer**. A page is
queued when it yields fewer than **{threshold} characters** of text.
De-duplicated by content SHA-256, so each distinct file appears once even when
it was crawled into several run directories.

## What to produce

Vietnamese, UTF-8, one of two layouts. **Per-page is strongly preferred** -
OCR quality varies page to page and the ingest pipeline works per page:

```text
ocr-results/
  <pdf-stem>/
    page-0001.txt
    page-0002.txt
    ...
```

Fallback, whole document in one file:

```text
ocr-results/
  <pdf-stem>.txt
```

`<pdf-stem>` is the PDF filename without `.pdf`, exactly as in `manifest.jsonl`
(`filename` field). Do not rename.

## Settings that matter

| Setting | Value | Why |
|---------|-------|-----|
| Language | `vie` | Vietnamese diacritics; without this the text is unusable |
| DPI | 300 | Standard for printed legal text |
| Page segmentation | single column (`--psm 4` in Tesseract) | Matches the gazette layout |
| Encoding | UTF-8 | |

Keep the original line breaks. Do not reflow paragraphs, and do not "tidy"
headings: the ingest parser detects `Điều`, `Khoản` and `Điểm` at line starts,
and reflowing destroys that structure.

## Only some pages need OCR

For files classified `mixed`, `manifest.jsonl` lists the exact pages in
`pages_needing_ocr` (1-indexed). OCR-ing only those pages is enough; the rest
already have a usable text layer. For `image_only` files every page is needed.

## Returning the results

Put `ocr-results/` anywhere and tell me the path. Reintegration runs:

```bash
python -m tools.ingest_ocr_results --results <path-to-ocr-results>
```

That step verifies every returned file against the manifest, reports coverage,
and writes the text into the Silver layer keyed by `document_id`.
"""


if __name__ == "__main__":
    raise SystemExit(main())
