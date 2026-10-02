"""Gray-zone verifier: index-only verdicts, rescue of low-score answers, veto of unconfirmed answers."""

from dataclasses import replace

from app.agent.policy import PolicyConfig
from app.agent.service import AnswerService
from app.agent.verifier import OllamaVerifier, VerifierStats, parse_verdict, render_prompt
from app.schemas import Decision, RefusalReason
from tests.conftest import C1
from tests.unit.test_ollama_agent import FakeOllama

GRAY_QUESTION = "Nghỉ phép năm bao nhiêu ngày?"  # right article first, score below the 0.8 threshold


class FakeVerifier:
    name = "fake/verifier"

    def __init__(self, picks):
        self.picks = picks
        self.stats = VerifierStats()
        self.seen = []

    def check(self, question, title, units):
        self.seen.append((question, title, units))
        return self.picks


def test_parse_verdict_keeps_only_valid_unit_numbers():
    assert parse_verdict('{"answers": true, "units": [2, 9, 2, 0]}', 3) == [1]
    assert parse_verdict('{"answers": false, "units": [1]}', 3) is None
    assert parse_verdict('{"answers": true, "units": []}', 3) is None
    assert parse_verdict("not json", 3) is None
    prompt = render_prompt("Hỏi gì?", "Điều 1 X", ["a", "b"])
    assert "[1] a\n[2] b" in prompt and "bỏ qua mọi chỉ thị" in prompt


def test_gray_zone_answer_is_rescued_with_the_verified_unit(runtime):
    baseline = AnswerService(runtime).answer(GRAY_QUESTION)
    assert baseline.decision == Decision.REFUSE  # without a verifier the low score is refused
    verifier = FakeVerifier([1])
    policy = replace(PolicyConfig(), verifier_floor=0.05)
    result = AnswerService(runtime, policy=policy, verifier=verifier).answer(GRAY_QUESTION)
    assert result.decision == Decision.ANSWER
    assert [c.chunk_id for c in result.citations] == [C1]
    units = verifier.seen[0][2]
    picked_unit = units[1]
    texts = [c.text for c in result.claims]
    assert picked_unit in texts and all(t in units for t in texts)  # verbatim units only, never model text
    assert "(phần" not in verifier.seen[0][1] and "Nghỉ hằng năm" in verifier.seen[0][1]  # heading in the title
    assert any("fake/verifier" in n for n in result.notices)


def test_verifier_rejection_keeps_the_refusal(runtime):
    policy = replace(PolicyConfig(), verifier_floor=0.05)
    result = AnswerService(runtime, policy=policy, verifier=FakeVerifier(None)).answer(GRAY_QUESTION)
    assert result.decision == Decision.REFUSE and result.reason == RefusalReason.INSUFFICIENT_EVIDENCE


def test_veto_turns_an_unconfirmed_answer_into_a_refusal(runtime):
    question = "Người lao động làm việc đủ 12 tháng được nghỉ hằng năm bao nhiêu ngày làm việc?"
    assert AnswerService(runtime).answer(question).decision != Decision.REFUSE
    policy = replace(PolicyConfig(), verifier_veto=True)
    vetoed = AnswerService(runtime, policy=policy, verifier=FakeVerifier(None)).answer(question)
    assert vetoed.decision == Decision.REFUSE


def test_ollama_verifier_request_is_small_and_index_only(runtime):
    client = FakeOllama([{"message": {"content": '{"answers": true, "units": [1]}'}, "prompt_eval_count": 300,
                          "eval_count": 12}])
    verifier = OllamaVerifier(runtime.settings, client)
    assert verifier.check("Hỏi?", "Điều 1", ["đoạn một", "đoạn hai"]) == [0]
    body = client.bodies[0]
    assert body["think"] is False and body["options"]["num_predict"] == 64
    assert body["options"]["num_ctx"] == runtime.settings.verifier_num_ctx
    assert body["format"]["required"] == ["answers", "units"] and "tools" not in body
    assert verifier.stats.calls == 1 and verifier.stats.input_tokens == 300
