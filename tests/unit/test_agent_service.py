import json
from types import SimpleNamespace

import pytest

from app.agent.claude_agent import ClaudeAgent
from app.agent.service import AnswerService
from app.agent.tools import TOOL_DEFINITIONS, ToolBox
from app.config import Settings
from app.retrieval.service import RetrievalService
from app.retrieval.sparse import SparseIndex
from app.runtime import Runtime
from app.schemas import Decision, RefusalReason
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


def test_get_source_only_opens_retrieved_chunks(runtime):
    tb = ToolBox(runtime.catalog, runtime.retrieval)
    text, err = tb.call("get_source", {"chunk_id": C2})
    assert err and "source_not_found" in text
    tb.call("search_evidence", {"query": "thời gian thử việc cao đẳng", "top_k": 3, "document_ids": None})
    text, err = tb.call("get_source", {"chunk_id": C2})
    assert not err and json.loads(text)["section"] == "Điều 25"


def test_tool_input_validation_and_limits(runtime):
    tb = ToolBox(runtime.catalog, runtime.retrieval, max_search_calls=1)
    text, err = tb.call("search_evidence", {"query": "x", "top_k": 99})
    assert err and "invalid_input" in text
    text, err = tb.call("search_evidence", {"query": "nghỉ hằng năm", "top_k": 2, "extra": 1})
    assert err
    assert not tb.call("search_evidence", {"query": "nghỉ hằng năm", "top_k": 2, "document_ids": None})[1]
    text, err = tb.call("search_evidence", {"query": "nghỉ hằng năm", "top_k": 2, "document_ids": None})
    assert err and "tool_limit" in text
    text, err = tb.call("run_shell", {"cmd": "ls"})
    assert err and "only search_evidence and get_source" in text
    assert [t["name"] for t in TOOL_DEFINITIONS] == ["search_evidence", "get_source"]


def test_extractive_answer_is_cited_from_the_snapshot(runtime):
    result = AnswerService(runtime).answer("Người lao động làm việc đủ 12 tháng được nghỉ hằng năm bao nhiêu ngày làm việc?")
    assert result.decision == Decision.ANSWER
    assert "12 ngày làm việc" in result.answer and "[1]" in result.answer
    assert [c.chunk_id for c in result.citations] == [C1]
    assert result.citations[0].source_url == "https://congbao.chinhphu.vn/van-ban/x.htm"
    assert any("chưa được chuyên gia" in n for n in result.notices)


def test_unverified_evidence_leads_to_currency_refusal(runtime):
    result = AnswerService(runtime).answer("Sổ quản lý lao động gồm thông tin về họ tên, ngày tháng năm sinh gì?")
    assert result.decision == Decision.REFUSE
    assert result.reason == RefusalReason.CURRENCY_UNVERIFIED
    assert result.citations == []
    assert any(s.chunk_id == C3 and not s.eligible for s in result.related_sources)


def test_out_of_scope_is_refused_without_search(runtime):
    result = AnswerService(runtime).answer("Cách tính thuế thu nhập cá nhân?")
    assert result.decision == Decision.REFUSE and result.reason == RefusalReason.OUT_OF_SCOPE
    assert result.metrics.search_calls == 0


# ----------------------------------------------------------------------------- Claude agent with a fake client
def block(**kw):
    return SimpleNamespace(**kw)


def response(stop, content):
    return SimpleNamespace(stop_reason=stop, content=content, model="claude-opus-5-5",
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=200, cache_read_input_tokens=0,
                                                 cache_creation_input_tokens=0))


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        step = self.script.pop(0)
        return step(kwargs) if callable(step) else step


def final_json(claims, decision="ANSWER"):
    text = json.dumps({"decision": decision, "reason": None, "claims": claims, "unanswered": None}, ensure_ascii=False)
    return response("end_turn", [block(type="thinking", thinking=""), block(type="text", text=text)])


def test_claude_agent_loop_and_citation_validation(runtime):
    runtime.settings.llm_provider = "anthropic"
    client = FakeClient([
        response("tool_use", [block(type="tool_use", id="t1", name="search_evidence",
                                    input={"query": "nghỉ hằng năm 12 tháng", "top_k": 3, "document_ids": None})]),
        response("tool_use", [block(type="tool_use", id="t2", name="get_source", input={"chunk_id": C1})]),
        final_json([
            {"text": "Người làm đủ 12 tháng được nghỉ 12 ngày làm việc.", "chunk_ids": [C1],
             "quote": "12 ngày làm việc đối với người làm công việc trong điều kiện bình thường"},
            {"text": "Người lao động được nghỉ 30 ngày.", "chunk_ids": [C1], "quote": "12 ngày làm việc"},
            {"text": "Thử việc tối đa 60 ngày.", "chunk_ids": [C2], "quote": "Không quá 60 ngày"},
        ]),
    ])
    result = AnswerService(runtime, llm_client=client).answer("Nghỉ phép năm bao nhiêu ngày?")
    assert result.decision == Decision.PARTIAL  # two claims failed validation
    assert [c.text for c in result.claims] == ["Người làm đủ 12 tháng được nghỉ 12 ngày làm việc."]
    assert [c.chunk_id for c in result.citations] == [C1]
    assert "30 ngày" not in result.answer
    assert any("Đã loại 2 nhận định" in n for n in result.notices)
    first = client.calls[0]
    assert first["model"] == "claude-opus-5-5" and first["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in first["betas"]
    assert [t["name"] for t in first["tools"]] == ["search_evidence", "get_source"]
    assert first["output_config"]["format"]["type"] == "json_schema"
    tool_results = client.calls[1]["messages"][-1]["content"]
    assert tool_results[0]["type"] == "tool_result" and "<untrusted_source_data>" in tool_results[0]["content"]
    assert result.metrics.input_tokens == 3000 and result.metrics.llm_cost_usd > 0


def test_claude_refusal_stop_reason(runtime):
    runtime.settings.llm_provider = "anthropic"
    client = FakeClient([response("refusal", [])])
    result = AnswerService(runtime, llm_client=client).answer("Nghỉ phép năm bao nhiêu ngày?")
    assert result.decision == Decision.REFUSE and result.citations == []


def test_claude_unparseable_final_answer_is_refused(runtime):
    agent = ClaudeAgent(ToolBox(runtime.catalog, runtime.retrieval), runtime.settings,
                        FakeClient([response("end_turn", [block(type="text", text="not json")])]))
    draft = agent.run("Nghỉ phép năm?", "2026-09-30")
    assert draft.decision == Decision.REFUSE and "unparseable_final_answer" in draft.notes
