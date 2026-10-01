"""Evidence sufficiency and scope rules that do not depend on the LLM.

Thresholds are on the cross-encoder relevance (0–1) and are tuned on the
development split of the evaluation set (see evaluation/tune_policy.py); the
values here are the tuned defaults recorded in reports/policy_tuning.json.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.schemas import RefusalReason, ScoredChunk
from ingestion.models import CurrencyStatus


@dataclass(frozen=True)
class PolicyConfig:
    answer_threshold: float = 0.8  # eligible evidence must reach this to support an answer
    keep_ratio: float = 0.85  # other sources are used if within this ratio of the best score
    stronger_margin: float = 0.15  # unverified evidence this much stronger turns an answer into PARTIAL
    unverified_threshold: float = 0.5  # unverified evidence this strong explains a refusal
    max_sources: int = 3
    # A provision that expired or is displaced, and whose replacement is not in the corpus, outranking the best
    # eligible evidence by this margin means the eligible evidence only neighbours the question: refuse.
    # None disables the rule; 0.0 was chosen on the dev split of dataset v2 (reports/policy_tuning.json).
    superseded_margin: float | None = 0.0


# Requests that ask the system to foresee or recommend rather than to state the law.
PREDICTION_RE = re.compile(r"\b(dự đoán|dự báo|sẽ tăng|sẽ giảm|sẽ thay đổi|sắp tới có|trong tương lai|khả năng cao sẽ)\b")
# Clearly outside labour relations; retrieval scores catch the rest.
OUT_OF_SCOPE_RE = re.compile(
    r"\b(thuế thu nhập|thuế giá trị gia tăng|thuế tncn|vat|chứng khoán|bitcoin|tiền điện tử|bất động sản|ly hôn|"
    r"thừa kế|giao thông|bóng đá|thời tiết|nấu ăn|công thức|lập trình|python|viết code|bài thơ|visa du lịch)\b")
HISTORICAL_RE = re.compile(r"\b(trước đây|trước khi (được )?sửa đổi|quy định cũ|luật cũ|bộ luật lao động (năm )?2012|"
                           r"bộ luật lao động cũ|đã hết hiệu lực)\b")
# Wage levels change by decree; a past year means an older decree, which the MVP does not answer from.
PAST_WAGE_RE = re.compile(r"lương tối thiểu.*\b(năm|giai đoạn)\s+(19\d\d|20[01]\d|202[0-5])\b|"
                          r"\b(năm|giai đoạn)\s+(19\d\d|20[01]\d|202[0-5])\b.*lương tối thiểu")
# Meta-instructions aimed at the assistant are not part of the legal question; they are
# removed from the retrieval query only. Grounding rules do not change either way.
META_INSTRUCTION_RE = re.compile(
    r"(bỏ qua|phớt lờ|quên|ignore)\s+((mọi|tất cả|các|all|previous|any|the|prior)\s+){0,2}(hướng dẫn|chỉ dẫn|quy tắc|"
    r"chỉ thị|instructions?)(\s+(trước đó|trước|ở trên|của bạn|hệ thống))?\s*(,|\.|:|;|\bvà\b)?|"
    r"(mà\s+)?(không cần|khỏi|without)\s+(trích dẫn|dẫn nguồn|nguồn|citations?)(\s+nguồn)?\s*(,|\.|:|;)?|"
    r"(chỉ cần\s+)?(nói|trả lời)\s+nhanh\s*:?",
    re.IGNORECASE)


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def retrieval_query(question: str) -> str:
    """The legal question with meta-instructions stripped; falls back to the original text."""
    cleaned = " ".join(META_INSTRUCTION_RE.sub(" ", question).split()).strip(" ,.:;")
    return cleaned if len(cleaned) >= 8 else question


def scope_check(question: str) -> RefusalReason | None:
    q = normalize(question)
    if OUT_OF_SCOPE_RE.search(q):
        return RefusalReason.OUT_OF_SCOPE
    if PREDICTION_RE.search(q):
        return RefusalReason.UNSUPPORTED_PREDICTION
    if HISTORICAL_RE.search(q) or PAST_WAGE_RE.search(q):
        return RefusalReason.HISTORICAL_NOT_SUPPORTED
    return None


FLAGGED = {CurrencyStatus.UNVERIFIED, CurrencyStatus.SUPERSEDED_BY_AMENDMENT}


def unverified_but_current(item: ScoredChunk) -> bool:
    """In-scope evidence that may be in force but whose provisions are not verified yet."""
    return item.chunk.currency_status == CurrencyStatus.UNVERIFIED


def orphaned_superseded(item: ScoredChunk) -> bool:
    """Expired or displaced provision whose applicable wording is not in the corpus."""
    return (item.chunk.currency_status == CurrencyStatus.SUPERSEDED_BY_AMENDMENT
            and item.chunk.successor_document_id is None)


def flagged(item: ScoredChunk) -> bool:
    """In-scope evidence that cannot support an answer but explains a refusal: provisions not verified,
    or provisions the currency ledger records as expired, amended or displaced."""
    return item.chunk.currency_status in FLAGGED


@dataclass
class EvidenceAssessment:
    sufficient: bool
    reason: RefusalReason | None
    selected: list[ScoredChunk]
    stronger_unverified: list[ScoredChunk]
    best_eligible: float
    best_unverified: float


def assess(eligible: list[ScoredChunk], ineligible: list[ScoredChunk], cfg: PolicyConfig) -> EvidenceAssessment:
    best = eligible[0].score if eligible else 0.0
    unverified = [s for s in ineligible if flagged(s)]
    best_unverified = max((s.score for s in unverified), default=0.0)
    orphaned = [s for s in unverified if orphaned_superseded(s)]
    best_orphaned = max((s.score for s in orphaned), default=0.0)
    if (cfg.superseded_margin is not None and orphaned and best_orphaned >= cfg.unverified_threshold
            and best_orphaned >= best + cfg.superseded_margin):
        return EvidenceAssessment(False, RefusalReason.SUPERSEDED_BY_AMENDMENT, [], orphaned, best, best_unverified)
    if best >= cfg.answer_threshold:
        floor = max(cfg.answer_threshold, best * cfg.keep_ratio)
        selected = [s for s in eligible if s.score >= floor][: cfg.max_sources]
        stronger = [s for s in unverified if s.score >= best + cfg.stronger_margin
                    and s.score >= cfg.unverified_threshold]
        return EvidenceAssessment(True, None, selected, stronger, best, best_unverified)
    if best_unverified >= cfg.unverified_threshold:
        top = max(unverified, key=lambda s: s.score)
        reason = (RefusalReason.SUPERSEDED_BY_AMENDMENT
                  if top.chunk.currency_status == CurrencyStatus.SUPERSEDED_BY_AMENDMENT
                  else RefusalReason.CURRENCY_UNVERIFIED)
        return EvidenceAssessment(False, reason, [], unverified, best, best_unverified)
    return EvidenceAssessment(False, RefusalReason.INSUFFICIENT_EVIDENCE, [], [], best, best_unverified)
