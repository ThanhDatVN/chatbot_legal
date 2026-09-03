"""Conflict detection and resolution across retrieved provisions.

Retrieval routinely returns two provisions that say different things about the
same subject.  Handing both to the model and hoping it picks correctly is how a
legal assistant produces a confident wrong answer, so the choice is made here,
by rule, and the rule is reported.

Resolution order, strongest first:

1.  **Temporal** - only provisions in force on the event date compete at all.
2.  **Hierarchical** (*lex superior*) - higher legal force wins.
3.  **Amendment** - an amending provision beats the text it amends.
4.  **Formal vs guidance** - a normative document beats a Cong van.
5.  **Specialis** (*lex specialis*) - a sector-specific rule beats the general one.
6.  **Posterior** (*lex posterior*) - between equals, the later text wins.

When no rule decides, the conflict is returned with ``winner_chunk_id=None`` so
the answer can say so instead of guessing.
"""

from __future__ import annotations

import re

from virag.legal import authority, temporal
from virag.schemas import ConflictFinding, RetrievedChunk

# Numbers that carry legal meaning: rates, thresholds, deadlines.
_PERCENT = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")
_MONEY = re.compile(r"(\d[\d.,]{5,})\s*(?:đồng|vnd|đ)\b", re.IGNORECASE)
_DAYS = re.compile(r"(\d{1,3})\s*(?:ngày|tháng)\b", re.IGNORECASE)

_STOPWORDS = {
    "của",
    "và",
    "các",
    "được",
    "theo",
    "trong",
    "cho",
    "với",
    "này",
    "đối",
    "tại",
    "hoặc",
    "quy",
    "định",
    "khoản",
    "điều",
    "điểm",
    "thì",
    "khi",
    "là",
    "có",
    "không",
    "một",
    "những",
    "phải",
    "từ",
    "đến",
    "về",
}

# Wording that marks a provision as a carve-out from a general rule.
_SPECIALIS_MARKERS = (
    "trừ trường hợp",
    "riêng đối với",
    "đối với trường hợp",
    "trường hợp đặc biệt",
    "chuyên ngành",
    "ngoại trừ",
    "không áp dụng đối với",
)


def _content_terms(text: str, limit: int = 240) -> set[str]:
    """Content words of the leading ``limit`` tokens, diacritics preserved."""
    words = re.findall(r"[0-9A-Za-zÀ-ỹ]+", text.lower())[:limit]
    return {word for word in words if len(word) > 2 and word not in _STOPWORDS}


