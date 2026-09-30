from ingestion.chunk import MAX_TOKENS, chunk_document
from ingestion.layout import DocumentLayout, Line, PageStats, RawFootnote
from ingestion.models import Registry, SectionKind
from ingestion.structure import parse_document, parse_footnote_text
from ingestion.tokenizer import TokenCounter

MARGIN, INDENT, RIGHT = 64.0, 92.0, 530.0


def line(page: int, y: float, text: str, x0: float = MARGIN, x1: float = RIGHT, markers=None) -> Line:
    return Line(page=page, part=1, part_page=page, x0=x0, y0=y, x1=x1, y1=y + 14, text=text, size=14, bold=False,
                markers=markers or [])


def para(page: int, y: float, *texts: str) -> list[Line]:
    """Justified paragraph as in Công báo PDFs: indented full first line, short last line at the margin."""
    if len(texts) == 1:
        words = texts[0].split()
        cut = max(1, len(words) // 2)
        texts = (" ".join(words[:cut]), " ".join(words[cut:])) if len(words) > 1 else texts
    out = []
    for k, t in enumerate(texts):
        last = k == len(texts) - 1
        out.append(line(page, y + 9 * k, t, x0=INDENT if k == 0 else MARGIN, x1=300 if last else RIGHT))
    return out


def layout(lines: list[Line], footnotes=None) -> DocumentLayout:
    pages = sorted({ln.page for ln in lines})
    return DocumentLayout(document_id="doc", body_size=14, lines=lines, footnotes=footnotes or [],
                          pages=[PageStats(page=p, part=1, part_page=p) for p in pages], tables=[], blank_pages=[])


def registry_doc():
    reg = Registry.model_validate({
        "registry_version": "t", "as_of_date": "2026-09-30",
        "documents": [{
            "document_id": "doc", "document_number": "1/2020/NĐ-CP", "title": "Nghị định thử", "short_title": "NĐ thử",
            "document_type": "Nghị định", "issuer": "Chính phủ", "issued_date": "2020-01-01", "effective_date": None,
            "source_url": "https://example.gov.vn/doc", "publisher": "p", "license": "l",
            "source_parts": [{"label": "a", "download_url": "https://example.gov.vn/a.pdf", "path": "a.pdf",
                              "sha256": "0" * 64, "pages": 3}],
            "scope": "in_scope", "corpus_use": "current", "corpus_use_reason": "r", "expected_main_articles": 3,
            "downloaded_at": "2026-09-24T00:00:00Z"}]})
    return reg.documents[0]


def sample_lines() -> list[Line]:
    lines = []
    lines += [line(1, 60, "CHÍNH PHỦ", x0=250, x1=330)]
    lines += para(1, 90, "Căn cứ Bộ luật Lao động ngày 20 tháng 11 năm 2019;")
    lines += [line(1, 130, "Chương I", x0=270, x1=320), line(1, 150, "QUY ĐỊNH CHUNG", x0=230, x1=360)]
    lines += para(1, 180, "Điều 1. Phạm vi điều chỉnh")
    lines += para(1, 200, "Nghị định này quy định chi tiết Điều 112 của Bộ luật Lao động về", "nghỉ lễ, tết.")
    lines += para(1, 250, "Điều 2. Sửa đổi khoản 1 Điều 5 như sau:")
    lines += para(1, 270, "“Điều 3. Điều khoản được trích dẫn trong văn bản sửa đổi.”")
    lines += para(2, 70, "Điều 3. Hiệu lực thi hành")
    lines += para(2, 90, "1. Nghị định này có hiệu lực từ ngày 01 tháng 01 năm 2021.")
    lines += para(2, 110, "2. Bộ trưởng chịu trách nhiệm thi hành Nghị định này./.")
    lines += [line(2, 150, "TM. CHÍNH PHỦ", x0=350, x1=450), line(2, 170, "THỦ TƯỚNG", x0=360, x1=440),
              line(2, 200, "Nguyễn Văn A", x0=355, x1=445)]
    lines += [line(3, 70, "Phụ lục", x0=270, x1=320), line(3, 90, "DANH MỤC ĐỊA BÀN", x0=220, x1=380),
              line(3, 110, "(Kèm theo Nghị định số 1/2020/NĐ-CP)", x0=180, x1=420)]
    lines += para(3, 140, "1. Vùng I, gồm các quận nội thành.")
    return lines


def test_articles_are_sequential_and_quotes_are_not_articles():
    parsed = parse_document(layout(sample_lines()))
    mains = [s for s in parsed.sections if s.kind == SectionKind.MAIN_TEXT]
    assert [s.article_number for s in mains] == [1, 2, 3]
    art2 = mains[1]
    assert art2.contains_quoted_amendment
    assert "Điều 3. Điều khoản được trích dẫn" in " ".join(parsed.section_text(art2).split())
    assert mains[2].title == "Hiệu lực thi hành"


def test_reference_to_other_article_is_not_a_heading():
    parsed = parse_document(layout(sample_lines()))
    art1 = next(s for s in parsed.sections if s.article_number == 1)
    assert "Điều 112 của Bộ luật" in " ".join(parsed.section_text(art1).split())


def test_chapter_path_signature_and_annex():
    parsed = parse_document(layout(sample_lines()))
    kinds = [s.kind for s in parsed.sections]
    assert kinds[0] == SectionKind.PREAMBLE
    assert SectionKind.SIGNATURE in kinds and SectionKind.ANNEX in kinds
    art1 = next(s for s in parsed.sections if s.article_number == 1)
    assert art1.path[0] == "Chương I. QUY ĐỊNH CHUNG"
    annex = next(s for s in parsed.sections if s.kind == SectionKind.ANNEX)
    assert annex.title == "DANH MỤC ĐỊA BÀN"
    signature = next(s for s in parsed.sections if s.kind == SectionKind.SIGNATURE)
    assert "Nguyễn Văn A" in parsed.section_text(signature)
    art3 = next(s for s in parsed.sections if s.article_number == 3)
    assert "TM. CHÍNH PHỦ" not in parsed.section_text(art3)


def test_every_paragraph_has_one_owner():
    parsed = parse_document(layout(sample_lines()))
    for k, p in enumerate(parsed.paragraphs):
        owners = sum(1 for s in parsed.sections if s.start <= p.start and p.end <= s.end)
        assert owners + (k in parsed.structural_paragraphs) == 1, p.text


def test_footnote_attaches_to_marked_clause():
    lines = sample_lines()
    target = next(i for i, ln in enumerate(lines) if ln.text.startswith("1. Nghị định này có hiệu lực"))
    lines[target].markers = [(2, "7")]
    note = RawFootnote(number="7", page=2, lines=["Khoản này được sửa đổi, bổ sung theo quy định tại khoản 2 Điều 1 "
                                                   "của Luật số 99/2025/QH15, có hiệu lực kể từ ngày 01 tháng 7 năm 2026."])
    parsed = parse_document(layout(lines, [note]))
    fn = parsed.footnotes[0]
    assert fn.target_label == "Điều 3 khoản 1"
    assert fn.change_type == "amended"
    assert fn.amending_instrument == "Luật số 99/2025/QH15"
    assert str(fn.effective_from) == "2026-07-01"
    assert fn.section_id == "doc:art3"


def test_footnote_classification():
    assert parse_footnote_text("Khoản này được bổ sung theo quy định tại khoản 4 Điều 49 của Luật số 1/2025/QH15")[0] \
        == "added"
    assert parse_footnote_text("Điểm này được sửa đổi, bổ sung theo quy định tại Luật số 1/2025/QH15")[0] == "amended"
    assert parse_footnote_text("Luật số 1/2025/QH15 có căn cứ ban hành như sau: “Căn cứ Hiến pháp đã được "
                               "sửa đổi, bổ sung”")[0] == "note"


def test_chunks_are_exact_slices_with_context_and_pages():
    parsed = parse_document(layout(sample_lines()))
    chunks = chunk_document(parsed, registry_doc(), "snap", TokenCounter())
    assert chunks, "expected chunks"
    for c in chunks:
        assert parsed.text[c.source_start_char:c.source_end_char] == c.raw_text
        assert c.text.strip()
        assert c.context_header.startswith("NĐ thử (1/2020/NĐ-CP) › ")
        assert c.embedding_text.startswith(c.context_header)
    art3 = next(c for c in chunks if c.article_number == 3)
    assert (art3.page_start, art3.page_end) == (2, 2)
    assert all(c.section_kind != SectionKind.SIGNATURE for c in chunks)


def test_chunk_ids_are_deterministic():
    a = chunk_document(parse_document(layout(sample_lines())), registry_doc(), "snap", TokenCounter())
    b = chunk_document(parse_document(layout(sample_lines())), registry_doc(), "snap", TokenCounter())
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert len({c.chunk_id for c in a}) == len(a)


def test_long_article_splits_at_clause_boundaries_within_budget():
    lines = [line(1, 60, "CHÍNH PHỦ", x0=250, x1=330)]
    lines += para(1, 80, "Điều 1. Điều rất dài")
    y = 100
    for k in range(1, 9):
        words = " ".join(["quy định về thời giờ làm việc của người lao động"] * 22)
        lines += para(1 + y // 700, y % 700 + 60, f"{k}. {words}.")
        y += 40
    parsed = parse_document(layout(lines))
    counter = TokenCounter()
    doc = registry_doc().model_copy(update={"expected_main_articles": 1})
    chunks = [c for c in chunk_document(parsed, doc, "snap", counter) if c.article_number == 1]
    assert len(chunks) > 1
    assert all(c.token_count <= MAX_TOKENS for c in chunks)
    assert all(c.text.split("\n")[0][:2].rstrip(".").isdigit() or c.ordinal == 0 for c in chunks)
    assert all(c.part_count == len(chunks) for c in chunks)
