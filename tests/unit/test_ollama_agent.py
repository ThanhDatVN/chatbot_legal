"""Ollama agent with a fake HTTP client: seeded search, tool loop, then a tool-less JSON turn."""

import json

import httpx

from app.agent.ollama_agent import OllamaAgent
from app.agent.service import AnswerService
from app.agent.tools import ToolBox
from app.schemas import Decision, RefusalReason
from tests.conftest import C1, C2


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class FakeOllama:
    def __init__(self, script):
        self.script = list(script)
        self.bodies = []

    def post(self, path, json=None):
        assert path == "/api/chat"
        self.bodies.append(json)
        return FakeResponse(self.script.pop(0))


def reply(content="", tool_calls=None):
    return {"message": {"role": "assistant", "content": content, "tool_calls": tool_calls or []},
            "prompt_eval_count": 900, "eval_count": 100}


def final(claims, decision="ANSWER"):
    return reply(json.dumps({"decision": decision, "reason": None, "claims": claims, "unanswered": None},
                            ensure_ascii=False))


def test_seeded_search_tool_loop_and_final_json(runtime):
    runtime.settings.llm_provider = "ollama"
    client = FakeOllama([
        reply(tool_calls=[{"function": {"name": "get_source", "arguments": {"chunk_id": C1}}}]),
        reply("Đủ căn cứ."),  # no more tool calls: phase 1 ends
        final([{"text": "Người làm đủ 12 tháng được nghỉ 12 ngày làm việc.", "chunk_ids": [C1],
                "quote": "12 ngày làm việc đối với người làm công việc trong điều kiện bình thường"},
               {"text": "Thử việc tối đa 60 ngày.", "chunk_ids": [C2], "quote": "Không quá 60 ngày"}]),
    ])
    result = AnswerService(runtime, llm_client=client).answer(
        "Người lao động làm việc đủ 12 tháng được nghỉ hằng năm bao nhiêu ngày làm việc?")
    assert result.decision == Decision.PARTIAL  # the claim on an unfetched source is dropped
    assert [c.chunk_id for c in result.citations] == [C1]
    first = client.bodies[0]
    # the agent ran the first search itself and the model saw its results
    assert first["messages"][2]["tool_calls"][0]["function"]["name"] == "search_evidence"
    assert first["messages"][3]["role"] == "tool" and "<untrusted_source_data>" in first["messages"][3]["content"]
    assert first["think"] is False and first["options"]["num_ctx"] == runtime.settings.ollama_num_ctx
    assert "tools" in first and "format" not in first
    last = client.bodies[-1]
    assert "tools" not in last and last["format"]["required"] == ["decision", "reason", "claims", "unanswered"]
    assert result.metrics.search_calls == 1 and result.metrics.llm_cost_usd == 0


def test_invented_chunk_ids_never_reach_the_answer(runtime):
    agent = OllamaAgent(ToolBox(runtime.catalog, runtime.retrieval), runtime.settings, FakeOllama([
        reply("Không cần thêm."),
        final([{"text": "Nghỉ 30 ngày.", "chunk_ids": ["chunk_1"], "quote": "nghỉ 30 ngày"}]),
    ]))
    draft = agent.run("Nghỉ phép năm?", "2026-10-01")
    assert draft.claims[0].chunk_ids == ["chunk_1"]  # what the model said...
    runtime.settings.llm_provider = "ollama"
    result = AnswerService(runtime, llm_client=FakeOllama([
        reply("Không cần thêm."),
        final([{"text": "Nghỉ 30 ngày.", "chunk_ids": ["chunk_1"], "quote": "nghỉ 30 ngày"}]),
    ])).answer("Nghỉ phép năm bao nhiêu ngày?")
    assert result.decision == Decision.REFUSE and result.citations == []  # ...is rejected by the validator


class DownClient:
    def post(self, path, json=None):
        raise httpx.ConnectError("connection refused")


def test_ollama_not_running_is_a_typed_refusal(runtime):
    runtime.settings.llm_provider = "ollama"
    result = AnswerService(runtime, llm_client=DownClient()).answer("Nghỉ phép năm bao nhiêu ngày?")
    assert result.decision == Decision.REFUSE and result.reason == RefusalReason.SOURCE_UNAVAILABLE
    assert result.mode == "error:llm_unavailable"
