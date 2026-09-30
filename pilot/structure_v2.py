"""Conservative page-aware structural experiment for scanned legal PDFs.

This parser fixes confirmed article/annex confusions. All output stays unreviewed.
"""

from __future__ import annotations

import json
import re

from pilot.collect import OUT, make_chunks, write_jsonl
from pilot.process_local import load_jsonl


ARTICLE = re.compile(r"^[\s`'\-–—:;]*Đi[ềê]u\s+(\d+[a-zA-Z]?)[.:]\s*(.*)$", re.IGNORECASE)
ANNEX_HEADING = re.compile(
    r"^.{0,12}Phụ\s*lục\s*(?:[IVXLCDM\d]+)?[.:]?\s*$", re.IGNORECASE
)
FORM = re.compile(r"^\s*Mẫu\s*số", re.IGNORECASE)
# Page 5 was checked against the source image: the annex heading is obscured
# by the seal and missed by OCR. Keep this explicit instead of guessing pages.
ANNEX_PAGE_OVERRIDES = {"74_2024_nd_cp": 5}
# Exact OCR heading read as Ø7. The image of PDF page 70 was inspected; it
# reads "Điều 97". Only the structural label is repaired, not the OCR source.
HEADING_OVERRIDES = {
    ("145_2020_nd_cp", 70, "Điều Ø7. Quản lý hòa giải viên lao động"): 97,
}


def first_annex_line(lines: list[str]) -> int | None:
    """Find a heading or compact form inventory near the start of a page."""
    head = lines[:25]
    for index, line in enumerate(head):
        if ANNEX_HEADING.match(line.strip()):
            return index
    form_indices = [index for index, line in enumerate(head) if FORM.match(line)]
    if len(form_indices) >= 3:
        return form_indices[0]
    return None


def finish(section: dict, output: list[dict]) -> None:
    if not section["lines"]:
        return
    located = section.pop("lines")
    blocks = []
    for page, line in located:
        if not blocks or blocks[-1]["page"] != page:
            blocks.append({"page": page, "lines": []})
        blocks[-1]["lines"].append(line)
    section["page_blocks"] = [
        {"page": block["page"], "text": "\n".join(block["lines"])} for block in blocks
    ]
    section["text"] = "\n".join(line for _, line in located)
    section["word_count"] = len(section["text"].split())
    output.append(section)


def make_structured_sections(
    pages: list[dict], doc_id: str = "", strict_sequence: bool = False
) -> tuple[list[dict], list[dict]]:
    sections: list[dict] = []
    warnings: list[dict] = []
    current = {
        "section": "preamble", "section_kind": "preamble",
        "page_start": 1, "page_end": 1, "lines": [],
    }
    last_article = 0
    in_annex = False
    for page in pages:
        number = page["page"]
        lines = page["normalized_text"].splitlines()
        annex_line = first_annex_line(lines) if not in_annex else 0
        if not in_annex and number == ANNEX_PAGE_OVERRIDES.get(doc_id):
            annex_line = 0
            warnings.append({
                "issue": "annex_boundary_checked_on_source_image", "page": number,
            })
        for index, line in enumerate(lines):
            if not in_annex and annex_line is not None and index == annex_line:
                finish(current, sections)
                current = {
                    "section": f"Phụ lục, trang {number}", "section_kind": "annex",
                    "page_start": number, "page_end": number, "lines": [],
                }
                in_annex = True
            if in_annex and current["page_start"] != number:
                finish(current, sections)
                current = {
                    "section": f"Phụ lục, trang {number}", "section_kind": "annex",
                    "page_start": number, "page_end": number, "lines": [],
                }
            if not in_annex:
                match = ARTICLE.match(line)
                override = HEADING_OVERRIDES.get((doc_id, number, line.strip()))
                if match or override is not None:
                    article = override if override is not None else int(re.match(r"\d+", match.group(1)).group())
                    if override is not None:
                        warnings.append({
                            "issue": "heading_number_checked_on_source_image",
                            "page": number, "ocr_heading": line.strip(),
                            "corrected_article": override,
                        })
                    if article > last_article and (
                        not strict_sequence or last_article == 0 or article == last_article + 1
                    ):
                        if last_article and article != last_article + 1:
                            warnings.append({
                                "issue": "article_sequence_gap", "page": number,
                                "previous": last_article, "observed": article,
                            })
                        finish(current, sections)
                        current = {
                            "section": f"Điều {override if override is not None else match.group(1)}",
                            "section_kind": "main_text",
                            "contains_quoted_amendment": bool(re.search(
                                r"sửa đổi|bổ sung", match.group(2) if match else line,
                                re.IGNORECASE,
                            )),
                            "page_start": number, "page_end": number, "lines": [],
                        }
                        last_article = article
                    elif strict_sequence and article > last_article + 1:
                        warnings.append({
                            "issue": "nonconsecutive_article_heading_unresolved", "page": number,
                            "previous": last_article, "observed": article,
                        })
                    elif article < last_article:
                        warnings.append({
                            "issue": "embedded_article_heading", "page": number,
                            "current_article": last_article, "observed": article,
                        })
            current["lines"].append((number, line))
            current["page_end"] = number
    finish(current, sections)
    return sections, warnings


def main() -> None:
    manifest = load_jsonl(OUT / "manifest.jsonl")
    all_warnings = []
    summary = []
    for document in manifest:
        doc_id = document["document_id"]
        pages = load_jsonl(OUT / "ocr_pages" / f"{doc_id}.jsonl")
        sections, warnings = make_structured_sections(pages, doc_id)
        chunks = make_chunks(doc_id, document["content_sha256"] + "|structured-v2", sections)
        # make_chunks emits chunks in section order, but no section index; attach
        # kind via the section's page/label combination, with annex pages unique.
        key_to_kind = {(s["section"], s["page_start"]): s["section_kind"] for s in sections}
        for chunk in chunks:
            chunk["section_kind"] = key_to_kind[(chunk["section"], chunk["section_page_start"])]
            chunk["text_quality_status"] = "unreviewed"
            chunk["currency_status"] = "unverified"
        write_jsonl(OUT / "structured_sections_v2" / f"{doc_id}.jsonl", sections)
        write_jsonl(OUT / "structured_chunks_v2" / f"{doc_id}.jsonl", chunks)
        for warning in warnings:
            all_warnings.append({"document_id": doc_id, **warning})
        summary.append({
            "document_id": doc_id,
            "main_articles": sum(s["section_kind"] == "main_text" for s in sections),
            "annex_pages": sum(s["section_kind"] == "annex" for s in sections),
            "max_section_words": max(s["word_count"] for s in sections),
            "chunks": len(chunks),
            "warnings": len(warnings),
        })
    write_jsonl(OUT / "structured_warnings_v2.jsonl", all_warnings)
    output = {"parser_version": "pilot-structured-v2", "documents": summary, "warning_count": len(all_warnings)}
    (OUT / "structured_summary_v2.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
