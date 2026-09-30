"""Build an immutable corpus snapshot from the registry.

    python -m ingestion.build --snapshot-id corpus-2026-09-30

Writes data/snapshots/<id>/ and exits non-zero when any hard quality gate fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from ingestion.chunk import CHUNKER_VERSION, MAX_TOKENS, chunk_document, sha
from ingestion.currency import apply_text_reviews, assign_currency, load_reviews
from ingestion.layout import read_layout
from ingestion.models import Registry
from ingestion.quality import check_document, chunk_problems
from ingestion.structure import parse_document
from ingestion.tokenizer import TokenCounter

ROOT = Path(__file__).resolve().parents[1]
PARSER_VERSION = "layout-structure-v3"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build(registry_path: Path, snapshot_id: str, out_root: Path, review_dir: Path, fixtures_path: Path) -> int:
    registry = Registry.model_validate_json(registry_path.read_text(encoding="utf-8"))
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8")) if fixtures_path.exists() else {}
    currency_reviews = load_reviews(review_dir / "currency_reviews.json")
    text_reviews = load_reviews(review_dir / "text_reviews.json")
    counter = TokenCounter()
    out = out_root / snapshot_id
    (out / "texts").mkdir(parents=True, exist_ok=True)

    all_chunks, all_sections, all_notes, doc_rows, quality_rows = [], [], [], [], []
    for doc in registry.documents:
        paths = [ROOT / part.path for part in doc.source_parts]
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            print(f"[{doc.document_id}] missing source files: {missing}. Run scripts/download_sources.py first.")
            return 2
        hashes_ok = all(file_sha256(p) == part.sha256 for p, part in zip(paths, doc.source_parts))
        layout = read_layout(doc.document_id, paths)
        parsed = parse_document(layout)
        chunks = chunk_document(parsed, doc, snapshot_id, counter)
        quality = check_document(doc, layout, parsed, chunks, hashes_ok, fixtures)
        footnote_texts = [fn.text[:80] for fn in parsed.footnotes]
        final = []
        for chunk in chunks:
            status, basis = assign_currency(chunk, doc, registry.documents, registry.as_of_date, currency_reviews)
            machine_ok = quality.passed and not chunk_problems(chunk, footnote_texts)
            final.append(chunk.model_copy(update={
                "currency_status": status, "currency_basis": basis,
                "text_quality_status": apply_text_reviews(chunk, text_reviews, machine_ok)}))
        all_chunks.extend(final)
        all_sections.extend(s.model_dump(mode="json") for s in parsed.sections)
        all_notes.extend(fn.model_dump(mode="json") for fn in parsed.footnotes)
        (out / "texts" / f"{doc.document_id}.txt").write_text(parsed.text, encoding="utf-8", newline="\n")
        doc_rows.append({**doc.model_dump(mode="json"), "pages_with_text": len(layout.pages),
                         "main_articles": quality.details["main_articles"], "chunks": len(final),
                         "text_sha256": sha(parsed.text)})
        quality_rows.append({"document_id": doc.document_id, "passed": quality.passed, "hard": quality.hard,
                             "details": quality.details, "soft": quality.soft,
                             "chunk_failures": quality.chunk_failures})
        status = "PASS" if quality.passed else "FAIL"
        failed = [k for k, v in quality.hard.items() if not v]
        print(f"[{status}] {doc.document_id}: {len(final)} chunks, {quality.details['main_articles']} articles"
              + (f", failed gates: {failed}" if failed else ""))

    ids = [c.chunk_id for c in all_chunks]
    duplicate_ids = len(ids) - len(set(ids))
    write_jsonl(out / "chunks.jsonl", [c.model_dump(mode="json") for c in all_chunks])
    write_jsonl(out / "sections.jsonl", all_sections)
    write_jsonl(out / "amendment_notes.jsonl", all_notes)
    write_jsonl(out / "documents.jsonl", doc_rows)
    status_counts: dict[str, int] = {}
    for c in all_chunks:
        key = f"{c.currency_status.value}/{c.text_quality_status.value}"
        status_counts[key] = status_counts.get(key, 0) + 1
    passed = all(q["passed"] for q in quality_rows) and duplicate_ids == 0
    report = {"snapshot_id": snapshot_id, "passed": passed, "duplicate_chunk_ids": duplicate_ids,
              "documents": quality_rows, "chunk_status_counts": dict(sorted(status_counts.items()))}
    (out / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str),
                                             encoding="utf-8")
    manifest = {"snapshot_id": snapshot_id, "as_of_date": str(registry.as_of_date),
                "registry_version": registry.registry_version, "parser_version": PARSER_VERSION,
                "chunker_version": CHUNKER_VERSION, "max_tokens": MAX_TOKENS, "tokenizer": counter.name,
                "documents": [{"document_id": d["document_id"], "chunks": d["chunks"], "text_sha256": d["text_sha256"],
                               "source_sha256": [p["sha256"] for p in d["source_parts"]]} for d in doc_rows],
                "chunk_count": len(all_chunks),
                "chunks_sha256": file_sha256(out / "chunks.jsonl"),
                "quality_passed": passed}
    (out / "snapshot.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"snapshot {snapshot_id}: {len(all_chunks)} chunks, quality {'PASSED' if passed else 'FAILED'}")
    print("status counts:", json.dumps(status_counts, ensure_ascii=False))
    return 0 if passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "data" / "corpus" / "registry.json")
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "snapshots")
    parser.add_argument("--reviews", type=Path, default=ROOT / "data" / "review")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "data" / "corpus" / "regression_fixtures.json")
    args = parser.parse_args()
    sys.exit(build(args.registry, args.snapshot_id, args.out, args.reviews, args.fixtures))


if __name__ == "__main__":
    main()
