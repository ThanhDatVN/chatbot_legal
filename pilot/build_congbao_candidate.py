"""Build an isolated 10-document native-text candidate from official Công báo PDFs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf

from pilot.collect import OUT, make_chunks, write_jsonl
from pilot.evaluate_data_quality import SAMPLES
from pilot.evaluate_ocr import normalize
from pilot.process_local import load_jsonl
from pilot.structure_v2 import make_structured_sections


def main() -> None:
    inventory = json.loads((OUT / "congbao_candidate_inventory.json").read_text(encoding="utf-8"))
    audits = {x["document_id"]: x for x in json.loads((OUT / "congbao_candidate_audit.json").read_text(encoding="utf-8"))}
    manifest = {x["document_id"]: x for x in load_jsonl(OUT / "manifest.jsonl")}
    output = OUT / "candidate_congbao_all"
    candidate_manifest = []
    all_chunks = 0
    for item in inventory:
        doc_id = item["document_id"]
        audit = audits[doc_id]
        if not item["files"] or not all(part.get("tls_certificate_verified") for part in item["files"]):
            raise RuntimeError(f"Source TLS verification missing: {doc_id}")
        if item.get("error") or audit.get("article_sequence_gaps") or not audit["full_text_preserved"]:
            raise RuntimeError(f"Candidate failed source/structure audit: {doc_id}")
        pages = []
        for part_number, part in enumerate(item["files"], start=1):
            source = Path(part["path"])
            with pymupdf.open(source) as pdf:
                for part_page, page in enumerate(pdf, start=1):
                    raw = page.get_text("text", sort=True)
                    if not raw.strip() and not page.get_images():
                        continue
                    pages.append({
                        "page": len(pages) + 1,
                        "normalized_text": raw,
                        "source_part": part_number,
                        "source_part_page": part_page,
                        "source_pdf_sha256": part["sha256"],
                    })
        sections, warnings = make_structured_sections(pages, doc_id, strict_sequence=True)
        joined_hashes = "|".join(p["sha256"] for p in item["files"])
        candidate_hash = hashlib.sha256(joined_hashes.encode()).hexdigest()
        chunks = make_chunks(doc_id, candidate_hash + "|congbao-native-v1", sections)
        kinds = {(s["section"], s["page_start"]): s["section_kind"] for s in sections}
        for chunk in chunks:
            chunk["section_kind"] = kinds[(chunk["section"], chunk["section_page_start"])]
            chunk["text_quality_status"] = "unreviewed"
            chunk["currency_status"] = "unverified"
            chunk["candidate_source_url"] = item["detail_url"]
            chunk["candidate_sha256"] = candidate_hash
        words = sum(len(p["normalized_text"].split()) for p in pages)
        if words != sum(s["word_count"] for s in sections):
            raise RuntimeError(f"Text loss during sectioning: {doc_id}")
        matched_samples = [
            {"reference_page_in_original_scan": s["page"], "exact_full_passage": normalize(s["reference"]) in normalize("\n".join(p["normalized_text"] for p in pages))}
            for s in SAMPLES if s["document_id"] == doc_id
        ]
        if any(not x["exact_full_passage"] for x in matched_samples):
            raise RuntimeError(f"Reference passage mismatch: {doc_id}")
        write_jsonl(output / "pages" / f"{doc_id}.jsonl", pages)
        write_jsonl(output / "sections" / f"{doc_id}.jsonl", sections)
        write_jsonl(output / "chunks" / f"{doc_id}.jsonl", chunks)
        candidate_manifest.append({
            "document_id": doc_id,
            "document_number": manifest[doc_id]["document_number"],
            "document_type": "Bộ luật" if doc_id == "45_2019_qh14" else manifest[doc_id]["document_type"],
            "document_type_evidence_url": "https://vbpl.vn/bolaodong/Pages/ivbpq-thuoctinh.aspx?ItemID=139264" if doc_id == "45_2019_qh14" else item["detail_url"],
            "source_url": item["detail_url"],
            "source_type": "official_congbao_native_pdf_candidate",
            "source_parts": item["files"],
            "candidate_sha256": candidate_hash,
            "pages": len(pages),
            "blank_pdf_pages_excluded": audit["blank_pdf_pages_excluded"],
            "native_words": words,
            "article_sections": audit["article_section_count"],
            "annex_pages": audit["annex_page_count"],
            "chunks": len(chunks),
            "parser_warnings": warnings,
            "hand_reference_checks": matched_samples,
            "text_quality_status": "unreviewed",
            "currency_status": "unverified",
            "review_status": "candidate_only",
        })
        all_chunks += len(chunks)
        print(doc_id, len(pages), words, len(chunks), flush=True)
    write_jsonl(output / "manifest.jsonl", candidate_manifest)
    summary = {
        "documents": len(candidate_manifest),
        "pages": sum(x["pages"] for x in candidate_manifest),
        "native_words": sum(x["native_words"] for x in candidate_manifest),
        "chunks": all_chunks,
        "exact_hand_reference_passages": sum(x["exact_full_passage"] for row in candidate_manifest for x in row["hand_reference_checks"]),
        "hand_reference_passage_count": len(SAMPLES),
        "document_numbers_exact_in_text": sum(audits[x["document_id"]]["exact_document_number_in_text"] for x in candidate_manifest),
        "document_numbers_space_tolerant_in_text": sum(audits[x["document_id"]]["space_tolerant_document_number_in_text"] for x in candidate_manifest),
        "source_pdf_parts_with_verified_tls": sum(len(x["source_parts"]) for x in candidate_manifest),
        "status": "candidate_only_not_current_qa",
        "limitations": [
            "Native PDF text and section paths have not been fully reviewed against source pages.",
            "Legal currency is unverified at the article level.",
            "18/VBHN-VPQH has extra spacing around the slash in the PDF body; retain original typography in source text.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
