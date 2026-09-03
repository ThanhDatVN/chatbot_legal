from tools.government_gazette_inventory import GazetteListingParser, listing_url


def test_gazette_card_parser() -> None:
    parser = GazetteListingParser()
    parser.feed(
        """
        <div class="item--vb event--btn" data-id="470173">
          <span class="kh"><span class="icon"></span>Ký hiệu: 66.23/2026/NQ-CP</span>
          <a href="https://g7.cdnchinhphu.vn/api/download?file_name=a.pdf"
             data-file="a.pdf">PDF</a>
          <div class="middle">
            <a class="sapo" href="/van-ban/nghi-quyet-470173.htm"
               title="Nghị quyết về trao đổi thông tin theo yêu cầu về thuế">Title</a>
          </div>
          <div class="bot"><span>[Ban hành: 24/07/2026]</span>
          <span>[Hiệu lực: 24/07/2027]</span></div>
        </div>
        """
    )
    assert len(parser.documents) == 1
    item = parser.documents[0]
    assert item["instrument_number"] == "66.23/2026/NQ-CP"
    assert item["promulgation_date"] == "2026-07-24"
    assert item["effective_date"] == "2027-07-24"
    assert item["detail_url"].startswith("https://congbao.chinhphu.vn/")
    assert len(item["attachment_urls"]) == 1


def test_listing_url() -> None:
    assert listing_url("nghi-quyet-l6", 1).endswith("nghi-quyet-l6.htm")
    assert listing_url("nghi-quyet-l6", 2).endswith("nghi-quyet-l6/trang-2.htm")
