"""Create a reviewer queue from OCR and structural warning signals."""

from __future__ import annotations

import collections
import json
import re

from pilot.collect import OUT, make_sections, write_jsonl


ANNEX_HINT = re.compile(r"^\s*(?:Phụ\s*lục|Mẫu\s*số\s*\d+)", re.IGNORECASE)


def load(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    findings = []
    for document in load(OUT / "manifest.jsonl"):
        doc_id = document["document_id"]
        pages = load(OUT / "ocr_pages" / f"{doc_id}.jsonl")
        sections = make_sections(pages)
        article_pages = collections.defaultdict(list)
        for section in sections:
            if section["section"] != "preamble":
                article_pages[section["section"]].append(section["page_start"])
            if section["word_count"] > 1200:
                findings.append({
                    "document_id": doc_id, "issue": "long_section",
                    "section": section["section"], "page_start": section["page_start"],
                    "page_end": section["page_end"], "word_count": section["word_count"],
                    "review_status": "open",
                })
        for section, starts in article_pages.items():
            if len(starts) > 1:
                findings.append({
                    "document_id": doc_id, "issue": "duplicate_article_heading",
                    "section": section, "pages": starts, "review_status": "open",
                })
        for page in pages:
            if page["word_count"] < 100:
                findings.append({
                    "document_id": doc_id, "issue": "low_ocr_text_page",
                    "page": page["page"], "word_count": page["word_count"],
                    "review_status": "open",
                })
            if any(ANNEX_HINT.match(line) for line in page["normalized_text"].splitlines()):
                findings.append({
                    "document_id": doc_id, "issue": "annex_or_form_hint",
                    "page": page["page"], "review_status": "open",
                })
    write_jsonl(OUT / "quality_audit.jsonl", findings)
    counts = collections.Counter(item["issue"] for item in findings)
    print(json.dumps({"total_findings": len(findings), "by_issue": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
