"""Offline agent: same workflow and tools, answers made only of verbatim source passages.

It runs without an LLM key: split a multi-part question into its parts, call
search_evidence for the whole question and each part (within the tool budget),
assess evidence per query, open the selected sources with get_source, and pick
the passages (clauses/points) that best answer each query with the cross-encoder.
"""

from __future__ import annotations

import re

from app.agent.draft import Draft
from app.agent.policy import EvidenceAssessment, PolicyConfig, assess, retrieval_query, scope_check
from app.agent.tools import ToolBox
from app.generation.validator import DraftClaim
from app.retrieval.models import Reranker
from app.schemas import Decision, RefusalReason, SourceEvidence
from ingestion.models import CurrencyStatus

CURRENCY_REASONS = (RefusalReason.SUPERSEDED_BY_AMENDMENT, RefusalReason.CURRENCY_UNVERIFIED)

HEADING_RE = re.compile(r"^Điều\s+\d+\.")
CLAUSE_RE = re.compile(r"^\d+[a-z]?\.\s")
POINT_RE = re.compile(r"^[a-zđ]\)\s")
QUESTION_CUE_RE = re.compile(r"\b(bao nhiêu|bao lâu|thế nào|ra sao|những gì|là gì|là ai|gì|nào|không|khi nào|ở đâu|"
                             r"mấy|có được|có phải)\b")
MAX_UNITS_PER_SOURCE = 3
MAX_LIST_POINTS = 8


def split_question(question: str, max_parts: int = 2) -> list[str]:
    """Split "A ... bao lâu và B ... thế nào?" into its asked parts; single questions stay whole."""
    for m in re.finditer(r",?\s+và\s+", question):
        left, right = question[:m.start()].strip(" ,"), question[m.end():].strip()
        if QUESTION_CUE_RE.search(left.lower()) and QUESTION_CUE_RE.search(right.lower()) \
                and len(left.split()) >= 4 and len(right.split()) >= 4:
            return [left + "?", right][:max_parts]
    return [question]


class ExtractiveAgent:
    def __init__(self, toolbox: ToolBox, reranker: Reranker | None, policy: PolicyConfig) -> None:
        self.toolbox = toolbox
        self.reranker = reranker
        self.policy = policy

    def _search(self, query: str) -> EvidenceAssessment:
        self.toolbox.search_evidence({"query": query, "top_k": 5})
        result = self.toolbox.last_result
        return assess(result.eligible, result.ineligible, self.policy)

    def run(self, question: str, as_of_date: str) -> Draft:
        blocked = scope_check(question)
        if blocked is not None:
            return Draft(Decision.REFUSE, blocked, notes=["scope_rule"])
        question = retrieval_query(question)
        whole = self._search(question)
        parts = split_question(question)
        verdicts = [(question, whole)]
        part_verdicts = []
        if len(parts) > 1:
            for part in parts[: self.toolbox.max_search_calls - 1]:
                part_verdicts.append((part, self._search(part)))
            verdicts += part_verdicts
        if not any(v.sufficient for _, v in verdicts):
            reason = next((v.reason for _, v in verdicts if v.reason in CURRENCY_REASONS), whole.reason)
            return Draft(Decision.REFUSE, reason, notes=[f"best_eligible={whole.best_eligible:.3f}",
                                                         f"best_unverified={whole.best_unverified:.3f}"])
        claims: list[DraftClaim] = []
        used: set[str] = set()
        # each part's best evidence first, then whatever the whole question adds
        ordered = part_verdicts + [(question, whole)]
        cap = self.policy.max_sources + max(0, len(part_verdicts) - 1)
        for query, verdict in ordered:
            for item in verdict.selected:
                if item.chunk.chunk_id in used or len(used) >= cap:
                    continue
                used.add(item.chunk.chunk_id)
                source = self.toolbox.get_source({"chunk_id": item.chunk.chunk_id})
                for unit in self._best_units(query, source):
                    claims.append(DraftClaim(text=unit, chunk_ids=[source.chunk_id], quote=unit))
        gaps = [part for part, v in part_verdicts if not v.sufficient]
        stronger = [s for _, v in verdicts for s in v.stronger_unverified]
        notes: list[str] = []
        if gaps:
            notes.append("Chưa tìm thấy căn cứ đủ mạnh cho phần: " + "; ".join(f"“{g}”" for g in gaps) + ".")
        unverified = [s for s in stronger if s.chunk.currency_status == CurrencyStatus.UNVERIFIED]
        superseded = [s for s in stronger if s.chunk.currency_status == CurrencyStatus.SUPERSEDED_BY_AMENDMENT]
        if unverified:
            titles = sorted({s.chunk.short_title + f" ({s.chunk.document_number})" for s in unverified})
            notes.append("Văn bản hướng dẫn chi tiết hơn có nội dung liên quan nhưng hiệu lực từng điều chưa được "
                         "xác minh nên chưa dùng làm căn cứ: " + "; ".join(titles) + ".")
        if superseded:
            labels = sorted({f"{s.chunk.section_label} {s.chunk.document_number}" for s in superseded})
            notes.append("Quy định chi tiết liên quan (" + "; ".join(labels) + ") đã hết hiệu lực hoặc được thay thế "
                         "bởi văn bản chưa có trong kho, nên chưa dùng làm căn cứ.")
        decision = Decision.PARTIAL if notes else Decision.ANSWER
        return Draft(decision, None, claims, unanswered=" ".join(notes) or None, layout="grouped")

    def _best_units(self, question: str, source: SourceEvidence) -> list[str]:
        units = [u.strip() for u in source.text.split("\n") if u.strip()]
        body = [u for u in units if not HEADING_RE.match(u)] or units
        if len(body) <= MAX_UNITS_PER_SOURCE:
            return body
        if self.reranker is not None:
            scores = self.reranker.score(question, body)
        else:
            q = set(re.findall(r"[^\W_]+", question.lower()))
            scores = [len(q & set(re.findall(r"[^\W_]+", u.lower()))) / (len(u.split()) ** 0.5 + 1) for u in body]
        best = max(scores)
        chosen = sorted(i for i, s in sorted(enumerate(scores), key=lambda x: -x[1])[:MAX_UNITS_PER_SOURCE]
                        if s >= best * 0.5)
        picked: set[int] = set(chosen)
        for i in chosen:
            # a point ("a) ...") reads better with the clause that introduces it
            if POINT_RE.match(body[i]):
                parent = next((k for k in range(i - 1, -1, -1) if not POINT_RE.match(body[k])), None)
                if parent is not None:
                    picked.add(parent)
            # a clause ending in ":" introduces a list; the list is the actual rule
            if body[i].endswith(":"):
                k = i + 1
                while k < len(body) and POINT_RE.match(body[k]) and k - i <= MAX_LIST_POINTS:
                    picked.add(k)
                    k += 1
        return [body[i] for i in sorted(picked)]
