"""Shared helpers for the reranker fine-tuning pipeline: corpus access, article keys, cross-references,
decontamination against every evaluation set, and the train/validation split by article."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from app.storage.corpus import CorpusCatalog
from ingestion.models import Chunk

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "training"
MODELS = ROOT / "models"
EVAL_DIR = ROOT / "data" / "eval"
LABOUR_CODE = "18_2026_vbhn_vpqh"

# Articles nobody asks about in everyday words; they stay available as negatives.
SKIP_TITLE_RE = re.compile(r"^(Phạm vi điều chỉnh|Đối tượng áp dụng|Hiệu lực thi hành|Trách nhiệm thi hành|"
                           r"Điều khoản thi hành|Hiệu lực và trách nhiệm thi hành|Trách nhiệm hướng dẫn thi hành|"
                           r"Sửa đổi, bổ sung một số điều của các luật)", re.IGNORECASE)
REF_RE = re.compile(r"Điều (\d+)(?: của)? (Bộ luật Lao động|Bộ luật này|Nghị định này|Nghị định số (\d+/\d{4}/NĐ-CP))")


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def article_key(chunk: Chunk) -> tuple[str, str]:
    return chunk.document_id, chunk.section_label


def is_validation(key: tuple[str, str], fraction: int = 10) -> bool:
    """About 1/fraction of the articles hold the synthetic validation questions (never the evaluation sets)."""
    return int(hashlib.sha256("|".join(key).encode()).hexdigest(), 16) % fraction == 0


def references(chunk: Chunk, number_to_doc: dict[str, str]) -> set[tuple[str, str]]:
    """Articles this chunk cites, resolved to (document_id, "Điều n")."""
    out = set()
    for n, target, number in REF_RE.findall(chunk.text):
        if target == "Bộ luật Lao động" or (target == "Bộ luật này" and chunk.document_id == LABOUR_CODE):
            out.add((LABOUR_CODE, f"Điều {n}"))
        elif target == "Nghị định này":
            out.add((chunk.document_id, f"Điều {n}"))
        elif number in number_to_doc:
            out.add((number_to_doc[number], f"Điều {n}"))
    return out


class Corpus:
    def __init__(self, catalog: CorpusCatalog) -> None:
        self.catalog = catalog
        number_to_doc = {d.document_number: d.document_id for d in catalog.documents.values()}
        self.refs = {cid: references(c, number_to_doc) for cid, c in catalog.chunks.items()}

    def related(self, a: Chunk, b: Chunk) -> bool:
        """Same article (another part of it) or one cites the other: never use b as a negative for a."""
        ka, kb = article_key(a), article_key(b)
        return ka == kb or kb in self.refs[a.chunk_id] or ka in self.refs[b.chunk_id]

    def generation_chunks(self, subset: str = "in_scope") -> list[Chunk]:
        chunks = [self.catalog.chunks[cid] for cid in self.catalog.ids(subset)]
        return [c for c in chunks if not SKIP_TITLE_RE.match(c.section_title or "")]


def evaluation_questions() -> list[str]:
    """Every question of every evaluation set, read only to drop near-duplicates from the training data."""
    out = []
    for path in sorted(EVAL_DIR.glob("questions_*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            out.extend(json.loads(line)["question"] for line in fh if line.strip())
    return out


def char_ngrams(text: str, n: int = 4) -> set[str]:
    t = normalize(text)
    return {t[i:i + n] for i in range(max(1, len(t) - n + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
