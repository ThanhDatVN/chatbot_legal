"""Assign a currency status to every chunk, with the reason spelled out.

Only a named human reviewer can mark a provision `verified_current`
(data/review/currency_reviews.json). Everything else is derived from the
registry and the consolidated-text footnotes, and says so in `currency_basis`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ingestion.models import Chunk, CorpusUse, CurrencyStatus, RegistryDocument, TextQualityStatus

CONSOLIDATED_TYPE = "Văn bản hợp nhất"


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str
    status: str
    reviewer: str
    reviewed_at: date
    evidence_url: str
    note: str = ""


def load_reviews(path: Path) -> dict[str, Review]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {r.section_id: r for r in (Review.model_validate(x) for x in rows)}


def _consolidated_by(doc: RegistryDocument, registry: list[RegistryDocument]) -> RegistryDocument | None:
    return next((d for d in registry if doc.document_number in d.consolidates and d.corpus_use == CorpusUse.CURRENT),
                None)


def assign_currency(chunk: Chunk, doc: RegistryDocument, registry: list[RegistryDocument], as_of: date,
                    reviews: dict[str, Review]) -> tuple[CurrencyStatus, str]:
    review = reviews.get(chunk.section_id)
    if review is not None:
        return CurrencyStatus(review.status), f"Người duyệt {review.reviewer} ngày {review.reviewed_at}: {review.note}"
    if doc.corpus_use == CorpusUse.OUT_OF_SCOPE:
        return CurrencyStatus.UNVERIFIED, "Văn bản ngoài phạm vi MVP (quan hệ lao động)."
    if doc.corpus_use == CorpusUse.HISTORICAL:
        consolidated = _consolidated_by(doc, registry)
        if consolidated is not None:
            return (CurrencyStatus.SUPERSEDED_BY_CONSOLIDATION,
                    f"Câu hỏi hiện hành dùng văn bản hợp nhất {consolidated.document_number}.")
        return CurrencyStatus.HISTORICAL, doc.corpus_use_reason
    if doc.effective_date and doc.effective_date > as_of:
        return CurrencyStatus.PENDING_AMENDMENT, f"Văn bản chưa có hiệu lực tại {as_of}."
    if doc.document_type == CONSOLIDATED_TYPE:
        future = [n for n in chunk.amendment_notes
                  if n.change_type in ("amended", "added") and n.effective_from and n.effective_from > as_of]
        if future:
            n = future[0]
            return (CurrencyStatus.PENDING_AMENDMENT,
                    f"{n.target_label} theo {n.amending_instrument} chỉ có hiệu lực từ {n.effective_from}.")
        applied = [n for n in chunk.amendment_notes if n.change_type in ("amended", "added", "repealed")]
        basis = (f"Văn bản hợp nhất chính thức {doc.document_number} xác thực ngày {doc.issued_date}"
                 f"; chưa đối chiếu văn bản sửa đổi ban hành sau ngày hợp nhất.")
        if applied:
            basis += " Đã phản ánh: " + "; ".join(
                f"{n.target_label} ({n.amending_instrument}, hiệu lực {n.effective_from})" for n in applied) + "."
        return CurrencyStatus.CONSOLIDATED_CURRENT, basis
    lead = doc.legal_status_lead
    if lead and lead.status.startswith("listed_current"):
        return (CurrencyStatus.PRESUMED_CURRENT,
                f"VBPL (tra cứu gián tiếp {lead.checked_on}) ghi văn bản còn hiệu lực; chưa xác minh từng điều.")
    if lead and lead.status == "partially_expired":
        return (CurrencyStatus.UNVERIFIED,
                f"VBPL ghi hết hiệu lực một phần; chưa lập ánh xạ điều bị sửa đổi/bãi bỏ ({lead.note})")
    return CurrencyStatus.UNVERIFIED, "Chưa có căn cứ xác định hiệu lực."


def apply_text_reviews(chunk: Chunk, reviews: dict[str, Review], machine_ok: bool) -> TextQualityStatus:
    review = reviews.get(chunk.section_id)
    if review is not None:
        return TextQualityStatus(review.status)
    return TextQualityStatus.MACHINE_CHECKED if machine_ok else TextQualityStatus.UNREVIEWED
