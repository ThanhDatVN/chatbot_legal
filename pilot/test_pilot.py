from pilot.collect import make_chunks, make_sections, parse_portal_page, scan_like


def test_scan_detection_ignores_footer_text_on_image_pages():
    assert scan_like({"pages": 83, "substantial_text_pages": 0, "full_page_image_pages": 83})
    assert not scan_like({"pages": 83, "substantial_text_pages": 83, "full_page_image_pages": 83})
    assert not scan_like({"pages": 83, "substantial_text_pages": 0, "full_page_image_pages": 0})


def test_portal_metadata_and_attachment_allowlist():
    html = b"""
    <html><head><title>Sample document</title></head><body>
      <table><tr><td class='col1'>S&#7889; k&#253; hi&#7879;u</td><td>01/2026/ND-CP</td></tr></table>
      <a href='https://datafiles.chinhphu.vn/sample.pdf'>official.pdf</a>
      <a href='https://example.com/fake.pdf'>fake.pdf</a>
    </body></html>
    """
    parsed = parse_portal_page(html)
    assert parsed["fields"]["Số ký hiệu"] == "01/2026/ND-CP"
    assert len(parsed["pdf_attachments"]) == 1


def test_article_spans_pages_and_chunk_ids_are_repeatable():
    pages = [
        {"page": 1, "normalized_text": "Mở đầu\nĐiều 1. Nội dung\nDòng thứ nhất"},
        {"page": 2, "normalized_text": "Dòng tiếp theo\nĐiều 2. Phạm vi\nDòng cuối"},
    ]
    sections = make_sections(pages)
    assert [s["section"] for s in sections] == ["preamble", "Điều 1", "Điều 2"]
    assert (sections[1]["page_start"], sections[1]["page_end"]) == (1, 2)
    first = make_chunks("doc", "sourcehash", sections)
    second = make_chunks("doc", "sourcehash", sections)
    assert first == second
    assert len({c["chunk_id"] for c in first}) == len(first)


def test_reference_at_line_start_is_not_a_new_article():
    pages = [{"page": 1, "normalized_text": "Điều 1. Quy định\nĐiều 112 của Bộ luật này vẫn áp dụng."}]
    sections = make_sections(pages)
    assert len(sections) == 1
    assert "Điều 112 của" in sections[0]["text"]


def test_split_article_keeps_the_actual_pages_of_each_chunk():
    pages = [
        {"page": 1, "normalized_text": "Điều 1. Tiêu đề\n" + " ".join(["một"] * 300)},
        {"page": 2, "normalized_text": " ".join(["hai"] * 400)},
    ]
    chunks = make_chunks("doc", "sourcehash", make_sections(pages))
    assert len(chunks) == 2
    assert (chunks[0]["page_start"], chunks[0]["page_end"]) == (1, 2)
    assert (chunks[1]["page_start"], chunks[1]["page_end"]) == (2, 2)
