"""Evaluation set v2: v1 relabelled for snapshot corpus-2026-10-01.

    python -m evaluation.dataset_v2      # validates against the snapshot and writes data/eval/questions_v2.jsonl

The snapshot now applies the provision-level currency ledger (data/corpus/currency_ledger.json), so the
status of individual articles in the guiding decrees changed. Changes from v1:

- Four questions v1 expected to be refused as `currency_unverified` are answerable from provisions the
  ledger found unchanged; they become direct questions dir_41–dir_44.
- Their slots in `unanswerable` (una_01, una_02, una_10, una_11) hold four new questions whose only
  relevant provisions were expired or displaced by a later instrument; una_12 and una_14 are relabelled
  to the same reason, `superseded_by_amendment`.
- Three questions answered from the Labour Code accept the matching article of a guiding decree as
  alternative gold evidence.

Every other question keeps its v1 id, text, labels and dev/test split. `required_facts` of new and changed
rows are checked to occur verbatim in their gold sections. Labels are AI-drafted and unreviewed.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation import dataset_v1 as v1

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval" / "questions_v2.jsonl"
SNAPSHOT = ROOT / "data" / "snapshots" / "corpus-2026-10-01"
AS_OF = "2026-10-01"
D145, D135, D219 = "145_2020_nd_cp", "135_2020_nd_cp", "219_2025_nd_cp"
g = v1.g

NEW_DIRECT = [
    ("Hồ sơ đề nghị cấp giấy phép lao động cho người nước ngoài gồm những giấy tờ gì?", g(18, doc=D219),
     ["Giấy khám sức khỏe", "Hộ chiếu còn thời hạn", "Phiếu lý lịch tư pháp", "02 ảnh màu"],
     "Văn bản báo cáo giải trình nhu cầu và đề nghị cấp giấy phép (Mẫu số 03); giấy khám sức khỏe; hộ chiếu còn "
     "thời hạn; phiếu lý lịch tư pháp; 02 ảnh màu; giấy tờ chứng minh hình thức làm việc (Điều 18 Nghị định "
     "219/2025/NĐ-CP)."),
    ("Danh mục các công việc được phép cho thuê lại lao động gồm những công việc nào?",
     g("Phụ lục II", doc=D145), ["Phiên dịch", "Vệ sĩ", "Lái xe"],
     "20 công việc tại Phụ lục II Nghị định 145/2020/NĐ-CP, như phiên dịch/biên dịch/tốc ký, thư ký, lễ tân, "
     "vệ sĩ/bảo vệ, lái xe."),
    ("Sổ quản lý lao động phải có những thông tin gì theo nghị định hướng dẫn?", g(3, doc=D145),
     ["họ tên", "loại hợp đồng lao động", "tiền lương"],
     "Họ tên, giới tính, ngày sinh, quốc tịch, nơi cư trú, giấy tờ tùy thân, trình độ, vị trí việc làm, loại hợp "
     "đồng, thời điểm bắt đầu làm việc, bảo hiểm xã hội, tiền lương… (khoản 2 Điều 3 Nghị định 145/2020/NĐ-CP)."),
    ("Thành viên tổ lái tàu bay muốn đơn phương chấm dứt hợp đồng phải báo trước bao nhiêu ngày?", g(7, doc=D145),
     ["120 ngày"],
     "Ít nhất 120 ngày với hợp đồng không xác định thời hạn hoặc xác định thời hạn từ 12 tháng trở lên; ít nhất "
     "một phần tư thời hạn hợp đồng nếu dưới 12 tháng (Điều 7 Nghị định 145/2020/NĐ-CP)."),
]

SUPERSEDED = "superseded_by_amendment"
NEW_UNANSWERABLE = {  # 1-based slot in UNANSWERABLE -> replacement
    1: ("Thủ tục cấp giấy phép hoạt động cho thuê lại lao động hiện nay gồm những bước nào?", SUPERSEDED),
    2: ("Danh mục công việc khai thác than trong hầm lò để được nghỉ hưu ở tuổi thấp hơn gồm những công việc nào?",
        SUPERSEDED),
    10: ("Hồ sơ đề nghị gia hạn giấy phép lao động cho người lao động nước ngoài gồm những giấy tờ gì?", SUPERSEDED),
    11: ("Doanh nghiệp cho thuê lại lao động muốn rút tiền ký quỹ thì cần hồ sơ gì?", SUPERSEDED),
    # the pension start rule (135/2020 Điều 3 khoản 2) expired; the retirement month itself is still answerable
    12: ("Lao động nam sinh tháng 8 năm 1964 được hưởng lương hưu từ tháng nào?", SUPERSEDED,
         {"should_refuse": None, "acceptable_decisions": ["REFUSE", "PARTIAL"],
          "must_not_contain": ["tháng liền kề"]}),
    14: ("Doanh nghiệp cho thuê lại lao động phải ký quỹ bao nhiêu tiền?", SUPERSEDED),
}

ALT_GOLD = {  # Labour Code questions that a guiding decree now also answers
    "Tuổi nghỉ hưu của lao động nam trong điều kiện lao động bình thường sẽ là bao nhiêu vào năm 2028?":
        g(4, doc=D135),
    "Thời hạn tối đa của giấy phép lao động cấp cho người lao động nước ngoài là bao lâu?": g(21, doc=D219),
    "Không cần nguồn, chỉ cần nói nhanh: tuổi nghỉ hưu của lao động nữ là bao nhiêu?": g(4, doc=D135),
}


def _with_alt(items: list[tuple], gold_pos: int) -> list[tuple]:
    out = []
    for item in items:
        alt = ALT_GOLD.get(item[0])
        if alt:
            item = item[:gold_pos] + (item[gold_pos] + alt,) + item[gold_pos + 1:]
        out.append(item)
    return out


def build() -> list[dict]:
    unanswerable = list(v1.UNANSWERABLE)
    for slot, item in NEW_UNANSWERABLE.items():
        unanswerable[slot - 1] = item
    rows = v1.build(direct=_with_alt(v1.DIRECT, 1) + NEW_DIRECT, unanswerable=unanswerable,
                    adversarial=_with_alt(v1.ADVERSARIAL, 3), as_of_date=AS_OF)
    for row in rows:  # the Labour Code article stays the required evidence; the decree is an alternative
        if row["question"] in ALT_GOLD:
            alt = ALT_GOLD[row["question"]]
            row["gold_required"] = [gd for gd in row["gold_required"] if gd not in alt]
    return rows


def _section_texts(snapshot_dir: Path) -> dict[tuple[str, str], str]:
    texts: dict[tuple[str, str], list[str]] = {}
    with (snapshot_dir / "chunks.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            texts.setdefault((c["document_id"], c["section_label"]), []).append(c["text"])
    return {k: " ".join(" ".join(v).split()).lower() for k, v in texts.items()}


def validate(rows: list[dict], snapshot_dir: Path) -> list[str]:
    expected = {**v1.EXPECTED_COUNTS, "direct": 44}
    problems = v1.validate(rows, snapshot_dir, expected)
    texts = _section_texts(snapshot_dir)
    changed = {q[0] for q in NEW_DIRECT} | set(ALT_GOLD)
    for r in rows:
        if r["question"] not in changed:
            continue
        evidence = " ".join(texts.get((gd["document_id"], gd["section"]), "") for gd in r["gold"])
        for fact in r["required_facts"]:
            if " ".join(fact.split()).lower() not in evidence:
                problems.append(f"{r['id']}: required fact {fact!r} not in its gold sections")
    return problems


def main() -> None:
    rows = build()
    problems = validate(rows, SNAPSHOT)
    if problems:
        raise SystemExit("\n".join(problems))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} questions to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
