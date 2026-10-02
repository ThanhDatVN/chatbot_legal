"""Step 4: compare the base and fine-tuned rerankers from the reports written by kaggle/finetune_reranker.sh.

    python -m training.compare [--base _rr_base] [--ft _rr_ft]

Prints a Markdown summary: thresholds each reranker got from dev + paraphrase dev, retrieval quality, and the
answer decisions of system D on test v2 and held-out v3 (one measurement per configuration).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.common import REPORTS
from training.common import MODELS


def load(name: str) -> dict | None:
    path = REPORTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def f3(x) -> str:
    return "–" if x is None else f"{x:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="_rr_base")
    parser.add_argument("--ft", default="_rr_ft")
    parser.add_argument("--meta", type=Path, default=MODELS / "reranker-ft" / "training_meta.json")
    args = parser.parse_args()
    tags = {"base": args.base, "fine-tuned": args.ft}
    out = ["# Reranker fine-tuning: base vs fine-tuned", ""]

    if args.meta.exists():
        meta = json.loads(args.meta.read_text(encoding="utf-8"))
        before, after = meta["history"][0]["val"], meta["history"][-1]["val"]
        data = meta.get("data", {})
        out += [f"Training: {meta['groups']['train']} groups, {meta['args']['epochs']} epoch(s), lr "
                f"{meta['args']['lr']}, {meta['seconds'] // 60} min on {meta['gpu']}; commit {meta['git_commit']}.",
                f"Questions after decontamination: {data.get('questions', '?')}; false-negative check "
                f"{data.get('false_negative_check', '?')}.", "",
                "| synthetic validation | acc@1 | MRR | positive ≥ 0.8 | negative ≥ 0.8 | near-miss ≥ 0.8 |",
                "| --- | --- | --- | --- | --- | --- |"]
        for label, v in (("before", before), ("after", after)):
            out.append(f"| {label} | {f3(v['acc_at_1'])} | {f3(v['mrr'])} | {f3(v['positive_at_threshold'])} | "
                       f"{f3(v['negative_at_threshold'])} | {f3(v['near_miss_at_threshold'])} |")
        out.append("")

    out += ["## Thresholds chosen on dev v2 + paraphrase dev", "",
            "| reranker | answer_threshold | unverified | stronger_margin | superseded_margin | dev objective |",
            "| --- | --- | --- | --- | --- | --- |"]
    for label, tag in tags.items():
        t = load(f"policy_tuning{tag}.json")
        if t:
            p = t["best"]["params"]
            out.append(f"| {label} | {p['answer_threshold']} | {p['unverified_threshold']} | {p['stronger_margin']} | "
                       f"{p['superseded_margin']} | {f3(t['best']['objective'])} |")

    out += ["", "## Retrieval (article-level)", "", "| set | reranker | system | Hit@5 | MRR | Recall@5 |",
            "| --- | --- | --- | --- | --- | --- |"]
    for split in ("all", "heldout3"):
        for label, tag in tags.items():
            r = load(f"retrieval_{split}{tag}.json")
            for system in ("C_rerank", "D_rerank_expanded"):
                if r and system in r["systems"]:
                    s = r["systems"][system]
                    out.append(f"| {split} | {label} | {system} | {f3(s['hit@5'])} | {f3(s['mrr'])} | "
                               f"{f3(s['recall@5'])} |")

    out += ["", "## Answers, system D (extractive, no verifier)", "",
            "| set | reranker | accuracy | false answers | false refusals | correctness | citation precision |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    rows = [(split, label, f"answers_{split}_extractive{tag}.json") for split in ("test", "heldout3")
            for label, tag in tags.items()]
    rows.append(("heldout3", "base, default policy", f"answers_heldout3_extractive{args.base}_defaults.json"))
    for split, label, name in rows:
        a = load(name)
        if a and "D" in a["systems"]:
            s = a["systems"]["D"]
            out.append(f"| {split} | {label} | {f3(s['decision_accuracy'])} | {s['refusal']['false_answers']} | "
                       f"{s['refusal']['false_refusals']} | {f3(s['correctness_proxy'])} | "
                       f"{f3(s['citation_precision_proxy'])} |")
    print("\n".join(out))


if __name__ == "__main__":
    main()
