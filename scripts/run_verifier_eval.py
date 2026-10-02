"""Tune and evaluate the gray-zone verifier for one local model, on a laptop or on Kaggle.

    python scripts/run_verifier_eval.py --model qwen3:4b              # Ollama must be running with the model pulled
    python scripts/run_verifier_eval.py --model qwen3:8b --skip-tune --floor 0.05

Steps: tune verifier_floor / verifier_veto on dev v2 + paraphrase dev (evaluation.tune_verifier), read the best
setting from its report, then run system D once with that setting on the v2 test split and on both held-out
sets. Reports land in reports/ with a tag naming the model, e.g. answers_heldout2_extractive_verifier_qwen3-4b.json.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = [  # (split, dataset)
    ("test", "data/eval/questions_v2.jsonl"),
    ("heldout2", "data/eval/questions_heldout_v2.jsonl"),
    ("heldout", "data/eval/questions_heldout_v1.jsonl"),
]


def run(args: list[str]) -> None:
    print(">>", " ".join(args), flush=True)
    code = subprocess.run([sys.executable, "-X", "utf8", "-W", "ignore", "-m", *args], cwd=ROOT).returncode
    if code:
        raise SystemExit(f"step failed ({code}): {' '.join(args)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Ollama model, e.g. qwen3:4b, qwen3:8b, qwen3:14b")
    parser.add_argument("--verifier", default="ollama", choices=["ollama", "openai"])
    parser.add_argument("--skip-tune", action="store_true", help="use --floor/--veto instead of tuning")
    parser.add_argument("--floor", type=float, default=None)
    parser.add_argument("--veto", action="store_true")
    args = parser.parse_args()
    label = args.model.replace("/", "-").replace(":", "-")
    if args.skip_tune:
        floor, veto = args.floor, args.veto
    else:
        run(["evaluation.tune_verifier", "--verifier", args.verifier, "--model", args.model])
        report = ROOT / "reports" / f"verifier_tuning_{args.verifier}_{label}.json"
        best = json.loads(report.read_text(encoding="utf-8"))["best"]
        floor, veto = best["verifier_floor"], best["verifier_veto"]
        print(f"best on development data: floor={floor} veto={veto} objective={best['objective']}")
    for split, dataset in RUNS:
        cmd = ["evaluation.answer_eval", "--split", split, "--dataset", dataset, "--systems", "D",
               "--provider", "extractive", "--verifier", args.verifier, "--verifier-model", args.model,
               "--tag", f"_verifier_{label}"]
        if floor is not None:
            cmd += ["--verifier-floor", str(floor)]
        if veto:
            cmd.append("--verifier-veto")
        run(cmd)
    print("done; reports in reports/")


if __name__ == "__main__":
    main()
