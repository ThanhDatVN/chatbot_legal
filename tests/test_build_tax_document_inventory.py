from tools.build_tax_document_inventory import (
    build_crawl_config,
    classify_title,
    inventory_type_group,
    is_pdf_attachment_url,
    semantic_document_key,
    source_doc_id,
    stable_document_key,
)


def test_high_precision_title_classification() -> None:
    status, reasons = classify_title("Gia hạn nộp thuế và tiền thuê đất")
    assert status == "priority_fulltext_fetch"
    assert "direct_tax_or_invoice_term" in reasons

    status, reasons = classify_title("Quy định chi phí quản lý dự án")
    assert status == "fulltext_screening_pending"
    assert reasons == ["no_high_precision_title_term"]


def test_source_identity_uses_docid_not_instrument_number() -> None:
    first = {
        "instrument_number": "31/2024/QH15",
        "promulgation_date": "2024-01-18",
        "title": "Luật Đất đai",
        "detail_url": "https://chinhphu.vn/?docid=211189&pageid=27160",
    }
    second = dict(first, detail_url="https://chinhphu.vn/?docid=999999&pageid=27160")
    assert source_doc_id(first["detail_url"]) == "211189"
    assert stable_document_key("law_or_ordinance", first) != stable_document_key(
        "law_or_ordinance", second
    )

    gazette_part_a = dict(first, detail_url=None, source_item_id="100")
    gazette_part_b = dict(first, detail_url=None, source_item_id="101")
    assert stable_document_key("consolidated", gazette_part_a) != stable_document_key(
        "consolidated", gazette_part_b
    )
    assert semantic_document_key("consolidated", gazette_part_a) == semantic_document_key(
        "consolidated", gazette_part_b
    )


def test_legacy_inventory_type_is_inferred_from_source_url() -> None:
    assert (
        inventory_type_group(
            {"source_url": "https://chinhphu.vn/he-thong-van-ban?typegroupid=3"}
        )
        == "law_or_ordinance"
    )


def test_crawl_config_preserves_every_known_pdf_attachment() -> None:
    item = {
        "document_key": "D-1",
        "instrument_number": "1/2026/TEST",
        "document_type_label": "Luật",
        "title": "Văn bản nhiều phần",
        "promulgation_date": "2026-01-01",
        "detail_url": "https://chinhphu.vn/?docid=1",
        "screening_reasons": ["fulltext_required"],
        "attachment_urls": [f"https://datafiles.chinhphu.vn/part-{i}.pdf" for i in range(7)],
    }
    config = build_crawl_config([item], "all-documents")
    assert len(config["documents"][0]["official_attachment_urls"]) == 7
    assert config["max_attachments_per_document"] >= 7


def test_pdf_stream_url_is_recognized_from_file_name_query() -> None:
    url = "https://g7.cdnchinhphu.vn/api/download/stream?Url=token&file_name=2026_1%2F1.pdf"
    assert is_pdf_attachment_url(url)
