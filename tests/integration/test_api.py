"""API contract tests on the synthetic corpus (no model downloads, no GPU)."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.errors import SnapshotUnavailable
from app.storage.sessions import SessionStore
from tests.conftest import C1, C2


@pytest.fixture()
def client(runtime, tmp_path):
    app = create_app(runtime_factory=lambda: runtime, sessions=SessionStore(tmp_path / "s.sqlite3"))
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_reports_unavailable_snapshot(tmp_path):
    def missing():
        raise SnapshotUnavailable()

    with TestClient(create_app(runtime_factory=missing)) as c:
        r = c.get("/ready")
    assert r.status_code == 503 and r.json()["error"] == "snapshot_unavailable"


def test_chat_answer_session_and_feedback(client):
    r = client.post("/api/chat", json={"message": "Người lao động làm việc đủ 12 tháng được nghỉ hằng năm bao nhiêu "
                                                  "ngày làm việc?"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "ANSWER" and body["citations"][0]["chunk_id"] == C1
    assert body["trace"] == []  # traces only in debug mode
    sid = body["session_id"]
    history = client.get(f"/api/sessions/{sid}").json()["messages"]
    assert len(history) == 1 and history[0]["result"]["query_id"] == body["query_id"]
    assert client.post("/api/feedback", json={"query_id": body["query_id"], "rating": -1,
                                              "reason": "citation_wrong"}).status_code == 201
    assert client.post("/api/feedback", json={"query_id": "q_unknown", "rating": 1}).status_code == 404
    assert client.delete(f"/api/sessions/{sid}").status_code == 200


def test_chat_debug_returns_trace(client):
    r = client.post("/api/chat", json={"message": "Thời gian thử việc với công việc cần trình độ cao đẳng?",
                                       "debug": True})
    assert r.status_code == 200 and r.json()["trace"]


def test_chat_rejects_invalid_input_without_traceback(client):
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_request" and "Traceback" not in r.text
    assert client.post("/api/chat", json={"message": "x", "tools": ["run_shell"]}).status_code == 400


def test_search_returns_ranks_and_eligibility(client):
    r = client.post("/api/search", json={"query": "nghỉ hằng năm 12 ngày", "top_k": 3})
    results = r.json()["results"]
    assert results[0]["chunk_id"] == C1 and results[0]["eligible"]
    assert {"dense_rank", "bm25_rank", "rrf_score", "reranker_score"} <= set(results[0])
    assert any(not x["eligible"] for x in results)  # superseded / unverified evidence is labelled, not hidden


def test_source_lookup_by_id_only(client):
    r = client.get(f"/api/sources/{C2}")
    assert r.status_code == 200 and r.json()["section"] == "Điều 25"
    assert client.get("/api/sources/" + "f" * 24).status_code == 404
    assert client.get(f"/api/sources/{C2}", params={"snapshot_id": "other"}).status_code == 404


def test_documents_catalog(client):
    docs = client.get("/api/documents").json()
    assert docs["total"] == 3 and docs["snapshot_id"] == "test"
    filtered = client.get("/api/documents", params={"q": "18/VBHN"}).json()
    assert filtered["total"] >= 1
    detail = client.get("/api/documents/18_2026_vbhn_vpqh").json()
    assert {s["section"] for s in detail["sections"]} == {"Điều 113", "Điều 25"}
    decree = client.get("/api/documents/145_2020_nd_cp").json()
    statuses = {s["section"]: s["currency_statuses"] for s in decree["sections"]}
    assert statuses == {"Điều 3": ["unverified"], "Điều 18": ["superseded_by_amendment"]}  # one row per article
    assert client.get("/api/documents/nope").status_code == 404
