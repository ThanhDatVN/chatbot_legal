#!/usr/bin/env bash
# Shared setup for the Kaggle runs: dependencies, models, sources, snapshot, indexes and (optionally) Ollama.
# Sourced by run_on_kaggle.sh and finetune_reranker.sh; sets ACTIVE_SNAPSHOT and leaves the shell in the repo.
#
#   OLLAMA_MODELS="qwen3:8b" SOURCES_ZIP=/kaggle/input/.../citeagent_sources.zip source kaggle/setup.sh
set -euo pipefail

SNAP="${ACTIVE_SNAPSHOT:-corpus-2026-10-01-r2}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT=/kaggle/working
cd "$REPO_DIR"

echo "== setup 1/5 Python dependencies (torch comes with the Kaggle image)"
pip install -q -r requirements/api.txt

export HF_OFFLINE=false MODEL_DEVICE=cuda LLM_PROVIDER=extractive PYTHONUTF8=1

echo "== setup 2/5 Models from Hugging Face (the tokenizer must be cached before chunking)"
python - <<'PY'
from huggingface_hub import snapshot_download
for repo in ("BAAI/bge-m3", "BAAI/bge-reranker-v2-m3"):
    snapshot_download(repo, allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt"])
print("models cached")
PY

echo "== setup 3/5 Official source PDFs (from the uploaded zip if given, else the government CDNs)"
if [ -n "${SOURCES_ZIP:-}" ] && [ -f "$SOURCES_ZIP" ]; then
  python -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall('.')" "$SOURCES_ZIP"
fi
python scripts/download_sources.py   # verifies every SHA-256 and fetches what is missing

echo "== setup 4/5 Snapshot $SNAP (must reproduce the published chunks_sha256) and indexes"
if ! python -m ingestion.build --snapshot-id "$SNAP"; then
  echo "The build did not reproduce $SNAP. Building ${SNAP}-kaggle instead; compare its quality_report.json."
  SNAP="${SNAP}-kaggle"
  python -m ingestion.build --snapshot-id "$SNAP" --overwrite
fi
export ACTIVE_SNAPSHOT="$SNAP"
python -m app.indexing

if [ -n "${OLLAMA_MODELS:-}" ]; then
  echo "== setup 5/5 Ollama with ${OLLAMA_MODELS}"
  if ! command -v ollama >/dev/null; then
    (command -v zstd >/dev/null || (apt-get update -qq && apt-get install -y -qq zstd)) || true
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  if ! curl -s localhost:11434/api/tags >/dev/null; then
    (OLLAMA_KEEP_ALIVE=60m OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}" nohup ollama serve > "$OUT/ollama.log" 2>&1 &)
    for _ in $(seq 1 60); do curl -s localhost:11434/api/tags >/dev/null && break; sleep 2; done
  fi
  for model in $OLLAMA_MODELS; do ollama pull "$model"; done
else
  echo "== setup 5/5 Ollama not needed"
fi
