"""Legal force hierarchy for Vietnamese normative documents.

Cosine similarity does not know that a Cong van answering one company's letter
cannot override the Luat it interprets.  This module turns the document type
into a tier so ranking and conflict resolution can.

Tiers follow the order of legal force in the Law on Promulgation of Legal
Normative Documents.  Lower number = higher force.
"""

from __future__ import annotations

import re
import unicodedata

#: tier -> canonical description, for reports and the UI legend.
TIER_LABELS: dict[int, str] = {
    1: "Hiến pháp",
    2: "Bộ luật, Luật, Nghị quyết của Quốc hội",
    3: "Pháp lệnh, Nghị quyết của Ủy ban Thường vụ Quốc hội",
    4: "Lệnh, Quyết định của Chủ tịch nước",
    5: "Nghị định, Nghị quyết của Chính phủ",
    6: "Quyết định của Thủ tướng Chính phủ",
    7: "Thông tư, Thông tư liên tịch",
    8: "Quyết định, Chỉ thị cấp bộ và địa phương",
    9: "Công văn, hướng dẫn nghiệp vụ (không phải VBQPPL)",
}

MIN_TIER = 1
MAX_TIER = 9

# Longest patterns first: "nghi quyet lien tich" must win over "nghi quyet".
_TYPE_PATTERNS: tuple[tuple[str, int], ...] = (
    ("hien phap", 1),
    ("bo luat", 2),
    ("nghi quyet cua quoc hoi", 2),
    ("nghi quyet quoc hoi", 2),
    ("luat", 2),
    ("phap lenh", 3),
    ("nghi quyet cua uy ban thuong vu quoc hoi", 3),
    ("nghi quyet uy ban thuong vu quoc hoi", 3),
    ("lenh cua chu tich nuoc", 4),
    ("quyet dinh cua chu tich nuoc", 4),
    ("nghi dinh", 5),
    ("nghi quyet cua chinh phu", 5),
    ("nghi quyet chinh phu", 5),
    ("quyet dinh cua thu tuong", 6),
    ("quyet dinh thu tuong", 6),
    ("chi thi cua thu tuong", 6),
    ("thong tu lien tich", 7),
    ("thong tu", 7),
    ("quyet dinh", 8),
    ("chi thi", 8),
    ("thong bao", 9),
    ("cong van", 9),
    ("huong dan", 9),
    ("cong dien", 9),
)

# Instrument-number suffixes are the most reliable signal when the title is noisy.
_SUFFIX_TIERS: tuple[tuple[str, int], ...] = (
    ("qh", 2),
    ("ubtvqh", 3),
    ("ctn", 4),
    ("nd-cp", 5),
    ("nq-cp", 5),
    ("qd-ttg", 6),
    ("ct-ttg", 6),
    ("ttlt", 7),
    ("tt-btc", 7),
    ("tt-bkhdt", 7),
    ("tt", 7),
    ("qd-btc", 8),
    ("qd", 8),
    ("cv", 9),
    ("cd", 9),
)

# A "van ban hop nhat" is a convenience consolidation - its force is that of the
# instrument it consolidates, which the number carries (VBHN-BTC -> Thong tu).
_VBHN = re.compile(r"\bvbhn\b", re.IGNORECASE)


