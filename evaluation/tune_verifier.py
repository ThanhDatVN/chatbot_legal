"""Choose the gray-zone verifier settings on development data only (dev split of v2 + paraphrase dev).

    python -m evaluation.tune_verifier [--verifier ollama|openai] [--model qwen3:4b]

Runs system D for every combination of verifier_floor and verifier_veto. Verifier verdicts depend only on
(question, article units), so they are cached and each distinct check reaches the model once. Writes
reports/verifier_tuning.json. The held-out sets are never read here.
"""

from __future__ import annotations

import argparse
import itertools
import time
from dataclasses import asdict, replace

from app.agent.policy import PolicyConfig
from app.agent.service import AnswerService
from app.agent.verifier import VerifierStats, make_verifier
from app.runtime import build_runtime
from evaluation.answer_eval import evaluate
from evaluation.common import REPORTS, ROOT, load_dataset, run_metadata, write_json

PARAPHRASE_DEV = ROOT / "data" / "eval" / "questions_paraphrase_dev_v1.jsonl"
FLOORS = [None, 0.02, 0.05, 0.1, 0.2, 0.4]
VETO = [False, True]


class CachedVerifier:
    def __init__(self, inner):
        self.inner = inner
        self.name = inner.name
        self.stats = VerifierStats()
        self.cache: dict[tuple, list[int] | None] = {}

    def check(self, question, title, units):
        key = (question, title, tuple(units))
        if key not in self.cache:
            self.cache[key] = self.inner.check(question, title, units)
        return self.cache[key]


def score(results, catalog) -> dict:
    m = evaluate(results, catalog)
    r = m["refusal"]
    n = m["questions"]
    correct = round(m["decision_accuracy"] * n)
    return {"accuracy": m["decision_accuracy"], "false_answers": r["false_answers"],
            "false_refusals": r["false_refusals"], "correctness": m["correctness_proxy"],
            "citation_precision": m["citation_precision_proxy"],
            "objective": round((correct - r["false_answers"]) / n, 4)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifier", default="ollama", choices=["ollama", "openai"])
    parser.add_argument("--model", default=None, help="defaults to OLLAMA_MODEL / OPENAI_MODEL")
    args = parser.parse_args()
    runtime = build_runtime()
    runtime.settings.llm_verifier = args.verifier
    if args.model:
        runtime.settings.verifier_model = args.model
    inner = make_verifier(runtime.settings)
    if inner is None:
        raise SystemExit("verifier not available (missing OPENAI_API_KEY?)")
    verifier = CachedVerifier(inner)
    sets = {"dev": load_dataset("dev"), "pdev": load_dataset("pdev", PARAPHRASE_DEV)}
    trials = []
    for floor, veto in itertools.product(FLOORS, VETO):
        policy = replace(PolicyConfig(), verifier_floor=floor, verifier_veto=veto)
        service = AnswerService(runtime, policy=policy, verifier=verifier if (floor is not None or veto) else None)
        started = time.perf_counter()
        per_set = {}
        for name, questions in sets.items():
            results = [(q, service.answer(q["question"], system="D", provider="extractive")) for q in questions]
            per_set[name] = score(results, runtime.catalog)
        combined = {k: round((per_set["dev"][k] * len(sets["dev"]) + per_set["pdev"][k] * len(sets["pdev"]))
                             / (len(sets["dev"]) + len(sets["pdev"])), 4)
                    for k in ("accuracy", "objective")}
        trial = {"verifier_floor": floor, "verifier_veto": veto, **combined, "by_set": per_set,
                 "seconds": round(time.perf_counter() - started, 1)}
        trials.append(trial)
        print(trial, flush=True)
    best = sorted(trials, key=lambda t: (-t["objective"], t["verifier_veto"], -(t["verifier_floor"] or 1)))[0]
    report = {"meta": run_metadata(runtime.settings, split="dev+pdev", verifier=inner.name,
                                   objective="(correct - false_answers) / n"),
              "base_policy": asdict(PolicyConfig()), "best": best, "trials": trials,
              "verifier_calls": inner.stats.calls, "verifier_seconds": round(inner.stats.seconds, 1),
              "verifier_tokens": {"input": inner.stats.input_tokens, "output": inner.stats.output_tokens},
              "verifier_errors": inner.stats.errors[:20]}
    out = REPORTS / f"verifier_tuning_{inner.name.replace('/', '_').replace(':', '-')}.json"
    write_json(out, report)
    print("best:", best)
    print(f"wrote {out.relative_to(ROOT)} ({inner.stats.calls} verifier calls, {inner.stats.seconds:.0f}s)")


if __name__ == "__main__":
    main()
