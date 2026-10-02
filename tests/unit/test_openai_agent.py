"""OpenAI agent with a fake client: same tools, same untrusted wrapping, same citation validation."""

import json
from types import SimpleNamespace

from app.agent.openai_agent import OpenAIAgent
from app.agent.service import AnswerService
from app.agent.tools import ToolBox
from app.schemas import Decision, RefusalReason
from tests.conftest import C1, C2


def call(cid, name, args):
    return SimpleNamespace(id=cid, type="function", function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def completion(message, finish="stop"):
    return SimpleNamespace(model="gpt-4o-mini-2024-07-18",
                           choices=[SimpleNamespace(message=message, finish_reason=finish)],
                           usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=200,
                                                 prompt_tokens_details=SimpleNamespace(cached_tokens=400)))


def msg(content=None, tool_calls=None, refusal=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls, refusal=refusal, role="assistant")


class FakeOpenAI:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs, default=str)))
        return self.script.pop(0)


def final(claims, decision="ANSWER"):
    return completion(msg(json.dumps({"decision": decision, "reason": None, "claims": claims, "unanswered": None},
                                     ensure_ascii=False)))


def test_openai_agent_loop_and_citation_validation(runtime):
    runtime.settings.llm_provider = "openai"
    client = FakeOpenAI([
        completion(msg(tool_calls=[call("c1", "search_evidence",
                                        {"query": "nghỉ hằng năm 12 tháng", "top_k": 3, "document_ids": None})]),
                   "tool_calls"),
        completion(msg(tool_calls=[call("c2", "get_source", {"chunk_id": C1})]), "tool_calls"),
        final([{"text": "Người làm đủ 12 tháng được nghỉ 12 ngày làm việc.", "chunk_ids": [C1],
                "quote": "12 ngày làm việc đối với người làm công việc trong điều kiện bình thường"},
               {"text": "Thử việc tối đa 60 ngày.", "chunk_ids": [C2], "quote": "Không quá 60 ngày"}]),
    ])
    result = AnswerService(runtime, llm_client=client).answer("Nghỉ phép năm bao nhiêu ngày?")
    assert result.decision == Decision.PARTIAL  # the claim citing an unfetched source is dropped
    assert [c.chunk_id for c in result.citations] == [C1]
    first = client.calls[0]
    assert first["model"] == "gpt-4o-mini" and first["temperature"] == 0 and first["parallel_tool_calls"] is False
    assert [t["function"]["name"] for t in first["tools"]] == ["search_evidence", "get_source"]
    assert all(t["function"]["strict"] for t in first["tools"])
    assert first["response_format"]["json_schema"]["strict"] is True
    assert first["messages"][0]["role"] == "system"
    tool_msg = client.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1"
    assert "<untrusted_source_data>" in tool_msg["content"]
    assert result.metrics.input_tokens == 3000 and 0 < result.metrics.llm_cost_usd < 0.01


def test_openai_refusal_and_bad_json(runtime):
    runtime.settings.llm_provider = "openai"
    refused = AnswerService(runtime, llm_client=FakeOpenAI([completion(msg(refusal="I can't help"))])).answer("x" * 10)
    assert refused.decision == Decision.REFUSE and refused.citations == []
    agent = OpenAIAgent(ToolBox(runtime.catalog, runtime.retrieval), runtime.settings,
                        FakeOpenAI([completion(msg("not json"))]))
    draft = agent.run("Nghỉ phép năm?", "2026-10-01")
    assert draft.decision == Decision.REFUSE and "unparseable_final_answer" in draft.notes


def test_missing_openai_key_is_a_typed_refusal(runtime):
    runtime.settings.llm_provider = "openai"
    runtime.settings.openai_api_key = None
    result = AnswerService(runtime).answer("Nghỉ phép năm bao nhiêu ngày?")
    assert result.decision == Decision.REFUSE and result.reason == RefusalReason.SOURCE_UNAVAILABLE
    assert result.mode == "error:llm_unavailable"
