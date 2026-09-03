"""Regression tests for the vector store (defects D-10, D-11).

D-10: the NumPy fallback appended blindly, so re-ingesting a chunk produced two
rows with the same id. Qdrant overwrites by point id, so the two backends
disagreed on recall and ranking — which defeats the purpose of a fallback that
is supposed to behave like the real thing (ADR-016).

D-11: the two stores used different identity functions — the NumPy store keyed
on the full `chunk_id` string, Qdrant on `int(chunk_id[:15], 16)`, discarding
part of the id.

Also covers `SearchFilters.matches`, which must stay equivalent to the Qdrant
payload filter it mirrors.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from virag.index.vector_store import (  # noqa: E402
    UNKNOWN_FROM,
    UNKNOWN_TO,
    NumpyVectorStore,
    SearchFilters,
    _point_id,
    to_days,
)
from virag.schemas import Chunk  # noqa: E402


def chunk(index: int, **overrides) -> Chunk:
    base = {
        "chunk_id": f"id{index}",
        "document_id": "DOC-1",
        "parent_id": "P1",
        "text": f"text {index}",
        "citation_label": f"Điều {index}",
    }
    base.update(overrides)
    return Chunk(**base)


@pytest.fixture()
def store(tmp_path) -> NumpyVectorStore:
    s = NumpyVectorStore(tmp_path)
    s.recreate(4)
    return s


class TestUpsertSemantics:
    def test_inserts_new_chunks(self, store):
        store.upsert([chunk(1), chunk(2)], np.eye(4, dtype=np.float32)[:2])
        assert store.count() == 2

    def test_reupsert_replaces_instead_of_duplicating(self, store):
        """D-10: the defect produced two rows with the same id."""
        store.upsert([chunk(1)], np.array([[1, 0, 0, 0]], dtype=np.float32))
        store.upsert([chunk(1)], np.array([[0, 0, 1, 0]], dtype=np.float32))
        assert store.count() == 1
        assert store.ids == ["id1"]

    def test_reupsert_replaces_the_vector(self, store):
        store.upsert([chunk(1)], np.array([[1, 0, 0, 0]], dtype=np.float32))
        store.upsert([chunk(1)], np.array([[0, 0, 1, 0]], dtype=np.float32))
        assert list(store.matrix[0]) == [0.0, 0.0, 1.0, 0.0]

    def test_reupsert_replaces_the_payload(self, store):
        store.upsert([chunk(1, effective_from="2020-01-01")], np.eye(4, dtype=np.float32)[:1])
        store.upsert([chunk(1, effective_from="2022-01-01")], np.eye(4, dtype=np.float32)[:1])
        assert store.payloads[0]["effective_from"] == "2022-01-01"

    def test_mixed_batch_updates_and_appends(self, store):
        store.upsert([chunk(1), chunk(2)], np.eye(4, dtype=np.float32)[:2])
        store.upsert([chunk(2), chunk(3)], np.eye(4, dtype=np.float32)[2:4])
        assert store.count() == 3
        assert store.ids == ["id1", "id2", "id3"]

    def test_empty_batch_is_a_noop(self, store):
        store.upsert([], np.zeros((0, 4), dtype=np.float32))
        assert store.count() == 0

    def test_search_returns_no_duplicate_ids_after_reingest(self, store):
        store.upsert([chunk(1), chunk(2)], np.eye(4, dtype=np.float32)[:2])
        store.upsert([chunk(1), chunk(2)], np.eye(4, dtype=np.float32)[:2])
        hits = store.search(np.array([1, 0, 0, 0], dtype=np.float32), top_k=10)
        assert len(hits) == len({chunk_id for chunk_id, _ in hits})


class TestPointIdentity:
    def test_is_deterministic(self):
        assert _point_id("a3f9c1d2e4b58607") == _point_id("a3f9c1d2e4b58607")

    def test_uses_the_whole_chunk_id(self):
        """D-11: truncating to 15 hex chars made these two collide."""
        assert _point_id("a" * 15 + "1") != _point_id("a" * 15 + "2")

    def test_is_a_uuid_string(self):
        value = _point_id("abc")
        assert isinstance(value, str)
        assert len(value) == 36 and value.count("-") == 4


class TestSearchFilters:
    def _payload(self, **overrides) -> dict:
        base = {
            "effective_from_days": to_days("2020-01-01", UNKNOWN_FROM),
            "effective_to_days": to_days("2022-12-31", UNKNOWN_TO),
            "authority_tier": 7,
            "tax_domains": ["gtgt"],
            "document_id": "DOC-1",
        }
        base.update(overrides)
        return base

    def test_in_force_on_date(self):
        f = SearchFilters(as_of_days=to_days("2021-06-15", 0))
        assert f.matches(self._payload())

    def test_not_yet_effective(self):
        f = SearchFilters(as_of_days=to_days("2019-06-15", 0))
        assert not f.matches(self._payload())

    def test_expired(self):
        f = SearchFilters(as_of_days=to_days("2023-06-15", 0))
        assert not f.matches(self._payload())

    def test_unknown_bounds_always_match(self):
        payload = self._payload(
            effective_from_days=UNKNOWN_FROM, effective_to_days=UNKNOWN_TO
        )
        assert SearchFilters(as_of_days=to_days("1999-01-01", 0)).matches(payload)

    def test_tax_domain_filter(self):
        assert SearchFilters(tax_domains=["gtgt"]).matches(self._payload())
        assert not SearchFilters(tax_domains=["tndn"]).matches(self._payload())

    def test_authority_tier_ceiling(self):
        assert SearchFilters(max_authority_tier=7).matches(self._payload())
        assert not SearchFilters(max_authority_tier=5).matches(self._payload())

    def test_document_id_filter(self):
        assert SearchFilters(document_ids=["DOC-1"]).matches(self._payload())
        assert not SearchFilters(document_ids=["DOC-2"]).matches(self._payload())

    def test_temporal_filter_applied_during_search(self, store):
        store.upsert(
            [
                chunk(1, effective_from="2020-01-01", effective_to="2020-12-31"),
                chunk(2, effective_from="2022-01-01", effective_to="2022-12-31"),
            ],
            np.array([[1, 0, 0, 0], [1, 0, 0, 0]], dtype=np.float32),
        )
        hits = store.search(
            np.array([1, 0, 0, 0], dtype=np.float32),
            top_k=10,
            filters=SearchFilters(as_of_days=to_days("2020-06-15", 0)),
        )
        assert [chunk_id for chunk_id, _ in hits] == ["id1"]


class TestPersistence:
    def test_round_trip_preserves_upsert_semantics(self, tmp_path):
        store = NumpyVectorStore(tmp_path)
        store.recreate(4)
        store.upsert([chunk(1), chunk(2)], np.eye(4, dtype=np.float32)[:2])
        store.save()

        reloaded = NumpyVectorStore(tmp_path).load()
        assert reloaded.count() == 2
        reloaded.upsert([chunk(1)], np.array([[0, 0, 0, 1]], dtype=np.float32))
        assert reloaded.count() == 2, "the id map must survive a reload"
