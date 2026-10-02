#!/usr/bin/env bash
# Rebuild CiteAgent VN on a Kaggle GPU notebook and evaluate the gray-zone verifier with a larger local model.
#
#   VERIFIER_MODEL=qwen3:8b SOURCES_ZIP=/kaggle/input/citeagent-sources/citeagent_sources.zip \
#     bash kaggle/run_on_kaggle.sh
#
# Needs: GPU (T4 x2 or P100) and Internet enabled in the notebook settings. No API key is used.
set -euo pipefail

MODEL="${VERIFIER_MODEL:-qwen3:8b}"
SNAP="${ACTIVE_SNAPSHOT:-corpus-2026-10-01-r2}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT=/kaggle/working
cd "$REPO_DIR"

echo "== 1/7 Python dependencies (torch comes with the Kaggle image)"
pip install -q -r requirements/api.txt

export HF_OFFLINE=false MODEL_DEVICE=cuda LLM_PROVIDER=extractive LLM_VERIFIER=ollama PYTHONUTF8=1

echo "== 2/7 Models from Hugging Face (the tokenizer must be cached before chunking)"
python - <<'PY'
from huggingface_hub import snapshot_download
for repo in ("BAAI/bge-m3", "BAAI/bge-reranker-v2-m3"):
    snapshot_download(repo, allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt"])
print("models cached")
PY

echo "== 3/7 Official source PDFs (from the uploaded zip if given, else the government CDNs)"
if [ -n "${SOURCES_ZIP:-}" ] && [ -f "$SOURCES_ZIP" ]; then
  python -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall('.')" "$SOURCES_ZIP"
fi
python scripts/download_sources.py   # verifies every SHA-256 and fetches what is missing

echo "== 4/7 Snapshot $SNAP (must reproduce the published chunks_sha256) and indexes"
if ! python -m ingestion.build --snapshot-id "$SNAP"; then
  echo "The build did not reproduce $SNAP. Building ${SNAP}-kaggle instead; compare its quality_report.json."
  SNAP="${SNAP}-kaggle"
  python -m ingestion.build --snapshot-id "$SNAP" --overwrite
fi
export ACTIVE_SNAPSHOT="$SNAP"
python -m app.indexing

echo "== 5/7 Ollama with $MODEL"
if ! command -v ollama >/dev/null; then
  (command -v zstd >/dev/null || (apt-get update -qq && apt-get install -y -qq zstd)) || true
  curl -fsSL https://ollama.com/install.sh | sh
fi
if ! curl -s localhost:11434/api/tags >/dev/null; then
  (OLLAMA_KEEP_ALIVE=60m nohup ollama serve > "$OUT/ollama.log" 2>&1 &)
  for _ in $(seq 1 60); do curl -s localhost:11434/api/tags >/dev/null && break; sleep 2; done
fi
ollama pull "$MODEL"

echo "== 6/7 Tune on development data, then evaluate once on test and both held-out sets"
python scripts/run_verifier_eval.py --model "$MODEL"
python -X utf8 -W ignore -m evaluation.answer_eval --split heldout2 --dataset data/eval/questions_heldout_v2.jsonl \
  --systems A,D --provider extractive --verifier none --tag _no_verifier

echo "== 7/7 Results"
python - <<'PY'
import glob, json
for path in sorted(glob.glob("reports/answers_*verifier*.json")):
    d = json.load(open(path, encoding="utf-8"))
    for name, s in d["systems"].items():
        r = s["refusal"]
        print(f"{path}: {name} acc={s['decision_accuracy']:.3f} false_answers={r['false_answers']} "
              f"false_refusals={r['false_refusals']} correctness={s['correctness_proxy']}")
PY
python -c "import shutil; shutil.make_archive('$OUT/citeagent_results', 'zip', 'reports')"
cp "$OUT/ollama.log" reports/ 2>/dev/null || true
echo "Download $OUT/citeagent_results.zip from the notebook's Output panel."
