"""Typed runtime configuration read from environment variables or .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    # corpus
    active_snapshot: str = "corpus-2026-10-01-r2"
    snapshots_dir: Path = ROOT / "data" / "snapshots"
    index_dir: Path = ROOT / "data" / "indexes"
    runtime_dir: Path = ROOT / "data" / "runtime"

    # which evidence may support an answer about current law
    currency_policy: Literal["strict", "pilot"] = "pilot"

    # vector store: QDRANT_URL for a server, otherwise an embedded store under index_dir
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None

    # models
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    model_device: Literal["auto", "cpu", "cuda"] = "auto"
    hf_offline: bool = True

    # retrieval
    dense_top_k: int = Field(20, ge=1, le=100)
    sparse_top_k: int = Field(20, ge=1, le=100)
    rrf_k: int = 60
    rerank_top_k: int = Field(5, ge=1, le=20)
    # cross-encoder cost control: candidates scored per search and their max length in tokens
    rerank_candidates: int = Field(20, ge=1, le=60)
    ineligible_rerank_candidates: int = Field(10, ge=0, le=30)
    reranker_max_length: int = Field(1024, ge=128, le=8192)

    # answering
    llm_provider: Literal["extractive", "ollama", "openai", "anthropic"] = "extractive"
    llm_model: str = "claude-opus-5-5"
    # Claude Opus 5.5 defaults to medium; grounded QA over short sources rarely needs more, and latency counts
    llm_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    llm_server_fallback: bool = True
    anthropic_api_key: str | None = None
    # OpenAI agent (LLM_PROVIDER=openai): same tools, prompt and validator as the Claude agent
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    # local Ollama agent (LLM_PROVIDER=ollama): no API cost; num_ctx must hold the prompt plus fetched sources
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    ollama_num_ctx: int = Field(12288, ge=2048, le=131072)
    ollama_think: bool = False
    ollama_timeout_s: float = 600.0
    # gray-zone verifier for the extractive agent (app/agent/verifier.py): none | ollama | openai
    llm_verifier: Literal["none", "ollama", "openai"] = "none"
    verifier_model: str | None = None  # defaults to OLLAMA_MODEL / OPENAI_MODEL
    verifier_num_ctx: int = Field(4096, ge=1024, le=32768)
    llm_timeout_s: float = 60.0
    max_search_calls: int = 3
    max_source_calls: int = 8
    # reranker-score floor under which evidence is treated as insufficient; tuned on the dev split
    # (reports/policy_tuning.json)
    refusal_threshold: float = 0.8
    log_questions: Literal["hash", "plain"] = "hash"

    @property
    def snapshot_dir(self) -> Path:
        return self.snapshots_dir / self.active_snapshot

    @property
    def collection(self) -> str:
        return "citeagent_" + self.active_snapshot.replace("-", "_")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
