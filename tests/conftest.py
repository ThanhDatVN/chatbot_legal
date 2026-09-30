"""Shared fixtures: a tiny synthetic corpus with an embedded Qdrant store and deterministic models."""

import pytest

from app.config import Settings
from app.retrieval.service import RetrievalService
from app.retrieval.sparse import SparseIndex
from app.runtime import Runtime
from app.storage.corpus import CorpusCatalog
from app.storage.vector_store import VectorStore
from tests.unit.helpers import HashEncoder, OverlapReranker, make_chunk, write_snapshot

ANNUAL = ("Điều 113. Nghỉ hằng năm\n1. Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động "
          "thì được nghỉ hằng năm như sau:\na) 12 ngày làm việc đối với người làm công việc trong điều kiện bình thường;")
PROBATION = "Điều 25. Thời gian thử việc\n2. Không quá 60 ngày đối với công việc cần trình độ cao đẳng trở lên;"
LEDGER = "Điều 3. Sổ quản lý lao động\nSổ quản lý lao động gồm thông tin về họ tên, ngày tháng năm sinh, số sổ bảo hiểm."
C1, C2, C3, C4 = "1" * 24, "2" * 24, "3" * 24, "4" * 24


@pytest.fixture()
def runtime(tmp_path):
    chunks = [
        make_chunk(C1, ANNUAL),
        make_chunk(C2, PROBATION, section="Điều 25", article=25),
        make_chunk(C3, LEDGER, document_id="145_2020_nd_cp", section="Điều 3", article=3, currency_status="unverified"),
        make_chunk(C4, ANNUAL, document_id="45_2019_qh14", currency_status="superseded_by_consolidation"),
    ]
    snap = write_snapshot(tmp_path / "snapshots", chunks)
    settings = Settings(snapshots_dir=tmp_path / "snapshots", active_snapshot="test", index_dir=tmp_path / "idx",
                        runtime_dir=tmp_path / "rt", llm_provider="extractive", _env_file=None)
    catalog = CorpusCatalog(snap, "pilot")
    encoder = HashEncoder()
    store = VectorStore("t", path=tmp_path / "idx" / "qdrant")
    store.recreate(encoder.dim)
    ids = catalog.order
    texts = [catalog.chunks[c].embedding_text for c in ids]
    store.upsert(ids, encoder.encode(texts), [{"chunk_id": c} for c in ids])
    retrieval = RetrievalService(catalog, store, SparseIndex.build(ids, texts), encoder, OverlapReranker())
    rt = Runtime(settings=settings, catalog=catalog, store=store, retrieval=retrieval, index_manifest={})
    yield rt
    store.client.close()
