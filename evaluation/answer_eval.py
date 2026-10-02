"""End-to-end answer benchmark for Systems A–D.

A: dense top-5 naive RAG · B: hybrid (dense + BM25 + RRF) naive RAG · C: B + reranker naive RAG ·
D: final agent (hybrid + reranker + refusal policy + citation validation).

    python -m evaluation.answer_eval [--split test|dev|all] [--provider extractive|ollama|openai|anthropic]

Metrics (all automatic; see docs/EVALUATION.md for what each proxy can and cannot show):
- decision accuracy: decision is one of the question's acceptable decisions
- refusal accuracy / precision / recall / F1 (refusal = positive), false answers, false refusals
- correctness proxy (answerable questions): 2 if every required fact appears in the answer,
  1 if some do, 0 otherwise or when refused; reported as mean/2
- citation precision proxy: share of citations whose article is a gold article or whose text
  contains a required fact
- groundedness: share of claims whose text occurs verbatim in a cited source
- adversarial invariants: forbidden strings absent; answers carry citations
- latency p50/p95 per stage, LLM cost per 100 questions
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from dataclasses import replace
from pathlib import Path

from app.agent.policy import PolicyConfig
from app.agent.service import AnswerService
from app.runtime import build_runtime
from evaluation.common import DATASET, REPORTS, load_dataset, percentile, run_metadata, write_json


def norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def evaluate(results: list[tuple[dict, object]], catalog) -> dict:
    n = len(results)
    acc = sum(r.decision.value in q["acceptable_decisions"] for q, r in results) / n
    labelled = [(q, r) for q, r in results if q["should_refuse"] is not None]
    tp = sum(1 for q, r in labelled if q["should_refuse"] and r.decision.value == "REFUSE")
    fp = sum(1 for q, r in labelled if not q["should_refuse"] and r.decision.value == "REFUSE")
    fn = sum(1 for q, r in labelled if q["should_refuse"] and r.decision.value != "REFUSE")
    tn = len(labelled) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    answerable = [(q, r) for q, r in results if q["type"] in ("direct", "multi")]
    correctness = []
    for q, r in answerable:
        text = norm(r.answer)
        found = sum(norm(f) in text for f in q["required_facts"])
        correctness.append(0 if r.decision.value == "REFUSE" or found == 0 else
                           2 if found == len(q["required_facts"]) else 1)
    cite_total = cite_ok = 0
    claims_total = claims_grounded = 0
    for q, r in results:
        gold = {(g["document_id"], g["section"]) for g in q["gold"]}
        for c in r.citations:
            cite_total += 1
            chunk = catalog.get(c.chunk_id)
            text = norm(chunk.text)
            if (c.document_id, c.section) in gold or any(norm(f) in text for f in q["required_facts"]):
                cite_ok += 1
        sources = {c.citation_id: norm(catalog.get(c.chunk_id).text) for c in r.citations}
        for claim in r.claims:
            claims_total += 1
            claim_text = norm(claim.text)
            if any(claim_text in sources.get(cid, "") for cid in claim.citation_ids):
                claims_grounded += 1
    adversarial = [(q, r) for q, r in results if q["type"] == "adversarial"]
    violations = []
    for q, r in adversarial:
        blob = norm(r.answer + " " + " ".join(c.section + " " + c.document_number for c in r.citations))
        for bad in q["must_not_contain"]:
            if norm(bad) in blob:
                violations.append({"id": q["id"], "problem": f"contains {bad!r}"})
        if r.decision.value != "REFUSE" and q.get("must_cite_if_answered") and not r.citations:
            violations.append({"id": q["id"], "problem": "answer without citations"})
        if r.decision.value not in q["acceptable_decisions"]:
            violations.append({"id": q["id"], "problem": f"decision {r.decision.value}"})
    total = [r.metrics.total_ms for _, r in results]
    retrieval = [r.metrics.retrieval_ms for _, r in results if r.metrics.search_calls]
    rerank = [r.metrics.rerank_ms for _, r in results if r.metrics.rerank_ms]
    generation = [r.metrics.generation_ms for _, r in results]
    cost = sum(r.metrics.llm_cost_usd for _, r in results)
    by_type: dict[str, dict] = {}
    for q, r in results:
        t = by_type.setdefault(q["type"], {"n": 0, "acceptable": 0})
        t["n"] += 1
        t["acceptable"] += r.decision.value in q["acceptable_decisions"]
    return {
        "questions": n, "decision_accuracy": round(acc, 4),
        "refusal": {"labelled": len(labelled), "accuracy": round((tp + tn) / len(labelled), 4) if labelled else None,
                    "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
                    "false_answers": fn, "false_refusals": fp},
        "correctness_proxy": round(sum(correctness) / (2 * len(correctness)), 4) if correctness else None,
        "correctness_distribution": {str(k): correctness.count(k) for k in (0, 1, 2)},
        "citation_precision_proxy": round(cite_ok / cite_total, 4) if cite_total else None,
        "citations": cite_total,
        "groundedness": round(claims_grounded / claims_total, 4) if claims_total else None,
        "adversarial_violations": violations,
        "latency_ms": {"total_p50": percentile(total, 0.5), "total_p95": percentile(total, 0.95),
                       "retrieval_p50": percentile(retrieval, 0.5), "retrieval_p95": percentile(retrieval, 0.95),
                       "rerank_p50": percentile(rerank, 0.5), "rerank_p95": percentile(rerank, 0.95),
                       "generation_p50": percentile(generation, 0.5), "generation_p95": percentile(generation, 0.95)},
        "llm_cost_usd_per_100": round(cost / n * 100, 4),
        "by_type": {k: {**v, "rate": round(v["acceptable"] / v["n"], 4)} for k, v in sorted(by_type.items())},
    }


def _model_name(settings, provider: str | None) -> str:
    provider = provider or settings.llm_provider
    return {"openai": settings.openai_model, "ollama": settings.ollama_model,
            "anthropic": settings.llm_model}.get(provider, "none (extractive)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="test")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--systems", default="A,B,C,D")
    parser.add_argument("--dataset", type=Path, default=DATASET, help="e.g. data/eval/questions_heldout_v1.jsonl")
    parser.add_argument("--verifier", choices=["none", "ollama", "openai"], default=None,
                        help="gray-zone verifier for the extractive agent (overrides LLM_VERIFIER)")
    parser.add_argument("--verifier-model", default=None)
    parser.add_argument("--verifier-floor", type=float, default=None)
    parser.add_argument("--verifier-veto", action="store_true")
    parser.add_argument("--tag", default="", help="suffix for the report name, e.g. a model label")
    parser.add_argument("--policy", type=Path, default=None,
                        help="tuning report (its best.params) or a JSON of PolicyConfig fields, e.g. "
                             "reports/policy_tuning_rr_ft.json for a fine-tuned reranker")
    args = parser.parse_args()
    runtime = build_runtime()
    if args.verifier:
        runtime.settings.llm_verifier = args.verifier
    if args.verifier_model:
        runtime.settings.verifier_model = args.verifier_model
    policy = PolicyConfig(answer_threshold=runtime.settings.refusal_threshold)
    if args.policy:
        data = json.loads(args.policy.read_text(encoding="utf-8"))
        policy = replace(policy, **(data["best"]["params"] if "best" in data else data))
    if args.verifier_floor is not None or args.verifier_veto:
        policy = replace(policy, verifier_floor=args.verifier_floor, verifier_veto=args.verifier_veto)
    service = AnswerService(runtime, policy=policy)
    questions = load_dataset(args.split, args.dataset)
    runtime.retrieval.search("khởi động mô hình", top_k=1)  # warm models so latency excludes loading
    report = {"meta": run_metadata(runtime.settings, args.dataset, split=args.split,
                                   provider=args.provider or runtime.settings.llm_provider,
                                   llm_model=_model_name(runtime.settings, args.provider), policy=vars(service.policy),
                                   policy_source=str(args.policy) if args.policy else "defaults",
                                   verifier=service.verifier.name if service.verifier else None),
              "systems": {}}
    traces = []
    for system in args.systems.split(","):
        results = []
        for q in questions:
            r = service.answer(q["question"], system=system, provider=args.provider)
            results.append((q, r))
            traces.append({"system": system, "id": q["id"], "type": q["type"], "question": q["question"],
                           "acceptable": q["acceptable_decisions"], "decision": r.decision.value,
                           "reason": r.reason.value if r.reason else None, "answer": r.answer,
                           "citations": [(c.document_number, c.section) for c in r.citations],
                           "metrics": r.metrics.model_dump()})
        metrics = evaluate(results, runtime.catalog)
        metrics["failures"] = [t["id"] for t in traces if t["system"] == system
                               and t["decision"] not in t["acceptable"]]
        report["systems"][system] = metrics
        print(system, json.dumps({k: v for k, v in metrics.items() if k not in ("by_type",)}, ensure_ascii=False))
    name = f"answers_{args.split}_{args.provider or runtime.settings.llm_provider}{args.tag}"
    if service.verifier:
        report["meta"]["verifier_stats"] = vars(service.verifier.stats)
    write_json(REPORTS / f"{name}.json", report)
    with (REPORTS / f"{name}_traces.jsonl").open("w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote reports/{name}.json")


if __name__ == "__main__":
    main()
