"""Reproducible quality inventory for the 10-document pilot snapshot.

Counts describe the pilot artifacts. They do not certify legal currency or OCR.
"""

from __future__ import annotations

from collections import Counter
import json

from pilot.collect import OUT


REQUIRED_PROVENANCE = (
    "document_id", "title", "document_number", "document_type", "publisher",
    "source_url", "content_url", "downloaded_at", "html_sha256",
    "content_sha256", "license", "source_type", "language",
)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def assess():
    manifest = read_jsonl(OUT / "manifest.jsonl")
    audits = read_jsonl(OUT / "quality_audit.jsonl")
    ocr_sample = json.loads((OUT / "data_quality_metrics.json").read_text(encoding="utf-8"))
    source_integrity = json.loads((OUT / "source_integrity_findings.json").read_text(encoding="utf-8"))
    candidate_path = OUT / "candidate_congbao_all" / "summary.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path.exists() else None
    legal_leads_path = OUT / "legal_status_leads.json"
    legal_leads = json.loads(legal_leads_path.read_text(encoding="utf-8")) if legal_leads_path.exists() else None
    missing_by_document = {}
    identifier_matches = []
    chunk_counts = Counter()
    page_count = ocr_page_count = total_words = 0
    all_chunks = []

    for item in manifest:
        doc_id = item["document_id"]
        missing = [field for field in REQUIRED_PROVENANCE if not item.get(field)]
        if missing:
            missing_by_document[doc_id] = missing
        pages = read_jsonl(OUT / "ocr_pages" / f"{doc_id}.jsonl")
        chunks = read_jsonl(OUT / "ocr_chunks" / f"{doc_id}.jsonl")
        all_chunks.extend(chunks)
        page_count += item["pages"]
        ocr_page_count += len(pages)
        total_words += item["ocr_word_count"]
        number = item["document_number"]
        exact_first = number in pages[0]["normalized_text"]
        exact_anywhere = any(number in page["normalized_text"] for page in pages)
        identifier_matches.append({
            "document_id": doc_id,
            "document_number": number,
            "exact_in_first_ocr_page": exact_first,
            "exact_in_any_ocr_page": exact_anywhere,
        })
        chunk_counts[doc_id] = len(chunks)

    audit_counts = Counter(item["issue"] for item in audits)
    result = {
        "snapshot": OUT.name,
        "document_count": len(manifest),
        "provenance": {
            "required_fields": list(REQUIRED_PROVENANCE),
            "documents_with_all_required_fields": len(manifest) - len(missing_by_document),
            "missing_by_document": missing_by_document,
            "licenses_unconfirmed": sum(item["license"] == "publicly_accessible_unknown_license" for item in manifest),
        },
        "content": {
            "pdf_page_count": page_count,
            "full_page_image_page_count": sum(item["full_page_image_pages"] for item in manifest),
            "native_word_count": sum(item["word_count"] for item in manifest),
            "native_chunk_count": sum(item["chunk_count"] for item in manifest),
            "ocr_page_count": ocr_page_count,
            "ocr_word_count": total_words,
            "ocr_unreviewed_document_count": sum(item["ocr_review_status"] == "unreviewed" for item in manifest),
            "ocr_sample": {
                "excerpt_count": ocr_sample["sample_count"],
                "reference_word_count": ocr_sample["pooled_reference_words"],
                "character_error_rate": ocr_sample["pooled_character_error_rate"],
                "word_error_rate": ocr_sample["pooled_word_error_rate"],
                "selection": "deliberately selected short excerpts; not a corpus estimate",
            },
            "identifier_check": {
                "exact_first_page_count": sum(x["exact_in_first_ocr_page"] for x in identifier_matches),
                "exact_any_page_count": sum(x["exact_in_any_ocr_page"] for x in identifier_matches),
                "documents": identifier_matches,
                "interpretation": "Exact string check only; a miss is a review trigger, not proof of OCR error.",
            },
        },
        "structure": {
            "experimental_ocr_chunk_count": len(all_chunks),
            "chunks_below_100_words": sum(c["word_count"] < 100 for c in all_chunks),
            "chunks_100_to_600_words": sum(100 <= c["word_count"] <= 600 for c in all_chunks),
            "chunks_above_600_words": sum(c["word_count"] > 600 for c in all_chunks),
            "chunks_with_coarse_page_span": sum(c["page_span_coarse"] for c in all_chunks),
            "audit_warning_count": len(audits),
            "audit_warning_counts_by_type": dict(sorted(audit_counts.items())),
            "audit_open_count": sum(a["review_status"] == "open" for a in audits),
            "interpretation": "Warnings may overlap and are not confirmed errors.",
        },
        "legal_currency": {
            "unverified_document_count": sum(item["legal_status"] == "unverified" for item in manifest),
            "pilot_only_document_count": sum(item["review_status"] == "pilot_only" for item in manifest),
            "verified_current_document_count": sum(item["legal_status"] == "verified_current" for item in manifest),
        },
        "source_integrity": {
            "confirmed_issue_count": sum(x["confirmed"] for x in source_integrity["findings"]),
            "affected_document_ids": sorted({
                x["document_id"] for x in source_integrity["findings"] if x["confirmed"]
            }),
            "issues": source_integrity["findings"],
        },
        "official_native_text_candidate": candidate,
        "legal_status_triage": {
            "records": len(legal_leads["records"]),
            "status_lead_counts": dict(Counter(x["source_status_lead"] for x in legal_leads["records"])),
            "verified_current_document_count": legal_leads["verified_current_document_count"],
            "note": legal_leads["purpose"],
        } if legal_leads else None,
        "current_qa_index_eligible_document_count": sum(
            item["ocr_review_status"] == "verified"
            and item["legal_status"] == "verified_current"
            and item["document_id"] not in {
                x["document_id"] for x in source_integrity["findings"] if x["confirmed"]
            }
            for item in manifest
        ),
    }
    result["readiness"] = (
        "eligible" if result["current_qa_index_eligible_document_count"] == len(manifest)
        else "blocked"
    )
    result["readiness_reason"] = (
        "All documents passed document-level OCR and legal-status gates."
        if result["readiness"] == "eligible"
        else "At least one document has unreviewed OCR, unverified legal status, or a confirmed source-integrity defect."
    )
    return result


def main():
    result = assess()
    path = OUT / "data_quality_summary.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
