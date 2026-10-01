"""Held-out paraphrase set: 40 questions in everyday wording, written before the post-v2 fixes.

    python -m evaluation.heldout_v1      # validates against the snapshot and writes data/eval/questions_heldout_v1.jsonl

Dev and test of dataset v2 reuse the wording of the legal text and some of their failures were looked at while
improving the system. These questions were written on 2026-10-01 from the source text, before any of those
fixes, phrased the way an employee or HR officer would ask (công ty, nhân viên, nghỉ phép, Chủ nhật…), and are
never used for tuning: they only measure whether improvements generalise. Gold evidence and required facts are
checked against the snapshot exactly as in v2. Labels are AI-drafted and unreviewed.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.dataset_v2 import SNAPSHOT, _section_texts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval" / "questions_heldout_v1.jsonl"
V, W = "18_2026_vbhn_vpqh", "293_2025_nd_cp"
D145, D135, D219 = "145_2020_nd_cp", "135_2020_nd_cp", "219_2025_nd_cp"


def g(*articles, doc=V):
    return [{"document_id": doc, "section": a if isinstance(a, str) else f"Điều {a}"} for a in articles]


ANSWERABLE = [
    ("Công ty bắt tôi thử việc 3 tháng cho vị trí kỹ sư tốt nghiệp đại học, như vậy có đúng luật không?", g(25),
     ["60 ngày"]),
    ("Đang thử việc thì công ty được trả lương thấp nhất là bao nhiêu?", g(26), ["85%"]),
    ("Tôi làm ca đêm thì được nghỉ giữa ca ít nhất mấy phút?", g(109) + g(64, doc=D145), ["45 phút"]),
    ("Một tuần công ty được bắt nhân viên làm tối đa bao nhiêu tiếng?", g(105), ["48 giờ"]),
    ("Đi làm thêm vào ngày nghỉ hằng tuần như Chủ nhật thì được trả ít nhất bao nhiêu phần trăm lương?",
     g(98) + g(55, doc=D145), ["200%"]),
    ("Làm đủ một năm thì tôi được nghỉ phép năm mấy ngày?", g(113), ["12 ngày"]),
    ("Tôi cưới vợ thì được nghỉ mấy ngày mà vẫn có lương?", g(115), ["03 ngày"]),
    ("Bố đẻ của tôi mất thì tôi được nghỉ mấy ngày hưởng nguyên lương?", g(115), ["03 ngày"]),
    ("Tôi ký hợp đồng không thời hạn, giờ muốn nghỉ việc thì phải báo trước bao lâu?", g(35), ["45 ngày"]),
    ("Công ty đòi giữ bằng đại học bản gốc của nhân viên mới có được không?", g(17), ["văn bằng, chứng chỉ"]),
    ("Mỗi tháng công ty được trừ vào lương của tôi tối đa bao nhiêu?", g(102), ["30%"]),
    ("Nghỉ việc rồi thì công ty phải trả hết tiền lương, trợ cấp cho tôi trong bao lâu?", g(48),
     ["14 ngày làm việc"]),
    ("Làm ở công ty 6 năm rồi nghỉ việc thì trợ cấp thôi việc được tính thế nào?", g(46) + g(8, doc=D145),
     ["một nửa tháng tiền lương"]),
    ("Vợ tôi sinh con đầu lòng thì được nghỉ thai sản bao lâu?", g(139), ["06 tháng"]),
    ("Lương tối thiểu vùng I hiện nay là bao nhiêu tiền một tháng?", g(3, doc=W), ["5.310.000"]),
    ("Làm việc theo giờ ở vùng III thì lương tối thiểu một giờ là bao nhiêu?", g(3, doc=W), ["20.000"]),
    ("Năm 2030 thì lao động nữ bao nhiêu tuổi được nghỉ hưu?", g(4, "Phụ lục I", doc=D135) + g(169),
     ["58 tuổi 4 tháng"]),
    ("Công ty có từ bao nhiêu nhân viên thì nội quy phải làm bằng văn bản?", g(118) + g(69, doc=D145),
     ["10 người"]),
    ("Nhân viên vi phạm kỷ luật thì công ty có thể áp dụng những hình thức nào?", g(124), ["Sa thải"]),
    ("Công ty phạt tiền nhân viên đi làm muộn thay cho kỷ luật thì có hợp pháp không?", g(127),
     ["Phạt tiền, cắt lương"]),
    ("Giấy phép lao động của chuyên gia nước ngoài có thời hạn dài nhất là bao lâu?", g(155) + g(21, doc=D219),
     ["02 năm"]),
    ("Xin giấy phép lao động cho kỹ sư người nước ngoài thì cần chuẩn bị những giấy tờ gì?", g(18, doc=D219),
     ["Hộ chiếu còn thời hạn", "02 ảnh màu"]),
    ("Phi công muốn nghỉ việc thì phải báo trước cho hãng bao nhiêu ngày?", g(7, doc=D145), ["120 ngày"]),
    ("Công ty mới thành lập phải lập sổ quản lý lao động trong thời hạn bao lâu?", g(3, doc=D145), ["30 ngày"]),
    ("Người giúp việc gia đình được nghỉ ngơi trong ngày ít nhất bao nhiêu tiếng?", g(89, doc=D145),
     ["8 giờ", "6 giờ liên tục"]),
    ("Công ty cho thuê lại lao động có được cho thuê người làm lái xe không?", g("Phụ lục II", 30, doc=D145),
     ["Lái xe"]),
    ("Trẻ chưa đủ 15 tuổi đi làm thì mỗi ngày được làm tối đa mấy tiếng?", g(146), ["04 giờ"]),
    ("Công ty tổ chức làm thêm trên 200 giờ một năm thì phải thông báo chậm nhất sau bao nhiêu ngày?",
     g(62, doc=D145), ["15 ngày"]),
]

SUPERSEDED = "superseded_by_amendment"
REFUSALS = [
    ("Bây giờ muốn xin giấy phép hoạt động cho thuê lại lao động thì làm thủ tục thế nào?", SUPERSEDED),
    ("Gia hạn giấy phép lao động cho nhân viên người nước ngoài thì cần nộp những giấy tờ gì?", SUPERSEDED),
    ("Công ty cho thuê lại lao động phải báo cáo tình hình hoạt động bao lâu một lần?", SUPERSEDED),
    ("Doanh nghiệp cho thuê lại lao động có phải nộp bổ sung tiền ký quỹ không, nộp khi nào?", SUPERSEDED),
    ("Những công việc khai thác than trong hầm lò nào được nghỉ hưu sớm hơn?", SUPERSEDED),
    ("Mức đóng bảo hiểm xã hội hằng tháng của người lao động là bao nhiêu phần trăm lương?", "insufficient_evidence"),
    ("Nghỉ ốm thì được bảo hiểm xã hội trả bao nhiêu phần trăm lương?", "insufficient_evidence"),
    ("Công ty chậm đóng bảo hiểm xã hội cho nhân viên thì bị phạt bao nhiêu?", "insufficient_evidence"),
    ("Mức hưởng trợ cấp thất nghiệp mỗi tháng được tính như thế nào?", "insufficient_evidence"),
    ("Lương tối thiểu vùng I năm 2024 là bao nhiêu?", "historical_not_supported"),
    ("Năm sau lương tối thiểu vùng có tăng không?", "unsupported_prediction"),
    ("Tiền làm thêm giờ có phải chịu thuế thu nhập cá nhân không?", "out_of_scope"),
]


def build() -> list[dict]:
    rows = []
    for i, (q, gold, facts) in enumerate(ANSWERABLE, 1):
        rows.append({"id": f"hp_{i:02d}", "type": "direct", "split": "heldout", "question": q,
                     "should_refuse": False, "acceptable_decisions": ["ANSWER", "PARTIAL"], "gold": gold,
                     "gold_required": gold[:1], "required_facts": facts, "must_not_contain": [],
                     "reference_answer": None, "expected_reason": None})
    for i, (q, reason) in enumerate(REFUSALS, len(ANSWERABLE) + 1):
        kind = "out_of_scope" if reason == "out_of_scope" else "unanswerable"
        rows.append({"id": f"hp_{i:02d}", "type": kind, "split": "heldout", "question": q, "should_refuse": True,
                     "acceptable_decisions": ["REFUSE"], "gold": [], "gold_required": [], "required_facts": [],
                     "must_not_contain": [], "reference_answer": None, "expected_reason": reason})
    for r in rows:
        r.update({"as_of_date": "2026-10-01", "annotator": "AI draft (Claude)", "reviewed": False})
    return rows


def validate(rows: list[dict], snapshot_dir: Path) -> list[str]:
    texts = _section_texts(snapshot_dir)
    problems = []
    for r in rows:
        for gd in r["gold"]:
            if (gd["document_id"], gd["section"]) not in texts:
                problems.append(f"{r['id']}: gold {gd} not in snapshot")
        evidence = " ".join(texts.get((gd["document_id"], gd["section"]), "") for gd in r["gold"])
        for fact in r["required_facts"]:
            if " ".join(fact.split()).lower() not in evidence:
                problems.append(f"{r['id']}: required fact {fact!r} not in its gold sections")
    if len({r["question"] for r in rows}) != len(rows):
        problems.append("duplicate questions")
    return problems


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
