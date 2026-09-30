"""Audit the official Công báo alternate for the damaged 18/VBHN-VPQH PDF."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile

import pymupdf

from pilot.collect import OUT


STEM = OUT / "raw_alternates" / "18_2026_vbhn_vpqh_congbao"
SOURCE = "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm"


def main() -> None:
    pdf_path = STEM.with_suffix(".pdf")
    docx_path = STEM.with_suffix(".docx")
    pdf = pymupdf.open(pdf_path)
    printed_pages = []
    pdf_headings = []
    for page in pdf:
        raw = page.get_text()
        match = re.search(r"CÔNG BÁO/Số[^\n]*\n(\d+)\s*$", raw, re.M)
        printed_pages.append(int(match.group(1)) if match else None)
        pdf_headings.extend(int(x) for x in re.findall(r"^Điều\s+(\d{1,3})\.", raw, re.M))
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = ["".join(p.itertext()) for p in root.findall(".//w:p", ns)]
    docx_headings = []
    for paragraph in paragraphs:
        match = re.match(r"^Điều\s+(\d{1,3})\.", paragraph)
        if match:
            docx_headings.append(int(match.group(1)))
    result = {
        "document_id": "18_2026_vbhn_vpqh",
        "source_url": SOURCE,
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "docx_sha256": hashlib.sha256(docx_path.read_bytes()).hexdigest(),
        "pdf_page_count": len(pdf),
        "pdf_native_word_count": sum(len(p.get_text("words")) for p in pdf),
        "printed_page_numbers": printed_pages,
        "printed_page_breaks": [
            {"pdf_page": i + 2, "previous_printed": a, "next_printed": b}
            for i, (a, b) in enumerate(zip(printed_pages, printed_pages[1:]))
            if a is None or b is None or b != a + 1
        ],
        "pdf_article_headings": sorted(set(pdf_headings)),
        "docx_article_headings": sorted(set(docx_headings)),
        "missing_pdf_articles_1_to_220": sorted(set(range(1, 221)) - set(pdf_headings)),
        "missing_docx_articles_1_to_220": sorted(set(range(1, 221)) - set(docx_headings)),
        "articles_76_to_79_on_pdf": all(x in pdf_headings for x in range(76, 80)),
        "articles_76_to_79_in_docx": all(x in docx_headings for x in range(76, 80)),
        "status": "candidate_only_not_released",
        "note": "PDF article regex is a diagnostic; footnotes and layout may affect counts. Review before release.",
    }
    path = OUT / "alternate_source_audit.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"printed_page_numbers", "pdf_article_headings", "docx_article_headings"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
