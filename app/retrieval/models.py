"""Dense encoder (bge-m3 CLS embeddings) and cross-encoder reranker behind small interfaces.

Models load lazily, run in fp16 on CUDA when available and fp32 on CPU, and read
weights only from the local Hugging Face cache when HF offline mode is set.
"""

from __future__ import annotations

import os
import threading
from typing import Protocol

import numpy as np

from app.errors import EmbeddingFailure


class Encoder(Protocol):
    model_name: str
    dim: int

    def encode(self, texts: list[str], batch_size: int = 16, max_length: int = 1024) -> np.ndarray: ...


class Reranker(Protocol):
    model_name: str

    def score(self, query: str, passages: list[str], batch_size: int = 16) -> list[float]: ...


def _device(preference: str):
    import torch

    if preference == "cuda" or (preference == "auto" and torch.cuda.is_available()):
        return torch.device("cuda"), torch.float16
    torch.set_num_threads(int(os.environ.get("TORCH_NUM_THREADS", os.cpu_count() or 1)))
    return torch.device("cpu"), torch.float32


class _Lazy:
    def __init__(self, model_name: str, device: str, offline: bool) -> None:
        self.model_name = model_name
        self._pref = device
        self._offline = offline
        self._lock = threading.Lock()
        self._loaded = None

    def _load(self, loader):
        with self._lock:
            if self._loaded is None:
                if self._offline:
                    os.environ["HF_HUB_OFFLINE"] = "1"
                self._loaded = loader()
        return self._loaded


class BgeM3Encoder(_Lazy):
    dim = 1024

    def _build(self):
        import torch
        from transformers import AutoModel, AutoTokenizer

        device, dtype = _device(self._pref)
        tok = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name, dtype=dtype).to(device).eval()
        return tok, model, device, torch

    def encode(self, texts: list[str], batch_size: int = 16, max_length: int = 1024) -> np.ndarray:
        try:
            tok, model, device, torch = self._load(self._build)
            out = []
            with torch.inference_mode():
                for i in range(0, len(texts), batch_size):
                    batch = tok(texts[i:i + batch_size], padding=True, truncation=True, max_length=max_length,
                                return_tensors="pt").to(device)
                    cls = model(**batch).last_hidden_state[:, 0].float()
                    out.append(torch.nn.functional.normalize(cls, dim=-1).cpu().numpy())
            return np.concatenate(out, axis=0).astype(np.float32) if out else np.zeros((0, self.dim), np.float32)
        except Exception as exc:  # noqa: BLE001 - surfaced as a typed dependency error
            raise EmbeddingFailure() from exc


class BgeReranker(_Lazy):
    def __init__(self, model_name: str, device: str, offline: bool, max_length: int = 1024) -> None:
        super().__init__(model_name, device, offline)
        self.max_length = max_length

    def _build(self):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        device, dtype = _device(self._pref)
        tok = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_name, dtype=dtype).to(device).eval()
        return tok, model, device, torch

    def score(self, query: str, passages: list[str], batch_size: int = 16) -> list[float]:
        """Relevance in [0, 1] (sigmoid of the cross-encoder logit); higher is more relevant."""
        if not passages:
            return []
        tok, model, device, torch = self._load(self._build)
        scores: list[float] = []
        with torch.inference_mode():
            for i in range(0, len(passages), batch_size):
                pairs = [[query, p] for p in passages[i:i + batch_size]]
                batch = tok(pairs, padding=True, truncation=True, max_length=self.max_length,
                            return_tensors="pt").to(device)
                logits = model(**batch).logits.float().view(-1)
                scores.extend(torch.sigmoid(logits).cpu().tolist())
        return scores
