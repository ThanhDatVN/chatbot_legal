"""Regression tests for legal authority resolution (defect D-06).

The defect: any instrument number containing `VBHN` returned tier 7
unconditionally. A consolidated **Law** was therefore ranked as a Circular -
five tiers too low - and the authority component of the ranking score acted on
that. 150 of 1,580 corpus documents are consolidated; 30 were mis-ranked.

A Văn bản hợp nhất inherits the force of the instrument it consolidates. The
title is the authoritative signal: measured on the corpus, `19/VBHN-BTC` carries
a ministry code yet consolidates a Nghị định.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from virag.legal.authority import (  # noqa: E402
    authority_score,
    is_consolidated,
    is_normative,
    resolve_tier,
    tier_for_consolidated,
)


class TestConsolidatedInheritsForce:
    def test_consolidated_law_is_tier_2_not_7(self):
        """The corpus case that motivated the fix - a consolidated tax Law."""
        tier = resolve_tier(
            "Văn bản hợp nhất",
            "08/VBHN-VPQH",
            "Văn bản hợp nhất số 08/VBHN-VPQH hợp nhất Luật Thuế tiêu thụ đặc biệt",
        )
        assert tier == 2

    def test_consolidated_decree_is_tier_5(self):
        """`19/VBHN-BTC` has a ministry code but consolidates a Decree."""
        tier = resolve_tier(
            "Văn bản hợp nhất",
            "19/VBHN-BTC",
            "Văn bản hợp nhất số 19/VBHN-BTC hợp nhất Nghị định Quy định chi tiết",
        )
        assert tier == 5, "the title must beat the ministry code"

    def test_consolidated_circular_is_tier_7(self):
        tier = resolve_tier(
            "Văn bản hợp nhất",
            "59/VBHN-BXD",
            "Văn bản hợp nhất số 59/VBHN-BXD hợp nhất Thông tư Quy định chi tiết",
        )
        assert tier == 7

    def test_consolidated_ordinance_is_tier_3(self):
        tier = resolve_tier(
            "Văn bản hợp nhất",
            "123/2026/VBHN-PL-VPQH",
            "Văn bản hợp nhất số 123/2026/VBHN-PL-VPQH hợp nhất Pháp lệnh Ưu đãi",
        )
        assert tier == 3

    def test_consolidated_law_outranks_an_ordinary_circular(self):
        """The ranking consequence the defect had inverted."""
        consolidated_law = resolve_tier(
            "Văn bản hợp nhất", "08/VBHN-VPQH", "… hợp nhất Luật Thuế tiêu thụ đặc biệt"
        )
        circular = resolve_tier("Thông tư", "41/2026/TT-BTC", "Thông tư hướng dẫn")
        assert consolidated_law < circular
        assert authority_score(consolidated_law) > authority_score(circular)


class TestConsolidatedFallbacks:
    def test_type_code_in_number_when_title_is_silent(self):
        assert tier_for_consolidated("67/VBHN-NĐ-BCT", "") == 5

    def test_national_assembly_office_defaults_to_law_tier(self):
        assert tier_for_consolidated("115/VBHN-VPQH", "") == 2

    def test_ministry_only_defaults_to_circular_tier(self):
        assert tier_for_consolidated("87/VBHN-NHNN", "") == 7

    def test_unknown_shape_falls_back_to_seven(self):
        assert tier_for_consolidated("999/VBHN-XXX", "") == 7

    def test_detection(self):
        assert is_consolidated("59/VBHN-BXD", None)
        assert is_consolidated(None, "Văn bản hợp nhất")
        assert not is_consolidated("41/2026/TT-BTC", "Thông tư")


class TestOrdinaryInstruments:
    def test_law(self):
        assert resolve_tier("Luật", "48/2024/QH15", None) == 2

    def test_decree(self):
        assert resolve_tier("Nghị định", "123/2020/NĐ-CP", None) == 5

    def test_circular(self):
        assert resolve_tier("Thông tư", "41/2026/TT-BTC", None) == 7

    def test_official_letter_is_not_normative(self):
        tier = resolve_tier("Công văn", None, "Công văn hướng dẫn")
        assert tier == 9
        assert not is_normative(tier)

    def test_law_is_normative(self):
        assert is_normative(resolve_tier("Luật", "48/2024/QH15", None))

    def test_unknown_falls_back_to_lowest(self):
        assert resolve_tier(None, None, None) == 9
