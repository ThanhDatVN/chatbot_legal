from tools.legal_effective_dates import (
    DocumentSpan,
    extract_temporal_evidence,
    find_document_span,
    normalize_date_token,
    normalize_space,
)


def test_normalize_vietnamese_date_formats() -> None:
    assert normalize_date_token("ngày 01 tháng 7 năm 2026") == "2026-07-01"
    assert normalize_date_token("01/07/2026") == "2026-07-01"


def test_normalize_space_repairs_common_pdf_text_artifacts() -> None:
    assert normalize_space("co\u0301 hiệu lực từ n ăm 2026") == "có hiệu lực từ năm 2026"


def test_find_document_span_skips_contents_and_stops_at_next_instrument() -> None:
    pages = [
        "MỤC LỤC 24-04-2026 - Luật số 09/2026/QH16 trang 45",
        (
            "QUỐC HỘI Luật số: 09/2026/QH16 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM "
            "Độc lập - Tự do - Hạnh phúc LUẬT SỬA ĐỔI"
        ),
        "Điều 5. Hiệu lực thi hành Luật này có hiệu lực thi hành từ ngày được thông qua.",
        (
            "CHÍNH PHỦ Số: 153/2026/NĐ-CP CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM "
            "Độc lập - Tự do - Hạnh phúc NGHỊ ĐỊNH"
        ),
    ]

    span = find_document_span(pages, "09/2026/QH16")

    assert span.start_page == 2
    assert span.end_page == 3
    assert span.candidate_pages == (1, 2)
    assert span.location_confidence == "high"


def test_closing_formula_is_not_mistaken_for_a_new_document_header() -> None:
    pages = [
        "QUỐC HỘI Luật số: 43/2024/QH15 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        (
            "Điều 5. Hiệu lực thi hành Luật này có hiệu lực từ ngày 01 tháng 8 năm 2024. "
            + " nội dung" * 100
            + " Luật này được Quốc hội nước Cộng hòa xã hội chủ nghĩa Việt Nam thông qua."
        ),
    ]
    span = find_document_span(pages, "43/2024/QH15")
    assert span.end_page == 2


def test_extracts_general_provision_and_application_dates_separately() -> None:
    pages = [
        (
            "Điều 52. Hiệu lực thi hành. Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2026. "
            "Riêng Điều 13 có hiệu lực thi hành từ ngày 01 tháng 01 năm 2026. "
            "Chính sách được áp dụng từ ngày 01 tháng 01 năm 2026 đến hết ngày 30 tháng 6 năm 2026."
        )
    ]
    span = DocumentSpan(1, 1, "high", (1,))

    evidence = extract_temporal_evidence(pages, span, "2025-12-10")

    general = [item for item in evidence if item["kind"] == "general_effective"]
    provision = [item for item in evidence if item["kind"] == "provision_effective"]
    periods = [item for item in evidence if item["kind"] == "application_period"]
    assert general[0]["effective_date"] == "2026-07-01"
    assert provision[0]["effective_date"] == "2026-01-01"
    assert periods[0]["start_date"] == "2026-01-01"
    assert periods[0]["end_date"] == "2026-06-30"


def test_relative_effective_clause_uses_promulgation_date_with_explicit_resolution() -> None:
    pages = [
        "Điều 9. Hiệu lực thi hành. Thông tư này có hiệu lực thi hành kể từ ngày ký ban hành."
    ]
    evidence = extract_temporal_evidence(
        pages,
        DocumentSpan(1, 1, "high", (1,)),
        "2026-03-05",
    )

    assert evidence[0]["effective_date"] == "2026-03-05"
    assert evidence[0]["date_resolution"] == "relative_content_clause_plus_promulgation_date"


def test_ignores_legislative_session_range_and_repairs_split_ocr_words() -> None:
    pages = [
        (
            "Căn cứ kết quả Kỳ họp từ ngày 21 tháng 10 năm 2024 đến ngày 30 tháng 11 năm 2024. "
            "Điều 5. Hiệu lực thi hành. 1. Luật này có hi ệu lực thi hành t ừ ngày được "
            "Quốc hội thông qua. 2. Quy đ ịnh tại các điều 1, 2 và 3 của Luật này có hi ệu "
            "lực thi hành t ừ ngày 01 tháng 01 năm 2026."
        )
    ]

    evidence = extract_temporal_evidence(
        pages,
        DocumentSpan(1, 1, "high", (1,)),
        "2026-04-24",
    )

    assert not [item for item in evidence if item["kind"] == "application_period"]
    general = [item for item in evidence if item["kind"] == "general_effective"]
    provision = [item for item in evidence if item["kind"] == "provision_effective"]
    assert general[0]["effective_date"] == "2026-04-24"
    assert provision[0]["effective_date"] == "2026-01-01"
