"""Tax-domain and taxpayer-type tagging.

These tags do two jobs: they let the API scope a search to a single tax
(``/api/search?domain=gtgt``) and they feed the *specificity* component of the
composite ranking score, so a VAT question prefers a VAT provision over a
generally-worded administrative rule that happens to match the wording.

Matching is on diacritic-folded text, so "gia tri gia tang" and
"gia tri gia tang" both hit regardless of how the source spelled it.
"""

from __future__ import annotations

import unicodedata

#: domain code -> (label, surface forms)
DOMAINS: dict[str, tuple[str, tuple[str, ...]]] = {
    "gtgt": (
        "Thuế giá trị gia tăng",
        ("gia tri gia tang", "gtgt", "vat", "thue suat 10%", "khau tru thue dau vao"),
    ),
    "tndn": (
        "Thuế thu nhập doanh nghiệp",
        ("thu nhap doanh nghiep", "tndn", "uu dai thue", "chi phi duoc tru", "lo ket chuyen"),
    ),
    "tncn": (
        "Thuế thu nhập cá nhân",
        ("thu nhap ca nhan", "tncn", "giam tru gia canh", "nguoi phu thuoc", "tien luong tien cong"),
    ),
    "ttdb": ("Thuế tiêu thụ đặc biệt", ("tieu thu dac biet", "ttdb")),
    "xnk": (
        "Thuế xuất khẩu, nhập khẩu",
        ("xuat khau", "nhap khau", "thue quan", "hai quan", "bieu thue nhap khau"),
    ),
    "tnmt": ("Thuế bảo vệ môi trường, tài nguyên", ("bao ve moi truong", "tai nguyen")),
    "sdd": (
        "Thuế, phí về đất",
        ("su dung dat", "tien thue dat", "le phi truoc ba", "thue nha dat"),
    ),
    "hoa_don": (
        "Hóa đơn, chứng từ",
        ("hoa don", "chung tu", "hoa don dien tu", "may tinh tien"),
    ),
    "quan_ly_thue": (
        "Quản lý thuế",
        (
            "quan ly thue",
            "khai thue",
            "nop thue",
            "hoan thue",
            "quyet toan thue",
            "an dinh thue",
            "cuong che",
            "thanh tra thue",
            "ma so thue",
        ),
    ),
}

TAXPAYERS: dict[str, tuple[str, ...]] = {
    "doanh_nghiep": ("doanh nghiep", "cong ty", "to chuc kinh te", "phap nhan"),
    "ho_kinh_doanh": ("ho kinh doanh", "ho, ca nhan kinh doanh", "kinh doanh ca the"),
    "ca_nhan": ("ca nhan", "nguoi nop thue la ca nhan", "nguoi lao dong"),
    "nha_thau_nuoc_ngoai": ("nha thau nuoc ngoai", "nha thau phu nuoc ngoai", "to chuc nuoc ngoai"),
    "don_vi_su_nghiep": ("don vi su nghiep", "co quan nha nuoc", "to chuc phi loi nhuan"),
}


def fold(text: str) -> str:
    """Lowercase and strip Vietnamese diacritics."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d")


def classify_domains(text: str, limit: int = 3) -> list[str]:
    """Return the tax domains a text is about, most-evidenced first."""
    folded = fold(text)
    if not folded:
        return []
    scored: list[tuple[int, str]] = []
    for code, (_label, terms) in DOMAINS.items():
        hits = sum(folded.count(term) for term in terms)
        if hits:
            scored.append((hits, code))
    scored.sort(reverse=True)
    return [code for _hits, code in scored[:limit]]


def classify_taxpayers(text: str, limit: int = 3) -> list[str]:
    folded = fold(text)
    if not folded:
        return []
    scored: list[tuple[int, str]] = []
    for code, terms in TAXPAYERS.items():
        hits = sum(folded.count(term) for term in terms)
        if hits:
            scored.append((hits, code))
    scored.sort(reverse=True)
    return [code for _hits, code in scored[:limit]]


def domain_label(code: str) -> str:
    entry = DOMAINS.get(code)
    return entry[0] if entry else code


def specificity_score(chunk_domains: list[str], query_domains: list[str]) -> float:
    """How well a provision's subject matches the question's subject.

    A provision tagged with exactly the asked-about tax scores 1.0; an untagged
    general provision scores 0.5 (neutral, not penalised); a provision about a
    different tax scores 0.
    """
    if not query_domains:
        return 0.5
    if not chunk_domains:
        return 0.5
    overlap = set(chunk_domains) & set(query_domains)
    if not overlap:
        return 0.0
    # Reward a narrow, on-topic provision over one tagged with everything.
    return min(1.0, len(overlap) / len(set(chunk_domains)))
