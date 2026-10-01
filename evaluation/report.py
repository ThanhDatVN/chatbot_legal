"""Render reports/benchmark_v2.md from the JSON reports; no number is typed by hand.

    python -m evaluation.report
"""

from __future__ import annotations

import json

from evaluation.common import REPORTS

VERSION = "v3"

SYSTEM_NAMES = {"A": "A — Dense + RAG đơn giản", "B": "B — Dense + BM25 + RRF", "C": "C — Hybrid + reranker",
                "D": "D — Hybrid + reranker + từ chối + kiểm tra citation"}
RETRIEVAL_KEY = {"A": "A_dense", "B": "B_hybrid", "C": "C_rerank", "D": "D_rerank_expanded"}


def load(name: str) -> dict | None:
    path = REPORTS / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def f3(v) -> str:
    return "—" if v is None else f"{v:.3f}"


def ms(v) -> str:
    return "—" if v is None else f"{v:,.0f}"


def _answer_row(label: str, report: dict | None, system: str = "D") -> str | None:
    if not report or system not in report["systems"]:
        return None
    a, r = report["systems"][system], report["systems"][system]["refusal"]
    return (f"| {label} | {report['meta']['git_commit']} | {a['questions']} | {f3(a['decision_accuracy'])} | "
            f"{r['false_answers']} | {r['false_refusals']} | {f3(a['correctness_proxy'])} | "
            f"{f3(a['citation_precision_proxy'])} |")


def paraphrase_section() -> list[str]:
    """Everyday-wording questions: the held-out set before/after the fixes and the paraphrase dev set."""
    before, after = load("heldout_before_fixes_answers"), load("answers_heldout_extractive")
    pdev = load("answers_pdev_extractive")
    rows = [_answer_row("Held-out — D trước khi sửa", before), _answer_row("Held-out — A (RAG đơn giản)", after, "A"),
            _answer_row("Held-out — D hiện tại", after), _answer_row("Paraphrase dev — D hiện tại (đã dùng để chỉnh)", pdev)]
    rows = [r for r in rows if r]
    if not rows:
        return []
    out = ["## Câu hỏi diễn đạt theo lối thông thường", "",
           "Bộ held-out (`questions_heldout_v1.jsonl`) được viết và commit trước khi sửa, không dùng để chỉnh; bộ "
           "paraphrase dev dùng để chẩn đoán và chọn ngưỡng.", "",
           "| Bộ / hệ thống | Commit | Số câu | Quyết định đúng | Trả lời sai | Từ chối nhầm | Correctness | "
           "Citation precision |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"] + rows
    ret_before, ret_after = load("heldout_before_fixes_retrieval"), load("retrieval_heldout")
    if ret_before and ret_after:
        c0 = ret_before["systems"]["C_rerank"]
        d1 = ret_after["systems"].get("D_rerank_expanded", ret_after["systems"]["C_rerank"])
        out += ["", f"Truy xuất trên held-out: Hit@5 / MRR {f3(c0['hit@5'])} / {f3(c0['mrr'])} trước khi sửa (C) → "
                f"{f3(d1['hit@5'])} / {f3(d1['mrr'])} với mở rộng truy vấn (D)."]
    return out + [""]


