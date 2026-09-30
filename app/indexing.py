"""Build the dense (Qdrant) and sparse (BM25) indexes for the active snapshot.

    python -m app.indexing

Embeddings are cached by sha256(embedding_text) per model, so re-indexing an
unchanged snapshot does not re-encode anything. The index manifest records the
snapshot hash; the API refuses to serve when they disagree.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from app.config import Settings, get_settings
from app.retrieval.models import BgeM3Encoder, Encoder
from app.retrieval.sparse import TOKENIZER_VERSION, SparseIndex, tokenize
from app.storage.corpus import CorpusCatalog
from app.storage.vector_store import VectorStore


def text_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cache(path: Path) -> dict[str, np.ndarray]:
    if not path.exists():
        return {}
    data = np.load(path)
    return {k: data[k] for k in data.files}


def vector_store(settings: Settings) -> VectorStore:
    return VectorStore(settings.collection, url=settings.qdrant_url, api_key=settings.qdrant_api_key,
                       path=settings.index_dir / "qdrant")


def build_index(settings: Settings, encoder: Encoder | None = None) -> dict:
    catalog = CorpusCatalog(settings.snapshot_dir, settings.currency_policy)
    out = settings.index_dir / catalog.snapshot_id
    out.mkdir(parents=True, exist_ok=True)
    ids = catalog.order
    texts = [catalog.chunks[c].embedding_text for c in ids]

    encoder = encoder or BgeM3Encoder(settings.embedding_model, settings.model_device, settings.hf_offline)
    cache_path = settings.index_dir / "embedding_cache" / (settings.embedding_model.replace("/", "__") + ".npz")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = load_cache(cache_path)
    keys = [text_key(t) for t in texts]
    missing = [i for i, k in enumerate(keys) if k not in cache]
    started = time.perf_counter()
    if missing:
        vectors = encoder.encode([texts[i] for i in missing])
        for i, v in zip(missing, vectors):
            cache[keys[i]] = v
        np.savez(cache_path, **cache)
    encode_s = time.perf_counter() - started
    matrix = np.stack([cache[k] for k in keys]).astype(np.float32)

    store = vector_store(settings)
    store.recreate(encoder.dim)
    payloads = [{"chunk_id": c, "document_id": catalog.chunks[c].document_id,
                 "currency_status": catalog.chunks[c].currency_status.value,
                 "section_kind": catalog.chunks[c].section_kind.value} for c in ids]
    store.upsert(ids, matrix, payloads)

    tokens = [tokenize(t) for t in texts]
    SparseIndex(ids, tokens).save(out / "bm25.json", tokens)
    manifest = {"snapshot_id": catalog.snapshot_id, "chunks_sha256": catalog.manifest["chunks_sha256"],
                "collection": settings.collection, "embedding_model": settings.embedding_model,
                "dim": encoder.dim, "vectors": store.count(), "bm25_tokenizer": TOKENIZER_VERSION,
                "encoded_now": len(missing), "encode_seconds": round(encode_s, 1)}
    (out / "index_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def main() -> None:
    print(json.dumps(build_index(get_settings()), indent=1))


if __name__ == "__main__":
    main()
