"""Retrieval benchmark for Systems A (dense), B (hybrid RRF) and C (hybrid + reranker).

    python -m evaluation.retrieval_eval [--split all|dev|test]

All systems search the same candidate set (chunks eligible for current-law answers)
of the same snapshot, so differences come from the retrieval method only.
Relevance is judged at article level: a chunk hits when its (document, article)
is one of the question's gold sections.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.runtime import build_runtime
from evaluation.common import DATASET, REPORTS, load_dataset, percentile, run_metadata, section_key, write_json

SYSTEMS = {"A_dense": "dense", "B_hybrid": "hybrid", "C_rerank": "rerank"}


def metrics_for(ranked: list[tuple[str, str]], gold: set[tuple[str, str]], required: set[tuple[str, str]]) -> dict:
    first = next((i for i, key in enumerate(ranked, start=1) if key in gold), None)
    top5, top10 = set(ranked[:5]), set(ranked[:10])
    return {"hit@5": int(first is not None and first <= 5), "mrr": 1.0 / first if first else 0.0,
            "recall@5": len(gold & top5) / len(gold), "recall@10": len(gold & top10) / len(gold),
            "all_evidence@5": int(required <= top5), "first_rank": first}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="all")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args()
    runtime = build_runtime()
    questions = [q for q in load_dataset(args.split, args.dataset) if q["type"] in ("direct", "multi")]
    runtime.retrieval.search("khởi động mô hình", top_k=1)  # warm-up: exclude model loading from latency
    results: dict[str, dict] = {}
    per_query = []
    for name, mode in SYSTEMS.items():
        rows, latencies = [], []
        for q in questions:
            gold = {(g["document_id"], g["section"]) for g in q["gold"]}
            required = {(g["document_id"], g["section"]) for g in q["gold_required"]}
            started = time.perf_counter()
            res = runtime.retrieval.search(q["question"], top_k=10, mode=mode, include_ineligible=False)
            latencies.append((time.perf_counter() - started) * 1000)
            ranked = [section_key(s) for s in res.eligible]
            m = metrics_for(ranked, gold, required)
            rows.append({"id": q["id"], "type": q["type"], **m})
            per_query.append({"system": name, "id": q["id"], "question": q["question"],
                              "gold": sorted(gold), "top5": ranked[:5], **m})
        n = len(rows)
        multi = [r for r in rows if r["type"] == "multi"]
        results[name] = {
            "questions": n, "hit@5": round(sum(r["hit@5"] for r in rows) / n, 4),
            "mrr": round(sum(r["mrr"] for r in rows) / n, 4),
            "recall@5": round(sum(r["recall@5"] for r in rows) / n, 4),
            "recall@10": round(sum(r["recall@10"] for r in rows) / n, 4),
            "all_evidence@5_multi": round(sum(r["all_evidence@5"] for r in multi) / len(multi), 4) if multi else None,
            "latency_ms_p50": percentile(latencies, 0.5), "latency_ms_p95": percentile(latencies, 0.95),
            "misses": [r["id"] for r in rows if not r["hit@5"]]}
        print(name, {k: v for k, v in results[name].items() if k != "misses"})
    report = {"meta": run_metadata(runtime.settings, args.dataset, split=args.split, candidate_set="eligible chunks",
                                   relevance="article-level (document_id, section)"),
              "systems": results, "per_query": per_query}
    write_json(REPORTS / f"retrieval_{args.split}.json", report)
    print(f"wrote reports/retrieval_{args.split}.json")


if __name__ == "__main__":
    main()
