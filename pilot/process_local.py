"""Reclassify downloaded PDFs and evaluate an optional OCR branch locally."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pymupdf

from pilot.collect import OUT, extract_pdf, make_chunks, make_sections, normalize_text, scan_like, write_jsonl


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def ocr_pdf(doc_id: str, pdf_path: Path, tessdata: Path) -> list[dict]:
    output = OUT / "ocr_pages" / f"{doc_id}.jsonl"
    output.parent.mkdir(exist_ok=True)
    existing = load_jsonl(output)
    with pymupdf.open(pdf_path) as doc:
        if len(existing) == len(doc):
            print(f"OCR cached {doc_id}: {len(doc)} pages", flush=True)
            return existing
        if existing and [x["page"] for x in existing] != list(range(1, len(existing) + 1)):
            raise ValueError(f"Invalid partial OCR cache: {doc_id}")
        with output.open("a", encoding="utf-8", newline="\n") as handle:
            for index in range(len(existing), len(doc)):
                page = doc[index]
                try:
                    textpage = page.get_textpage_ocr(
                        language="vie", dpi=200, full=True, tessdata=str(tessdata)
                    )
                    # Tesseract's text order is already usable; sort=True scrambles
                    # words on these scans and should not be used for the OCR branch.
                    raw = page.get_text("text", textpage=textpage, sort=False)
                    record = {
                        "page": index + 1, "raw_text": raw,
                        "normalized_text": normalize_text(raw),
                        "word_count": len(raw.split()), "ocr_error": None,
                    }
                except Exception as exc:
                    record = {
                        "page": index + 1, "raw_text": "", "normalized_text": "",
                        "word_count": 0, "ocr_error": f"{type(exc).__name__}: {exc}",
                    }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                existing.append(record)
                if (index + 1) % 10 == 0 or index + 1 == len(doc):
                    print(f"OCR {doc_id}: {index + 1}/{len(doc)}", flush=True)
    return existing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr", action="store_true", help="OCR all image pages with PyMuPDF/Tesseract")
    args = parser.parse_args()
    manifest_path = OUT / "manifest.jsonl"
    manifest = load_jsonl(manifest_path)
    tessdata = (OUT / "tessdata").resolve()
    if args.ocr and not (tessdata / "vie.traineddata").exists():
        raise FileNotFoundError(f"Vietnamese OCR data missing: {tessdata}")

    for record in manifest:
        doc_id = record["document_id"]
        record["source_type"] = "pdf"
        record["language"] = "vi"
        pdf_path = OUT / "raw" / f"{doc_id}.pdf"
        if not pdf_path.exists():
            continue
        pages, stats = extract_pdf(pdf_path.read_bytes())
        write_jsonl(OUT / "pages" / f"{doc_id}.jsonl", pages)
        is_scan = scan_like(stats)
        record.update(stats)
        record["native_status"] = "unsupported_scan" if is_scan else "processed"
        record["status"] = record["native_status"]
        native_sections = [] if is_scan else make_sections(pages)
        native_chunks = make_chunks(doc_id, record["content_sha256"], native_sections)
        write_jsonl(OUT / "chunks" / f"{doc_id}.jsonl", native_chunks)
        record["article_sections"] = sum(s["section"] != "preamble" for s in native_sections)
        record["chunk_count"] = len(native_chunks)
        record["max_section_words"] = max((s["word_count"] for s in native_sections), default=0)
        record["coarse_page_chunks"] = sum(c["page_span_coarse"] for c in native_chunks)
        if args.ocr and is_scan:
            ocr_pages = ocr_pdf(doc_id, pdf_path, tessdata)
            ocr_sections = make_sections(ocr_pages)
            ocr_chunks = make_chunks(doc_id, record["content_sha256"] + "|ocr-vie-fast-200", ocr_sections)
            write_jsonl(OUT / "ocr_chunks" / f"{doc_id}.jsonl", ocr_chunks)
            record.update({
                "ocr_status": "complete_unreviewed" if all(not p["ocr_error"] for p in ocr_pages) else "partial_error",
                "ocr_review_status": "unreviewed",
                "ocr_engine": "PyMuPDF-integrated Tesseract",
                "ocr_language": "vie",
                "ocr_dpi": 200,
                "ocr_model_sha256": hashlib.sha256((tessdata / "vie.traineddata").read_bytes()).hexdigest(),
                "chunker_version": "pilot-article-v2-page-located",
                "ocr_pages": sum(not p["ocr_error"] for p in ocr_pages),
                "ocr_word_count": sum(p["word_count"] for p in ocr_pages),
                "ocr_article_sections": sum(s["section"] != "preamble" for s in ocr_sections),
                "ocr_max_section_words": max((s["word_count"] for s in ocr_sections), default=0),
                "ocr_chunk_count": len(ocr_chunks),
                "ocr_coarse_page_chunks": sum(c["page_span_coarse"] for c in ocr_chunks),
            })
        write_jsonl(manifest_path, manifest)
        print(f"CLASSIFIED {doc_id}: {record['native_status']}, {stats['full_page_image_pages']}/{stats['pages']} image pages", flush=True)

    summary = {
        "sample_count": len(manifest),
        "downloaded_pdf_count": sum((OUT / "raw" / f"{x['document_id']}.pdf").exists() for x in manifest),
        "native_processed": sum(x.get("native_status") == "processed" for x in manifest),
        "native_unsupported_scan": sum(x.get("native_status") == "unsupported_scan" for x in manifest),
        "total_pages": sum(x.get("pages", 0) for x in manifest),
        "total_full_page_image_pages": sum(x.get("full_page_image_pages", 0) for x in manifest),
        "total_native_words": sum(x.get("word_count", 0) for x in manifest),
        "total_native_chunks": sum(x.get("chunk_count", 0) for x in manifest),
        "ocr_complete_unreviewed": sum(x.get("ocr_status") == "complete_unreviewed" for x in manifest),
        "total_ocr_pages": sum(x.get("ocr_pages", 0) for x in manifest),
        "total_ocr_words": sum(x.get("ocr_word_count", 0) for x in manifest),
        "total_ocr_chunks": sum(x.get("ocr_chunk_count", 0) for x in manifest),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
