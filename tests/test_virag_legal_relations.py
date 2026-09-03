"""Regression tests for the legal dependency graph (defect D-14).

The defect: relation extraction matched instrument numbers only, while 69% of
amendment links in the corpus cite their target **by name**.  The single most
important instrument in the v1 scope - the VAT Law - had zero resolvable
incoming edges under the old extractor.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from virag.legal.relations import (  # noqa: E402
    LegalGraph,
    extract_relations,
    extract_subject,
    normalise_instrument,
)

VAT_LAW = "Luật số 48/2024/QH15 của Quốc hội: Luật Thuế giá trị gia tăng"
AMENDING_LAW = (
    "Luật số 149/2025/QH15 của Quốc hội: Luật sửa đổi, bổ sung một số điều "
    "của Luật Thuế giá trị gia tăng"
)
DETAILING_DECREE = (
    "Nghị định số 181/2025/NĐ-CP của Chính phủ: Quy định chi tiết thi hành "
    "một số điều của Luật Thuế giá trị gia tăng"
)


class TestSubjectExtraction:
    def test_instrument_with_its_own_name(self):
        assert extract_subject(VAT_LAW) == "luat thue gia tri gia tang"

    def test_implementing_document_has_no_own_name(self):
        """D-14 guard: a Decree that *details* a Law must not be indexed under
        the Law's name, or it absorbs every link aimed at that Law."""
        assert extract_subject(DETAILING_DECREE) == ""

    def test_diacritics_are_folded(self):
        a = extract_subject("Luật số 1/2020/QH14: Luật Thuế Giá Trị Gia Tăng")
        b = extract_subject(VAT_LAW)
        assert a == b


class TestNameBasedResolution:
    def _graph(self) -> LegalGraph:
        graph = LegalGraph()
        graph.register_document("VAT-48", "48/2024/QH15", VAT_LAW)
        graph.register_document("AMEND-149", "149/2025/QH15", AMENDING_LAW)
        graph.add_all(extract_relations("AMEND-149", AMENDING_LAW))
        return graph

    def test_amendment_cited_by_name_is_resolved(self):
        graph = self._graph()
        incoming = graph.incoming("48/2024/QH15")
        assert len(incoming) == 1
        assert incoming[0].relation == "AMENDS"
        assert incoming[0].matched_by == "name"

    def test_number_only_extraction_would_have_missed_it(self):
        """The amending title contains its own number but not the target's."""
        relations = extract_relations("AMEND-149", AMENDING_LAW)
        by_name = [r for r in relations if r.target_subject]
        assert by_name, "the target is cited by name only"
        assert all(not r.target_instrument for r in by_name)

    def test_resolution_is_audited(self):
        graph = self._graph()
        stats = graph.resolution_stats()
        assert stats["total"] >= 1
        assert stats.get("name", 0) >= 1

    def test_self_reference_is_not_an_edge(self):
        graph = LegalGraph()
        graph.register_document("AMEND-149", "149/2025/QH15", AMENDING_LAW)
        graph.add_all(extract_relations("AMEND-149", AMENDING_LAW))
        assert not graph.incoming("149/2025/QH15")


class TestNumberBasedResolution:
    def test_repeal_cited_by_number(self):
        graph = LegalGraph()
        graph.register_document("TT-39", "39/2014/TT-BTC", "Thông tư số 39/2014/TT-BTC")
        graph.register_document("TT-78", "78/2021/TT-BTC", "Thông tư số 78/2021/TT-BTC")
        graph.add_all(
            extract_relations("TT-78", "Thông tư này bãi bỏ Thông tư số 39/2014/TT-BTC.")
        )
        incoming = graph.incoming("39/2014/TT-BTC")
        assert len(incoming) == 1
        assert incoming[0].relation == "REPEALS"
        assert incoming[0].matched_by == "number"

    def test_consolidated_number_without_year(self):
        """VBHN numbers routinely omit the year: '67/VBHN-NĐ-BCT'."""
        relations = extract_relations("X", "Văn bản hợp nhất số 67/VBHN-NĐ-BCT hợp nhất Nghị định")
        assert any("VBHN" in r.target_instrument for r in relations if r.target_instrument)


class TestGraphHygiene:
    def test_bare_cross_reference_by_name_is_not_an_edge(self):
        """A subject name with no directional cue is too weak to be a relation."""
        relations = extract_relations("X", "Căn cứ Luật Thuế giá trị gia tăng;")
        assert all(r.target_subject is None for r in relations)

    def test_dangling_target_is_kept(self):
        graph = LegalGraph()
        graph.register_document("TT-78", "78/2021/TT-BTC", "Thông tư số 78/2021/TT-BTC")
        graph.add_all(extract_relations("TT-78", "Bãi bỏ Thông tư số 99/1999/TT-XX."))
        # The target is absent from the corpus; the edge still records what is
        # missing rather than being discarded.
        assert graph.edges
        assert graph.edges[0].target_document_id is None

    def test_normalise_instrument(self):
        assert normalise_instrument(" 48 / 2024 / qh15 ") == "48/2024/QH15"
