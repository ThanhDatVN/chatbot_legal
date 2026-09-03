import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("legal_crawler", ROOT / "tools" / "legal_crawler.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LegalCrawlerTests(unittest.TestCase):
    def test_html_parser_extracts_metadata_and_pdf(self):
        parser = MODULE.LegalHTMLParser()
        parser.feed(
            """
            <html><head><title>Luật số 09/2026/QH16</title>
            <meta name="description" content="Luật sửa đổi bốn luật thuế">
            <link rel="canonical" href="https://chinhphu.vn/doc"></head>
            <body><div>Số, ký hiệu</div><div>09/2026/QH16</div>
            <div>Ngày ban hành</div><div>24-04-2026</div>
            <div>Ngày hiệu lực</div><div>24-04-2026</div>
            <div>Loại văn bản</div><div>Luật</div>
            <a href="/files/09-qh.signed.pdf">Tài liệu PDF</a></body></html>
            <footer><div>Loại văn bản</div><div>Hiến pháp</div></footer>
            """
        )
        metadata = MODULE.extract_labeled_metadata(parser.text_parts)
        links = MODULE.find_pdf_links(parser, "https://chinhphu.vn/doc", ["chinhphu.vn"])
        self.assertEqual(metadata["instrument_number"], "09/2026/QH16")
        self.assertEqual(metadata["promulgation_date"], "24-04-2026")
        self.assertEqual(metadata["effective_date"], "24-04-2026")
        self.assertEqual(metadata["document_type"], "Luật")
        self.assertEqual(parser.description, "Luật sửa đổi bốn luật thuế")
        self.assertEqual(links[0]["url"], "https://chinhphu.vn/files/09-qh.signed.pdf")

    def test_parser_ignores_script_and_style_text(self):
        parser = MODULE.LegalHTMLParser()
        parser.feed("<style>secret-style</style><script>secret-script</script><p>Public text</p>")
        self.assertEqual(parser.text_parts, ["Public text"])

    def test_content_signal_parser(self):
        signals = MODULE.parse_content_signals(
            "User-agent: *\nContent-Signal: search=yes, ai-train=no, use=reference\nAllow: /"
        )
        self.assertEqual(
            signals,
            {"search": "yes", "ai-train": "no", "use": "reference"},
        )

    def test_reference_policy_rejects_non_reference_use(self):
        source = {
            "content_signal_policy": {
                "required_search": "yes",
                "forbidden_ai_train": True,
                "maximum_use": "reference",
            }
        }
        allowed, reason = MODULE.content_signal_allows_reference(
            source,
            {"content_signals": {"search": "yes", "ai-train": "no", "use": "reference"}},
        )
        self.assertTrue(allowed)
        self.assertIsNone(reason)
        allowed, reason = MODULE.content_signal_allows_reference(
            source,
            {"content_signals": {"search": "yes", "use": "train"}},
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "content_signal_use_exceeds_policy")

    def test_url_policy_rejects_http_credentials_and_unknown_host(self):
        allowed = ["chinhphu.vn"]
        for url in (
            "http://chinhphu.vn/doc",
            "https://user:password@chinhphu.vn/doc",
            "https://example.com/doc",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                MODULE.validate_url(url, allowed, resolve_dns=False)

    def test_date_normalization(self):
        self.assertEqual(MODULE.normalize_date("Ngày 01-07-2025"), "2025-07-01")
        self.assertEqual(MODULE.normalize_date("24/04/2026"), "2026-04-24")
        self.assertIsNone(MODULE.normalize_date("31/02/2026"))

    def test_expected_metadata_flags_mismatch(self):
        document = {
            "instrument_number": "48/2024/QH15",
            "document_type_expected": "Luật",
            "promulgation_date_expected": "2024-11-26",
            "effective_date_expected": "2025-07-01",
        }
        issues = MODULE.validate_expected_metadata(
            document,
            {
                "instrument_number": "48/2024/QH15",
                "promulgation_date": "26-11-2024",
                "effective_date": "02-07-2025",
                "document_type": "Luật",
            },
            "Luật Thuế giá trị gia tăng",
        )
        self.assertEqual(issues, ["effective_date_mismatch:2025-07-02!=2025-07-01"])

    def test_repository_allowlist_is_valid(self):
        config = json.loads((ROOT / "config" / "legal-crawl-allowlist.json").read_text(encoding="utf-8"))
        MODULE.validate_config(config)
        self.assertEqual(len(config["documents"]), 15)
        self.assertEqual(config["sources"]["thuvienphapluat"]["store_raw_html"], False)

    def test_selection_window_requires_explicit_dependency_exception(self):
        config = {
            "selection_window": {
                "start": "2016-08-11",
                "end": "2026-08-11",
                "date_basis": "promulgation_date",
            },
            "sources": {
                "chinhphu": {
                    "allowed_hosts": ["chinhphu.vn"],
                }
            },
            "documents": [
                {
                    "id": "IMPORT-EXPORT-TAX-LAW-107-2016",
                    "instrument_number": "107/2016/QH13",
                    "promulgation_date_expected": "2016-04-06",
                    "effective_date_expected": "2016-09-01",
                    "coverage_class": "historical_temporal",
                    "selection_rationale": "Root law needed for later implementing decrees.",
                    "official_url": "https://chinhphu.vn/document",
                    "relations": [],
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "must be a dependency_exception"):
            MODULE.validate_config(config)

        config["documents"][0]["coverage_class"] = "dependency_exception"
        config["documents"][0]["dependency_exception_reason"] = (
            "Promulgated shortly before the window and effective within it."
        )
        MODULE.validate_config(config)

    def test_selection_window_rejects_unknown_relation_target(self):
        config = {
            "selection_window": {
                "start": "2016-08-11",
                "end": "2026-08-11",
                "date_basis": "promulgation_date",
            },
            "sources": {"chinhphu": {"allowed_hosts": ["chinhphu.vn"]}},
            "documents": [
                {
                    "id": "VAT-LAW-48-2024",
                    "instrument_number": "48/2024/QH15",
                    "promulgation_date_expected": "2024-11-26",
                    "effective_date_expected": "2025-07-01",
                    "coverage_class": "core_current",
                    "selection_rationale": "Current VAT root law.",
                    "official_url": "https://chinhphu.vn/document",
                    "relations": [{"type": "amends", "target": "MISSING"}],
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "Unknown relation target"):
            MODULE.validate_config(config)

    def test_ten_year_tax_allowlist_is_valid_and_selective(self):
        config = json.loads(
            (ROOT / "config" / "tax-law-10y-allowlist.json").read_text(encoding="utf-8")
        )
        MODULE.validate_config(config)
        self.assertEqual(len(config["documents"]), 50)
        self.assertEqual(config["selection_window"]["start"], "2016-08-11")
        self.assertEqual(config["selection_window"]["end"], "2026-08-11")
        self.assertEqual(
            [
                item["instrument_number"]
                for item in config["documents"]
                if item["coverage_class"] == "dependency_exception"
            ],
            ["107/2016/QH13"],
        )
        self.assertEqual(
            sum(bool(item.get("known_source_discrepancy")) for item in config["documents"]),
            2,
        )


if __name__ == "__main__":
    unittest.main()
