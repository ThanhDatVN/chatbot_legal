#!/usr/bin/env python3
"""Split a large crawl allowlist into deterministic, independently resumable shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def shard_config(config: dict[str, Any], shard_size: int) -> list[dict[str, Any]]:
    if shard_size <= 0:
        raise ValueError("shard_size must be positive")
    documents = config["documents"]
    shards: list[dict[str, Any]] = []
    for start in range(0, len(documents), shard_size):
        shard_number = len(shards) + 1
        shard = dict(config)
        shard["pilot_id"] = f"{config['pilot_id']}-shard-{shard_number:04d}"
        shard["parent_pilot_id"] = config["pilot_id"]
        shard["shard_number"] = shard_number
        shard["shard_start_index"] = start
        shard["documents"] = documents[start : start + shard_size]
        shards.append(shard)
    return shards


def run(args: argparse.Namespace) -> int:
    source_path = Path(args.config)
    source_bytes = source_path.read_bytes()
    config = json.loads(source_bytes.decode("utf-8"))
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    shards = shard_config(config, args.shard_size)
    records: list[dict[str, Any]] = []
    for shard in shards:
        name = f"shard-{shard['shard_number']:04d}.json"
        encoded = (json.dumps(shard, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (output / name).write_bytes(encoded)
        records.append(
            {
                "shard_number": shard["shard_number"],
                "config_path": name,
                "document_count": len(shard["documents"]),
                "first_document_id": shard["documents"][0]["id"],
                "last_document_id": shard["documents"][-1]["id"],
                "sha256": sha256_bytes(encoded),
                "run_status": "pending",
            }
        )
    index = {
        "schema_version": "1.0",
        "source_config": source_path.as_posix(),
        "source_config_sha256": sha256_bytes(source_bytes),
        "parent_pilot_id": config["pilot_id"],
        "document_count": len(config["documents"]),
        "shard_size": args.shard_size,
        "shard_count": len(shards),
        "shards": records,
    }
    (output / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.as_posix(),
                "documents": len(config["documents"]),
                "shards": len(shards),
            }
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--shard-size", type=int, default=100)
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
