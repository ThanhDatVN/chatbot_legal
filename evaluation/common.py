"""Shared helpers for evaluation runs: dataset loading, run metadata, percentiles."""

from __future__ import annotations

import json
import math
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "eval" / "questions_v2.jsonl"
REPORTS = ROOT / "reports"


def load_dataset(split: str | None = None, path: Path = DATASET) -> list[dict]:
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    return [r for r in rows if split in (None, "all") or r["split"] == split]


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo), 1)


def git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.strip()
        # evaluation runs write reports/ and docs are edited alongside; neither changes what is measured
        dirty = subprocess.run(["git", "status", "--porcelain", "--", ".", ":(exclude)reports", ":(exclude)docs",
                                ":(exclude)*.md"], cwd=ROOT, capture_output=True, text=True).stdout
        return sha + ("-dirty" if dirty.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def hardware() -> dict:
    info = {"platform": platform.platform(), "python": platform.python_version(), "processor": platform.processor()}
    try:
        import torch

        info["torch"] = torch.__version__
        info["cuda_device"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except ImportError:
        pass
    return info


def run_metadata(settings, dataset_path: Path = DATASET, **extra) -> dict:
    return {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": git_commit(),
            "snapshot": settings.active_snapshot, "currency_policy": settings.currency_policy,
            "embedding_model": settings.embedding_model, "reranker_model": settings.reranker_model,
            "dense_top_k": settings.dense_top_k, "sparse_top_k": settings.sparse_top_k, "rrf_k": settings.rrf_k,
            "dataset": dataset_path.name, "hardware": hardware(), **extra}


def section_key(item) -> tuple[str, str]:
    chunk = getattr(item, "chunk", item)
    return chunk.document_id, chunk.section_label


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
