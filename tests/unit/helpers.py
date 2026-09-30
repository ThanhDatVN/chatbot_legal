"""Small builders for unit tests that need corpus objects without a built snapshot."""

from __future__ import annotations

import json
import zlib
from pathlib import Path

import numpy as np

from ingestion.models import Chunk


def make_chunk(chunk_id: str, text: str = "Điều 113. Nghỉ hằng năm\n1. Người lao động được nghỉ 12 ngày làm việc.",
               document_id: str = "18_2026_vbhn_vpqh", section: str = "Điều 113", article: int | None = 113,
               currency_status: str = "consolidated_current", quality: str = "machine_checked",
               kind: str = "main_text") -> Chunk:
    return Chunk(chunk_id=chunk_id, corpus_snapshot_id="test", document_id=document_id,
                 document_number="18/VBHN-VPQH", document_title="Bộ luật Lao động", short_title="BLLĐ hợp nhất",
                 document_type="Văn bản hợp nhất", issuer="Văn phòng Quốc hội", section_id=f"{document_id}:{section}",
                 section_kind=kind, section_label=section, section_title="Nghỉ hằng năm",
                 section_path=[f"{section}. Nghỉ hằng năm"], article_number=article, ordinal=0, part_count=1,
                 page_start=44, page_end=44, source_start_char=0, source_end_char=len(text), raw_text=text,
                 text=text, context_header=f"BLLĐ › {section}", embedding_text=f"BLLĐ › {section}\n{text}",
                 token_count=30, embedding_token_count=35, source_url="https://congbao.chinhphu.vn/van-ban/x.htm",
                 source_sha256=["0" * 64], content_sha256="1" * 64, contains_quoted_amendment=False,
                 contains_table=False, currency_status=currency_status, currency_basis="test basis",
                 text_quality_status=quality)


def write_snapshot(root: Path, chunks: list[Chunk], snapshot_id: str = "test") -> Path:
    out = root / snapshot_id
    out.mkdir(parents=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(c.model_dump_json() + "\n")
    docs = {c.document_id for c in chunks}
    with (out / "documents.jsonl").open("w", encoding="utf-8") as fh:
        for d in sorted(docs):
            fh.write(json.dumps({
                "document_id": d, "document_number": "18/VBHN-VPQH", "title": "Bộ luật Lao động",
                "short_title": "BLLĐ hợp nhất", "document_type": "Văn bản hợp nhất", "issuer": "VPQH",
                "issued_date": "2026-02-12", "effective_date": None, "source_url": "https://congbao.chinhphu.vn/x",
                "publisher": "Công báo", "license": "publicly_accessible_unknown_license",
                "scope": "boundary" if d.startswith("12_") else "in_scope", "corpus_use": "current",
                "corpus_use_reason": "r", "downloaded_at": "2026-09-25", "chunks": 1, "main_articles": 1},
                ensure_ascii=False) + "\n")
    (out / "snapshot.json").write_text(json.dumps({"snapshot_id": snapshot_id, "as_of_date": "2026-09-30",
                                                   "chunks_sha256": "x", "quality_passed": True}), encoding="utf-8")
    return out


class HashEncoder:
    """Deterministic bag-of-syllables encoder: similar wording gives similar vectors."""

    model_name = "hash"
    dim = 64

    def encode(self, texts, batch_size=16, max_length=1024):
        out = np.zeros((len(texts), self.dim), np.float32)
        for i, t in enumerate(texts):
            for tok in t.lower().split():
                out[i, zlib.crc32(tok.encode("utf-8")) % self.dim] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(norms, 1e-9)


class OverlapReranker:
    model_name = "overlap"

    def score(self, query, passages, batch_size=16):
        q = set(query.lower().split())
        return [min(1.0, len(q & set(p.lower().split())) / max(3, len(q)) * 1.2) for p in passages]
