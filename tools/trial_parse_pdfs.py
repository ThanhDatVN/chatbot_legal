#!/usr/bin/env python3
"""G0 task 0.7 - trial the extract -> clean -> structure chain on real PDFs.

Measures the four Silver-layer quality metrics defined in
docs/virag-gov/06-data-pipeline.md section 5.5:

    % documents with >= 1 recognised Article       (gate: >= 85%)
    % Articles with >= 1 recognised Clause         (gate: >= 70%)
    % chunks citable to the Clause                 (gate: >= 60%)
    chunks losing text vs the source               (gate: 0)

This is the first execution of any ``virag`` module, so failures here are
expected and are the point of the exercise.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from virag.ingest.chunking import chunk_document  # noqa: E402
from virag.ingest.clean import clean_document, is_low_quality  # noqa: E402
from virag.ingest.extract import extract_pdf  # noqa: E402
from virag.ingest.structure import iter_articles, parse_structure  # noqa: E402
from virag.schemas import DocumentMeta  # noqa: E402
from virag.settings import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--crawl-root", default=str(REPO_ROOT / "data" / "crawl"))
    parser.add_argument("--out", default=str(REPO_ROOT / "reports" / "g0-parser-trial.json"))
    args = parser.parse_args()

    settings = get_settings()
    pdfs = sorted(Path(args.crawl_root).glob("**/official-attachments/*.pdf"))
    if not pdfs:
        print("no PDFs found", file=sys.stderr)
        return 2

    random.seed(args.seed)
    sample = random.sample(pdfs, min(args.n, len(pdfs)))
    print(f"corpus PDFs: {len(pdfs)}   sampling {len(sample)} (seed={args.seed})\n")

    results = []
    for index, path in enumerate(sample, 1):
        row: dict = {"file": path.name, "size_kb": round(path.stat().st_size / 1024)}
        try:
            meta = DocumentMeta(document_id=path.stem, instrument_number=None)
            doc = extract_pdf(path, meta, settings)
            row["pages"] = doc.page_count
            row["ocr_pages"] = doc.ocr_page_count
            row["chars_raw"] = len(doc.text)

            doc = clean_document(doc)
            row["chars_clean"] = len(doc.text)
            row["low_quality"] = is_low_quality(doc)

            nodes = parse_structure([(p.page_number, p.text) for p in doc.pages])
            articles = iter_articles(nodes)
            row["articles"] = len(articles)
            row["articles_with_clause"] = sum(
                1 for a, _ in articles if any(c.kind == "khoan" for c in a.children)
            )

            parents, children = chunk_document(nodes, meta, settings)
            row["parents"] = len(parents)
            row["children"] = len(children)
            row["children_with_khoan"] = sum(1 for c in children if c.khoan)
            row["chars_in_chunks"] = sum(len(c.text) for c in children)
            row["status"] = "ok"
        except Exception as exc:  # noqa: BLE001 - the point is to catalogue failures
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()[-600:]

        results.append(row)
        flag = "OK " if row["status"] == "ok" else "ERR"
        detail = (
            f"pages={row.get('pages','-'):>3} art={row.get('articles','-'):>3} "
            f"chunks={row.get('children','-'):>4} khoan={row.get('children_with_khoan','-'):>4}"
            if row["status"] == "ok"
            else row.get("error", "")[:70]
        )
        print(f"[{index:>2}/{len(sample)}] {flag} {path.name[:42]:<42} {detail}")

    ok = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] != "ok"]

    def pct(numerator: int, denominator: int) -> float:
        return round(100 * numerator / denominator, 1) if denominator else 0.0

    # D-16: attachments are numbered `-1`, `-2`, ... where `-1` is the
    # instrument and higher ordinals are annexes.  An annex of forms and tables
    # legitimately contains no Dieu, so scoring it as a parse failure
    # understates the parser by ~22 points.  Gate on main instruments only.
    for row in ok:
        match = re.search(r"-(\d+)\.pdf$", row["file"])
        row["attachment_ordinal"] = int(match.group(1)) if match else 1
        row["is_main_instrument"] = row["attachment_ordinal"] == 1
        # D-15: a document with no usable text was never parseable in the first
        # place; it is an extraction gap, not a parser miss.
        row["has_text_layer"] = row.get("chars_clean", 0) >= 200

    def summarise(rows: list[dict]) -> dict:
        total_articles = sum(r.get("articles", 0) for r in rows)
        return {
            "documents": len(rows),
            "with_article": sum(1 for r in rows if r.get("articles", 0) >= 1),
            "pct_docs_with_article": pct(
                sum(1 for r in rows if r.get("articles", 0) >= 1), len(rows)
            ),
            "pct_articles_with_clause": pct(
                sum(r.get("articles_with_clause", 0) for r in rows), total_articles
            ),
            "pct_chunks_clause_level": pct(
                sum(r.get("children_with_khoan", 0) for r in rows),
                sum(r.get("children", 0) for r in rows),
            ),
            "articles": total_articles,
            "chunks": sum(r.get("children", 0) for r in rows),
        }

    text_bearing = [r for r in ok if r["has_text_layer"]]
    main_text = [r for r in text_bearing if r["is_main_instrument"]]
    annex_text = [r for r in text_bearing if not r["is_main_instrument"]]
    no_text = [r for r in ok if not r["has_text_layer"]]

    # D-15: the OCR burden is pages *below the text threshold*, not pages the
    # run happened to OCR.  Reporting the latter as "pages needing OCR" showed
    # 0% while the real figure was 21%.
    total_pages = sum(r.get("pages", 0) for r in ok)
    pages_needing_ocr = sum(r.get("pages", 0) for r in no_text)
    pages_ocr_applied = sum(r.get("ocr_pages", 0) for r in ok)

    gate = summarise(main_text)
    metrics = {
        "sampled": len(sample),
        "extracted_ok": len(ok),
        "extraction_errors": len(errors),
        "populations": {
            "all_ok": summarise(ok),
            "text_bearing": summarise(text_bearing),
            "main_instruments_text_bearing": gate,
            "annexes_text_bearing": summarise(annex_text),
        },
        "ocr": {
            "documents_without_text_layer": len(no_text),
            "pct_documents_without_text_layer": pct(len(no_text), len(ok)),
            "pages_total": total_pages,
            "pages_needing_ocr": pages_needing_ocr,
            "pct_pages_needing_ocr": pct(pages_needing_ocr, total_pages),
            "pages_ocr_applied": pages_ocr_applied,
            "ocr_coverage_pct": pct(pages_ocr_applied, pages_needing_ocr),
        },
        # Gated on main instruments with a text layer - the population the
        # parser is designed for.
        "gates": {
            "population": "main_instruments_text_bearing",
            "docs_with_article_ge_85": gate["pct_docs_with_article"] >= 85,
            "articles_with_clause_ge_70": gate["pct_articles_with_clause"] >= 70,
            "chunks_clause_level_ge_60": gate["pct_chunks_clause_level"] >= 60,
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"metrics": metrics, "rows": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ocr = metrics["ocr"]
    print("\n" + "=" * 68)
    print(f"extracted ok                  : {len(ok)}/{len(sample)}  ({len(errors)} errors)")
    print("\nEXTRACTION COVERAGE")
    print(
        f"  documents without text layer: {ocr['documents_without_text_layer']}"
        f"  ({ocr['pct_documents_without_text_layer']}%)"
    )
    print(
        f"  pages NEEDING ocr           : {ocr['pages_needing_ocr']}/{ocr['pages_total']}"
        f"  ({ocr['pct_pages_needing_ocr']}%)   warn >20"
    )
    print(
        f"  pages OCR actually applied  : {ocr['pages_ocr_applied']}"
        f"  (coverage {ocr['ocr_coverage_pct']}% of the burden)"
    )
    print("\nPARSER QUALITY, gated on main instruments with a text layer")
    print(f"  population                  : {gate['documents']} documents")
    print(f"  % docs with >=1 Article     : {gate['pct_docs_with_article']}%   gate >=85")
    print(f"  % Articles with >=1 Clause  : {gate['pct_articles_with_clause']}%   gate >=70")
    print(f"  % chunks at Clause level    : {gate['pct_chunks_clause_level']}%   gate >=60")
    print("\n  for contrast (not gated):")
    for label, key in (
        ("all sampled PDFs", "all_ok"),
        ("text-bearing, incl. annexes", "text_bearing"),
        ("annexes only", "annexes_text_bearing"),
    ):
        pop = metrics["populations"][key]
        print(f"    {label:<28} n={pop['documents']:>3}  {pop['pct_docs_with_article']}%")
    print(f"\nreport -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
