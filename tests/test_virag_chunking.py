"""Regression tests for parent windowing (defect D-03).

The defect had two parts in one line, `article_text[: parent_max_tokens * 8]`:

1. a **unit error** - a token budget multiplied by 8 and applied as a character
   bound;
2. a **correctness bug** - a head slice, so a Khoản late in a long Điều was cut
   out of the parent context by the very step meant to supply that context,
   while the citation still pointed at it.

Parent expansion now keeps two things unconditionally: the article's opening
lines, and the retrieved child.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from virag.ingest.chunking import count_tokens, window_parent  # noqa: E402

HEADING = "Điều 9. Các trường hợp sau đây được miễn thuế:"


def _article(n_clauses: int = 25, filler: int = 40) -> str:
    body = "\n".join(
        f"{i}. Trường hợp thứ {i} " + "chi tiết " * filler for i in range(1, n_clauses + 1)
    )
    return HEADING + "\n" + body


def _child(index: int, filler: int = 40) -> str:
    # Children repeat the article heading, as the chunker emits them.
    return HEADING + "\n" + f"{index}. Trường hợp thứ {index} " + "chi tiết " * filler


class TestWindowFitsBudget:
    def test_short_article_returned_whole(self):
        parent = HEADING + "\n1. Một trường hợp ngắn."
        assert window_parent(parent, _child(1), 1600) == parent

    def test_long_article_is_reduced(self):
        parent = _article()
        out = window_parent(parent, _child(25), 300)
        assert count_tokens(out) <= 300
        assert count_tokens(parent) > 300


class TestChildIsNeverDropped:
    def test_last_clause_survives_windowing(self):
        """The exact failure the defect describes: a head slice loses this."""
        parent = _article()
        out = window_parent(parent, _child(25), 300)
        assert "Trường hợp thứ 25" in out

    def test_middle_clause_survives(self):
        parent = _article()
        out = window_parent(parent, _child(13), 300)
        assert "Trường hợp thứ 13" in out

    def test_first_clause_survives(self):
        parent = _article()
        out = window_parent(parent, _child(1), 300)
        assert "Trường hợp thứ 1 " in out

    def test_head_slice_would_have_failed(self):
        """Pin the old behaviour so a regression is unmistakable."""
        parent = _article()
        head_slice = parent[: 300 * 8]
        assert "Trường hợp thứ 25" not in head_slice, "the old slice dropped the clause"
        assert "Trường hợp thứ 25" in window_parent(parent, _child(25), 300)


class TestArticleContextIsPreserved:
    def test_heading_is_always_kept(self):
        """A Khoản is meaningless without the article's opening sentence."""
        parent = _article()
        for index in (1, 13, 25):
            out = window_parent(parent, _child(index), 300)
            assert "Điều 9" in out
            assert "được miễn thuế" in out

    def test_elision_is_marked(self):
        out = window_parent(_article(), _child(25), 300)
        assert "[...]" in out, "omitted text must be visible, not silent"


class TestDegradedCases:
    def test_unlocatable_child_keeps_head_and_marks_elision(self):
        parent = _article()
        out = window_parent(parent, "một khoản không thuộc điều này", 300)
        assert "Điều 9" in out
        assert "[...]" in out
        assert count_tokens(out) <= 300

    def test_empty_child_does_not_crash(self):
        out = window_parent(_article(), "", 300)
        assert "Điều 9" in out

    def test_budget_is_measured_in_tokens_not_characters(self):
        """The unit error: 300 tokens is nothing like 300*8 characters."""
        parent = _article()
        out = window_parent(parent, _child(25), 300)
        assert count_tokens(out) <= 300
        # Had the bound been characters, the result would be far shorter.
        assert len(out) > 300