def topical_overlap(left: str, right: str) -> float:
    """Jaccard overlap of content words - a cheap "same subject" proxy."""
    a, b = _content_terms(left), _content_terms(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _numbers(text: str) -> set[str]:
    out: set[str] = set()
    out.update(f"pct:{m.replace(',', '.')}" for m in _PERCENT.findall(text))
    out.update(f"money:{m}" for m in _MONEY.findall(text))
    out.update(f"days:{m}" for m in _DAYS.findall(text))
    return out


def _is_specialis(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _SPECIALIS_MARKERS)


def _numeric_divergence(left: str, right: str) -> bool:
    """True when both sides state the same *kind* of number with different values.

    "10%" vs "8%" diverges.  "10%" vs "30 ngay" does not - those answer
    different questions and are not in conflict.
    """
    left_numbers, right_numbers = _numbers(left), _numbers(right)
    if not left_numbers or not right_numbers:
        return False

    for category in ("pct", "money", "days"):
        left_values = {n for n in left_numbers if n.startswith(f"{category}:")}
        right_values = {n for n in right_numbers if n.startswith(f"{category}:")}
        if left_values and right_values and not (left_values & right_values):
            return True
    return False


def detect_conflicts(
    chunks: list[RetrievedChunk],
    as_of: str,
    *,
    min_overlap: float = 0.28,
    max_pairs: int = 40,
) -> list[ConflictFinding]:
    """Find and resolve pairwise conflicts among the retrieved provisions."""
    findings: list[ConflictFinding] = []
    pairs_examined = 0

    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            if pairs_examined >= max_pairs:
                return findings
            pairs_examined += 1

            left, right = chunks[i], chunks[j]
            lc, rc = left.chunk, right.chunk

            # Two clauses of the same article of the same version are not in
            # conflict; they are one rule read together.
            if lc.document_id == rc.document_id and lc.version_id == rc.version_id:
                continue

            left_text, right_text = left.text_for_context, right.text_for_context
            overlap = topical_overlap(left_text, right_text)
            if overlap < min_overlap:
                continue
            if not _numeric_divergence(left_text, right_text) and overlap < 0.55:
                continue

            finding = _resolve(left, right, as_of, overlap)
            if finding is not None:
                findings.append(finding)

    findings.sort(key=lambda f: f.confidence, reverse=True)
    return findings


def _resolve(
    left: RetrievedChunk,
    right: RetrievedChunk,
    as_of: str,
    overlap: float,
) -> ConflictFinding | None:
    lc, rc = left.chunk, right.chunk

    def build(kind, winner, rule, explanation, confidence) -> ConflictFinding:
        return ConflictFinding(
            kind=kind,
            left_chunk_id=lc.chunk_id,
            right_chunk_id=rc.chunk_id,
            left_label=lc.citation_label,
            right_label=rc.citation_label,
            winner_chunk_id=winner,
            rule=rule,
            explanation=explanation,
            confidence=confidence,
        )

    # 1. Temporal - only one of them was in force on the event date.
    left_in_force = temporal.in_force(lc.effective_from, lc.effective_to, as_of)
    right_in_force = temporal.in_force(rc.effective_from, rc.effective_to, as_of)
    if left_in_force != right_in_force:
        winner = lc.chunk_id if left_in_force else rc.chunk_id
        loser_label = rc.citation_label if left_in_force else lc.citation_label
        winner_label = lc.citation_label if left_in_force else rc.citation_label
        return build(
            "temporal",
            winner,
            "hiệu lực theo thời điểm",
            f"Tại ngày {as_of}, {winner_label} đang có hiệu lực còn {loser_label} thì không.",
            0.92,
        )

    # 2. Hierarchical - lex superior.
    order = authority.compare(lc.authority_tier, rc.authority_tier)
    if order != 0:
        winner_chunk = lc if order < 0 else rc
        loser_chunk = rc if order < 0 else lc
        kind = (
            "formal_vs_guidance"
            if not authority.is_normative(loser_chunk.authority_tier)
            and authority.is_normative(winner_chunk.authority_tier)
            else "hierarchical"
        )
        note = ""
        if kind == "formal_vs_guidance":
            note = (
                " Văn bản thua là công văn/hướng dẫn nghiệp vụ, chỉ có giá trị tham khảo "
                "cho trường hợp cụ thể đã hỏi."
            )
        return build(
            kind,
            winner_chunk.chunk_id,
            "hiệu lực pháp lý cao hơn (lex superior)",
            (
                f"{winner_chunk.citation_label} thuộc cấp "
                f"'{authority.TIER_LABELS[winner_chunk.authority_tier]}', cao hơn "
                f"{loser_chunk.citation_label} ('{authority.TIER_LABELS[loser_chunk.authority_tier]}')."
                + note
            ),
            0.88,
        )

    # 3. Amendment - one text explicitly amends the other's instrument.
    left_amends = _mentions_amendment(left.text_for_context, rc.meta.instrument_number if rc.meta else None)
    right_amends = _mentions_amendment(right.text_for_context, lc.meta.instrument_number if lc.meta else None)
    if left_amends != right_amends:
        winner_chunk = lc if left_amends else rc
        loser_chunk = rc if left_amends else lc
        return build(
            "amendment",
            winner_chunk.chunk_id,
            "văn bản sửa đổi thay thế nội dung bị sửa đổi",
            f"{winner_chunk.citation_label} sửa đổi trực tiếp {loser_chunk.citation_label}.",
            0.85,
        )

    # 4. Specialis - a carve-out beats the general rule at equal force.
    left_special = _is_specialis(left.text_for_context)
    right_special = _is_specialis(right.text_for_context)
    if left_special != right_special:
        winner_chunk = lc if left_special else rc
        loser_chunk = rc if left_special else lc
        return build(
            "general_vs_special",
            winner_chunk.chunk_id,
            "quy định riêng ưu tiên quy định chung (lex specialis)",
            (
                f"{winner_chunk.citation_label} quy định cho trường hợp riêng, "
                f"ưu tiên áp dụng so với quy định chung tại {loser_chunk.citation_label}. "
                "Cần xác nhận người nộp thuế thuộc phạm vi điều chỉnh riêng đó."
            ),
            0.6,
        )

    # 5. Posterior - same force, both in effect, the later text wins.
    left_date = lc.effective_from or (lc.meta.promulgation_date if lc.meta else None)
    right_date = rc.effective_from or (rc.meta.promulgation_date if rc.meta else None)
    if left_date and right_date and left_date != right_date:
        winner_chunk = lc if left_date > right_date else rc
        loser_chunk = rc if left_date > right_date else lc
        return build(
            "implicit_repeal",
            winner_chunk.chunk_id,
            "văn bản ban hành sau (lex posterior)",
            (
                f"Hai quy định cùng cấp hiệu lực và cùng đang áp dụng; "
                f"{winner_chunk.citation_label} ban hành sau {loser_chunk.citation_label}. "
                "Đây là suy luận bãi bỏ ngầm định, cần chuyên gia xác nhận."
            ),
            0.45,
        )

    return build(
        "implicit_repeal",
        None,
        "không đủ căn cứ phân định",
        (
            f"Phát hiện khác biệt giữa {lc.citation_label} và {rc.citation_label} "
            f"(mức trùng chủ đề {overlap:.2f}) nhưng cùng cấp hiệu lực, cùng thời điểm "
            "và không có quan hệ sửa đổi rõ ràng. Cần chuyên gia thuế xem xét."
        ),
        0.3,
    )


def _mentions_amendment(text: str, instrument_number: str | None) -> bool:
    if not instrument_number:
        return False
    lowered = text.lower()
    if not any(cue in lowered for cue in ("sửa đổi", "bổ sung", "thay thế", "bãi bỏ")):
        return False
    return instrument_number.lower() in lowered


def summarise(findings: list[ConflictFinding]) -> str:
    """Render conflicts as a block the answer prompt can quote verbatim."""
    if not findings:
        return ""
    lines = ["CẢNH BÁO XUNG ĐỘT QUY ĐỊNH:"]
    for finding in findings[:5]:
        if finding.winner_chunk_id:
            winner = (
                finding.left_label
                if finding.winner_chunk_id == finding.left_chunk_id
                else finding.right_label
            )
            lines.append(
                f"- [{finding.kind}] Áp dụng {winner} (căn cứ: {finding.rule}). {finding.explanation}"
            )
        else:
            lines.append(f"- [{finding.kind}] Chưa phân định được. {finding.explanation}")
    return "\n".join(lines)
