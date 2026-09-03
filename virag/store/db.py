"""Bitemporal document store: instruments, versions, articles, relations, changes.

Two time axes are kept, which is what makes the Time Machine and the audit
trail possible:

*   **valid time** - ``effective_from`` / ``effective_to``: when the rule bound
    taxpayers in the real world.
*   **transaction time** - ``ingested_at`` / ``superseded_at``: when *this
    system* learned about it.

"Which rule applied on 15/06/2021, as far as we knew last March" is then a
plain query rather than an archaeology exercise.

Versions are immutable.  Re-ingesting an unchanged document is a no-op; an
changed body inserts a new version and closes the previous one, so citations
issued months ago still resolve to the exact text they were made against.

``DATABASE_URL`` selects the backend: Postgres in Docker, SQLite for tests and
local runs.  Only SQLAlchemy Core is used, so both behave identically.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    select,
)
from sqlalchemy.engine import Engine

from virag.schemas import DocumentMeta, LegalRelation
from virag.settings import get_settings

metadata = MetaData()


def _utcnow() -> datetime:
    return datetime.now(UTC)


documents = Table(
    "documents",
    metadata,
    Column("document_id", String(128), primary_key=True),
    Column("instrument_number", String(128), index=True),
    Column("document_type", String(128)),
    Column("issuing_authority", String(256)),
    Column("signer", String(256)),
    Column("title", Text),
    Column("promulgation_date", Date),
    Column("authority_tier", Integer, index=True),
    Column("source", String(64)),
    Column("source_url", Text),
    Column("source_role", String(64)),
    Column("tax_domains", JSON),
    Column("taxpayer_types", JSON),
    Column("first_seen_at", DateTime(timezone=True), default=_utcnow),
)

document_versions = Table(
    "document_versions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("version_id", String(200), nullable=False),
    Column("document_id", String(128), ForeignKey("documents.document_id"), nullable=False),
    Column("content_hash", String(64), nullable=False),
    # valid time
    Column("effective_from", Date),
    Column("effective_to", Date),
    Column("legal_status", String(32), default="UNKNOWN"),
    # transaction time
    Column("ingested_at", DateTime(timezone=True), default=_utcnow),
    Column("superseded_at", DateTime(timezone=True), nullable=True),
    Column("source_url", Text),
    Column("page_count", Integer, default=0),
    Column("ocr_page_count", Integer, default=0),
    Column("chunk_count", Integer, default=0),
    UniqueConstraint("version_id", name="uq_document_versions_version_id"),
    Index("ix_document_versions_document", "document_id", "superseded_at"),
)

legal_articles = Table(
    "legal_articles",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("version_id", String(200), nullable=False, index=True),
    Column("document_id", String(128), nullable=False, index=True),
    Column("parent_id", String(64), nullable=False),
    Column("dieu", String(16)),
    Column("chuong", String(16)),
    Column("heading", Text),
    Column("content", Text),
    Column("page_number", Integer),
    UniqueConstraint("version_id", "parent_id", name="uq_legal_articles_version_parent"),
)

legal_relations = Table(
    "legal_relations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_document_id", String(128), nullable=False, index=True),
    Column("relation", String(32), nullable=False),
    Column("target_instrument", String(128), nullable=False, index=True),
    Column("target_document_id", String(128), nullable=True),
    Column("target_dieu", String(16)),
    Column("target_khoan", String(16)),
    Column("confidence", Float, default=0.0),
    Column("evidence", Text),
    UniqueConstraint(
        "source_document_id", "relation", "target_instrument", name="uq_legal_relations_edge"
    ),
)

change_events = Table(
    "change_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("document_id", String(128), nullable=False, index=True),
    Column("from_version_id", String(200)),
    Column("to_version_id", String(200), nullable=False),
    Column("article_key", String(64), nullable=False),
    Column("change_kind", String(16), nullable=False),
    Column("detail", Text),
    Column("detected_at", DateTime(timezone=True), default=_utcnow, index=True),
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("question", Text, nullable=False),
    Column("answer", Text),
    Column("verdict", String(32), nullable=False),
    Column("comment", Text),
    Column("citations", JSON),
    Column("as_of_date", String(16)),
    Column("config_name", String(64)),
    Column("created_at", DateTime(timezone=True), default=_utcnow, index=True),
)

eval_runs = Table(
    "eval_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String(64), nullable=False, index=True),
    Column("config_name", String(64), nullable=False),
    Column("dataset", String(128)),
    Column("n_items", Integer),
    Column("metrics", JSON),
    Column("created_at", DateTime(timezone=True), default=_utcnow),
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_ENGINE: Engine | None = None


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    path = get_settings().index_root / "virag.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+pysqlite:///{path}"


def get_engine(url: str | None = None, echo: bool = False) -> Engine:
    global _ENGINE
    if url is not None:
        return create_engine(url, echo=echo, future=True)
    if _ENGINE is None:
        _ENGINE = create_engine(database_url(), echo=echo, future=True)
    return _ENGINE


def init_db(engine: Engine | None = None) -> Engine:
    engine = engine or get_engine()
    metadata.create_all(engine)
    return engine


def reset_db(engine: Engine | None = None) -> Engine:
    engine = engine or get_engine()
    metadata.drop_all(engine)
    metadata.create_all(engine)
    return engine


def _as_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def upsert_document(engine: Engine, meta: DocumentMeta) -> None:
    row = {
        "document_id": meta.document_id,
        "instrument_number": meta.instrument_number,
        "document_type": meta.document_type,
        "issuing_authority": meta.issuing_authority,
        "signer": meta.signer,
        "title": meta.title,
        "promulgation_date": _as_date(meta.promulgation_date),
        "authority_tier": meta.authority_tier,
        "source": meta.source,
        "source_url": meta.source_url,
        "source_role": meta.source_role,
        "tax_domains": meta.tax_domains,
        "taxpayer_types": meta.taxpayer_types,
    }
    with engine.begin() as conn:
        exists = conn.execute(
            select(documents.c.document_id).where(documents.c.document_id == meta.document_id)
        ).first()
        if exists:
            conn.execute(
                documents.update()
                .where(documents.c.document_id == meta.document_id)
                .values(**{k: v for k, v in row.items() if k != "document_id"})
            )
        else:
            conn.execute(documents.insert().values(first_seen_at=_utcnow(), **row))


def record_version(
    engine: Engine,
    meta: DocumentMeta,
    content_hash: str,
    *,
    page_count: int = 0,
    ocr_page_count: int = 0,
    chunk_count: int = 0,
) -> tuple[str, bool]:
    """Insert a version if the content changed.

    Returns ``(version_id, is_new)``.  ``is_new`` is False when this exact
    content was already ingested, which is what makes re-running ingestion
    idempotent.
    """
    version_id = meta.version_id or f"{meta.document_id}#{content_hash[:12]}"

    with engine.begin() as conn:
        existing = conn.execute(
            select(document_versions.c.version_id).where(
                document_versions.c.version_id == version_id
            )
        ).first()
        if existing:
            return version_id, False

        # Close the previous open version in transaction time.
        conn.execute(
            document_versions.update()
            .where(
                document_versions.c.document_id == meta.document_id,
                document_versions.c.superseded_at.is_(None),
            )
            .values(superseded_at=_utcnow())
        )
        conn.execute(
            document_versions.insert().values(
                version_id=version_id,
                document_id=meta.document_id,
                content_hash=content_hash,
                effective_from=_as_date(meta.effective_from),
                effective_to=_as_date(meta.effective_to),
                legal_status=meta.legal_status,
                ingested_at=_utcnow(),
                superseded_at=None,
                source_url=meta.source_url,
                page_count=page_count,
                ocr_page_count=ocr_page_count,
                chunk_count=chunk_count,
            )
        )
    return version_id, True


def record_articles(engine: Engine, version_id: str, document_id: str, parents: Iterable) -> int:
    rows = [
        {
            "version_id": version_id,
            "document_id": document_id,
            "parent_id": parent.parent_id,
            "dieu": parent.dieu,
            "chuong": parent.chuong,
            "heading": parent.citation_label,
            "content": parent.text,
            "page_number": parent.page_number,
        }
        for parent in parents
    ]
    if not rows:
        return 0
    with engine.begin() as conn:
        conn.execute(
            delete(legal_articles).where(legal_articles.c.version_id == version_id)
        )
        conn.execute(legal_articles.insert(), rows)
    return len(rows)


def record_relations(engine: Engine, relations: Iterable[LegalRelation]) -> int:
    written = 0
    with engine.begin() as conn:
        for relation in relations:
            exists = conn.execute(
                select(legal_relations.c.id).where(
                    legal_relations.c.source_document_id == relation.source_document_id,
                    legal_relations.c.relation == relation.relation,
                    legal_relations.c.target_instrument == relation.target_instrument,
                )
            ).first()
            if exists:
                continue
            conn.execute(
                legal_relations.insert().values(
                    source_document_id=relation.source_document_id,
                    relation=relation.relation,
                    target_instrument=relation.target_instrument,
                    target_document_id=relation.target_document_id,
                    target_dieu=relation.target_dieu,
                    target_khoan=relation.target_khoan,
                    confidence=relation.confidence,
                    evidence=relation.evidence,
                )
            )
            written += 1
    return written


def record_changes(engine: Engine, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with engine.begin() as conn:
        conn.execute(change_events.insert(), rows)
    return len(rows)


def record_feedback(engine: Engine, payload: dict[str, Any]) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            feedback.insert().values(
                question=payload.get("question", ""),
                answer=payload.get("answer"),
                verdict=payload.get("verdict", "unknown"),
                comment=payload.get("comment"),
                citations=payload.get("citations"),
                as_of_date=payload.get("as_of_date"),
                config_name=payload.get("config_name"),
                created_at=_utcnow(),
            )
        )
        return int(result.inserted_primary_key[0])


def record_eval_run(
    engine: Engine, run_id: str, config_name: str, dataset: str, n_items: int, metrics: dict
) -> None:
    with engine.begin() as conn:
        conn.execute(
            eval_runs.insert().values(
                run_id=run_id,
                config_name=config_name,
                dataset=dataset,
                n_items=n_items,
                metrics=metrics,
                created_at=_utcnow(),
            )
        )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def current_version(engine: Engine, document_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            select(document_versions)
            .where(
                document_versions.c.document_id == document_id,
                document_versions.c.superseded_at.is_(None),
            )
            .order_by(document_versions.c.ingested_at.desc())
        ).mappings().first()
    return dict(row) if row else None


def versions_of(engine: Engine, document_id: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(document_versions)
            .where(document_versions.c.document_id == document_id)
            .order_by(document_versions.c.ingested_at.asc())
        ).mappings().all()
    return [dict(row) for row in rows]


def version_as_of(engine: Engine, document_id: str, as_of: str) -> dict | None:
    """The version that was in force (valid time) on ``as_of``."""
    target = _as_date(as_of)
    if target is None:
        return None
    with engine.connect() as conn:
        rows = conn.execute(
            select(document_versions).where(document_versions.c.document_id == document_id)
        ).mappings().all()
    candidates = [
        dict(row)
        for row in rows
        if (row["effective_from"] is None or row["effective_from"] <= target)
        and (row["effective_to"] is None or row["effective_to"] >= target)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: (r["effective_from"] or target, r["ingested_at"]))


def recent_changes(engine: Engine, limit: int = 50, since: str | None = None) -> list[dict]:
    query = select(change_events).order_by(change_events.c.detected_at.desc()).limit(limit)
    if since:
        cutoff = _as_date(since)
        if cutoff:
            query = query.where(change_events.c.detected_at >= datetime.combine(cutoff, datetime.min.time()))
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(query).mappings().all()]


def relations_for(engine: Engine, document_id: str) -> list[dict]:
    with engine.connect() as conn:
        outgoing = conn.execute(
            select(legal_relations).where(legal_relations.c.source_document_id == document_id)
        ).mappings().all()
        incoming = conn.execute(
            select(legal_relations).where(legal_relations.c.target_document_id == document_id)
        ).mappings().all()
    return [dict(row) for row in list(outgoing) + list(incoming)]


def all_relations(engine: Engine) -> list[dict]:
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(select(legal_relations)).mappings().all()]


def stats(engine: Engine) -> dict[str, Any]:
    """Numbers for the admin dashboard."""
    with engine.connect() as conn:
        def scalar(query) -> int:
            return int(conn.execute(query).scalar() or 0)

        by_tier = conn.execute(
            select(documents.c.authority_tier, func.count())
            .group_by(documents.c.authority_tier)
            .order_by(documents.c.authority_tier)
        ).all()

        return {
            "documents": scalar(select(func.count()).select_from(documents)),
            "versions": scalar(select(func.count()).select_from(document_versions)),
            "active_versions": scalar(
                select(func.count())
                .select_from(document_versions)
                .where(document_versions.c.superseded_at.is_(None))
            ),
            "articles": scalar(select(func.count()).select_from(legal_articles)),
            "relations": scalar(select(func.count()).select_from(legal_relations)),
            "change_events": scalar(select(func.count()).select_from(change_events)),
            "feedback": scalar(select(func.count()).select_from(feedback)),
            "documents_by_authority_tier": {str(tier): count for tier, count in by_tier},
        }


def export_json(engine: Engine, path: Path) -> Path:
    """Dump the graph and stats for offline inspection / the report."""
    payload = {"stats": stats(engine), "relations": all_relations(engine)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path
