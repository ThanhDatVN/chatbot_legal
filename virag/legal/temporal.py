"""Temporal reasoning: which version of the law applied when.

The failure this module exists to prevent, in one line:

    User asks in 2026 about a 2021 transaction -> retriever returns the 2026
    rule -> the model cites a real document that did not apply.

Everything here works on ISO ``YYYY-MM-DD`` strings.  Vietnamese source
metadata uses ``DD-MM-YYYY`` and prose uses "ngay 08 thang 8 nam 2026", so
``parse_vn_date`` normalises both.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Literal

from virag.schemas import LegalStatus, TemporalContext

_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DMY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_YMD = re.compile(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b")
_VN_LONG = re.compile(r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE)
_VN_MONTH_YEAR = re.compile(r"tháng\s+(\d{1,2})\s*[/,]?\s*(?:năm\s+)?(\d{4})", re.IGNORECASE)
_VN_QUARTER = re.compile(r"quý\s+([1-4IViv]+)\s*[/,]?\s*(?:năm\s+)?(\d{4})", re.IGNORECASE)
_VN_YEAR = re.compile(r"\bnăm\s+(\d{4})\b", re.IGNORECASE)
_BARE_YEAR = re.compile(r"\b(19|20)(\d{2})\b")

_QUARTER_MAP = {"1": 1, "2": 2, "3": 3, "4": 4, "i": 1, "ii": 2, "iii": 3, "iv": 4}

# Phrases that make a question date-sensitive even without a date in it.
_TEMPORAL_TRIGGERS = (
    "năm ngoái",
    "năm trước",
    "năm nay",
    "hiện nay",
    "hiện hành",
    "trước đây",
    "tại thời điểm",
    "thời điểm phát sinh",
    "kỳ tính thuế",
    "quyết toán",
    "hồi tố",
    "áp dụng từ",
    "còn hiệu lực",
    "hết hiệu lực",
    "đã sửa đổi",
    "mới nhất",
    "thay đổi gì",
)

# Question shapes where getting the date wrong changes the answer.
_RATE_OR_OBLIGATION = (
    "thuế suất",
    "mức thuế",
    "tỷ lệ",
    "hạn nộp",
    "thời hạn",
    "mức giảm trừ",
    "ngưỡng",
    "doanh thu",
    "miễn thuế",
    "được trừ",
    "phải nộp",
)


def today_iso() -> str:
    return date.today().isoformat()


def _safe_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_vn_date(value: str | None) -> str | None:
    """Parse a Vietnamese date string into ISO ``YYYY-MM-DD``.

    Accepts ``08-08-2026``, ``08/08/2026``, ``2026-08-08`` and
    ``ngay 08 thang 8 nam 2026``.  Returns None when nothing parses.
    """
    if not value:
        return None
    text = value.strip()

    if _ISO.match(text):
        return text

    match = _VN_LONG.search(text)
    if match:
        return _safe_date(int(match.group(3)), int(match.group(2)), int(match.group(1)))

    match = _YMD.search(text)
    if match:
        return _safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    match = _DMY.search(text)
    if match:
        first, second, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        # Vietnamese official metadata is day-first; fall back to month-first
        # only when the first field cannot be a day.
        iso = _safe_date(year, second, first)
        return iso or _safe_date(year, first, second)

    return None


#: Values the portal puts in a date field that are not dates.  Measured on the
#: corpus: 152 of 819 documents carry the literal section label "Công báo"
#: (D-13).  Anything that is not a recognisable date is malformed, but these are
#: listed so the data-quality report can name the known offenders.
KNOWN_NON_DATE_LABELS = ("công báo", "chưa xác định", "không xác định", "n/a", "-")

DateQuality = Literal["valid", "malformed", "absent"]


def classify_portal_date(value: str | None) -> tuple[str | None, DateQuality]:
    """Split a portal date field into ``(iso_date, quality)``.

    Never test a date field for truthiness.  The corpus puts the literal string
    ``"Công báo"`` in ``effective_date`` on 152 documents; ``if value:`` treats
    that as a present date and silently reports the corpus as far more complete
    than it is.  This function forces the caller to distinguish:

    ``valid``     - parsed to an ISO date
    ``malformed`` - a non-empty value that is not a date (must be reported)
    ``absent``    - genuinely missing
    """
    if value is None or not str(value).strip():
        return None, "absent"
    parsed = parse_vn_date(str(value))
    if parsed:
        return parsed, "valid"
    return None, "malformed"


def extract_event_date(question: str, today: str | None = None) -> TemporalContext:
    """Work out the date the question is *about*.

    Precedence: an explicit date, then a month/quarter/year, then a relative
    expression, then the default.  Anything below "explicit" is recorded so the
    UI and the eval can see how the date was obtained.
    """
    today = today or today_iso()
    today_date = date.fromisoformat(today)
    text = question.strip()

    explicit = parse_vn_date(text)
    if explicit:
        return TemporalContext(as_of_date=explicit, source="explicit", raw_expression=text)

    match = _VN_QUARTER.search(text)
    if match:
        quarter = _QUARTER_MAP.get(match.group(1).lower(), 1)
        year = int(match.group(2))
        # Mid-quarter is the least surprising representative date.
        iso = _safe_date(year, quarter * 3 - 1, 15)
        if iso:
            return TemporalContext(iso, "inferred", match.group(0))

    match = _VN_MONTH_YEAR.search(text)
    if match:
        iso = _safe_date(int(match.group(2)), int(match.group(1)), 15)
        if iso:
            return TemporalContext(iso, "inferred", match.group(0))

    match = _VN_YEAR.search(text) or _BARE_YEAR.search(text)
    if match:
        year = int(match.group(0)[-4:])
        if 1990 <= year <= today_date.year + 5:
            # Mid-year keeps us inside the year whichever rule changed when.
            return TemporalContext(f"{year}-06-30", "inferred", match.group(0))

    lowered = text.lower()
    if "năm ngoái" in lowered or "năm trước" in lowered:
        return TemporalContext(f"{today_date.year - 1}-06-30", "inferred", "năm ngoái")
    if "năm nay" in lowered or "hiện nay" in lowered or "hiện hành" in lowered:
        return TemporalContext(today, "inferred", "năm nay")

    return TemporalContext(
        as_of_date=today,
        source="default",
        raw_expression=None,
        needs_clarification=is_temporally_sensitive(question),
    )


def is_temporally_sensitive(question: str) -> bool:
    """True when answering without a date risks citing the wrong version."""
    lowered = question.lower()
    if any(trigger in lowered for trigger in _TEMPORAL_TRIGGERS):
        return True
    return any(term in lowered for term in _RATE_OR_OBLIGATION)


# ---------------------------------------------------------------------------
# Validity
# ---------------------------------------------------------------------------


def in_force(effective_from: str | None, effective_to: str | None, as_of: str) -> bool:
    """Whether a provision was in force on ``as_of``.

    An unknown start date is treated as in force: the corpus has documents
    whose effective date is still under gazette verification, and dropping them
    would silently shrink recall.  The uncertainty surfaces through
    ``validity_score`` instead.
    """
    if effective_from and as_of < effective_from:
        return False
    # The two guards are deliberately symmetric - one per validity bound.
    # Collapsing only the second one (SIM103) would hide that symmetry.
    if effective_to and as_of > effective_to:  # noqa: SIM103
        return False
    return True


def validity_score(effective_from: str | None, effective_to: str | None, as_of: str) -> float:
    """Graded temporal fitness in [0, 1].

    1.0  - in force on the date, both bounds known.
    0.7  - in force but a bound is unknown.
    0.25 - out of force but adjacent (within a year), which is often the
           amended predecessor the user actually wants to compare against.
    0.0  - far out of force.
    """
    if not in_force(effective_from, effective_to, as_of):
        # Measure adjacency from the bound that was actually violated.  For an
        # expired provision that is ``effective_to``; taking ``effective_from``
        # instead makes every long-lived instrument look distant the moment it
        # expires, and hides the amended predecessor the user often wants.
        if effective_to and as_of > effective_to:
            reference = effective_to
        elif effective_from and as_of < effective_from:
            reference = effective_from
        else:
            reference = effective_from or effective_to
        if not reference:
            return 0.3
        try:
            delta = abs((date.fromisoformat(as_of) - date.fromisoformat(reference)).days)
        except ValueError:
            return 0.0
        return 0.25 if delta <= 365 else 0.0

    if effective_from and effective_to:
        return 1.0
    if effective_from or effective_to:
        return 0.7
    return 0.5


def compute_status(
    effective_from: str | None,
    effective_to: str | None,
    as_of: str,
    *,
    amended: bool = False,
    repealed_parts: bool = False,
    replaced: bool = False,
) -> LegalStatus:
    """Derive a clause-level status for a given observation date."""
    if replaced:
        return "REPLACED"
    if effective_from and as_of < effective_from:
        return "NOT_YET_EFFECTIVE"
    if effective_to and as_of > effective_to:
        return "EXPIRED"
    if repealed_parts:
        return "PARTIALLY_REPEALED"
    if amended:
        return "PARTIALLY_AMENDED"
    if effective_from or effective_to:
        return "ACTIVE"
    return "UNKNOWN"


def shift_days(iso_date: str, days: int) -> str:
    return (date.fromisoformat(iso_date) + timedelta(days=days)).isoformat()


def year_of(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        return datetime.fromisoformat(iso_date).year
    except ValueError:
        return None
