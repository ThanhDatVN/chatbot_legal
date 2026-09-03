"""Central configuration for ViRAG-Gov.

Every knob that the ablation study varies lives here so that a run configuration
is a single serialisable object.  Values come from environment variables with a
``VIRAG_`` prefix; ``.env`` is read when present.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(REPO_ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.environ.get(f"VIRAG_{name}", default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


RetrieverMode = Literal["bm25", "dense", "hybrid"]


@dataclass(frozen=True)
class RankingWeights:
    """Weights of the composite legal relevance score.

    Pure semantic similarity ranks a Cong van above the Luat it interprets when
    the wording happens to match better.  That is wrong in law, so authority,
    temporal validity and specificity enter the score directly.
    """

    semantic: float = 0.55
    authority: float = 0.15
    temporal: float = 0.20
    specificity: float = 0.07
    citation_quality: float = 0.03

    def normalised(self) -> RankingWeights:
        total = (
            self.semantic
            + self.authority
            + self.temporal
            + self.specificity
            + self.citation_quality
        )
        if total <= 0:
            return RankingWeights()
        return RankingWeights(
            semantic=self.semantic / total,
            authority=self.authority / total,
            temporal=self.temporal / total,
            specificity=self.specificity / total,
            citation_quality=self.citation_quality / total,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalConfig:
    """One point in the ablation grid.

    ``name`` identifies the configuration in benchmark tables.
    """

    name: str = "full"
    mode: RetrieverMode = "hybrid"
    top_k_sparse: int = 30
    top_k_dense: int = 30
    top_k_fused: int = 20
    top_k_final: int = 6
    rrf_k: int = 60
    dense_weight: float = 0.5
    use_reranker: bool = True
    use_parent_expansion: bool = True
    #: Hard pre-filter on validity interval; the single biggest guard against
    #: temporal misgrounding.
    use_temporal_filter: bool = True
    #: Apply the composite legal score on top of the relevance score.
    use_legal_ranking: bool = True
    min_rerank_score: float = -8.0
    weights: RankingWeights = field(default_factory=RankingWeights)

    def to_dict(self) -> dict:
        return asdict(self)

    def with_(self, **kwargs) -> RetrievalConfig:
        return replace(self, **kwargs)


@dataclass(frozen=True)
class Settings:
    # --- storage ---------------------------------------------------------
    qdrant_url: str = field(default_factory=lambda: _env("QDRANT_URL", "http://localhost:6333"))
    qdrant_collection: str = field(default_factory=lambda: _env("QDRANT_COLLECTION", "virag_chunks"))
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))

    # --- filesystem ------------------------------------------------------
    repo_root: Path = REPO_ROOT
    crawl_root: Path = field(default_factory=lambda: REPO_ROOT / _env("CRAWL_ROOT", "data/crawl"))
    processed_root: Path = field(
        default_factory=lambda: REPO_ROOT / _env("PROCESSED_ROOT", "data/processed")
    )
    index_root: Path = field(default_factory=lambda: REPO_ROOT / _env("INDEX_ROOT", "data/index"))
    reports_root: Path = field(default_factory=lambda: REPO_ROOT / _env("REPORTS_ROOT", "reports"))
    eval_root: Path = field(default_factory=lambda: REPO_ROOT / _env("EVAL_ROOT", "eval"))

    # --- models ----------------------------------------------------------
    embedding_model: str = field(default_factory=lambda: _env("EMBEDDING_MODEL", "BAAI/bge-m3"))
    embedding_dim: int = field(default_factory=lambda: _env_int("EMBEDDING_DIM", 1024))
    reranker_model: str = field(
        default_factory=lambda: _env("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    )
    # "auto" uses the real transformer when torch is importable, otherwise the
    # deterministic hashing encoder so that CI and offline demos still run.
    embedding_backend: str = field(default_factory=lambda: _env("EMBEDDING_BACKEND", "auto"))
    reranker_backend: str = field(default_factory=lambda: _env("RERANKER_BACKEND", "auto"))

    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "claude-opus-5"))
    llm_judge_model: str = field(default_factory=lambda: _env("LLM_JUDGE_MODEL", "claude-opus-5"))
    llm_effort: str = field(default_factory=lambda: _env("LLM_EFFORT", "medium"))
    llm_max_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS", 4096))
    llm_backend: str = field(default_factory=lambda: _env("LLM_BACKEND", "auto"))

    # --- chunking --------------------------------------------------------
    child_target_tokens: int = field(default_factory=lambda: _env_int("CHILD_TARGET_TOKENS", 220))
    child_overlap_tokens: int = field(default_factory=lambda: _env_int("CHILD_OVERLAP_TOKENS", 40))
    parent_max_tokens: int = field(default_factory=lambda: _env_int("PARENT_MAX_TOKENS", 1600))

    # --- ocr -------------------------------------------------------------
    ocr_enabled: bool = field(default_factory=lambda: _env_bool("OCR_ENABLED", True))
    ocr_language: str = field(default_factory=lambda: _env("OCR_LANGUAGE", "vie"))
    ocr_min_chars_per_page: int = field(default_factory=lambda: _env_int("OCR_MIN_CHARS_PER_PAGE", 180))
    ocr_dpi: int = field(default_factory=lambda: _env_int("OCR_DPI", 300))

    # --- cache -----------------------------------------------------------
    cache_enabled: bool = field(default_factory=lambda: _env_bool("CACHE_ENABLED", True))
    cache_ttl_seconds: int = field(default_factory=lambda: _env_int("CACHE_TTL_SECONDS", 86400))
    cache_similarity_threshold: float = field(
        default_factory=lambda: _env_float("CACHE_SIMILARITY_THRESHOLD", 0.94)
    )
    cache_max_entries: int = field(default_factory=lambda: _env_int("CACHE_MAX_ENTRIES", 5000))

    # --- temporal reasoning ----------------------------------------------
    #: Date used when the user gives no event date.  "today" resolves at call
    #: time; a fixed ISO date makes evaluation runs reproducible.
    default_as_of: str = field(default_factory=lambda: _env("DEFAULT_AS_OF", "today"))
    #: Ask the user for the taxable-event date instead of silently assuming
    #: "today" when the question is temporally sensitive.
    temporal_clarification: bool = field(
        default_factory=lambda: _env_bool("TEMPORAL_CLARIFICATION", True)
    )

    # --- guardrails ------------------------------------------------------
    min_citation_coverage: float = field(default_factory=lambda: _env_float("MIN_CITATION_COVERAGE", 0.6))
    min_grounding_score: float = field(default_factory=lambda: _env_float("MIN_GROUNDING_SCORE", 0.45))
    refuse_when_unsupported: bool = field(
        default_factory=lambda: _env_bool("REFUSE_WHEN_UNSUPPORTED", True)
    )
    injection_block_threshold: float = field(
        default_factory=lambda: _env_float("INJECTION_BLOCK_THRESHOLD", 0.5)
    )
    #: Refuse to mix two versions of the same article in one answer.
    block_version_mixing: bool = field(default_factory=lambda: _env_bool("BLOCK_VERSION_MIXING", True))

    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)

    def ensure_dirs(self) -> None:
        for path in (self.processed_root, self.index_root, self.reports_root):
            path.mkdir(parents=True, exist_ok=True)


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS


# ---------------------------------------------------------------------------
# Ablation grid - referenced by docs/BENCHMARK.md and virag/eval/ablation.py.
#
# The grid is cumulative: each configuration adds exactly one component to the
# previous one, so the delta between two rows attributes the gain to that
# component alone.
# ---------------------------------------------------------------------------
ABLATION_CONFIGS: tuple[RetrievalConfig, ...] = (
    RetrievalConfig(
        name="A-bm25-baseline",
        mode="bm25",
        use_reranker=False,
        use_parent_expansion=False,
        use_temporal_filter=False,
        use_legal_ranking=False,
    ),
    RetrievalConfig(
        name="B-dense-only",
        mode="dense",
        use_reranker=False,
        use_parent_expansion=False,
        use_temporal_filter=False,
        use_legal_ranking=False,
    ),
    RetrievalConfig(
        name="C-hybrid",
        mode="hybrid",
        use_reranker=False,
        use_parent_expansion=False,
        use_temporal_filter=False,
        use_legal_ranking=False,
    ),
    RetrievalConfig(
        name="D-hybrid-rerank-parent",
        mode="hybrid",
        use_reranker=True,
        use_parent_expansion=True,
        use_temporal_filter=False,
        use_legal_ranking=False,
    ),
    RetrievalConfig(
        name="E-full-temporal-legal",
        mode="hybrid",
        use_reranker=True,
        use_parent_expansion=True,
        use_temporal_filter=True,
        use_legal_ranking=True,
    ),
)