def main() -> None:
    retrieval, answers = load("retrieval_all"), load("answers_test_extractive")
    tuning, security = load("policy_tuning"), load("security_extractive")
    meta = answers["meta"]
    out = [f"# Benchmark CiteAgent VN — {VERSION}", "",
           "_Tệp này được sinh tự động bởi `python -m evaluation.report` từ các báo cáo JSON trong `reports/`._", "",
           "## Điều kiện chạy", "",
           f"- Ngày chạy: {meta['date']} · commit `{meta['git_commit']}`",
           f"- Snapshot corpus: `{meta['snapshot']}` · chính sách hiệu lực: `{meta['currency_policy']}`",
           f"- Embedding: `{meta['embedding_model']}` · reranker: `{meta['reranker_model']}`",
           f"- Truy xuất: dense top {meta['dense_top_k']}, BM25 top {meta['sparse_top_k']}, RRF k={meta['rrf_k']}",
           f"- Chế độ trả lời: `{meta['provider']}` (LLM cấu hình: `{meta['llm_model']}`)",
           f"- Chính sách bằng chứng: `{json.dumps(meta['policy'])}`",
           f"- Dữ liệu đánh giá: `{meta['dataset']}`, split `{meta['split']}`",
           f"- Phần cứng: {meta['hardware'].get('cuda_device') or 'CPU'} · torch {meta['hardware'].get('torch')} · "
           f"{meta['hardware'].get('platform')}", "",
           "## Bảng tổng hợp", "",
           "| Hệ thống | Hit@5 | MRR | Citation precision | Correctness | Refusal accuracy | p95 (ms) |",
           "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, name in SYSTEM_NAMES.items():
        r = retrieval["systems"][RETRIEVAL_KEY[key]]
        a = answers["systems"].get(key, {})
        out.append(f"| {name} | {f3(r['hit@5'])} | {f3(r['mrr'])} | {f3(a.get('citation_precision_proxy'))} | "
                   f"{f3(a.get('correctness_proxy'))} | {f3((a.get('refusal') or {}).get('accuracy'))} | "
                   f"{ms((a.get('latency_ms') or {}).get('total_p95'))} |")
    answerable = retrieval["systems"]["C_rerank"]["questions"]
    out += ["", f"Hit@5/MRR đo ở tầng truy xuất trên toàn bộ {answerable} câu trả lời được (D = truy xuất của C cộng "
            "mở rộng truy vấn bằng thuật ngữ pháp lý). "
            "Các cột còn lại đo đầu cuối trên split test. Correctness và citation precision là chỉ số tự động "
            "(proxy) — xem định nghĩa trong `docs/EVALUATION.md`.", "",
            "## Truy xuất", "",
            "| Hệ thống | Hit@5 | MRR | Recall@5 | Recall@10 | Đủ mọi bằng chứng@5 (multi) | p50 ms | p95 ms |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, r in retrieval["systems"].items():
        out.append(f"| {key} | {f3(r['hit@5'])} | {f3(r['mrr'])} | {f3(r['recall@5'])} | {f3(r['recall@10'])} | "
                   f"{f3(r['all_evidence@5_multi'])} | {ms(r['latency_ms_p50'])} | {ms(r['latency_ms_p95'])} |")
    out += ["", f"Câu bị trượt Hit@5: " + "; ".join(f"{k}: {', '.join(v['misses']) or 'không'}"
                                                   for k, v in retrieval["systems"].items()), "",
            "## Trả lời đầu cuối", "",
            "| Hệ thống | Quyết định đúng | Refusal P / R / F1 | Trả lời sai | Từ chối nhầm | Correctness (0/1/2) | "
            "Citation precision | Groundedness | Vi phạm đối kháng | p50 / p95 ms | Chi phí LLM /100 |",
            "| --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: |"]
    for key, a in answers["systems"].items():
        r = a["refusal"]
        dist = a["correctness_distribution"]
        out.append(f"| {SYSTEM_NAMES[key]} | {f3(a['decision_accuracy'])} | {f3(r['precision'])} / {f3(r['recall'])} / "
                   f"{f3(r['f1'])} | {r['false_answers']} | {r['false_refusals']} | {f3(a['correctness_proxy'])} "
                   f"({dist['0']}/{dist['1']}/{dist['2']}) | {f3(a['citation_precision_proxy'])} | "
                   f"{f3(a['groundedness'])} | {len(a['adversarial_violations'])} | "
                   f"{ms(a['latency_ms']['total_p50'])} / {ms(a['latency_ms']['total_p95'])} | "
                   f"${a['llm_cost_usd_per_100']:.2f} |")
    d = answers["systems"]["D"]
    out += ["", f"Độ trễ của D theo bước (p50 / p95 ms): truy xuất {ms(d['latency_ms']['retrieval_p50'])} / "
            f"{ms(d['latency_ms']['retrieval_p95'])}, rerank {ms(d['latency_ms']['rerank_p50'])} / "
            f"{ms(d['latency_ms']['rerank_p95'])}, phần còn lại {ms(d['latency_ms']['generation_p50'])} / "
            f"{ms(d['latency_ms']['generation_p95'])}.", "",
            "Tỷ lệ quyết định đúng theo loại câu hỏi (D): " + ", ".join(
                f"{k} {v['acceptable']}/{v['n']}" for k, v in d["by_type"].items()) + ".", "",
            "Ca lỗi của D: " + (", ".join(d["failures"]) or "không có") + ".", ""]
    out += paraphrase_section()
    if tuning:
        chosen = tuning.get("chosen", tuning["best"]["params"])
        out += ["## Hiệu chỉnh ngưỡng (chỉ trên dữ liệu phát triển: dev v2 + paraphrase dev)", "",
                f"- Tham số chọn: `{json.dumps({k: v for k, v in chosen.items() if k not in ('notes', 'dev_score')})}`",
                f"- Điểm của tham số chọn trên dev: `{json.dumps(chosen.get('dev_score'))}`"
                + (f" (theo bộ: `{json.dumps(chosen['dev_score_by_set'])}`)" if chosen.get("dev_score_by_set") else ""),
                f"- Kết quả tốt nhất trên dev: độ chính xác {f3(tuning['best']['accuracy'])}, "
                f"trả lời sai {tuning['best']['false_answers']}, từ chối nhầm {tuning['best']['false_refusals']}"]
        out += [f"- {n}" for n in chosen.get("notes", [])]
        out.append("")
    if security:
        s = security["summary"]
        out += [f"## Bộ kiểm thử bảo mật: {s['passed']}/{s['cases']} ca đạt", "", "| Nhóm | Số ca | Đạt |",
                "| --- | ---: | ---: |"]
        out += [f"| {k} | {v['cases']} | {v['passed']} |" for k, v in s["by_category"].items()]
        out.append("")
    (REPORTS / f"benchmark_{VERSION}.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote reports/benchmark_{VERSION}.md")


if __name__ == "__main__":
    main()
