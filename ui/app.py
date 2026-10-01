"""CiteAgent VN — Streamlit front end. Talks to the FastAPI service only.

    streamlit run ui/app.py
"""

from __future__ import annotations

import streamlit as st

import api_client as api
from components import STATUS_LABEL, render_result, source_dialog
from evaluation_view import evaluation_page

st.set_page_config(page_title="CiteAgent VN", page_icon="⚖️", layout="wide")
st.markdown("""
<style>
.source-text { font-size: 1rem; line-height: 1.65; }
.source-text mark { background: #fde68a; color: #1f2937; padding: 0 2px; }
@media (prefers-color-scheme: dark) { .source-text mark { background: #92400e; color: #fffbeb; } }
</style>""", unsafe_allow_html=True)

EXAMPLES = [
    "Người lao động làm đủ 12 tháng được nghỉ hằng năm bao nhiêu ngày?",
    "Thời gian thử việc tối đa là bao lâu?",
    "Quy định nào áp dụng cho làm thêm giờ?",
    "Mức lương tối thiểu tháng vùng I hiện nay là bao nhiêu?",
]
USE_LABEL = {"current": "Dùng cho quy định hiện hành", "historical": "Tham khảo lịch sử", "out_of_scope": "Ngoài phạm vi"}

state = st.session_state
state.setdefault("session_id", None)
state.setdefault("messages", [])
state.setdefault("n_sources", 5)
state.setdefault("show_details", False)
state.setdefault("debug", False)


@st.cache_data(ttl=30, show_spinner=False)
def readiness() -> dict:
    return api.ready()


def sidebar() -> None:
    with st.sidebar:
        st.markdown("### CiteAgent VN")
        if st.button("＋ Cuộc trò chuyện mới", width="stretch"):
            state.session_id, state.messages = None, []
            st.rerun()
        if state.session_id and st.button("🗑 Xóa cuộc trò chuyện này", width="stretch"):
            try:
                api.delete_session(state.session_id)
            except api.ApiError:
                pass
            state.session_id, state.messages = None, []
            st.rerun()
        st.markdown("**Lịch sử**")
        try:
            for s in api.sessions()[:10]:
                label = (s["title"] or "Cuộc trò chuyện")[:40]
                if st.button(f"💬 {label}", key=f"hist-{s['session_id']}", width="stretch",
                             help=f"{s['messages']} câu hỏi"):
                    state.session_id = s["session_id"]
                    state.messages = [{"question": m["question"], "result": m["result"]}
                                      for m in api.history(s["session_id"])]
                    st.rerun()
        except api.ApiError:
            st.caption("Chưa tải được lịch sử.")
        st.divider()
        st.markdown("**Cài đặt**")
        state.n_sources = st.radio("Số nguồn hiển thị", [3, 5, 8], index=[3, 5, 8].index(state.n_sources),
                                   horizontal=True)
        state.show_details = st.toggle("Hiển thị chi tiết truy xuất", value=state.show_details)
        if state.show_details:
            state.debug = st.toggle("Chế độ debug (rank từng bước)", value=state.debug)
        ready = readiness()
        st.caption(("🟢 Hệ thống sẵn sàng" if ready.get("ready") else "🔴 Hệ thống chưa sẵn sàng")
                   + (f" · snapshot {ready['snapshot_id']}" if ready.get("snapshot_id") else ""))


def ask(question: str) -> None:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.status("Đang tìm nguồn phù hợp...", expanded=False) as status:
            try:
                result = api.chat(question, state.session_id, debug=state.debug)
            except api.ApiError as exc:
                status.update(label="Không nhận được câu trả lời", state="error")
                st.error(exc.message)
                return
            status.update(label="Đã kiểm tra căn cứ", state="complete")
        state.session_id = result["session_id"]
        state.messages.append({"question": question, "result": result})
        st.rerun()


def chat_page() -> None:
    st.title("CiteAgent VN")
    st.caption("Hỏi đáp dựa trên tài liệu có nguồn kiểm chứng.")
    ready = readiness()
    st.caption(f"Phạm vi: quan hệ lao động theo Bộ luật Lao động (văn bản hợp nhất 2026) và các văn bản hướng dẫn "
               f"đã xác định hiệu lực. Dữ liệu tại ngày {ready.get('as_of_date', '—')}. "
               "Không thay thế tư vấn pháp lý.")
    pending = state.pop("pending_question", None)
    if not state.messages and not pending:
        st.markdown("##### Câu hỏi gợi ý")
        cols = st.columns(2)
        for i, q in enumerate(EXAMPLES):
            if cols[i % 2].button(q, key=f"ex-{i}", width="stretch"):
                pending = q
    for i, m in enumerate(state.messages):
        with st.chat_message("user"):
            st.write(m["question"])
        with st.chat_message("assistant"):
            follow = render_result(m["result"], f"m{i}", state.n_sources, state.show_details)
            if follow:
                state.pending_question = follow
                st.rerun()
    typed = st.chat_input("Nhập câu hỏi về quan hệ lao động…", max_chars=2000)
    question = typed or pending
    if question:
        ask(question)


