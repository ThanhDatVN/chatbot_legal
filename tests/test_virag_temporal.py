"""Regression tests for temporal reasoning and portal-date classification.

Defect D-13: the corpus carries the literal label ``"Công báo"`` in the
``effective_date`` field of 152 of 819 documents.  Any code that tests the field
for truthiness treats that as a present date; during the G0 run this exact
mistake reported corpus date-completeness as 97.3% against a true 78.8%.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from virag.legal.temporal import (  # noqa: E402
    classify_portal_date,
    in_force,
    parse_vn_date,
    validity_score,
)


class TestPortalDateClassification:
    def test_valid_day_first_date(self):
        assert classify_portal_date("18-08-2026") == ("2026-08-18", "valid")

    def test_valid_slash_date(self):
        assert classify_portal_date("01/01/2026") == ("2026-01-01", "valid")

    def test_iso_passes_through(self):
        assert classify_portal_date("2026-08-18") == ("2026-08-18", "valid")

    def test_the_cong_bao_label_is_malformed_not_present(self):
        """D-13: the exact value found on 152 corpus documents."""
        iso, quality = classify_portal_date("Công báo")
        assert iso is None
        assert quality == "malformed", "must be distinguishable from a genuine absence"

    def test_absent_is_distinct_from_malformed(self):
        assert classify_portal_date(None)[1] == "absent"
        assert classify_portal_date("")[1] == "absent"
        assert classify_portal_date("   ")[1] == "absent"

    def test_truthiness_would_have_been_wrong(self):
        """The bug this guards against, stated as an assertion."""
        value = "Công báo"
        assert bool(value) is True, "a naive `if value:` accepts it"
        assert classify_portal_date(value)[0] is None, "classification rejects it"


class TestVietnameseDateParsing:
    def test_long_form(self):
        assert parse_vn_date("ngày 08 tháng 8 năm 2026") == "2026-08-08"

    def test_day_first_is_preferred(self):
        # 08-08 is ambiguous; 25-01 is not and must read as 25 January.
        assert parse_vn_date("25-01-2026") == "2026-01-25"

    def test_unparseable_returns_none(self):
        assert parse_vn_date("không xác định") is None


class TestValidityWindow:
    AS_OF = "2021-06-15"

    def test_unknown_bounds_are_in_force(self):
        """Dropping documents with unverified dates would silently shrink recall."""
        assert in_force(None, None, self.AS_OF) is True

    def test_not_yet_effective(self):
        assert in_force("2022-01-01", None, self.AS_OF) is False

    def test_expired(self):
        assert in_force("2019-01-01", "2020-12-31", self.AS_OF) is False

    def test_in_force_within_window(self):
        assert in_force("2020-01-01", "2022-12-31", self.AS_OF) is True

    def test_score_rewards_fully_known_bounds(self):
        both = validity_score("2020-01-01", "2022-12-31", self.AS_OF)
        one = validity_score("2020-01-01", None, self.AS_OF)
        neither = validity_score(None, None, self.AS_OF)
        assert both == 1.0
        assert both > one > neither, "certainty must be graded, not binary"

    def test_recently_expired_scores_above_long_expired(self):
        adjacent = validity_score("2019-01-01", "2021-01-01", self.AS_OF)
        distant = validity_score("2001-01-01", "2002-01-01", self.AS_OF)
        assert adjacent > distant
        assert distant == 0.0
