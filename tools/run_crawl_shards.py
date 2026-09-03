#!/usr/bin/env python3
"""Run deterministic crawl shards sequentially with auditable checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_terminal_summary(summary: dict[str, Any], expected_documents: int) -> bool:
    fetches = summary.get("page_fetches", {})
    processed = int(fetches.get("attempted", 0)) + int(fetches.get("skipped", 0))
    return int(summary.get("document_count", -1)) == expected_documents and processed == expected_documents


def summary_gap_count(summary: dict[str, Any]) -> int:
    fetches = summary.get("page_fetches", {})
    attachments = summary.get("attachments", {})
    return (
        int(fetches.get("failed", 0))
        + int(fetches.get("skipped", 0))
        + int(attachments.get("failed", 0))
    )


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def available_bytes(path: Path) -> int:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return shutil.disk_usage(candidate).free


def load_index(shards_dir: Path) -> dict[str, Any]:
    index_path = shards_dir / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for item in index["shards"]:
        shard_path = shards_dir / item["config_path"]
        actual = sha256_file(shard_path)
        if actual != item["sha256"]:
            raise ValueError(f"Shard hash mismatch: {shard_path}")
    return index


def run(args: argparse.Namespace) -> int:
    shards_dir = Path(args.shards_dir).resolve()
    output_root = Path(args.output_root).resolve()
    crawler = Path(args.crawler).resolve()
    index = load_index(shards_dir)
    start = args.start_shard or 1
    end = args.end_shard or int(index["shard_count"])
    if start < 1 or end < start or end > int(index["shard_count"]):
        raise ValueError(f"Invalid shard range {start}..{end}")

    state_path = output_root / "run-state.json"
    state: dict[str, Any] = {
        "schema_version": "1.0",
        "parent_pilot_id": index["parent_pilot_id"],
        "source_index": (shards_dir / "index.json").as_posix(),
        "source_index_sha256": sha256_file(shards_dir / "index.json"),
        "selected_range": {"start": start, "end": end},
        "updated_at": datetime.now(UTC).isoformat(),
        "shards": {},
    }
    if state_path.exists():
        previous = json.loads(state_path.read_text(encoding="utf-8"))
        if previous.get("source_index_sha256") != state["source_index_sha256"]:
            raise ValueError(f"Output root belongs to a different shard index: {output_root}")
        state["shards"] = previous.get("shards", {})

    records = {int(item["shard_number"]): item for item in index["shards"]}
    for number in range(start, end + 1):
        item = records[number]
        name = f"shard-{number:04d}"
        config_path = shards_dir / item["config_path"]
        output_dir = output_root / name
        summary_path = output_dir / "summary.json"

        minimum_free = int(args.min_free_gb * 1024**3)
        free = available_bytes(output_root)
        if free < minimum_free:
            state["stopped_reason"] = "minimum_free_space_guard"
            state["available_bytes"] = free
            state["required_free_bytes"] = minimum_free
            state["updated_at"] = datetime.now(UTC).isoformat()
            write_json_atomic(state_path, state)
            return 3

        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if not is_terminal_summary(summary, int(item["document_count"])):
                raise RuntimeError(f"Non-terminal summary must not be overwritten: {summary_path}")
            gaps = summary_gap_count(summary)
            state["shards"][name] = {
                "status": "completed" if gaps == 0 else "completed_with_gaps",
                "output": output_dir.as_posix(),
                "summary_sha256": sha256_file(summary_path),
                "gap_count": gaps,
                "skipped_existing": True,
            }
            state["updated_at"] = datetime.now(UTC).isoformat()
            write_json_atomic(state_path, state)
            if gaps and not args.continue_on_error:
                return 2
            continue

        if output_dir.exists() and any(output_dir.iterdir()):
            raise RuntimeError(
                f"Partial output preserved at {output_dir}; use a new output root or archive the attempt"
            )

        command = [
            sys.executable,
            str(crawler),
            "--config",
            str(config_path),
            "--output",
            str(output_dir),
        ]
        if args.download_official_pdfs:
            command.append("--download-official-pdfs")
        completed = subprocess.run(command, check=False)
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
        terminal = bool(summary) and is_terminal_summary(summary, int(item["document_count"]))
        gaps = summary_gap_count(summary) if summary else None
        if completed.returncode != 0 or not terminal:
            status = "failed"
        else:
            status = "completed" if gaps == 0 else "completed_with_gaps"
        state["shards"][name] = {
            "status": status,
            "output": output_dir.as_posix(),
            "returncode": completed.returncode,
            "summary_sha256": sha256_file(summary_path) if summary_path.exists() else None,
            "gap_count": gaps,
            "skipped_existing": False,
        }
        state["updated_at"] = datetime.now(UTC).isoformat()
        write_json_atomic(state_path, state)
        if status != "completed" and not args.continue_on_error:
            return completed.returncode or (2 if status == "completed_with_gaps" else 1)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--crawler", default="tools/legal_crawler.py")
    parser.add_argument("--start-shard", type=int)
    parser.add_argument("--end-shard", type=int)
    parser.add_argument("--download-official-pdfs", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--min-free-gb", type=float, default=10.0)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
