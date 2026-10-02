"""Held-out paraphrase set v3: 54 new everyday-wording questions, written before any reranker fine-tuning.

    python -m evaluation.heldout_v3      # validates against the snapshot and writes data/eval/questions_heldout_v3.jsonl

Held-out v2 was spent measuring the qwen3:4b verifier. These questions were written on 2026-10-02 from the source
text, before the reranker fine-tuning pipeline (training/) existed, and are never used for tuning, training-data
filtering thresholds or diagnosis. Most target articles that no earlier evaluation set asks about, so the set also
measures coverage beyond the articles the policy was tuned on. Same conventions and validation as v1;
AI-drafted and unreviewed.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.dataset_v2 import SNAPSHOT
from evaluation.heldout_v1 import D145, D219, W, g, validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval" / "questions_heldout_v3.jsonl"

ANSWERABLE = [
    ("Hết thời gian thử việc thì công ty có phải báo cho tôi biết là đạt hay không đạt không?", g(27),
     ["thông báo kết quả thử việc"]),
    ("Tôi xin ứng trước một phần lương thì công ty có được tính lãi không?", g(101), ["không bị tính lãi"]),
    ("Ngày nghỉ cuối tuần trùng đúng ngày lễ thì có được nghỉ bù hôm khác không?", g(111),
     ["nghỉ bù ngày nghỉ hằng tuần vào ngày làm việc kế tiếp"]),
    ("Bị kỷ luật kéo dài thời hạn nâng lương thì bao lâu sau mới được xóa kỷ luật?", g(126), ["sau 06 tháng"]),
    ("Nội quy công ty nộp lên cơ quan lao động rồi thì bao lâu sau mới có hiệu lực?", g(121), ["15 ngày"]),
    ("Trẻ 13, 14 tuổi có được đi làm thuê không?", g(145), ["từ đủ 13 tuổi đến chưa đủ 15 tuổi"]),
    ("Thỏa ước lao động tập thể ký xong thì có giá trị trong bao lâu?", g(78), ["từ 01 năm đến 03 năm"]),
    ("Công đoàn muốn đình công thì phải báo trước cho công ty bao nhiêu ngày?", g(202), ["05 ngày làm việc"]),
    ("Những ngày nghỉ ốm có được tính vào thời gian làm việc để hưởng phép năm không?", g(65, doc=D145),
     ["cộng dồn không quá 02 tháng trong một năm"]),
    ("Hết hợp đồng thì công ty có phải báo cho tôi bằng văn bản không?", g(45), ["thông báo bằng văn bản"]),
    ("Công ty sáp nhập với công ty khác thì người lao động cũ được giải quyết thế nào?", g(43, 44),
     ["phương án sử dụng lao động"]),
    ("Người giúp việc nhà muốn nghỉ thì phải báo trước cho chủ nhà bao nhiêu ngày?", g(162), ["15 ngày"]),
    ("Công ty trả lương qua thẻ ngân hàng thì phí mở tài khoản ai trả?", g(96),
     ["phải trả các loại phí liên quan đến việc mở tài khoản"]),
    ("Mỗi lần nhận lương, công ty có phải đưa bảng chi tiết các khoản không?", g(95), ["bảng kê trả lương"]),
    ("Làm cho cai thầu mà cai thầu không trả lương thì ai phải trả?", g(100),
     ["chủ chính phải chịu trách nhiệm trả lương"]),
    ("Có trường hợp nào công ty bắt làm thêm giờ mà mình không được từ chối không?", g(108),
     ["không được từ chối"]),
    ("Không đồng ý với quyết định kỷ luật của công ty thì tôi có được khiếu nại không?", g(131),
     ["có quyền khiếu nại"]),
    ("Nghỉ thai sản xong đi làm lại thì công ty có phải giữ chỗ làm cũ cho tôi không?", g(140),
     ["bảo đảm việc làm cũ"]),
    ("Người dưới 18 tuổi có bị cấm làm những việc như bưng bê vác nặng không?", g(147),
     ["Mang, vác, nâng các vật nặng"]),
    ("Nhà thuê người giúp việc thì có phải trả tiền bảo hiểm cho họ không?", g(163),
     ["khoản tiền bảo hiểm xã hội, bảo hiểm y tế"]),
    ("Tranh chấp với công ty vì bị sa thải thì có bắt buộc phải qua hòa giải trước khi kiện ra tòa không?",
     g(188), ["không bắt buộc phải qua thủ tục hòa giải"]),
    ("Tham gia đình công thì những ngày đó có được trả lương không?", g(207), ["không được trả lương"]),
    ("Phòng vắt sữa cho lao động nữ ở công ty phải đáp ứng những yêu cầu gì?", g(76, doc=D145),
     ["không phải buồng tắm hay buồng vệ sinh"]),
    ("Nghỉ phép năm về quê xa thì tiền tàu xe đi đường ai chịu?", g(67, doc=D145) + g(113),
     ["do hai bên thỏa thuận"]),
    ("Người nước ngoài làm việc ở Việt Nam bị thu hồi giấy phép lao động trong những trường hợp nào?",
     g(30, doc=D219), ["bị khởi tố, truy cứu trách nhiệm hình sự"]),
    ("Khám sức khỏe định kỳ thì lao động nữ có được khám phụ khoa không?", g(80, doc=D145),
     ["khám chuyên khoa phụ sản"]),
    ("Đang nghỉ phép năm thì công ty có được đơn phương cho tôi nghỉ việc không?", g(37),
     ["đang nghỉ hằng năm"]),
    ("Nhân viên tự ý nghỉ ngang trái luật thì phải đền cho công ty những gì?", g(40), ["nửa tháng tiền lương"]),
    ("Một người có được ký hợp đồng làm việc cho hai công ty cùng lúc không?", g(19),
     ["nhiều hợp đồng lao động với nhiều người sử dụng lao động"]),
    ("Phụ lục hợp đồng có được dùng để kéo dài thời hạn hợp đồng không?", g(22),
     ["không được sửa đổi thời hạn của hợp đồng lao động"]),
    ("Công ty nhận người vào tập nghề thì có được thu tiền học không, tập tối đa bao lâu?", g(61),
     ["không được thu học phí", "không quá 03 tháng"]),
    ("Công ty phải cho nghỉ vì mất điện thì có được trả lương không?", g(99), ["sự cố về điện, nước"]),
    ("Làm theo ca thì giữa hai ca được nghỉ ít nhất bao nhiêu tiếng?", g(110), ["12 giờ"]),
    ("Làm bán thời gian có được đối xử như nhân viên toàn thời gian không?", g(32),
     ["bình đẳng trong thực hiện quyền và nghĩa vụ"]),
    ("Thời gian đi họp, đi tập huấn theo yêu cầu của công ty có được tính lương không?", g(58, doc=D145),
     ["Thời giờ hội họp, học tập, tập huấn"]),
    ("Bà bầu có giấy bác sĩ xác nhận đi làm tiếp sẽ hại thai thì có được nghỉ việc ngay không?", g(138),
     ["ảnh hưởng xấu tới thai nhi"]),
    ("Chủ nhà có được giữ căn cước của người giúp việc không?", g(165), ["Giữ giấy tờ tùy thân"]),
    ("Những hành vi nào bị coi là quấy rối tình dục ở chỗ làm?", g(84, doc=D145),
     ["Quấy rối tình dục bằng lời nói"]),
    ("Đang có tranh chấp chưa giải quyết xong thì công ty có được tự ý làm gì bất lợi cho tôi không?", g(186),
     ["không bên nào được hành động đơn phương"]),
    ("Làm theo giờ ở vùng IV thì lương tối thiểu một giờ là bao nhiêu?", g(3, doc=W), ["17.800"]),
]

SUPERSEDED = "superseded_by_amendment"
INSUFFICIENT = "insufficient_evidence"
REFUSALS = [
    ("Giấy phép cho thuê lại lao động sắp hết hạn thì xin gia hạn thế nào, phải nộp trước bao lâu?", SUPERSEDED),
    ("Giấy phép hoạt động cho thuê lại lao động có thời hạn tối đa bao nhiêu tháng?", SUPERSEDED),
    ("Công ty cho thuê lại lao động nợ lương người lao động thì tiền ký quỹ được trích ra trả thế nào?",
     SUPERSEDED),
    ("Đóng bảo hiểm y tế cho nhân viên thì công ty đóng bao nhiêu phần trăm?", INSUFFICIENT),
    ("Công ty không đăng ký nội quy lao động thì bị phạt bao nhiêu tiền?", INSUFFICIENT),
    ("Tiền ăn giữa ca mỗi ngày công ty phải chi tối thiểu bao nhiêu?", INSUFFICIENT),
    ("Rút bảo hiểm xã hội một lần thì cần những giấy tờ gì?", INSUFFICIENT),
    ("Bị bệnh nghề nghiệp thì được hưởng trợ cấp hằng tháng bao nhiêu?", INSUFFICIENT),
    ("Sinh con thì tiền trợ cấp thai sản được tính thế nào?", INSUFFICIENT),
    ("Đi công tác thì công ty phải trả phụ cấp công tác bao nhiêu một ngày?", INSUFFICIENT),
    ("Lương tối thiểu vùng III năm 2022 là bao nhiêu?", "historical_not_supported"),
    ("Bao giờ thì nhà nước tăng lương tối thiểu vùng lần tiếp theo?", "unsupported_prediction"),
    ("Mở quán cà phê thì cần xin những giấy phép gì?", "out_of_scope"),
    ("Cách tính tiền điện sinh hoạt theo bậc thang như thế nào?", "out_of_scope"),
]


def build() -> list[dict]:
    rows = []
    for i, (q, gold, facts) in enumerate(ANSWERABLE, 1):
        rows.append({"id": f"h3_{i:02d}", "type": "direct", "split": "heldout3", "question": q,
                     "should_refuse": False, "acceptable_decisions": ["ANSWER", "PARTIAL"], "gold": gold,
                     "gold_required": gold[:1], "required_facts": facts, "must_not_contain": [],
                     "reference_answer": None, "expected_reason": None})
    for i, (q, reason) in enumerate(REFUSALS, len(ANSWERABLE) + 1):
        kind = "out_of_scope" if reason == "out_of_scope" else "unanswerable"
        rows.append({"id": f"h3_{i:02d}", "type": kind, "split": "heldout3", "question": q, "should_refuse": True,
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
