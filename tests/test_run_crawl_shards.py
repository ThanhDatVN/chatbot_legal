from pathlib import Path

from tools.run_crawl_shards import available_bytes, is_terminal_summary, summary_gap_count


def test_terminal_summary_counts_attempted_and_skipped() -> None:
    summary = {
        "document_count": 100,
        "page_fetches": {"attempted": 98, "skipped": 2},
    }
    assert is_terminal_summary(summary, 100)


def test_summary_is_not_terminal_when_a_document_is_missing() -> None:
    summary = {
        "document_count": 100,
        "page_fetches": {"attempted": 99, "skipped": 0},
    }
    assert not is_terminal_summary(summary, 100)


def test_summary_is_not_terminal_for_wrong_shard() -> None:
    summary = {
        "document_count": 50,
        "page_fetches": {"attempted": 50, "skipped": 0},
    }
    assert not is_terminal_summary(summary, 100)


def test_summary_gaps_include_page_skips_and_attachment_failures() -> None:
    summary = {
        "page_fetches": {"failed": 1, "skipped": 2},
        "attachments": {"failed": 3},
    }
    assert summary_gap_count(summary) == 6


def test_available_bytes_accepts_a_not_yet_created_child() -> None:
    assert available_bytes(Path("future-test-output") / "run") > 0
