#!/usr/bin/env bash
# Fine-tune the reranker on synthetic everyday-wording questions and measure it against the base reranker.
#
#   GEN_MODEL=qwen3:8b SOURCES_ZIP=/kaggle/input/citeagent-sources/citeagent_sources.zip \
#     bash kaggle/finetune_reranker.sh
#
# Needs: GPU T4 x2 (or P100/L4) and Internet. No API key unless GEN_BACKEND=openai (then OPENAI_API_KEY must be
# set, e.g. from Kaggle Secrets; gpt-4o-mini costs about 0.3 USD for the whole corpus).
#
# Options (environment):
#   GEN_BACKEND   ollama (default) | openai
#   GEN_MODEL     generator and checker model: qwen3:8b (default), qwen3:14b (better, ~2x slower), gpt-4o-mini
#   QUERIES_JSONL already generated questions (e.g. made on the laptop); skips generation
#   EPOCHS, LR    training (default 1 epoch, 1e-5)
#
# Protocol: held-out v3 is measured once per configuration at the end, never used to choose anything. Each
# reranker gets its thresholds from evaluation.tune_policy on dev v2 + paraphrase dev (same grid for both).
set -euo pipefail

GEN_BACKEND="${GEN_BACKEND:-ollama}"
GEN_MODEL="${GEN_MODEL:-qwen3:8b}"
EPOCHS="${EPOCHS:-1}"
LR="${LR:-1e-5}"
PULL=""
[ "$GEN_BACKEND" = "ollama" ] && PULL="$GEN_MODEL"
OLLAMA_NUM_PARALLEL=4 OLLAMA_MODELS="$PULL" source "$(dirname "${BASH_SOURCE[0]}")/setup.sh"
export LLM_VERIFIER=none   # measure the reranker alone
PY="python -X utf8 -W ignore"
V3="--dataset data/eval/questions_heldout_v3.jsonl --split heldout3"

measure() {  # $1 = tag; RERANKER_MODEL decides which reranker runs
  local tag="$1"
  $PY -m evaluation.tune_policy --tag "$tag"
  $PY -m evaluation.retrieval_eval --split all --tag "$tag"
  $PY -m evaluation.retrieval_eval $V3 --tag "$tag"
  for split in test heldout3; do
    local data=""
    [ "$split" = "heldout3" ] && data="$V3" || data="--split test"
    $PY -m evaluation.answer_eval $data --systems D --provider extractive --verifier none \
      --policy "reports/policy_tuning${tag}.json" --tag "${tag}"
  done
}

echo "== 1/6 Base reranker: tuning on dev + paraphrase dev, then test and held-out v3"
measure _rr_base
$PY -m evaluation.answer_eval $V3 --systems D --provider extractive --verifier none --tag _rr_base_defaults

echo "== 2/6 Synthetic questions ($GEN_BACKEND/$GEN_MODEL)"
mkdir -p data/training
if [ -n "${QUERIES_JSONL:-}" ] && [ -f "$QUERIES_JSONL" ]; then
  cp "$QUERIES_JSONL" data/training/queries.jsonl
fi
$PY -m training.generate_queries --backend "$GEN_BACKEND" --model "$GEN_MODEL" --workers 4

echo "== 3/6 Hard negatives (false-negative check with the same model)"
$PY -m training.mine_negatives --check-backend "$GEN_BACKEND" --check-model "$GEN_MODEL"

echo "== 4/6 Free the GPU and fine-tune"
if [ "$GEN_BACKEND" = "ollama" ]; then ollama stop "$GEN_MODEL" || true; pkill -f "ollama serve" || true; fi
$PY -m training.train_reranker --epochs "$EPOCHS" --lr "$LR" --out models/reranker-ft

echo "== 5/6 Fine-tuned reranker: same tuning and measurements"
export RERANKER_MODEL="$PWD/models/reranker-ft"
measure _rr_ft

echo "== 6/6 Summary and packaging"
$PY -m training.compare | tee reports/reranker_experiment.md
cp data/training/*_summary.json models/reranker-ft/training_meta.json reports/ 2>/dev/null || true
python - <<PY
import shutil
shutil.make_archive("$OUT/citeagent_reranker_results", "zip", ".", "reports")
shutil.make_archive("$OUT/citeagent_training_data", "zip", "data", "training")
shutil.make_archive("$OUT/citeagent_reranker_ft", "zip", "models", "reranker-ft")
PY
echo "Download from the Output panel: citeagent_reranker_results.zip (reports), citeagent_training_data.zip"
echo "(questions and groups) and citeagent_reranker_ft.zip (model, ~1.1 GB; unzip into models/ on the laptop)."
