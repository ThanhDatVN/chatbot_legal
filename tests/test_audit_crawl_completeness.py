from tools.audit_crawl_completeness import (
    choose_recovered_records,
    expected_attachment_urls,
)


def test_recovered_page_supersedes_failed_page() -> None:
    records = [
        {"record_type": "source_page", "document_id": "D-1", "fetch_status": "failed"},
        {"record_type": "source_page", "document_id": "D-1", "fetch_status": "fetched"},
    ]
    selected = choose_recovered_records(records, "source_page", "document_id")
    assert selected["D-1"]["fetch_status"] == "fetched"


def test_expected_attachments_are_deduplicated_across_pages() -> None:
    pages = {
        "D-1": {
            "fetch_status": "fetched",
            "attachment_links": [{"url": "https://example.test/a.pdf"}],
        },
        "D-2": {
            "fetch_status": "fetched",
            "attachment_links": [{"url": "https://example.test/a.pdf"}],
        },
    }
    assert expected_attachment_urls(pages) == {"https://example.test/a.pdf"}
