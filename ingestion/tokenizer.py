"""Token counting with the embedding model's own tokenizer."""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path

DEFAULT_MODEL = "BAAI/bge-m3"


def _tokenizer_file(model: str) -> Path | None:
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:  # pragma: no cover - huggingface_hub ships with transformers
        return None
    found = try_to_load_from_cache(model, "tokenizer.json")
    return Path(found) if isinstance(found, str) and os.path.exists(found) else None


@lru_cache(maxsize=4)
def _load(model: str):
    path = _tokenizer_file(model)
    if path is None:
        return None
    from tokenizers import Tokenizer

    return Tokenizer.from_file(str(path))


class TokenCounter:
    """Counts model tokens; falls back to a conservative estimate when the tokenizer is not cached."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model
        self._tok = _load(model)
        self.exact = self._tok is not None

    def count(self, text: str) -> int:
        if self._tok is not None:
            return len(self._tok.encode(text).ids)  # includes <s> and </s>
        return math.ceil(len(text.split()) * 1.45) + 2

    @property
    def name(self) -> str:
        return f"{self.model}:{'tokenizer' if self.exact else 'estimate'}"
