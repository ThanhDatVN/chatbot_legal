"""BM25 over Vietnamese syllables plus syllable bigrams.

Vietnamese words are often two syllables ("hợp đồng", "người lao động"); adding
adjacent-syllable bigrams lets BM25 reward the compound without a word segmenter.
The same tokenizer is used when the index is built and when it is queried.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

TOKENIZER_VERSION = "vi-syllable-bigram-v1"
STOPWORDS = {"và", "của", "các", "là", "có", "được", "cho", "trong", "theo", "với", "này", "những", "một", "thì",
             "để", "tại", "về", "từ", "khi", "hoặc", "bao", "nhiêu", "gì", "nào", "không", "sao", "thế"}


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    syllables = re.findall(r"[^\W_]+", text)
    tokens = [s for s in syllables if s not in STOPWORDS]
    bigrams = [f"{a}_{b}" for a, b in zip(syllables, syllables[1:])
               if not (a in STOPWORDS and b in STOPWORDS)]
    return tokens + bigrams


class SparseIndex:
    def __init__(self, ids: list[str], tokens: list[list[str]]) -> None:
        self.ids = ids
        self.position = {cid: i for i, cid in enumerate(ids)}
        self.bm25 = BM25Okapi(tokens)

    @classmethod
    def build(cls, ids: list[str], texts: list[str]) -> SparseIndex:
        return cls(ids, [tokenize(t) for t in texts])

    def save(self, path: Path, tokens: list[list[str]]) -> None:
        path.write_text(json.dumps({"tokenizer": TOKENIZER_VERSION, "ids": self.ids, "tokens": tokens},
                                   ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> SparseIndex:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["tokenizer"] != TOKENIZER_VERSION:
            raise ValueError(f"BM25 artifact built with {data['tokenizer']}, expected {TOKENIZER_VERSION}")
        return cls(data["ids"], data["tokens"])

    def search(self, query: str, allowed: list[str], top_k: int) -> list[tuple[str, float]]:
        q = tokenize(query)
        if not q or not allowed:
            return []
        scores = self.bm25.get_scores(q)
        idx = np.array([self.position[c] for c in allowed if c in self.position])
        if idx.size == 0:
            return []
        sub = scores[idx]
        order = np.argsort(-sub, kind="stable")[:top_k]
        return [(self.ids[idx[i]], float(sub[i])) for i in order if sub[i] > 0]