def _fold(text: str) -> str:
    """Strip Vietnamese diacritics and lowercase, so matching is spelling-proof."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return without_marks.replace("đ", "d").replace("đ", "d")


def tier_from_document_type(document_type: str | None) -> int | None:
    folded = _fold(document_type or "")
    if not folded:
        return None
    for pattern, tier in _TYPE_PATTERNS:
        if pattern in folded:
            return tier
    return None


#: Type codes embedded in a consolidated-document number, e.g. "VBHN-NĐ-BCT".
_VBHN_TYPE_CODES: tuple[tuple[str, int], ...] = (
    ("nqtv", 3),  # Standing Committee resolution
    ("pl", 3),  # Pháp lệnh
    ("nd", 5),  # Nghị định
    ("nq", 5),  # Nghị quyết (Government, unless VPQH - handled below)
    ("qd", 8),
    ("tt", 7),  # Thông tư
)

#: Organ codes, used only when neither the title nor a type code decides.
#: VPQH is the National Assembly Office, which consolidates Laws and Ordinances.
_VBHN_ORGAN_TIERS: tuple[tuple[str, int], ...] = (
    ("vpqh", 2),
    ("ctn", 4),
)


def tier_for_consolidated(instrument_number: str | None, title: str | None) -> int:
    """Authority of a Văn bản hợp nhất - inherited, never fixed.

    A consolidated document is a convenience view of another instrument and
    carries **that instrument's** legal force. Hard-coding tier 7 ranked a
    consolidated Law five tiers too low, which the authority component of the
    ranking score then acted on. 150 of 1,580 corpus documents are VBHN.

    The number alone is not sufficient. Measured on the corpus,
    ``19/VBHN-BTC`` carries a ministry code yet its title reads *"hợp nhất Nghị
    định"* - a Decree, tier 5, not a Circular. So the title is consulted first.

    Resolution order: title ("hợp nhất <type>") -> embedded type code -> organ
    code -> tier 7, the commonest ministry consolidation.
    """
    folded_title = _fold(title or "")
    marker = "hop nhat"
    if marker in folded_title:
        after = folded_title.split(marker, 1)[1]
        for pattern, tier in _TYPE_PATTERNS:
            # Only the leading phrase names the consolidated instrument; text
            # further in usually cites what that instrument implements.
            if after.lstrip().startswith(pattern):
                return tier

    folded_number = _fold(instrument_number or "")
    if "vbhn" in folded_number:
        segments = folded_number.split("vbhn", 1)[1].strip("-/").split("-")
        for segment in segments:
            for code, tier in _VBHN_TYPE_CODES:
                if segment == code:
                    # "VBHN-NQ-VPQH" is a National Assembly resolution, tier 2.
                    if code == "nq" and "vpqh" in segments:
                        return 2
                    return tier
        for organ, tier in _VBHN_ORGAN_TIERS:
            if organ in segments:
                return tier
    return 7


def tier_from_instrument_number(instrument_number: str | None) -> int | None:
    """Derive the tier from a number such as ``48/2024/QH15`` or ``123/2025/ND-CP``."""
    if not instrument_number:
        return None
    folded = _fold(instrument_number)
    # The organ code is the trailing segment after the last "/".
    tail = folded.rsplit("/", 1)[-1]
    if _VBHN.search(tail):
        # Resolved by tier_for_consolidated, which also needs the title.
        return None
    for suffix, tier in _SUFFIX_TIERS:
        if tail.startswith(suffix) or tail.endswith(suffix):
            return tier
    return None


def is_consolidated(instrument_number: str | None, document_type: str | None) -> bool:
    return "vbhn" in _fold(instrument_number or "") or "hop nhat" in _fold(document_type or "")


def resolve_tier(document_type: str | None, instrument_number: str | None, title: str | None = None) -> int:
    """Best-effort authority tier; falls back to the least-authoritative tier."""
    # A consolidated document inherits the force of what it consolidates, so it
    # must be resolved before the generic paths - which would otherwise read
    # "Văn bản hợp nhất" as a document type of its own (D-06).
    if is_consolidated(instrument_number, document_type):
        return tier_for_consolidated(instrument_number, title)

    for candidate in (
        tier_from_instrument_number(instrument_number),
        tier_from_document_type(document_type),
        tier_from_document_type(title),
    ):
        if candidate is not None:
            return candidate
    return MAX_TIER


def authority_score(tier: int) -> float:
    """Map a tier onto [0, 1] where 1.0 is the Constitution."""
    tier = max(MIN_TIER, min(MAX_TIER, int(tier)))
    return (MAX_TIER - tier) / (MAX_TIER - MIN_TIER)


def is_normative(tier: int) -> bool:
    """Tier 9 documents are administrative guidance, not binding law."""
    return tier <= 8


def compare(left_tier: int, right_tier: int) -> int:
    """Return -1 when ``left`` outranks ``right``, 1 when it is outranked, 0 when equal."""
    if left_tier == right_tier:
        return 0
    return -1 if left_tier < right_tier else 1
