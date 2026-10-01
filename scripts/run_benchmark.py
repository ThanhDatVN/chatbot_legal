"""Run the whole benchmark in order and stop at the first failing step.

    python scripts/run_benchmark.py            # extractive mode, writes reports/*.json and reports/benchmark_v3.md

Commit the code first: every report records the commit it measured and marks it "-dirty" when code or data
outside reports/ and docs/ differ from that commit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = "data/eval/questions_heldout_v1.jsonl"
PDEV = "data/eval/questions_paraphrase_dev_v1.jsonl"

STEPS = [
    ["evaluation.dataset_v2"],
    ["evaluation.heldout_v1"],
    ["evaluation.paraphrase_dev_v1"],
    ["evaluation.retrieval_eval", "--split", "all"],
    ["evaluation.retrieval_eval", "--split", "heldout", "--dataset", HELDOUT],
    ["evaluation.tune_policy"],  # dev split + paraphrase dev only
    ["evaluation.answer_eval", "--split", "test"],
    ["evaluation.answer_eval", "--split", "pdev", "--dataset", PDEV, "--systems", "D"],
    ["evaluation.answer_eval", "--split", "heldout", "--dataset", HELDOUT, "--systems", "A,D"],
    ["evaluation.security_eval"],
    ["evaluation.report"],
]


def main() -> int:
    for step in STEPS:
        print(">>", " ".join(step), flush=True)
        code = subprocess.run([sys.executable, "-X", "utf8", "-W", "ignore", "-m", *step], cwd=ROOT).returncode
        if code:
            print(f"step failed with exit code {code}: {' '.join(step)}")
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
