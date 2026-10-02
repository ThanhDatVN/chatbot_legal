"""Answer orchestration: agent → citation validation → structured AnswerResult.

`system` selects the benchmark variant for answers:
    A / baseline — dense top-5 retrieval, answer from the top passages; no BM25,
                   reranker, refusal policy or citation validation
    B            — as A with hybrid dense + BM25 + RRF retrieval
    C            — as B with cross-encoder reranking
    D / final    — hybrid + reranker, two-tool agent, evidence policy and
                   citation validation (extractive or Claude, per settings)
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Literal

from app.agent.claude_agent import ClaudeAgent
from app.agent.openai_agent import OpenAIAgent
from app.agent.draft import Draft
from app.agent.extractive import ExtractiveAgent
from app.agent.policy import PolicyConfig
from app.agent.tools import ToolBox
from app.config import Settings
from app.errors import CiteAgentError
from app.generation.validator import DraftClaim, validate_claims
from app.runtime import Runtime
from app.schemas import AnswerResult, Citation, Claim, Decision, RefusalReason, StageMetrics
from ingestion.models import CurrencyStatus, TextQualityStatus

REFUSAL_TEXT = {
    RefusalReason.INSUFFICIENT_EVIDENCE: "Tôi chưa tìm thấy nguồn trong kho tài liệu hiện tại đủ để kết luận câu hỏi này.",
    RefusalReason.CURRENCY_UNVERIFIED: ("Nội dung liên quan nằm trong văn bản chưa được xác minh hiệu lực đến từng điều, "
                                        "nên tôi không dùng nó để kết luận về quy định hiện hành."),
    RefusalReason.OUT_OF_SCOPE: ("Câu hỏi nằm ngoài phạm vi của CiteAgent VN: quan hệ lao động theo Bộ luật Lao động "
                                 "và các văn bản hướng dẫn trực tiếp."),
    RefusalReason.HISTORICAL_NOT_SUPPORTED: "Phiên bản hiện tại chỉ hỗ trợ quy định đang áp dụng tại ngày {as_of}.",
    RefusalReason.SUPERSEDED_BY_AMENDMENT: ("Quy định liên quan tìm được trong kho đã hết hiệu lực hoặc đang được áp dụng "
                                            "theo một văn bản khác chưa có trong kho, nên tôi không dùng nó để kết luận "
                                            "về quy định tại ngày {as_of}."),
    RefusalReason.UNSUPPORTED_PREDICTION: "Tôi không dự đoán thay đổi của pháp luật; kho tài liệu chỉ chứa quy định đã ban hành.",
    RefusalReason.CONFLICTING_SOURCES: "Các nguồn tìm được mâu thuẫn nhau, nên tôi chưa thể kết luận.",
    RefusalReason.SOURCE_UNAVAILABLE: "Không thể mở nguồn gốc để kiểm tra căn cứ lúc này.",
}
REFUSAL_TIPS = ("Bạn có thể:\n• diễn đạt lại câu hỏi;\n• giới hạn vào một văn bản cụ thể;\n"
                "• kiểm tra các nguồn gần nhất bên dưới.")
# Bodies renamed or abolished in the 2025 reorganisation; old guiding decrees still name them.
REORGANISED_BODY_RE = re.compile(r"Lao động\s*-\s*Thương binh và Xã hội|cấp huyện|Phòng Lao động")
REORGANISED_NOTICE = ("Nguồn được trích nêu Bộ/Sở/Phòng Lao động - Thương binh và Xã hội hoặc chính quyền cấp huyện. "
                      "Sau sắp xếp bộ máy năm 2025, nhiều nhiệm vụ này do cơ quan nội vụ và chính quyền địa phương "
                      "hai cấp thực hiện (ví dụ Điều 71 Nghị định 129/2025/NĐ-CP giao Sở Nội vụ nhận báo cáo sử dụng "
                      "lao động); hãy kiểm tra cơ quan có thẩm quyền hiện hành.")
FOLLOW_UPS = ["Quy định này nằm ở Điều nào?", "Có trường hợp ngoại lệ không?", "Cho tôi xem nguyên văn nguồn."]


class AnswerService:
    def __init__(self, runtime: Runtime, policy: PolicyConfig | None = None, llm_client=None) -> None:
        self.runtime = runtime
        self.settings: Settings = runtime.settings
        self.policy = policy or PolicyConfig(answer_threshold=self.settings.refusal_threshold)
        self.llm_client = llm_client
        self.log_path = self.settings.runtime_dir / "query_log.jsonl"

    # ------------------------------------------------------------------------------------------
    def answer(self, question: str, session_id: str | None = None,
               system: Literal["final", "baseline", "A", "B", "C", "D"] = "final",
               provider: str | None = None) -> AnswerResult:
        query_id = "q_" + uuid.uuid4().hex[:16]
        started = time.perf_counter()
        provider = provider or self.settings.llm_provider
        naive_mode = {"baseline": "dense", "A": "dense", "B": "hybrid", "C": "rerank"}.get(system)
        toolbox = ToolBox(self.runtime.catalog, self.runtime.retrieval, mode=naive_mode or "rerank",
                          max_search_calls=self.settings.max_search_calls,
                          max_source_calls=self.settings.max_source_calls)
        error = None
        try:
            if naive_mode is not None:
                draft = self._baseline(question, toolbox, naive_mode)
                mode = f"naive-{naive_mode}-extractive"
            elif provider == "anthropic":
                draft = ClaudeAgent(toolbox, self.settings, self.llm_client).run(question, self.runtime.catalog.as_of_date)
                mode = f"agent-{self.settings.llm_model}"
            elif provider == "openai":
                draft = OpenAIAgent(toolbox, self.settings, self.llm_client).run(question, self.runtime.catalog.as_of_date)
                mode = f"agent-{self.settings.openai_model}"
            else:
                draft = ExtractiveAgent(toolbox, self.runtime.retrieval.reranker, self.policy).run(
                    question, self.runtime.catalog.as_of_date)
                mode = "agent-extractive"
        except CiteAgentError as exc:
            error = exc
            draft = Draft(Decision.REFUSE, RefusalReason.SOURCE_UNAVAILABLE, notes=[exc.code])
            mode = f"error:{exc.code}"
        result = self._finalize(query_id, session_id, question, draft, toolbox, mode, validate=naive_mode is None)
        result.metrics = StageMetrics(
            total_ms=round((time.perf_counter() - started) * 1000, 1), retrieval_ms=round(toolbox.retrieval_ms, 1),
            rerank_ms=round(toolbox.rerank_ms, 1),
            generation_ms=round(max(0.0, (time.perf_counter() - started) * 1000 - toolbox.retrieval_ms
                                    - toolbox.rerank_ms), 1),
            input_tokens=draft.usage.input_tokens, output_tokens=draft.usage.output_tokens,
            llm_cost_usd=round(draft.usage.cost_usd, 6), search_calls=toolbox.search_calls,
            source_calls=toolbox.source_calls)
        self._log(result, question, toolbox, draft, error)
        return result

    # ------------------------------------------------------------------------------------------
    def _baseline(self, question: str, toolbox: ToolBox, mode: str = "dense") -> Draft:
        """Naive RAG: top-5 retrieval, answer from the top passages, no refusal or checks."""
        result = self.runtime.retrieval.search(question, top_k=5, mode=mode, subset="in_scope",
                                               include_ineligible=False)
        toolbox.retrieval_ms += result.timings_ms.get("retrieval_ms", 0.0)
        toolbox.rerank_ms += result.timings_ms.get("rerank_ms", 0.0)
        toolbox.search_calls += 1
        claims = []
        for item in result.eligible[:2]:
            toolbox.retrieved[item.chunk.chunk_id] = item
            source = toolbox.get_source({"chunk_id": item.chunk.chunk_id})
            lines = [u for u in source.text.split("\n") if u.strip()][:3]
            claims += [DraftClaim(text=u, chunk_ids=[source.chunk_id], quote=u) for u in lines]
        return Draft(Decision.ANSWER if claims else Decision.REFUSE,
                     None if claims else RefusalReason.INSUFFICIENT_EVIDENCE, claims)

    def _finalize(self, query_id: str, session_id: str | None, question: str, draft: Draft, toolbox: ToolBox,
                  mode: str, validate: bool) -> AnswerResult:
        catalog = self.runtime.catalog
        dropped: list[dict] = []
        claims = draft.claims
        decision, reason = draft.decision, draft.reason
        if validate and decision != Decision.REFUSE:
            scores = {cid: toolbox.score_of(cid) for cid in toolbox.fetched}
            report = validate_claims(claims, toolbox.fetched, scores, self.policy.answer_threshold)
            claims, dropped = report.kept, report.dropped
            if not claims:
                decision, reason = Decision.REFUSE, reason or RefusalReason.INSUFFICIENT_EVIDENCE
            elif dropped and decision == Decision.ANSWER:
                decision = Decision.PARTIAL
        if decision == Decision.REFUSE:
            claims = []
            reason = reason or RefusalReason.INSUFFICIENT_EVIDENCE

        # citation numbers come from code, in order of first use
        numbering: dict[str, int] = {}
        for claim in claims:
            for cid in claim.chunk_ids:
                numbering.setdefault(cid, len(numbering) + 1)
        citations = []
        for cid, n in numbering.items():
            src = toolbox.fetched[cid]
            quote = next((c.quote for c in claims if cid in c.chunk_ids), "")
            citations.append(Citation(citation_id=n, chunk_id=cid, document_id=src.document_id,
                                      document_number=src.document_number, title=src.short_title,
                                      section=src.section, page_start=src.page_start, page_end=src.page_end,
                                      source_url=src.source_url, quote=quote[:400],
                                      currency_status=src.currency_status))
        out_claims = [Claim(claim_id=f"c{i + 1}", text=c.text, citation_ids=[numbering[x] for x in c.chunk_ids])
                      for i, c in enumerate(claims)]
        answer = self._compose(decision, reason, out_claims, citations, draft)
        notices = self._notices(citations, toolbox, dropped, decision, reason)
        related = []
        if decision != Decision.ANSWER:
            seen = set(numbering)
            ranked = sorted(toolbox.retrieved.values(), key=lambda s: -s.score)
            related = [catalog.preview(s.chunk, s.score, limit=260) for s in ranked if s.chunk.chunk_id not in seen][:3]
        trace = toolbox.trace + ([{"validation_dropped": dropped}] if dropped else []) + \
            ([{"notes": draft.notes}] if draft.notes else [])
        return AnswerResult(query_id=query_id, session_id=session_id, corpus_snapshot_id=catalog.snapshot_id,
                            decision=decision, reason=reason if decision != Decision.ANSWER else None, answer=answer,
                            claims=out_claims, citations=citations, notices=notices, related_sources=related,
                            suggestions=FOLLOW_UPS if decision != Decision.REFUSE else [], mode=mode, trace=trace)

    def _compose(self, decision: Decision, reason: RefusalReason | None, claims: list[Claim],
                 citations: list[Citation], draft: Draft) -> str:
        if decision == Decision.REFUSE:
            text = REFUSAL_TEXT[reason or RefusalReason.INSUFFICIENT_EVIDENCE].format(
                as_of=self.runtime.catalog.as_of_date)
            return f"⚠ Chưa đủ căn cứ\n\n{text}\n\n{REFUSAL_TIPS}"
        by_id = {c.citation_id: c for c in citations}
        parts: list[str] = []
        if draft.layout == "grouped":
            current = None
            for claim in claims:
                cid = claim.citation_ids[0]
                if cid != current:
                    cite = by_id[cid]
                    parts.append(f"\nTheo {cite.section} – {cite.title} ({cite.document_number}):")
                    current = cid
                parts.append(f"- {claim.text} [{cid}]")
        else:
            for claim in claims:
                marks = "".join(f"[{n}]" for n in claim.citation_ids)
                parts.append(f"{claim.text} {marks}")
        text = "\n".join(parts).strip()
        if decision == Decision.PARTIAL:
            missing = draft.unanswered or "Một phần câu hỏi chưa có đủ căn cứ trong kho tài liệu hiện tại."
            text += f"\n\nPhần chưa đủ căn cứ: {missing}"
        return text

    def _notices(self, citations: list[Citation], toolbox: ToolBox, dropped: list[dict],
                 decision: Decision, reason: RefusalReason | None = None) -> list[str]:
        notices: list[str] = []
        if decision == Decision.REFUSE and reason == RefusalReason.SUPERSEDED_BY_AMENDMENT:
            superseded = sorted((s for s in toolbox.retrieved.values()
                                 if s.chunk.currency_status == CurrencyStatus.SUPERSEDED_BY_AMENDMENT),
                                key=lambda s: -s.score)
            seen_sections: set[tuple[str, str]] = set()
            for item in superseded:
                key = (item.chunk.document_id, item.chunk.section_label)
                if key in seen_sections:
                    continue  # one notice per article, not per chunk
                seen_sections.add(key)
                notices.append(f"{item.chunk.document_number}, {item.chunk.section_label}: {item.chunk.currency_basis}")
                if len(seen_sections) == 2:
                    break
        seen_docs: set[str] = set()
        for cite in citations:
            src = toolbox.fetched[cite.chunk_id]
            for note in src.amendment_notes:
                if note.change_type in ("amended", "added", "repealed"):
                    notices.append(f"{note.target_label} đã được {'bổ sung' if note.change_type == 'added' else 'sửa đổi'}"
                                   f" theo {note.amending_instrument}, hiệu lực từ "
                                   f"{note.effective_from.strftime('%d/%m/%Y') if note.effective_from else 'không rõ'}.")
            if src.document_id not in seen_docs:
                seen_docs.add(src.document_id)
                notices.append(f"Căn cứ hiệu lực ({src.document_number}): {src.currency_basis}")
            if src.currency_status != CurrencyStatus.VERIFIED_CURRENT.value \
                    or src.text_quality_status != TextQualityStatus.VERIFIED.value:
                flag = "Nguồn chưa được chuyên gia pháp lý duyệt; hãy đối chiếu văn bản gốc trước khi áp dụng."
                if flag not in notices:
                    notices.append(flag)
        if any(REORGANISED_BODY_RE.search(c.quote) for c in citations):
            notices.append(REORGANISED_NOTICE)
        if dropped:
            notices.append(f"Đã loại {len(dropped)} nhận định không kiểm chứng được với nguồn.")
        return notices

    def _log(self, result: AnswerResult, question: str, toolbox: ToolBox, draft: Draft,
             error: Exception | None) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        q = question if self.settings.log_questions == "plain" else \
            "sha256:" + hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]
        row = {"query_id": result.query_id, "timestamp": datetime.now(timezone.utc).isoformat(),
               "question": q, "snapshot": result.corpus_snapshot_id, "mode": result.mode,
               "decision": result.decision.value, "reason": result.reason.value if result.reason else None,
               "citations": [c.chunk_id for c in result.citations], "metrics": result.metrics.model_dump(),
               "retrieval": [{k: v for k, v in step.items() if k != "query"} for step in toolbox.trace],
               "llm_model": draft.usage.model, "error": getattr(error, "code", None)}
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
