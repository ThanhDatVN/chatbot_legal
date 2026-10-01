from pathlib import Path

from ingestion.chunk import chunk_document
from ingestion.html_parser import read_html_layout
from ingestion.models import SectionKind
from ingestion.structure import parse_document
from ingestion.tokenizer import TokenCounter
from tests.unit.test_ingestion_structure import registry_doc

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "html" / "sample_act.html"


def parsed():
    return parse_document(read_html_layout("doc", FIXTURE))


def test_navigation_scripts_ads_and_footer_are_removed():
    text = parsed().text
    for noise in ("Trang chủ", "Quảng cáo", "Bản quyền", "script không được lọt", "Văn bản liên quan"):
        assert noise not in text


def test_structure_matches_the_pdf_parser():
    doc = parsed()
    mains = [s for s in doc.sections if s.kind == SectionKind.MAIN_TEXT]
    assert [s.article_number for s in mains] == [1, 2, 3]
    assert mains[0].path[0] == "Chương I. QUY ĐỊNH CHUNG"
    assert mains[1].title == "Mức lương tối thiểu" and mains[1].contains_table
    assert any(s.kind == SectionKind.SIGNATURE for s in doc.sections)
    assert "Điều 91 của Bộ luật" in doc.section_text(mains[0])


def test_html_tables_keep_column_labels_through_rowspan_and_colspan():
    doc = parsed()
    art2 = next(s for s in doc.sections if s.article_number == 2)
    text = doc.section_text(art2)
    assert "Vùng: Vùng I; Mức lương tối thiểu – Tháng: 5.310.000; Mức lương tối thiểu – Giờ: 25.500" in text


def test_html_chunks_have_exact_offsets():
    doc = parsed()
    chunks = chunk_document(doc, registry_doc(), "snap", TokenCounter())
    assert chunks
    for c in chunks:
        assert doc.text[c.source_start_char:c.source_end_char] == c.raw_text
        assert (c.page_start, c.page_end) == (1, 1)
