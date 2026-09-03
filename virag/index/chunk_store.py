"""On-disk store for chunks and their parents.

Kept separate from the vector store so that BM25, dense retrieval and parent
expansion all read the same text, and so a re-embed never risks losing the
corpus.  JSONL because it is append-friendly, greppable and diffable.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from virag.schemas import Chunk, DocumentMeta, ParentChunk


class ChunkStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.chunks_path = root / "chunks.jsonl"
        self.parents_path = root / "parents.jsonl"
        self._chunks: dict[str, Chunk] = {}
        self._parents: dict[str, ParentChunk] = {}

    # -- write ------------------------------------------------------------
    def write(self, chunks: list[Chunk], parents: list[ParentChunk], append: bool = False) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with self.chunks_path.open(mode, encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(_chunk_to_dict(chunk), ensure_ascii=False) + "\n")
        with self.parents_path.open(mode, encoding="utf-8") as handle:
            for parent in parents:
                handle.write(json.dumps(_parent_to_dict(parent), ensure_ascii=False) + "\n")

    # -- read -------------------------------------------------------------
    def load(self) -> ChunkStore:
        self._chunks.clear()
        self._parents.clear()
        if self.chunks_path.exists():
            for line in self.chunks_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    chunk = _chunk_from_dict(json.loads(line))
                    self._chunks[chunk.chunk_id] = chunk
        if self.parents_path.exists():
            for line in self.parents_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    parent = _parent_from_dict(json.loads(line))
                    self._parents[parent.parent_id] = parent
        return self

    @property
    def chunks(self) -> dict[str, Chunk]:
        return self._chunks

    @property
    def parents(self) -> dict[str, ParentChunk]:
        return self._parents

    def get(self, chunk_id: str) -> Chunk | None:
        return self._chunks.get(chunk_id)

    def parent_of(self, chunk: Chunk) -> ParentChunk | None:
        return self._parents.get(chunk.parent_id)

    def bm25_items(self) -> list[tuple[str, str]]:
        """(chunk_id, indexable text) pairs.

        The citation label is indexed with the body so that a query naming
        "Dieu 9" or the instrument number matches lexically.
        """
        return [
            (chunk_id, f"{chunk.citation_label}\n{chunk.text}")
            for chunk_id, chunk in self._chunks.items()
        ]

    def __len__(self) -> int:
        return len(self._chunks)


def _chunk_to_dict(chunk: Chunk) -> dict:
    payload = asdict(chunk)
    payload["meta"] = asdict(chunk.meta) if chunk.meta else None
    return payload


def _chunk_from_dict(payload: dict) -> Chunk:
    meta_payload = payload.pop("meta", None)
    meta = DocumentMeta(**meta_payload) if meta_payload else None
    return Chunk(meta=meta, **payload)


def _parent_to_dict(parent: ParentChunk) -> dict:
    payload = asdict(parent)
    payload["meta"] = asdict(parent.meta) if parent.meta else None
    return payload


def _parent_from_dict(payload: dict) -> ParentChunk:
    meta_payload = payload.pop("meta", None)
    meta = DocumentMeta(**meta_payload) if meta_payload else None
    return ParentChunk(meta=meta, **payload)
