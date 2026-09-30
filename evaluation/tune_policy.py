"""Tune the evidence-sufficiency thresholds on the development split only.

    python -m evaluation.tune_policy

Retrieval runs once per dev question; each threshold combination is then replayed
through app.agent.policy.assess. The objective is decision accuracy against the
acceptable decisions, with false answers (answering when the question should be
refused) weighted twice as heavily as false refusals.
"""

from __future__ import annotations

import itertools

from app.agent.policy import PolicyConfig, assess, retrieval_query, scope_check
from app.runtime import build_runtime
from evaluation.common import REPORTS, load_dataset, run_metadata, write_json

GRID = {
    "answer_threshold": [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    "unverified_threshold": [0.5, 0.7, 0.9],
    "stronger_margin": [0.05, 0.15, 0.3],
}


def decide(scope, eligible, ineligible, cfg: PolicyConfig) -> str:
    if scope is not None:
        return "REFUSE"
    verdict = assess(eligible, ineligible, cfg)
    if not verdict.sufficient:
        return "REFUSE"
    return "PARTIAL" if verdict.stronger_unverified else "ANSWER"


def score(cached: list[tuple[dict, object, list, list]], cfg: PolicyConfig) -> dict:
    correct = false_answer = false_refusal = 0
    for q, scope, eligible, ineligible in cached:
        decision = decide(scope, eligible, ineligible, cfg)
        correct += decision in q["acceptable_decisions"]
        if q["should_refuse"] is True and decision != "REFUSE":
            false_answer += 1
        if q["should_refuse"] is False and decision == "REFUSE":
            false_refusal += 1
    n = len(cached)
    return {"accuracy": round(correct / n, 4), "false_answers": false_answer, "false_refusals": false_refusal,
            "objective": round((correct - false_answer) / n, 4)}


def main() -> None:
    runtime = build_runtime()
    dev = load_dataset("dev")
    cached = []
    for q in dev:
        scope = scope_check(q["question"])
        res = runtime.retrieval.search(retrieval_query(q["question"]), top_k=5, mode="rerank")
        cached.append((q, scope, res.eligible, res.ineligible))
    trials = []
    for values in itertools.product(*GRID.values()):
        params = dict(zip(GRID, values))
        cfg = PolicyConfig(**params)
        trials.append({"params": params, **score(cached, cfg)})
    trials.sort(key=lambda t: (-t["objective"], t["false_answers"], -t["params"]["answer_threshold"]))
    best = trials[0]
    report = {"meta": run_metadata(runtime.settings, split="dev", objective="(correct - false_answers) / n"),
              "best": best, "top10": trials[:10], "questions": len(dev),
              "per_question_best_scores": [
                  {"id": q["id"], "type": q["type"], "best_eligible": round(e[0].score, 4) if e else 0.0,
                   "best_ineligible": round(i[0].score, 4) if i else 0.0, "scope_rule": s.value if s else None}
                  for q, s, e, i in cached]}
    write_json(REPORTS / "policy_tuning.json", report)
    print("best:", best)
    for t in trials[1:6]:
        print("     ", t)


if __name__ == "__main__":
    main()
