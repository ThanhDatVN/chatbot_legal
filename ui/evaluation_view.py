"""Evaluation dashboard: KPI row, A/B/C/D comparison, small multiples, failed cases.

Reads only /api/evaluation. Numbers come from report files produced by the evaluation
scripts; nothing here is typed in by hand.
"""

from __future__ import annotations

import altair as alt
import streamlit as st

import api_client as api

SERIES = {"light": "#2a78d6", "dark": "#3987e5"}  # validated single-series hue (dataviz reference palette)
SYSTEMS = [
    ("A", "Dense + RAG đơn giản", "A_dense"),
    ("B", "Dense + BM25 + RRF", "B_hybrid"),
    ("C", "Hybrid + reranker", "C_rerank"),
    ("D", "Hybrid + reranker + từ chối + kiểm tra citation", "D_rerank_expanded"),
]
PANELS = [("hit@5", "Hit@5"), ("mrr", "MRR"), ("correctness", "Correctness (proxy)"),
          ("refusal_accuracy", "Refusal accuracy")]


def _fmt(value, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _rows(reports: dict) -> list[dict]:
    retrieval = reports.get("retrieval_all", {}).get("systems", {})
    answers = reports.get("answers_test_extractive", {}).get("systems", {})
    rows = []
    for key, desc, rkey in SYSTEMS:
        r, a = retrieval.get(rkey) or retrieval.get("C_rerank", {}), answers.get(key, {})
        refusal = a.get("refusal", {})
        rows.append({"system": key, "desc": desc, "hit@5": r.get("hit@5"), "mrr": r.get("mrr"),
                     "citation_precision": a.get("citation_precision_proxy"), "correctness": a.get("correctness_proxy"),
                     "groundedness": a.get("groundedness"), "refusal_accuracy": refusal.get("accuracy"),
                     "false_answers": refusal.get("false_answers"), "false_refusals": refusal.get("false_refusals"),
                     "p95_ms": (a.get("latency_ms") or {}).get("total_p95"),
                     "cost_per_100": a.get("llm_cost_usd_per_100")})
    return rows


def _theme() -> str:
    try:
        return st.context.theme.type or "light"
    except AttributeError:
        return "light"


def _small_multiples(rows: list[dict]) -> alt.HConcatChart:
    color = SERIES["dark" if _theme() == "dark" else "light"]
    charts = []
    for field, title in PANELS:
        data = [{"Hệ thống": r["system"], "Giá trị": r[field], "Mô tả": r["desc"]} for r in rows
                if r[field] is not None]
        base = alt.Chart(alt.Data(values=data)).encode(
            x=alt.X("Hệ thống:N", sort=[s[0] for s in SYSTEMS], axis=alt.Axis(labelAngle=0, title=None)),
            # headroom above 1.0 keeps value labels inside the plot so panel titles line up
            y=alt.Y("Giá trị:Q", scale=alt.Scale(domain=[0, 1.15]),
                    axis=alt.Axis(title=None, values=[0, 0.2, 0.4, 0.6, 0.8, 1.0], gridOpacity=0.3, domain=False)),
            tooltip=[alt.Tooltip("Hệ thống:N"), alt.Tooltip("Mô tả:N"),
                     alt.Tooltip("Giá trị:Q", format=".3f", title=title)])
        bars = base.mark_bar(color=color, size=22, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        labels = base.mark_text(dy=-7, fontSize=11).encode(text=alt.Text("Giá trị:Q", format=".2f"))
        charts.append((bars + labels).properties(title=title, width=150, height=170))
    return alt.hconcat(*charts, spacing=16).configure_view(stroke=None).configure_axis(labelFontSize=12)


def _paraphrase_section(reports: dict) -> None:
    rows = []
    for label, name, system in [("Held-out — D trước khi sửa", "heldout_before_fixes_answers", "D"),
                                ("Held-out — A (RAG đơn giản)", "answers_heldout_extractive", "A"),
                                ("Held-out — D hiện tại", "answers_heldout_extractive", "D"),
                                ("Paraphrase dev — D (đã dùng để chỉnh)", "answers_pdev_extractive", "D")]:
        rep = reports.get(name)
        a = (rep or {}).get("systems", {}).get(system)
        if not a:
            continue
        rows.append({"Bộ / hệ thống": label, "Commit": rep["meta"]["git_commit"], "Số câu": a["questions"],
                     "Quyết định đúng": _fmt(a["decision_accuracy"]), "Trả lời sai": a["refusal"]["false_answers"],
                     "Từ chối nhầm": a["refusal"]["false_refusals"], "Correctness": _fmt(a["correctness_proxy"]),
                     "Citation precision": _fmt(a["citation_precision_proxy"])})
    if rows:
        st.subheader("Câu hỏi diễn đạt theo lối thông thường")
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("Bộ held-out được viết và commit trước khi sửa, không dùng để chỉnh ngưỡng; đây là thước đo khách "
                   "quan nhất. Bộ paraphrase dev dùng để chẩn đoán nên số của nó lạc quan hơn.")


def evaluation_page() -> None:
    st.title("📊 Đánh giá hệ thống")
    try:
        data = api.evaluation()
    except api.ApiError as exc:
        st.error(exc.message)
        return
    reports = data["reports"]
    answers = reports.get("answers_test_extractive")
    if not answers:
        st.info("Chưa có báo cáo đánh giá. Chạy `python -m evaluation.answer_eval` để tạo.")
        return
    meta = answers["meta"]
    st.caption(f"Tập test {answers['systems']['D']['questions']} câu · bộ dữ liệu `{meta['dataset']}` · "
               f"snapshot `{meta['snapshot']}` · commit `{meta['git_commit']}` · chạy {meta['date'][:10]} · "
               f"chế độ trả lời `{meta['provider']}`. Nhãn gold do AI soạn, chưa được người duyệt; "
               "correctness và citation precision là chỉ số tự động (proxy).")
    rows = _rows(reports)
    base, final = rows[0], rows[3]

    st.caption("Chỉ số của hệ thống cuối D; mũi tên là chênh lệch so với hệ thống A (RAG đơn giản).")
    tiles = [("Hit@5", final["hit@5"], base["hit@5"]), ("MRR", final["mrr"], base["mrr"]),
             ("Citation precision", final["citation_precision"], base["citation_precision"]),
             ("Groundedness", final["groundedness"], base["groundedness"]),
             ("Refusal accuracy", final["refusal_accuracy"], base["refusal_accuracy"])]
    row1 = st.columns(4)
    for col, (label, value, ref) in zip(row1, tiles[:4]):
        delta = None if value is None or ref is None or abs(value - ref) < 0.0005 else f"{value - ref:+.3f}"
        col.metric(label, _fmt(value), delta, border=True)
    row2 = st.columns(4)
    label, value, ref = tiles[4]
    row2[0].metric(label, _fmt(value), None if ref is None else f"{value - ref:+.3f}", border=True)
    p95 = final["p95_ms"]
    row2[1].metric("p95 đầu cuối", "—" if p95 is None else f"{p95 / 1000:.2f} s", border=True,
                   help="Độ trễ phân vị 95 của toàn bộ request trên tập test (mô hình đã nạp sẵn).")
    row2[2].metric("Trả lời sai", final["false_answers"], None if base["false_answers"] is None else
                   f"{final['false_answers'] - base['false_answers']:+d}", delta_color="inverse", border=True,
                   help="Số câu lẽ ra phải từ chối nhưng hệ thống vẫn trả lời.")
    row2[3].metric("Chi phí / 100 câu", f"${final['cost_per_100']:.2f}", border=True,
                   help="Chi phí API LLM. Chế độ extractive chạy model cục bộ: API = $0, GPU/CPU không miễn phí.")

    st.subheader("So sánh A / B / C / D")
    st.dataframe([{"Hệ thống": f"{r['system']} — {r['desc']}", "Hit@5": _fmt(r["hit@5"]), "MRR": _fmt(r["mrr"]),
                   "Citation precision": _fmt(r["citation_precision"]), "Correctness": _fmt(r["correctness"]),
                   "Refusal accuracy": _fmt(r["refusal_accuracy"]), "Trả lời sai": r["false_answers"],
                   "Từ chối nhầm": r["false_refusals"],
                   "p95 (ms)": "—" if r["p95_ms"] is None else f"{r['p95_ms']:.0f}"} for r in rows],
                 hide_index=True, width="stretch")
    st.caption("Hit@5 và MRR đo ở tầng truy xuất (D = truy xuất của C + mở rộng truy vấn bằng thuật ngữ pháp lý). "
               "Các cột còn lại đo đầu cuối trên "
               "cùng tập test. A–C ghép câu trả lời từ đoạn đứng đầu, không có chính sách từ chối hay kiểm tra citation.")
    st.altair_chart(_small_multiples(rows), width="content")

    st.subheader("Ca lỗi của hệ thống D")
    failed = data.get("failed_cases", [])
    if failed:
        st.dataframe([{"ID": f["id"], "Loại": f["type"], "Câu hỏi": f["question"], "Quyết định": f["decision"],
                       "Vấn đề": f["issue"], "Đã trích": "; ".join(f["citations"])} for f in failed],
                     hide_index=True, width="stretch")
    else:
        st.success("Không có ca lỗi trong lần chạy gần nhất.", icon="✅")

    _paraphrase_section(reports)

    security = reports.get("security_extractive")
    if security:
        s = security["summary"]
        st.subheader(f"Bộ kiểm thử bảo mật: {s['passed']}/{s['cases']} ca đạt")
        st.dataframe([{"Nhóm": k, "Số ca": v["cases"], "Đạt": v["passed"]} for k, v in s["by_category"].items()],
                     hide_index=True, width="content")

    st.subheader("Phản hồi người dùng và kho dữ liệu")
    fb, corpus = data["feedback"], data["corpus"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Phản hồi đã nhận", fb["total"], border=True)
    c2.metric("👎 Chưa tốt", fb["by_rating"].get("-1", 0), border=True)
    c3.metric("Đoạn dùng được / tổng", f"{corpus['eligible_chunks']} / {corpus['chunks']}", border=True,
              help=f"Chính sách hiệu lực: {corpus['policy']} · dữ liệu tại {corpus['as_of_date']}")
    if fb["by_reason"]:
        st.dataframe([{"Lý do": k, "Số lần": v} for k, v in fb["by_reason"].items()], hide_index=True)
