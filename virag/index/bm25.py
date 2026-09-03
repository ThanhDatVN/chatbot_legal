"""BM25 over Vietnamese legal text.

Written in-repo rather than pulled from a library for two reasons specific to
this corpus:

*   **Tokenisation.**  Vietnamese words are multi-syllable but written with
    spaces, so unigrams alone lose "gia tri gia tang".  Syllable bigrams are
    indexed alongside unigrams to recover the compounds.
*   **Legal literals.**  "48/2024/QH15", "10%" and "Dieu 9" must survive
    tokenisation intact; a generic word splitter shreds all three, and they are
    the highest-precision query terms a user can give.

The index persists as a single JSON file so it rebuilds deterministically and
can be diffed.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Order matters: instrument numbers first, then percentages, then Dieu/Khoan
# pointers, then ordinary syllables.
_INSTRUMENT = re.compile(r"\d{1,4}/(?:19|20)\d{2}/[A-Za-zĐđ][A-Za-zĐđ0-9\-]{1,15}")
_PERCENT = re.compile(r"\d{1,3}(?:[.,]\d+)?\s*%")
_POINTER = re.compile(r"(?:điều|khoản|điểm)\s+\d{1,3}[a-zđ]?", re.IGNORECASE)
_WORD = re.compile(r"[0-9a-zà-ỹ]+", re.IGNORECASE)

_STOPWORDS = frozenset(
    {
        "của", "và", "các", "được", "theo", "trong", "cho", "với", "này", "đối",
        "tại", "hoặc", "thì", "khi", "là", "có", "không", "một", "những", "từ",
        "đến", "về", "như", "sau", "trên", "đã", "sẽ", "cũng", "nếu", "mà",
        "bị", "do", "vào", "ra", "nên", "rằng", "để",
    }
)


def tokenize(text: str, *, bigrams: bool = True) -> list[str]:
    """Tokenise Vietnamese legal text, preserving legal literals."""
    lowered = text.lower()
    tokens: list[str] = []

    reserved: list[tuple[int, int]] = []
    for pattern, prefix in ((_INSTRUMENT, "vb:"), (_PERCENT, "pct:"), (_POINTER, "ref:")):
        for match in pattern.finditer(lowered):
            literal = re.sub(r"\s+", "", match.group(0))
            tokens.append(f"{prefix}{literal}")
            reserved.append(match.span())

    def is_reserved(span: tuple[int, int]) -> bool:
        return any(start <= span[0] and span[1] <= end for start, end in reserved)

    words = [m.group(0) for m in _WORD.finditer(lowered) if not is_reserved(m.span())]
    content = [w for w in words if w not in _STOPWORDS and len(w) > 1]
    tokens.extend(content)

    if bigrams:
        # Bigrams are built over the *unfiltered* sequence so that a stopword
        # inside a compound does not silently join unrelated syllables.
        tokens.extend(f"{a}_{b}" for a, b in zip(words, words[1:], strict=False) if a not in _STOPWORDS)

    return tokens


@dataclass
class BM25Index:
    """Okapi BM25 with the standard ``k1`` / ``b`` parameters."""

    k1: float = 1.5
    b: float = 0.75
    doc_ids: list[str] = field(default_factory=list)
    doc_lengths: list[int] = field(default_factory=list)
    #: term -> {document position -> term frequency}
    postings: dict[str, dict[int, int]] = field(default_factory=lambda: defaultdict(dict))
    avg_doc_length: float = 0.0

    # -- build ------------------------------------------------------------
    def add(self, doc_id: str, text: str) -> None:
        position = len(self.doc_ids)
        tokens = tokenize(text)
        self.doc_ids.append(doc_id)
        self.doc_lengths.append(len(tokens))
        for term, freq in Counter(tokens).items():
            self.postings[term][position] = freq

    def finalise(self) -> BM25Index:
        total = sum(self.doc_lengths)
        self.avg_doc_length = total / len(self.doc_lengths) if self.doc_lengths else 0.0
        return self

    @classmethod
    def build(cls, items: list[tuple[str, str]]) -> BM25Index:
        index = cls()
        for doc_id, text in items:
            index.add(doc_id, text)
        return index.finalise()

    # -- query ------------------------------------------------------------
    def _idf(self, term: str) -> float:
        n_docs = len(self.doc_ids)
        df = len(self.postings.get(term, ()))
        if df == 0:
            return 0.0
        # Robertson/Sparck-Jones idf with the +1 smoothing that keeps it positive.
        return math.log(1 + (n_docs - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 30) -> list[tuple[str, float]]:
        if not self.doc_ids:
            return []

        scores: dict[int, float] = defaultdict(float)
        for term in set(tokenize(query)):
            postings = self.postings.get(term)
            if not postings:
                continue
            idf = self._idf(term)
            if idf <= 0:
                continue
            for position, freq in postings.items():
                length = self.doc_lengths[position] or 1
                denominator = freq + self.k1 * (
                    1 - self.b + self.b * length / (self.avg_doc_length or 1)
                )
                scores[position] += idf * (freq * (self.k1 + 1)) / denominator

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [(self.doc_ids[position], score) for position, score in ranked]

    # -- persistence ------------------------------------------------------
    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "k1": self.k1,
            "b": self.b,
            "doc_ids": self.doc_ids,
            "doc_lengths": self.doc_lengths,
            "avg_doc_length": self.avg_doc_length,
            # JSON object keys must be strings.
            "postings": {
                term: {str(pos): freq for pos, freq in posting.items()}
                for term, posting in self.postings.items()
            },
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> BM25Index:
        payload = json.loads(path.read_text(encoding="utf-8"))
        index = cls(k1=payload["k1"], b=payload["b"])
        index.doc_ids = payload["doc_ids"]
        index.doc_lengths = payload["doc_lengths"]
        index.avg_doc_length = payload["avg_doc_length"]
        index.postings = defaultdict(
            dict,
            {
                term: {int(pos): freq for pos, freq in posting.items()}
                for term, posting in payload["postings"].items()
            },
        )
        return index

    def __len__(self) -> int:
        return len(self.doc_ids)