def search_page() -> None:
    st.title("🔎 Tìm nguồn")
    st.caption("Tìm đoạn luật liên quan nhất mà không tạo câu trả lời. Kết quả có nhãn tình trạng hiệu lực.")
    with st.form("search"):
        query = st.text_input("Từ khóa hoặc câu hỏi", placeholder="Ví dụ: nghỉ hằng năm")
        c1, c2 = st.columns(2)
        top_k = c1.slider("Số kết quả", 3, 20, 8)
        include = c2.checkbox("Hiện cả nguồn chưa dùng cho quy định hiện hành", value=True)
        submitted = st.form_submit_button("Tìm")
    if submitted and query.strip():
        with st.spinner("Đang tìm nguồn phù hợp..."):
            try:
                state.search = api.search(query, top_k, include)
            except api.ApiError as exc:
                st.error(exc.message)
                return
    data = state.get("search")
    if not data:
        return
    st.caption(f"Query: {data['query']} · {data['timings_ms'].get('retrieval_ms', 0):.0f} ms truy xuất, "
               f"{data['timings_ms'].get('rerank_ms', 0):.0f} ms rerank")
    if not data["results"]:
        st.info("Không tìm thấy đoạn nào phù hợp.")
    for i, r in enumerate(data["results"], 1):
        badge = "✅ dùng được" if r["eligible"] else f"⛔ {STATUS_LABEL.get(r['currency_status'], r['currency_status'])}"
        with st.container(border=True):
            st.markdown(f"**{i}. {r['section']} — {r['short_title']}** ({r['document_number']}) · "
                        f"điểm {r['reranker_score'] or 0:.3f} · {badge}")
            st.caption(r["text_preview"])
            if st.button("Xem nguyên văn", key=f"s-{r['chunk_id']}"):
                source_dialog(r["chunk_id"], data["snapshot_id"])


def documents_page() -> None:
    st.title("📚 Kho tài liệu")
    c1, c2, c3 = st.columns([3, 2, 2])
    q = c1.text_input("Tìm theo tên hoặc số hiệu")
    all_label = lambda v: v or "Tất cả"  # noqa: E731
    doc_type = c2.selectbox("Loại tài liệu", ["", "Bộ luật", "Văn bản hợp nhất", "Nghị định"], format_func=all_label)
    year = c3.selectbox("Năm ban hành", ["", 2026, 2025, 2024, 2023, 2022, 2020, 2019], format_func=all_label)
    try:
        data = api.documents(q=q, type=doc_type, year=year or None)
    except api.ApiError as exc:
        st.error(exc.message)
        return
    st.caption(f"{data['total']} văn bản · snapshot {data['snapshot_id']} · dữ liệu tại {data['as_of_date']}")
    rows = [{"Số hiệu": d["document_number"], "Tên": d["short_title"],
             "Vai trò": USE_LABEL.get(d["corpus_use"], d["corpus_use"]),
             "Đoạn dùng trả lời": f"{d['eligible_chunks']} / {d['chunks']}", "Loại": d["document_type"],
             "Ban hành": d["issued_date"], "Hiệu lực từ": d["effective_date"] or "—",
             "Ngày tải": d["downloaded_at"][:10], "Nguồn": d["source_url"]}
            for d in data["documents"]]
    st.dataframe(rows, hide_index=True, width="stretch",
                 column_config={"Nguồn": st.column_config.LinkColumn("Nguồn", display_text="Mở ↗")})
    choice = st.selectbox("Xem chi tiết", [""] + [d["document_id"] for d in data["documents"]],
                          format_func=lambda x: next((d["document_number"] + " – " + d["short_title"]
                                                      for d in data["documents"] if d["document_id"] == x), "Chọn…"))
    if choice:
        detail = api.document(choice)
        st.markdown(f"**{detail['title']}** ({detail['document_number']})")
        st.caption(detail["corpus_use_reason"])
        if detail.get("section_scope"):
            st.caption("Chỉ nạp vào kho: " + ", ".join(detail["section_scope"]) + " (phần còn lại ngoài phạm vi).")
        lead = detail.get("legal_status_lead") or {}
        if lead:
            st.caption(f"Đầu mối hiệu lực: {lead.get('status')} — {lead.get('note')} (tra cứu {lead.get('checked_on')})")
        st.dataframe([{"Mục": s["section"], "Tiêu đề": s["title"] or "", "Loại": s["kind"], "Trang": s["page_start"],
                       "Hiệu lực": " / ".join(STATUS_LABEL.get(x, x) for x in s.get("currency_statuses") or
                                             [s["currency_status"]]), "Số phần": s["parts"]}
                      for s in detail["sections"]], hide_index=True, width="stretch")


sidebar()
navigation = st.navigation([
    st.Page(chat_page, title="Hỏi đáp", icon=":material/chat:", default=True),
    st.Page(search_page, title="Tìm nguồn", icon=":material/search:"),
    st.Page(documents_page, title="Kho tài liệu", icon=":material/library_books:"),
    st.Page(evaluation_page, title="Đánh giá", icon=":material/monitoring:"),
])
navigation.run()
