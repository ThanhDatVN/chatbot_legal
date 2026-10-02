"""Step 2: turn generated questions into training groups with hard negatives from the hybrid retriever.

    python -m training.mine_negatives [--check-backend ollama --check-model qwen3:8b]

For each answerable question the positive is the chunk it was written from. Negatives are other in-scope chunks
from the hybrid (bge-m3 + BM25) top 30, never another part of the same article and never an article that cites,
or is cited by, the positive (a decree article detailing a Labour Code article answers the same question).
Candidates the base reranker scores at least 0.5, or above the positive (from 0.1), may be false negatives:
with --check-backend the gray-zone verifier prompt decides for the highest --max-checks of them, and the rest are
dropped. Each group keeps the 4 hardest remaining negatives, 3 sampled from the rest of the top 30 and 1 random
in-scope chunk. A near-miss question gets only its own chunk as a negative: the generator wrote it so that chunk
does not answer it, and the self-check agreed.

Questions that are near-duplicates of any evaluation question (character 4-gram Jaccard >= 0.5 or bge-m3
cosine >= 0.92) are removed first. About one article in ten holds the synthetic validation questions.
Output: data/training/pairs.jsonl and data/training/pairs_summary.json.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from app.agent.extractive import ExtractiveAgent
from app.agent.verifier import make_verifier
from app.runtime import build_runtime
from training.common import (DATA, Corpus, article_key, char_ngrams, evaluation_questions, is_validation, jaccard,
                             normalize, read_jsonl)

QUERIES = DATA / "queries.jsonl"
PAIRS = DATA / "pairs.jsonl"
JACCARD_MAX = 0.5
COSINE_MAX = 0.92
SUSPICIOUS = 0.5  # base score from which a candidate may answer the question
SUSPICIOUS_FLOOR = 0.1  # candidates above the positive are suspicious only from this score


def answers(check, query: str, chunk) -> bool:
    units = ExtractiveAgent._body(chunk.text, chunk.section_label)
    return check.check(query, f"{chunk.section_label}. {chunk.section_title or ''} — {chunk.document_number}",
                       units) is not None


def decontaminate(items: list[dict], encoder) -> tuple[list[dict], dict]:
    evals = evaluation_questions()
    eval_grams = [char_ngrams(q) for q in evals]
    eval_vecs = encoder.encode(evals, batch_size=32, max_length=256)
    seen, kept, dropped = set(), [], {"duplicate": 0, "jaccard": 0, "cosine": 0}
    vecs = encoder.encode([it["query"] for it in items], batch_size=32, max_length=256)
    for it, vec in zip(items, vecs):
        key = normalize(it["query"])
        if key in seen:
            dropped["duplicate"] += 1
            continue
        seen.add(key)
        grams = char_ngrams(it["query"])
        if max(jaccard(grams, g) for g in eval_grams) >= JACCARD_MAX:
            dropped["jaccard"] += 1
            continue
        if float(np.max(eval_vecs @ vec)) >= COSINE_MAX:
            dropped["cosine"] += 1
            continue
        kept.append(it)
    return kept, {"evaluation_questions": len(evals), **dropped}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", default=str(QUERIES))
    parser.add_argument("--out", default=str(PAIRS))
    parser.add_argument("--hard", type=int, default=4, help="hardest remaining negatives per question")
    parser.add_argument("--sampled", type=int, default=3, help="negatives sampled from the rest of the top 30")
    parser.add_argument("--random", type=int, default=1, help="random in-scope negatives per question")
    parser.add_argument("--check-backend", choices=["none", "ollama", "openai"], default="none")
    parser.add_argument("--check-model", default=None)
    parser.add_argument("--max-checks", type=int, default=3,
                        help="suspicious candidates checked per question (in parallel); the rest are dropped")
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    runtime = build_runtime()
    catalog, retrieval = runtime.catalog, runtime.retrieval
    if runtime.settings.reranker_model != "BAAI/bge-reranker-v2-m3":
        print(f"warning: mining with {runtime.settings.reranker_model}, not the base reranker")
    corpus = Corpus(catalog)
    in_scope = catalog.ids("in_scope")
    check = None
    if args.check_backend != "none":
        check = make_verifier(runtime.settings.model_copy(
            update={"llm_verifier": args.check_backend, "verifier_model": args.check_model}))

    items, unknown = [], 0
    for rec in read_jsonl(Path(args.queries)):
        if rec["chunk_id"] not in catalog.chunks:  # generated on another snapshot
            unknown += 1
            continue
        for q in rec["questions"]:
            items.append({"query": q, "kind": "answerable", "source": rec["chunk_id"]})
        for q in rec["near_miss"]:
            items.append({"query": q, "kind": "near_miss", "source": rec["chunk_id"]})
    if unknown:
        print(f"warning: {unknown} generated records refer to chunks not in {catalog.snapshot_id}; skipped")
    items, contamination = decontaminate(items, retrieval.encoder)
    print(f"{len(items)} questions after decontamination: {contamination}", flush=True)

    started = time.perf_counter()
    executor = ThreadPoolExecutor(max(1, args.max_checks))
    stats = {"suspicious": 0, "dropped_false_negative": 0, "kept_after_check": 0, "no_negative": 0}
    pos_scores, near_scores, groups = [], [], []
    for i, it in enumerate(items, 1):
        source = catalog.get(it["source"])
        group = {"qid": f"q{i:05d}", "query": it["query"], "kind": it["kind"], "source": source.chunk_id,
                 "article": list(article_key(source)),
                 "split": "val" if is_validation(article_key(source)) else "train"}
        if it["kind"] == "near_miss":
            score = retrieval.reranker.score(it["query"], [source.embedding_text])[0]
            near_scores.append(score)
            groups.append({**group, "pos": [], "neg": [source.chunk_id], "base": {source.chunk_id: round(score, 5)}})
            continue
        found = retrieval.search(it["query"], top_k=30, mode="hybrid", subset="in_scope", include_ineligible=False)
        candidates = [s.chunk for s in found.eligible if not corpus.related(source, s.chunk)]
        scores = retrieval.reranker.score(it["query"], [source.embedding_text] + [c.embedding_text for c in candidates])
        pos_score, cand_scores = scores[0], scores[1:]
        pos_scores.append(pos_score)
        ranked = sorted(zip(candidates, cand_scores), key=lambda x: -x[1])
        suspicious = [(c, s) for c, s in ranked if s >= SUSPICIOUS or (s >= pos_score and s >= SUSPICIOUS_FLOOR)]
        stats["suspicious"] += len(suspicious)
        checked = suspicious[: args.max_checks] if check is not None else []
        verdicts = list(executor.map(answers, [check] * len(checked), [it["query"]] * len(checked),
                                     [c for c, _ in checked]))
        cleared = {c.chunk_id for (c, _), ok in zip(checked, verdicts) if not ok}
        stats["kept_after_check"] += len(cleared)
        stats["dropped_false_negative"] += len(suspicious) - len(cleared)
        dropped = {c.chunk_id for c, _ in suspicious} - cleared
        clean = [(c, s) for c, s in ranked if c.chunk_id not in dropped]
        hard = clean[: args.hard]
        rest = clean[args.hard:]
        sampled = rng.sample(rest, min(args.sampled, len(rest)))
        taken = {c.chunk_id for c, _ in hard + sampled}
        pool = [cid for cid in in_scope if cid not in taken and not corpus.related(source, catalog.get(cid))]
        randoms = [(catalog.get(cid), None) for cid in rng.sample(pool, args.random)]
        negs = hard + sampled + randoms
        if not negs:
            stats["no_negative"] += 1
            continue
        base = {source.chunk_id: round(pos_score, 5)}
        base.update({c.chunk_id: round(s, 5) for c, s in hard + sampled})
        groups.append({**group, "pos": [source.chunk_id], "neg": [c.chunk_id for c, _ in negs], "base": base})
        if i % 200 == 0:
            rate = (time.perf_counter() - started) / i
            print(f"[{i}/{len(items)}] {rate:.2f}s/question, ~{rate * (len(items) - i) / 60:.0f} min left", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for g in groups:
            fh.write(json.dumps(g, ensure_ascii=False) + "\n")
    summary = {
        "snapshot": catalog.snapshot_id, "reranker": runtime.settings.reranker_model, "questions": len(items),
        "groups": {"train": sum(g["split"] == "train" for g in groups), "val": sum(g["split"] == "val" for g in groups),
                   "answerable": sum(g["kind"] == "answerable" for g in groups),
                   "near_miss": sum(g["kind"] == "near_miss" for g in groups)},
        "decontamination": contamination, "negatives": stats,
        "false_negative_check": f"{args.check_backend}/{args.check_model}" if check else "none (dropped)",
        "base_positive_score": {"mean": round(statistics.mean(pos_scores), 4) if pos_scores else None,
                                "share_below_0.8": round(sum(s < 0.8 for s in pos_scores) / len(pos_scores), 4)
                                if pos_scores else None},
        "base_near_miss_score": {"mean": round(statistics.mean(near_scores), 4) if near_scores else None,
                                 "share_at_or_above_0.8": round(sum(s >= 0.8 for s in near_scores) / len(near_scores), 4)
                                 if near_scores else None},
        "seconds": round(time.perf_counter() - started)}
    out.with_name(out.stem + "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                                         encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
