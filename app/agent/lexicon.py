"""Everyday Vietnamese → statutory vocabulary for search queries.

People ask "công ty có được giữ bằng đại học không", the Labour Code says "người sử dụng lao động … giữ bản chính
… văn bằng". BM25 misses the statutory words and the cross-encoder scores the right article lower than the
threshold calibrated on statute-like questions. `expand_query` appends the statutory term after the question
when an everyday term is present; the question text itself is never changed, so nothing the user wrote is lost
and the validator still checks quotes against the sources only.

The table is general domain vocabulary, not tied to evaluation questions; add entries in the same spirit.
"""

from __future__ import annotations

import re
import unicodedata

FAMILY = r"(bố|mẹ|cha|má|ba|ông|bà|vợ|chồng|con|anh|chị|em)"

LEXICON: list[tuple[str, str]] = [
    (r"\btiếng\b", "giờ"),
    (r"\b(công ty|sếp|chủ doanh nghiệp|xí nghiệp|nhà máy|cơ sở)\b", "người sử dụng lao động"),
    (r"\b(nhân viên|công nhân|người làm công|người đi làm)\b", "người lao động"),
    (r"\bnghỉ phép\b", "nghỉ hằng năm"),
    (r"\b(nghỉ ngang|xin nghỉ việc|xin thôi việc|muốn nghỉ việc|bỏ việc)\b",
     "người lao động đơn phương chấm dứt hợp đồng lao động"),
    (r"\b(đuổi việc|cho thôi việc|chấm dứt hợp đồng với nhân viên)\b|\bcho\b[^,.?]{0,40}\bnghỉ việc\b",
     "người sử dụng lao động đơn phương chấm dứt hợp đồng lao động"),
    (r"\b(cắt giảm nhân sự|cắt giảm lao động|tái cơ cấu|giảm biên chế)\b",
     "thay đổi cơ cấu, công nghệ, lý do kinh tế mất việc làm"),
    (r"\b(lấy vợ|lấy chồng|cưới vợ|cưới chồng|đám cưới|cưới)\b", "kết hôn"),
    (rf"(qua đời|từ trần|\b{FAMILY}\b[^,.?]{{0,20}}\bmất\b(?!\s*việc))", "chết"),
    (r"\b(ca đêm|làm đêm|trực đêm)\b", "làm việc vào ban đêm"),
    (r"\bnghỉ trưa\b", "nghỉ giữa giờ"),
    (r"\b(đàn ông|nam giới)\b", "lao động nam"),
    (r"\b(phụ nữ|chị em|nữ giới)\b", "lao động nữ"),
    (r"\bcon (nhỏ )?dưới (1|một) tuổi\b", "nuôi con dưới 12 tháng tuổi"),
    (r"\b(đặt cọc|tiền cọc|thế chấp)\b", "biện pháp bảo đảm bằng tiền hoặc tài sản"),
    (r"\b(thưởng tết|thưởng cuối năm|lương tháng 13|tháng lương thứ 13)\b", "thưởng, quy chế thưởng"),
    (r"\b(nghỉ không phép|tự ý nghỉ|nghỉ không xin phép|nghỉ không báo)\b", "tự ý bỏ việc"),
    (r"\b(thời vụ|ngắn hạn)\b", "hợp đồng lao động xác định thời hạn, hình thức hợp đồng"),
    (r"\b(trừ lương|trừ vào lương|trừ tiền lương)\b", "khấu trừ tiền lương"),
    (r"\b(phạt tiền|phạt lương|bị phạt)\b", "phạt tiền, cắt lương, xử lý kỷ luật lao động"),
    (r"\bgiữ (bằng|căn cước|cccd|chứng minh|giấy tờ|hộ chiếu|văn bằng)",
     "giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ"),
    (r"\b(bằng đại học|bằng cấp|bằng tốt nghiệp)\b", "văn bằng, chứng chỉ"),
    (r"\b(căn cước|cccd|chứng minh nhân dân|cmnd)\b", "giấy tờ tùy thân"),
    (r"\b(tăng ca|làm ngoài giờ|làm thêm)\b", "làm thêm giờ"),
    (r"\b(chủ nhật|cuối tuần)\b", "ngày nghỉ hằng tuần"),
    (r"\b(có bầu|có thai|bầu bí)\b", "mang thai"),
    (r"\b(độ tuổi|bao nhiêu tuổi thì được (đi )?làm)\b", "độ tuổi lao động tối thiểu"),
    (r"\b(trẻ em|vị thành niên|chưa đủ 18 tuổi)\b", "người chưa thành niên"),
    (r"\b(người nước ngoài|chuyên gia nước ngoài|kỹ sư người nước ngoài|expat)\b", "người lao động nước ngoài"),
    (r"\bnghỉ hưu sớm\b", "nghỉ hưu ở tuổi thấp hơn"),
    (r"\b(công ty dịch vụ|công ty cung ứng nhân lực|cho thuê nhân viên)\b", "cho thuê lại lao động"),
    (r"\b(lương cơ bản|lương sàn)\b", "mức lương tối thiểu"),
    (r"\bnghỉ ốm\b", "ốm đau"),
    (r"\b(bhxh|sổ bảo hiểm)\b", "bảo hiểm xã hội"),
    (r"\b(nghỉ có lương|nghỉ hưởng lương)\b", "nghỉ việc riêng hưởng nguyên lương"),
    (r"\b(hỏng|làm hư|làm mất) (máy|thiết bị|dụng cụ|tài sản)", "bồi thường thiệt hại, làm hư hỏng dụng cụ, thiết bị"),
]

_COMPILED = [(re.compile(pattern), term) for pattern, term in LEXICON]


def expand_query(question: str) -> str:
    """The question followed by the statutory terms its everyday wording maps to (deduplicated)."""
    lowered = unicodedata.normalize("NFC", question).lower()
    extra: list[str] = []
    for pattern, term in _COMPILED:
        if pattern.search(lowered) and term not in extra and term not in lowered:
            extra.append(term)
    return f"{question} ({'; '.join(extra)})" if extra else question
