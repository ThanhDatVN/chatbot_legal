"""Five hand-transcribed OCR excerpts across distinct pilot documents.

This is a diagnostic sample, not an unbiased estimate of corpus-wide accuracy.
"""

from __future__ import annotations

import json

from pilot.collect import OUT
from pilot.evaluate_ocr import distance, normalize


SAMPLES = [
    {
        "document_id": "45_2019_qh14", "page": 42,
        "start": "Điều 113.", "end": "b)",
        "reference": """Điều 113. Nghỉ hằng năm
1. Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động
thì được nghỉ hằng năm, hưởng nguyên lương theo hợp đồng lao động như sau:
a) 12 ngày làm việc đối với người làm công việc trong điều kiện bình thường;""",
    },
    {
        "document_id": "145_2020_nd_cp", "page": 1,
        "start": "Điều 1.", "end": "2. Hợp đồng",
        "reference": """Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết và hướng dẫn thi hành một số nội dung
về điều kiện lao động và quan hệ lao động theo các điều, khoản sau đây của
Bộ luật Lao động:
1. Quản lý lao động theo khoản 3 Điều 12.""",
    },
    {
        "document_id": "293_2025_nd_cp", "page": 1,
        "start": "Điều 1.", "end": "Điều 2.",
        "reference": """Điều 1. Phạm vi điều chỉnh
Nghị định này quy định mức lương tối thiểu tháng và mức lương tối thiểu
giờ áp dụng đối với người lao động làm việc theo hợp đồng lao động.""",
    },
    {
        "document_id": "18_2026_vbhn_vpqh", "page": 2,
        "start": "Điều 2.", "end": "4. Cơ quan",
        "reference": """Điều 2. Đối tượng áp dụng
1. Người lao động, người học nghề, người tập nghề và người làm việc không
có quan hệ lao động.
2. Người sử dụng lao động.
3. Người lao động nước ngoài làm việc tại Việt Nam.""",
    },
    {
        "document_id": "152_2020_nd_cp", "page": 2,
        "start": "Điều 2.", "end": "c) Thực hiện",
        "reference": """Điều 2. Đối tượng áp dụng
1. Lao động là công dân nước ngoài vào làm việc tại Việt Nam (sau đây
viết tắt là người lao động nước ngoài) theo các hình thức sau đây:
a) Thực hiện hợp đồng lao động;
b) Di chuyển trong nội bộ doanh nghiệp;""",
    },
]


def excerpt(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise ValueError(f"Start marker missing: {start_marker}")
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        raise ValueError(f"End marker missing: {end_marker}")
    return text[start:end]


def main() -> None:
    results = []
    total_chars = total_char_errors = total_words = total_word_errors = 0
    for sample in SAMPLES:
        path = OUT / "ocr_pages" / f"{sample['document_id']}.jsonl"
        pages = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        prediction = normalize(excerpt(
            pages[sample["page"] - 1]["normalized_text"], sample["start"], sample["end"]
        ))
        gold = normalize(sample["reference"])
        char_errors = distance(gold, prediction)
        word_errors = distance(gold.split(), prediction.split())
        results.append({
            "document_id": sample["document_id"], "page": sample["page"],
            "reference_chars": len(gold), "reference_words": len(gold.split()),
            "character_error_rate": round(char_errors / len(gold), 4),
            "word_error_rate": round(word_errors / len(gold.split()), 4),
            "method": "hand transcription from source PDF image, NFC/lowercase/remove punctuation/collapse whitespace",
        })
        total_chars += len(gold)
        total_char_errors += char_errors
        total_words += len(gold.split())
        total_word_errors += word_errors
    output = {
        "sample_count": len(results), "samples": results,
        "pooled_reference_chars": total_chars,
        "pooled_reference_words": total_words,
        "pooled_character_error_rate": round(total_char_errors / total_chars, 4),
        "pooled_word_error_rate": round(total_word_errors / total_words, 4),
        "limitations": "Five deliberately selected short passages; not a random or clause-level corpus estimate.",
    }
    (OUT / "data_quality_metrics.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
