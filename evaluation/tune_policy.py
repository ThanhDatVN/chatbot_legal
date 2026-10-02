"""Tune the evidence-sufficiency thresholds on development data only.

    python -m evaluation.tune_policy [--tag _rr_ft]      # a tag writes reports/policy_tuning<tag>.json

Development data = the dev split of dataset v2 plus the paraphrase development set
(questions_paraphrase_dev_v1.jsonl, everyday wording). The held-out paraphrase set and the test split are
never read here. Retrieval runs once per question; each threshold combination is then replayed
through app.agent.policy.assess. The objective is decision accuracy against the
acceptable decisions, with false answers (answering when the question should be
refused) weighted twice as heavily as false refusals.
"""

from __future__ import annotations

import argparse
import itertools
from dataclasses import asdict

from app.agent.lexicon import expand_query
from app.agent.policy import PolicyConfig, assess, retrieval_query, scope_check
from app.runtime import build_runtime
from evaluation.common import DATASET, REPORTS, ROOT, load_dataset, run_metadata, write_json

PARAPHRASE_DEV = ROOT / "data" / "eval" / "questions_paraphrase_dev_v1.jsonl"

# keep_ratio only changes which sources are quoted, not the decision, so it was swept separately with the
# full answer pipeline on the dev split (python -m evaluation.answer_eval --split dev with PolicyConfig overrides).
KEEP_RATIO_SWEEP_NOTE = ("keep_ratio swept on dev with the full answer pipeline: 0.5/0.7 -> citation precision 0.818, "
                         "correctness 0.917; 0.85 -> 0.844 / 0.917; 0.95 -> 0.891 / 0.883 (correctness drops). "
                         "Chose 0.85.")

GRID = {
    "answer_threshold": [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95],
    "unverified_threshold": [0.5, 0.7, 0.9],
    "stronger_margin": [0.05, 0.15, 0.3],
    "superseded_margin": [None, 0.0, 0.02, 0.05],
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="",
                        help="suffix for the report name; a tagged run (e.g. _ft for a fine-tuned reranker) never "
                             "overwrites reports/policy_tuning.json, whose 'chosen' block documents the defaults")
    args = parser.parse_args()
    runtime = build_runtime()
    dev = load_dataset("dev") + (load_dataset("pdev", PARAPHRASE_DEV) if PARAPHRASE_DEV.exists() else [])
    cached = []
    for q in dev:
        scope = scope_check(q["question"])
        res = runtime.retrieval.search(expand_query(retrieval_query(q["question"])), top_k=5, mode="rerank")
        cached.append((q, scope, res.eligible, res.ineligible))
    trials = []
    for values in itertools.product(*GRID.values()):
        params = dict(zip(GRID, values))
        cfg = PolicyConfig(**params)
        trials.append({"params": params, **score(cached, cfg)})
    trials.sort(key=lambda t: (-t["objective"], t["false_answers"], -t["params"]["answer_threshold"],
                               t["params"]["superseded_margin"] is None))
    best = trials[0]
    chosen = asdict(PolicyConfig())
    chosen_score = score(cached, PolicyConfig())
    by_set = {name: score([c for c in cached if c[0]["split"] == name], PolicyConfig()) for name in ("dev", "pdev")}
    report = {"meta": run_metadata(runtime.settings, DATASET, split="dev+pdev",
                                   extra_dataset=PARAPHRASE_DEV.name, objective="(correct - false_answers) / n"),
              "best": best, "top10": trials[:10], "questions": len(dev),
              "chosen": {**chosen, "dev_score": chosen_score, "dev_score_by_set": by_set,
                         "notes": ["chosen = PolicyConfig defaults used by the service; ties on stronger_margin are "
                                   "broken towards the middle value",
                                   "superseded_margin added with dataset v2: None -> 3 false answers on dev, "
                                   "0.0 -> 1 with no extra false refusal; 0.0 chosen", KEEP_RATIO_SWEEP_NOTE]},
              "per_question_best_scores": [
                  {"id": q["id"], "type": q["type"], "best_eligible": round(e[0].score, 4) if e else 0.0,
                   "best_ineligible": round(i[0].score, 4) if i else 0.0, "scope_rule": s.value if s else None}
                  for q, s, e, i in cached]}
    write_json(REPORTS / f"policy_tuning{args.tag}.json", report)
    print("best:", best)
    print("chosen:", chosen, chosen_score, by_set)
    for t in trials[1:6]:
        print("     ", t)


if __name__ == "__main__":
    main()
