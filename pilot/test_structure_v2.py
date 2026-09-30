from pilot.structure_v2 import first_annex_line, make_structured_sections


def test_reference_to_annex_does_not_start_annex_but_heading_does():
    assert first_annex_line(["Phụ lục ban hành kèm theo Nghị định này."]) is None
    assert first_annex_line(["Con dấu", "Phụ lục I", "Danh mục"]) == 1


def test_quoted_article_remains_inside_amending_article():
    pages = [
        {"page": 1, "normalized_text": "Điều 218. Nội dung\n- Điều 219. Sửa đổi luật khác\nĐiều 55. Quy định được trích"},
        {"page": 2, "normalized_text": "Điều 220. Hiệu lực"},
    ]
    sections, warnings = make_structured_sections(pages, strict_sequence=True)
    assert [s["section"] for s in sections] == ["Điều 218", "Điều 219", "Điều 220"]
    assert "Điều 55" in sections[1]["text"]
    assert any(w["issue"] == "embedded_article_heading" for w in warnings)


def test_annex_forms_do_not_become_main_articles():
    pages = [
        {"page": 1, "normalized_text": "Điều 1. Nội dung\nThân văn bản"},
        {"page": 2, "normalized_text": "Phụ lục\nMẫu số 01\nĐiều 1. Mẫu hợp đồng"},
        {"page": 3, "normalized_text": "Điều 2. Quyết định mẫu"},
    ]
    sections, _ = make_structured_sections(pages)
    assert [s["section"] for s in sections if s["section_kind"] == "main_text"] == ["Điều 1"]
    assert [s["page_start"] for s in sections if s["section_kind"] == "annex"] == [2, 3]


def test_ocr_punctuation_and_missing_accent_do_not_hide_heading():
    pages = [{"page": 1, "normalized_text": "Điều 1. A\n` Điều 2. B\nĐiêu 3. C"}]
    sections, warnings = make_structured_sections(pages)
    assert [s["section"] for s in sections] == ["Điều 1", "Điều 2", "Điều 3"]
    assert not warnings


def test_distant_article_reference_stays_with_current_article():
    pages = [{"page": 1, "normalized_text": "Điều 1. Sửa đổi\nĐiều 68.\nĐiều 2. Hiệu lực"}]
    sections, warnings = make_structured_sections(pages, strict_sequence=True)
    assert [s["section"] for s in sections] == ["Điều 1", "Điều 2"]
    assert "Điều 68." in sections[0]["text"]
    assert any(w["issue"] == "nonconsecutive_article_heading_unresolved" for w in warnings)
