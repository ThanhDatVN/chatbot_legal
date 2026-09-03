from tools.build_tax_law_register import build_crawl_config, build_register, stable_id


def test_build_register_keeps_historical_dependencies_and_screening_queue() -> None:
    inventory = {
        "source_url": "https://chinhphu.vn/list",
        "document_count_in_window": 2,
        "documents": [
            {
                "instrument_number": "09/2026/QH16",
                "title": "Luật sửa đổi bốn luật thuế",
                "promulgation_date": "2026-04-24",
                "detail_url": "https://chinhphu.vn/?docid=1",
                "attachment_urls": ["https://datafiles.chinhphu.vn/09.pdf"],
            },
            {
                "instrument_number": "08/2026/QH16",
                "title": "Luật khác",
                "promulgation_date": "2026-04-23",
                "detail_url": "https://chinhphu.vn/?docid=2",
                "attachment_urls": [],
            },
        ],
    }
    scope = {
        "as_of_date": "2026-08-11",
        "window_start": "2016-08-11",
        "scope_definition": {},
        "chain_evidence_artifacts": [],
        "mandatory_in_window": [
            {"instrument_number": "09/2026/QH16", "tier": "A", "topics": ["vat"]}
        ],
        "historical_dependencies": [
            {
                "instrument_number": "13/2008/QH12",
                "title": "Luật Thuế giá trị gia tăng",
                "tier": "A",
                "topics": ["vat"],
                "promulgation_date": "2008-06-03",
                "effective_date": "2009-01-01",
                "official_url": "https://vanban.chinhphu.vn/?docid=3",
            }
        ],
    }

    register = build_register(inventory, scope)

    assert register["selected_count"] == 2
    assert register["fulltext_screening_queue_count"] == 1
    assert register["documents"][1]["temporal_role"] == "historical_dependency"
    assert stable_id("13/2008/QH12") == "LAW-13-2008-QH12"
    crawl_config = build_crawl_config(register)
    assert crawl_config["documents"][0]["download_attachments"] is True
    assert crawl_config["documents"][1]["effective_date_expected"] == "2009-01-01"
