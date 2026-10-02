#!/usr/bin/env bash
# Rebuild CiteAgent VN on a Kaggle GPU notebook and evaluate the gray-zone verifier with a larger local model.
#
#   VERIFIER_MODEL=qwen3:8b SOURCES_ZIP=/kaggle/input/citeagent-sources/citeagent_sources.zip \
#     bash kaggle/run_on_kaggle.sh
#
# Needs: GPU (T4 x2 or P100) and Internet enabled in the notebook settings. No API key is used.
set -euo pipefail

MODEL="${VERIFIER_MODEL:-qwen3:8b}"
OLLAMA_MODELS="$MODEL" source "$(dirname "${BASH_SOURCE[0]}")/setup.sh"
export LLM_VERIFIER=ollama

echo "== 1/2 Tune on development data, then evaluate once on test and both held-out sets"
python scripts/run_verifier_eval.py --model "$MODEL"
python -X utf8 -W ignore -m evaluation.answer_eval --split heldout2 --dataset data/eval/questions_heldout_v2.jsonl \
  --systems A,D --provider extractive --verifier none --tag _no_verifier

echo "== 2/2 Results"
python - <<'PY'
import glob, json
for path in sorted(glob.glob("reports/answers_*verifier*.json")):
    d = json.load(open(path, encoding="utf-8"))
    for name, s in d["systems"].items():
        r = s["refusal"]
        print(f"{path}: {name} acc={s['decision_accuracy']:.3f} false_answers={r['false_answers']} "
              f"false_refusals={r['false_refusals']} correctness={s['correctness_proxy']}")
PY
cp "$OUT/ollama.log" reports/ 2>/dev/null || true
python -c "import shutil; shutil.make_archive('$OUT/citeagent_results', 'zip', 'reports')"
echo "Download $OUT/citeagent_results.zip from the notebook's Output panel."
