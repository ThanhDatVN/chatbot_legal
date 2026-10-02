"""Held-out paraphrase set v2: 40 new everyday-wording questions, written before the LLM verifier existed.

    python -m evaluation.heldout_v2      # validates against the snapshot and writes data/eval/questions_heldout_v2.jsonl

Held-out v1 was spent measuring the query-expansion fixes. These questions were written on 2026-10-02 from the
source text, before the gray-zone LLM verifier was implemented, and are never used for tuning or diagnosis.
Same conventions and validation as v1; AI-drafted and unreviewed.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.dataset_v2 import SNAPSHOT
from evaluation.heldout_v1 import D135, D145, V, W, g, validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval" / "questions_heldout_v2.jsonl"
D129 = "129_2025_nd_cp"

ANSWERABLE = [
    ("Hợp đồng lao động bắt buộc phải ghi những nội dung gì?", g(21), ["Tên, địa chỉ của người sử dụng lao động"]),
    ("Công ty có được trả lương cho nhân viên qua người khác nhận hộ không?", g(94), ["trả lương trực tiếp"]),
    ("Công ty trả lương chậm thì có phải đền bù cho nhân viên không?", g(97), ["15 ngày trở lên"]),
    ("Nghỉ việc mà chưa dùng hết ngày phép năm thì có được trả tiền không?", g(113),
     ["thanh toán tiền lương cho những ngày chưa nghỉ"]),
    ("Làm lâu năm ở một công ty thì ngày phép năm được cộng thêm thế nào?", g(114), ["05 năm"]),
    ("Sếp có được điều tôi sang làm việc khác trái với hợp đồng không, tối đa bao lâu?", g(29),
     ["60 ngày làm việc cộng dồn"]),
    ("Hợp đồng hết hạn mà tôi vẫn đi làm bình thường thì công ty phải làm gì?", g(20), ["30 ngày"]),
    ("Bị tạm đình chỉ công việc thì có được nhận lương không?", g(128), ["50% tiền lương"]),
    ("Công ty họp kỷ luật nhân viên thì có cần công đoàn tham gia không?", g(122),
     ["tổ chức đại diện người lao động tại cơ sở"]),
    ("Lỡ làm hỏng đồ của công ty giá trị nhỏ thì phải bồi thường tối đa bao nhiêu?", g(129), ["03 tháng tiền lương"]),
    ("Thuê người giúp việc nhà thì có phải ký hợp đồng giấy tờ không?", g(162) + g(89, doc=D145), ["bằng văn bản"]),
    ("Người nước ngoài muốn đi làm ở Việt Nam thì phải đủ bao nhiêu tuổi?", g(151), ["Đủ 18 tuổi"]),
    ("Lương tối thiểu vùng IV bây giờ là bao nhiêu một tháng?", g(3, doc=W), ["3.700.000"]),
    ("Công ty trong khu công nghiệp nằm vắt qua hai vùng lương thì áp lương tối thiểu vùng nào?", g(3, doc=W),
     ["mức lương tối thiểu cao nhất"]),
    ("Làm nghề nặng nhọc độc hại thì được nghỉ hưu sớm hơn tối đa mấy tuổi?", g(169) + g(5, doc=D135),
     ["05 tuổi"]),
    ("Đã đến tuổi nghỉ hưu mà công ty vẫn muốn thuê tiếp thì ký hợp đồng kiểu gì?", g(149),
     ["hợp đồng lao động xác định thời hạn"]),
    ("Người đi làm thuê qua công ty cho thuê lại lao động có bị trả lương thấp hơn nhân viên chính thức không?",
     g(56), ["không thấp hơn tiền lương"]),
    ("Bà bầu được mấy tháng thì công ty không được bắt làm đêm, tăng ca?", g(137), ["tháng thứ 07"]),
    ("Đi làm ngày lễ, Tết thì được trả lương ít nhất bao nhiêu phần trăm?", g(98), ["300%"]),
    ("Làm ca đêm thì được trả thêm ít nhất bao nhiêu phần trăm lương?", g(98), ["30%"]),
    ("Báo cáo tình hình thay đổi lao động 6 tháng đầu năm phải nộp trước ngày nào?", g(71, doc=D129),
     ["trước ngày 05 tháng 6"]),
    ("Khi có tranh chấp lao động thì cơ quan nào cử hòa giải viên?", g(75, doc=D129), ["Sở Nội vụ"]),
    ("Đang nghỉ thai sản thì công ty có được cho tôi nghỉ việc không?", g(137), ["nghỉ thai sản"]),
    ("Nghỉ làm vào ngày Tết Dương lịch thì được nghỉ mấy ngày có lương?", g(112), ["01 ngày"]),
    ("Công ty có quyền bắt nhân viên làm việc để trừ nợ không?", g(17), ["trả nợ"]),
    ("Doanh nghiệp được tạm chuyển nhân viên sang việc khác thì lương được trả thế nào?", g(29),
     ["tiền lương theo công việc mới"]),
    ("Người lao động cao tuổi đang hưởng lương hưu mà vẫn đi làm thì được hưởng thêm gì?", g(149),
     ["tiền lương"]),
    ("Công ty có bắt buộc phải trả lương đúng hạn không?", g(94), ["đúng hạn"]),
]

SUPERSEDED = "superseded_by_amendment"
REFUSALS = [
    ("Doanh nghiệp cho thuê lại lao động bị thu hồi giấy phép trong những trường hợp nào?", SUPERSEDED),
    ("Hồ sơ gia hạn giấy xác nhận không thuộc diện cấp giấy phép lao động gồm những gì?", SUPERSEDED),
    ("Sở Lao động có trách nhiệm gì trong quản lý hoạt động cho thuê lại lao động?", SUPERSEDED),
    ("Mức đóng bảo hiểm thất nghiệp hằng tháng của người lao động là bao nhiêu?", "insufficient_evidence"),
    ("Bị tai nạn lao động thì công ty phải bồi thường bao nhiêu tiền?", "insufficient_evidence"),
    ("Sau khi sinh con thì được nghỉ dưỡng sức mấy ngày?", "insufficient_evidence"),
    ("Lương hưu hằng tháng được tính bằng bao nhiêu phần trăm mức lương?", "insufficient_evidence"),
    ("Công ty không ký hợp đồng lao động bằng văn bản thì bị phạt bao nhiêu tiền?", "insufficient_evidence"),
    ("Mức lương tối thiểu vùng II năm 2023 là bao nhiêu?", "historical_not_supported"),
    ("Tuổi nghỉ hưu sẽ tăng tiếp vào năm nào?", "unsupported_prediction"),
    ("Thủ tục đăng ký hộ kinh doanh cá thể gồm những bước nào?", "out_of_scope"),
    ("Tiền thuê nhà công ty trả cho nhân viên có tính thuế thu nhập cá nhân không?", "out_of_scope"),
]


def build() -> list[dict]:
    rows = []
    for i, (q, gold, facts) in enumerate(ANSWERABLE, 1):
        rows.append({"id": f"h2_{i:02d}", "type": "direct", "split": "heldout2", "question": q,
                     "should_refuse": False, "acceptable_decisions": ["ANSWER", "PARTIAL"], "gold": gold,
                     "gold_required": gold[:1], "required_facts": facts, "must_not_contain": [],
                     "reference_answer": None, "expected_reason": None})
    for i, (q, reason) in enumerate(REFUSALS, len(ANSWERABLE) + 1):
        kind = "out_of_scope" if reason == "out_of_scope" else "unanswerable"
        rows.append({"id": f"h2_{i:02d}", "type": kind, "split": "heldout2", "question": q, "should_refuse": True,
                     "acceptable_decisions": ["REFUSE"], "gold": [], "gold_required": [], "required_facts": [],
                     "must_not_contain": [], "reference_answer": None, "expected_reason": reason})
    for r in rows:
        r.update({"as_of_date": "2026-10-02", "annotator": "AI draft (Claude)", "reviewed": False})
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
