"""Paraphrase development set: everyday-wording questions used to diagnose and tune paraphrase robustness.

    python -m evaluation.paraphrase_dev_v1   # writes data/eval/questions_paraphrase_dev_v1.jsonl

Companion of the held-out set (evaluation/heldout_v1.py): same style, different questions. Failures are
analysed and thresholds chosen here, never on the held-out set. Labels are AI-drafted and unreviewed.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.dataset_v2 import SNAPSHOT
from evaluation.heldout_v1 import D135, D145, W, g, validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval" / "questions_paraphrase_dev_v1.jsonl"

ANSWERABLE = [
    ("Sếp có được bắt tôi làm thêm quá 40 tiếng trong một tháng không?", g(107), ["40 giờ"]),
    ("Nghỉ Tết Âm lịch người lao động được nghỉ mấy ngày?", g(112), ["05 ngày"]),
    ("Con tôi lấy vợ thì tôi được nghỉ mấy ngày có lương?", g(115), ["01 ngày"]),
    ("Ông nội tôi mất thì tôi có được nghỉ làm không, có được trả lương không?", g(115), ["01 ngày"]),
    ("Tôi làm hợp đồng 6 tháng, muốn nghỉ ngang thì phải báo trước mấy ngày?", g(35), ["03 ngày làm việc"]),
    ("Công ty muốn cho nhân viên hợp đồng không thời hạn nghỉ việc thì phải báo trước bao lâu?", g(36),
     ["45 ngày"]),
    ("Công ty cắt giảm nhân sự vì tái cơ cấu thì nhân viên bị mất việc được trợ cấp ít nhất bao nhiêu?", g(47),
     ["02 tháng tiền lương"]),
    ("Làm thời vụ 2 tuần thì có cần ký hợp đồng bằng văn bản không?", g(14), ["dưới 01 tháng"]),
    ("Chị em đang nuôi con nhỏ dưới 1 tuổi thì mỗi ngày được nghỉ bao lâu trong giờ làm?", g(137), ["60 phút"]),
    ("Làm giờ hành chính 8 tiếng thì được nghỉ trưa giữa giờ ít nhất bao lâu?", g(109), ["30 phút"]),
    ("Bao nhiêu tuổi thì được đi làm và ký hợp đồng lao động?", g(3), ["đủ 15 tuổi"]),
    ("Nhân viên tự ý nghỉ không phép mấy ngày thì công ty được sa thải?", g(125), ["05 ngày cộng dồn"]),
    ("Thưởng Tết cuối năm có phải khoản công ty bắt buộc trả không?", g(104), ["kết quả sản xuất, kinh doanh"]),
    ("Công ty dịch vụ được cho thuê một nhân viên sang công ty khác làm tối đa bao lâu?", g(53), ["12 tháng"]),
    ("Lương tối thiểu vùng II theo tháng hiện nay là bao nhiêu?", g(3, doc=W), ["4.730.000"]),
    ("Đàn ông nghỉ hưu năm 2027 thì phải đủ bao nhiêu tuổi?", g(4, "Phụ lục I", doc=D135) + g(169),
     ["61 tuổi 9 tháng"]),
    ("Công ty có được bắt nhân viên khuyết tật nặng làm ca đêm không?", g(160), ["làm việc vào ban đêm"]),
    ("Một ngày làm việc bình thường tối đa bao nhiêu tiếng?", g(105), ["08 giờ"]),
    ("Công ty có được bắt nhân viên đặt cọc tiền khi ký hợp đồng không?", g(17), ["biện pháp bảo đảm bằng tiền"]),
    ("Nhân viên làm hư hỏng máy móc của công ty thì thời hiệu xử lý bồi thường là bao lâu?", g(72, doc=D145),
     ["06 tháng"]),
    ("Doanh nghiệp được thuê người lao động của công ty cho thuê lại trong những trường hợp nào?", g(53),
     ["Đáp ứng tạm thời"]),
    ("Nghỉ việc rồi thì công ty có trách nhiệm gì với thời gian đóng bảo hiểm xã hội của tôi?", g(48),
     ["xác nhận thời gian đóng bảo hiểm xã hội"]),
]

SUPERSEDED = "superseded_by_amendment"
REFUSALS = [
    ("Vợ sinh con thì chồng được nghỉ mấy ngày hưởng chế độ?", "insufficient_evidence"),
    ("Kinh phí công đoàn công ty phải đóng bằng bao nhiêu phần trăm quỹ lương?", "insufficient_evidence"),
    ("Hồ sơ xin cấp lại giấy phép hoạt động cho thuê lại lao động gồm những gì?", SUPERSEDED),
    ("Doanh nghiệp cho thuê lại lao động phải ký quỹ ở đâu và quản lý tiền ký quỹ thế nào?", SUPERSEDED),
    ("Năm 2025 lương tối thiểu vùng I là bao nhiêu?", "historical_not_supported"),
]


def build() -> list[dict]:
    rows = []
    for i, (q, gold, facts) in enumerate(ANSWERABLE, 1):
        rows.append({"id": f"pd_{i:02d}", "type": "direct", "split": "pdev", "question": q, "should_refuse": False,
                     "acceptable_decisions": ["ANSWER", "PARTIAL"], "gold": gold, "gold_required": gold[:1],
                     "required_facts": facts, "must_not_contain": [], "reference_answer": None,
                     "expected_reason": None})
    for i, (q, reason) in enumerate(REFUSALS, len(ANSWERABLE) + 1):
        rows.append({"id": f"pd_{i:02d}", "type": "unanswerable", "split": "pdev", "question": q,
                     "should_refuse": True, "acceptable_decisions": ["REFUSE"], "gold": [], "gold_required": [],
                     "required_facts": [], "must_not_contain": [], "reference_answer": None,
                     "expected_reason": reason})
    for r in rows:
        r.update({"as_of_date": "2026-10-01", "annotator": "AI draft (Claude)", "reviewed": False})
    return rows


def main() -> None:
    rows = build()
    problems = validate(rows, SNAPSHOT)
    if problems:
        raise SystemExit("\n".join(problems))
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} questions to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
