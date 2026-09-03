"""Regression tests for the bitemporal store (defect D-05) and idempotent ingest.

D-05: `version_as_of` filtered **valid time** only. The table stored
`ingested_at` / `superseded_at` but nothing queried them, so the audit question
ADR-010 promises — *"what would the system have said, had you asked on date
X?"* — could not be expressed.

Both axes matter and mean different things:

    valid time        when the rule bound taxpayers
    transaction time  what this system had ingested at that moment
"""

from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from virag.schemas import DocumentMeta  # noqa: E402
from virag.store import db  # noqa: E402


@pytest.fixture()
def engine(tmp_path):
    eng = create_engine(f"sqlite+pysqlite:///{tmp_path / 'test.sqlite3'}", future=True)
    db.init_db(eng)
    return eng


def _meta(version_id: str, **overrides) -> DocumentMeta:
    base = {
        "document_id": "D1",
        "instrument_number": "10/2020/TT-BTC",
        "effective_from": "2020-01-01",
        "effective_to": "2022-12-31",
        "version_id": version_id,
    }
    base.update(overrides)
    return DocumentMeta(**base)


def _two_versions(engine) -> dt.datetime:
    """Ingest v1, capture the moment, then supersede it with v2."""
    meta = _meta("v1")
    db.upsert_document(engine, meta)
    db.record_version(engine, meta, "hash-v1")
    time.sleep(0.05)
    cut = dt.datetime.now(dt.UTC)
    time.sleep(0.05)
    db.record_version(engine, _meta("v2"), "hash-v2")
    return cut


class TestValidTime:
    def test_returns_version_in_force(self, engine):
        db.upsert_document(engine, _meta("v1"))
        db.record_version(engine, _meta("v1"), "h1")
        assert db.version_as_of(engine, "D1", "2021-06-15")["version_id"] == "v1"

    def test_date_outside_validity_returns_nothing(self, engine):
        db.upsert_document(engine, _meta("v1"))
        db.record_version(engine, _meta("v1"), "h1")
        assert db.version_as_of(engine, "D1", "2030-01-01") is None
        assert db.version_as_of(engine, "D1", "2019-01-01") is None

    def test_open_ended_validity_is_in_force(self, engine):
        meta = _meta("v1", effective_to=None)
        db.upsert_document(engine, meta)
        db.record_version(engine, meta, "h1")
        assert db.version_as_of(engine, "D1", "2030-01-01") is not None


class TestTransactionTime:
    def test_defaults_to_latest_knowledge(self, engine):
        _two_versions(engine)
        assert db.version_as_of(engine, "D1", "2021-06-15")["version_id"] == "v2"

    def test_reconstructs_earlier_knowledge(self, engine):
        """The audit query: same valid-time date, earlier knowledge cut."""
        cut = _two_versions(engine)
        assert db.version_as_of(engine, "D1", "2021-06-15", as_known_at=cut)["version_id"] == "v1"

    def test_the_two_axes_are_independent(self, engine):
        cut = _two_versions(engine)
        now = db.version_as_of(engine, "D1", "2021-06-15")
        then = db.version_as_of(engine, "D1", "2021-06-15", as_known_at=cut)
        assert now["version_id"] != then["version_id"], (
            "same valid-time date must resolve differently at different "
            "transaction times, or the second axis is not being used"
        )

    def test_before_anything_was_ingested(self, engine):
        _two_versions(engine)
        assert db.version_as_of(engine, "D1", "2021-06-15", as_known_at="2019-01-01") is None

    def test_accepts_a_bare_date_string(self, engine):
        _two_versions(engine)
        far_future = db.version_as_of(engine, "D1", "2021-06-15", as_known_at="2099-01-01")
        assert far_future["version_id"] == "v2"


class TestImmutableVersioning:
    def test_reingesting_identical_content_is_a_noop(self, engine):
        meta = _meta("v1")
        db.upsert_document(engine, meta)
        first = db.record_version(engine, meta, "same-hash")
        second = db.record_version(engine, _meta("v1"), "same-hash")
        assert first[1] is True, "first ingest creates a version"
        assert second[1] is False, "re-ingest must not create a second row"
        assert len(db.versions_of(engine, "D1")) == 1

    def test_changed_content_creates_a_new_version(self, engine):
        db.upsert_document(engine, _meta("v1"))
        db.record_version(engine, _meta("v1"), "hash-a")
        db.record_version(engine, _meta("v2"), "hash-b")
        assert len(db.versions_of(engine, "D1")) == 2

    def test_previous_version_is_closed_not_deleted(self, engine):
        db.upsert_document(engine, _meta("v1"))
        db.record_version(engine, _meta("v1"), "hash-a")
        db.record_version(engine, _meta("v2"), "hash-b")
        versions = {v["version_id"]: v for v in db.versions_of(engine, "D1")}
        assert versions["v1"]["superseded_at"] is not None, "the old version is closed"
        assert versions["v2"]["superseded_at"] is None, "the new version is open"
        assert db.current_version(engine, "D1")["version_id"] == "v2"
