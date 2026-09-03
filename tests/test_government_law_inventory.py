from tools.government_law_inventory import (
    ListingParser,
    normalize_row,
    parse_date,
    postback_data,
)


def test_listing_parser_and_relevance_classification() -> None:
    parser = ListingParser()
    parser.feed(
        """
        <input type="hidden" name="__VIEWSTATE" value="state" />
        <table id="ctrl_191017_163_grvDocument"><tr>
          <td><span class="code">109/2025/QH15</span></td>
          <td><span class="issue-v2">10/12/2025</span></td>
          <td><span class="substract">Luật Thuế thu nhập cá nhân</span></td>
          <td><a href="/?classid=1&amp;docid=999&amp;pageid=27160">Chi tiết</a></td>
          <td><a href="https://datafiles.chinhphu.vn/a.pdf">PDF</a></td>
        </tr></table>
        """
    )

    assert parser.hidden["__VIEWSTATE"] == "state"
    assert len(parser.rows) == 1
    item = normalize_row(parser.rows[0], 2)
    assert item["instrument_number"] == "109/2025/QH15"
    assert item["promulgation_date"] == "2025-12-10"
    assert item["title_relevance_class"] == "direct_tax_title"
    assert item["detail_url"].startswith("https://chinhphu.vn/")
    assert item["attachment_urls"] == ["https://datafiles.chinhphu.vn/a.pdf"]


def test_parse_date_rejects_invalid_value() -> None:
    assert parse_date("31/02/2025") is None
    assert parse_date("01-09-2016") == "2016-09-01"


def test_title_classifier_does_not_treat_kinh_phi_as_a_fee_document() -> None:
    item = normalize_row(
        {
            "code": "01/QD-TTG",
            "issue-v2": "01/01/2025",
            "substract": "Bố trí kinh phí thực hiện chương trình",
            "anchors": [],
        },
        1,
    )
    assert item["title_relevance_class"] == "requires_fulltext_tax_screening"


def test_postback_contains_page_event_and_viewstate() -> None:
    encoded = postback_data({"__VIEWSTATE": "a+b"}, 3).decode("ascii")
    assert "__EVENTARGUMENT=Page%243" in encoded
    assert "__VIEWSTATE=a%2Bb" in encoded
