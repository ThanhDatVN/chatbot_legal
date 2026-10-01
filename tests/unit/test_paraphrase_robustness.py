"""Everyday-wording support: query expansion, annex title stripping and the reorganised-body notice."""

from app.agent.extractive import ExtractiveAgent
from app.agent.lexicon import expand_query
from app.agent.service import REORGANISED_BODY_RE


def test_everyday_terms_gain_statutory_terms_without_changing_the_question():
    q = "Sếp có được bắt tôi làm thêm quá 40 tiếng trong một tháng không?"
    expanded = expand_query(q)
    assert expanded.startswith(q)
    for term in ("giờ", "người sử dụng lao động", "làm thêm giờ"):
        assert term in expanded
    assert "chết" in expand_query("Bố tôi mất thì được nghỉ mấy ngày?")
    assert "chết" not in expand_query("Người lao động bị mất việc làm được trợ cấp gì?")  # "mất việc" is not death
    assert "người sử dụng lao động đơn phương" in expand_query("Công ty muốn cho nhân viên nghỉ việc thì báo trước?")
    statutory = "Người lao động làm việc đủ 12 tháng được nghỉ hằng năm bao nhiêu ngày?"
    assert expand_query(statutory) == statutory  # statutory wording needs nothing


def test_annex_title_block_is_not_quoted():
    text = ("Phụ lục II\nDANH MỤC CÔNG VIỆC ĐƯỢC THỰC HIỆN\nCHO THUÊ LẠI LAO ĐỘNG\n"
            "(Kèm theo Nghị định số 145/2020/NĐ-CP\nngày 14 tháng 12 năm 2020 của Chính phủ)\n"
            "STT: 1; Công việc: Phiên dịch/Biên dịch/Tốc ký\nSTT: 17; Công việc: Lái xe")
    assert ExtractiveAgent._body(text, "Phụ lục II") == ["STT: 1; Công việc: Phiên dịch/Biên dịch/Tốc ký",
                                                         "STT: 17; Công việc: Lái xe"]
    article = "Điều 113. Nghỉ hằng năm\n1. Người lao động được nghỉ 12 ngày."
    assert ExtractiveAgent._body(article, "Điều 113") == ["1. Người lao động được nghỉ 12 ngày."]


def test_reorganised_bodies_are_detected():
    assert REORGANISED_BODY_RE.search("phải thông báo cho Sở Lao động - Thương binh và Xã hội tại các nơi sau")
    assert REORGANISED_BODY_RE.search("Ủy ban nhân dân cấp huyện")
    assert not REORGANISED_BODY_RE.search("Bộ luật Lao động quy định")


def test_list_questions_on_an_annex_get_the_whole_list():
    from app.schemas import SourceEvidence

    rows = [f"STT: {i}; Công việc: Việc số {i}" for i in range(1, 21)]
    source = SourceEvidence(chunk_id="x" * 24, corpus_snapshot_id="s", document_id="d", document_number="145/2020/NĐ-CP",
                            title="t", short_title="t", document_type="Nghị định", section="Phụ lục II",
                            section_path=["Phụ lục II"], page_start=1, page_end=1,
                            text="Phụ lục II\nDANH MỤC CÔNG VIỆC\n" + "\n".join(rows), source_url="https://x",
                            downloaded_at="2026-10-01", publisher="p", currency_status="presumed_current",
                            currency_basis="b", text_quality_status="machine_checked", amendment_notes=[], eligible=True)
    agent = ExtractiveAgent(toolbox=None, reranker=None, policy=None)
    assert agent._best_units("Danh mục công việc được cho thuê lại gồm những công việc nào?", source) == rows
    assert len(agent._best_units("Việc số 7 là gì?", source)) <= 3  # a pointed question still gets the best rows
