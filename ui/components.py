"""Rendering helpers shared by the Streamlit pages."""

from __future__ import annotations

import html
import re

import streamlit as st

import api_client as api

DECISION_BADGE = {
    "ANSWER": ("✅", "Có căn cứ"),
    "PARTIAL": ("◐", "Trả lời một phần"),
    "REFUSE": ("⚠", "Chưa đủ căn cứ"),
}
STATUS_LABEL = {
    "verified_current": "đã xác minh hiện hành",
    "consolidated_current": "văn bản hợp nhất chính thức",
    "presumed_current": "được ghi nhận còn hiệu lực",
    "pending_amendment": "sửa đổi chưa có hiệu lực",
    "superseded_by_consolidation": "đã có bản hợp nhất mới hơn",
    "superseded_by_amendment": "đã hết hiệu lực hoặc bị thay thế",
    "historical": "đã hết hiệu lực",
    "unverified": "chưa xác minh hiệu lực",
}
FEEDBACK_REASONS = {"Sai nội dung": "wrong_content", "Nguồn không phù hợp": "citation_wrong",
                    "Thiếu nguồn": "missing_source", "Khó hiểu": "unclear", "Khác": "other"}
CLAUSE_NUMBER_RE = re.compile(r"^(\d+[a-z]?)\.")


def as_markdown(text: str) -> str:
    """Keep the answer's line structure in Markdown: one line per passage, numbering shown literally."""
    out = []
    for line in text.split("\n"):
        if line.startswith("- "):
            line = "- " + CLAUSE_NUMBER_RE.sub(lambda m: m.group(1) + "\\.", line[2:])
        out.append(line)
    return "  \n".join(out).replace("  \n  \n", "\n\n")


def pages(start: int, end: int) -> str:
    return f"Trang {start}" if start == end else f"Trang {start}–{end}"


def _highlight(text: str, quote: str) -> str:
    """Escape source text and wrap the quoted passage in <mark>; the source is never rendered as HTML."""
    safe = html.escape(text)
    if quote:
        q = html.escape(" ".join(quote.split()))
        pattern = r"\s+".join(re.escape(part) for part in q.split(" "))
        safe = re.sub(pattern, lambda m: f"<mark>{m.group(0)}</mark>", safe, count=1)
    return safe.replace("\n", "<br>")


@st.dialog("Nguồn trích dẫn", width="large")
def source_dialog(chunk_id: str, snapshot_id: str | None, number: int | None = None, quote: str = "") -> None:
    try:
        src = api.source(chunk_id, snapshot_id)
    except api.ApiError as exc:
        st.error(exc.message)
        return
    if number is not None:
        st.caption(f"Nguồn {number}")
    st.markdown(f"**{src['short_title']}** ({src['document_number']})")
    st.markdown(f"{src['section']} · {pages(src['page_start'], src['page_end'])}")
    st.caption(" › ".join(src["section_path"]))
    st.divider()
    st.markdown(f"<div class='source-text'>{_highlight(src['text'], quote)}</div>", unsafe_allow_html=True)
    st.divider()
    for note in src.get("amendment_notes", []):
        if note.get("change_type") in ("amended", "added", "repealed"):
            st.info(f"Ghi chú hợp nhất: {note['text']}", icon="📝")
    st.caption(f"Tình trạng hiệu lực: {STATUS_LABEL.get(src['currency_status'], src['currency_status'])}. "
               f"{src['currency_basis']}")
    st.caption(f"Nguồn phát hành: {src['publisher']} · Tải về: {src['downloaded_at'][:10]} · "
               f"Snapshot: {src['corpus_snapshot_id']}")
    st.link_button("Mở nguồn gốc ↗", src["source_url"])


def render_result(result: dict, key: str, n_sources: int, show_details: bool) -> str | None:
    """Render one answer; returns a follow-up question to send, if the user picked one."""
    icon, label = DECISION_BADGE[result["decision"]]
    st.markdown(f"**{icon} {label}**")
    follow_up = None
    if result["decision"] == "REFUSE":
        st.warning(result["answer"].replace("⚠ Chưa đủ căn cứ\n\n", ""))
        if result.get("notices"):  # e.g. which later instrument replaced the provision that matched best
            st.markdown("**Vì sao nguồn gần nhất chưa dùng được**")
            for n in result["notices"]:
                st.markdown(f"- {n}")
        related = result.get("related_sources", [])[:n_sources]
        if related:
            st.markdown("**Nguồn gần nhất**")
            for i, s in enumerate(related, 1):
                status = STATUS_LABEL.get(s["currency_status"], s["currency_status"])
                cols = st.columns([5, 1])
                cols[0].markdown(f"{i}. {s['section']} – {s['short_title']} ({s['document_number']}) · _{status}_")
                if cols[1].button("Xem", key=f"{key}-rel-{i}", help=f"Mở {s['section']}"):
                    source_dialog(s["chunk_id"], result["corpus_snapshot_id"])
    else:
        if result["decision"] == "PARTIAL":
            st.info("Chỉ một phần câu hỏi có đủ căn cứ trong kho tài liệu.", icon="◐")
        st.markdown(as_markdown(result["answer"]))
        citations = result["citations"]
        if citations:
            st.caption("Bấm vào số trích dẫn để xem nguyên văn nguồn:")
            cols = st.columns(min(len(citations), 4))
            for i, c in enumerate(citations):
                if cols[i % len(cols)].button(f"[{c['citation_id']}] {c['section']} · {c['document_number']}",
                                              key=f"{key}-cite-{c['citation_id']}",
                                              help=f"Mở nguồn {c['citation_id']}: {c['title']}"):
                    source_dialog(c["chunk_id"], result["corpus_snapshot_id"], c["citation_id"], c["quote"])
            with st.expander(f"Nguồn tham khảo ({len(citations)})", expanded=False):
                for c in citations[:n_sources]:
                    st.markdown(f"**[{c['citation_id']}] {c['title']}** ({c['document_number']})  \n"
                                f"{c['section']} · {pages(c['page_start'], c['page_end'])}")
                    st.markdown(f"> {html.escape(c['quote'][:300])}")
                    st.markdown(f"[Mở nguồn gốc ↗]({c['source_url']})")
        notices = result.get("notices", [])
        if notices:
            with st.expander("Căn cứ hiệu lực và lưu ý", expanded=False):
                for n in notices:
                    st.markdown(f"- {n}")
        if result.get("suggestions"):
            st.caption("Bạn có thể hỏi tiếp:")
            cols = st.columns(len(result["suggestions"]))
            for i, s in enumerate(result["suggestions"]):
                if cols[i].button(s, key=f"{key}-sug-{i}"):
                    follow_up = _follow_up(s, result)
    if show_details:
        _details(result, key)
    _feedback(result["query_id"], key)
    return follow_up


def _follow_up(suggestion: str, result: dict) -> str | None:
    citations = result["citations"]
    if not citations:
        return None
    first = citations[0]
    if suggestion.startswith("Quy định này nằm ở"):
        st.info("Quy định được trích từ: " + "; ".join(f"{c['section']} – {c['title']} ({c['document_number']})"
                                                         for c in citations))
        return None
    if suggestion.startswith("Cho tôi xem nguyên văn"):
        source_dialog(first["chunk_id"], result["corpus_snapshot_id"], first["citation_id"], first["quote"])
        return None
    return f"Các trường hợp ngoại lệ theo {first['section']} {first['title']}"


def _details(result: dict, key: str) -> None:
    m = result["metrics"]
    with st.expander("Chi tiết truy xuất", expanded=False):
        st.markdown(f"- Nguồn được dùng: {len(result['citations'])}\n"
                    f"- Thời gian: tổng {m['total_ms']:.0f} ms · truy xuất {m['retrieval_ms']:.0f} ms · "
                    f"rerank {m['rerank_ms']:.0f} ms\n"
                    f"- Chế độ: `{result['mode']}` · snapshot `{result['corpus_snapshot_id']}`\n"
                    f"- Số lần gọi tool: search_evidence {m['search_calls']}, get_source {m['source_calls']}")
        rows = []
        for step in result.get("trace", []):
            for r in step.get("results", []):
                rows.append({"Điều": r["section"], "Văn bản": r["document_id"], "Dùng được": "có" if r["eligible"] else "không",
                             "Dense rank": r["dense_rank"], "BM25 rank": r["bm25_rank"], "RRF": r["rrf_score"],
                             "Reranker": r["reranker_score"]})
        if rows:
            st.dataframe(rows, hide_index=True, width="stretch")


def _feedback(query_id: str, key: str) -> None:
    done = st.session_state.setdefault("feedback_sent", set())
    if query_id in done:
        st.caption("Cảm ơn phản hồi của bạn.")
        return
    cols = st.columns([1, 1, 4])
    if cols[0].button("👍 Hữu ích", key=f"{key}-up"):
        _send_feedback(query_id, 1, None)
    if cols[1].button("👎 Chưa tốt", key=f"{key}-down"):
        st.session_state[f"{key}-ask-reason"] = True
    if st.session_state.get(f"{key}-ask-reason"):
        with st.form(f"{key}-reason-form"):
            reason = st.radio("Điều gì chưa tốt?", list(FEEDBACK_REASONS), horizontal=True)
            comment = st.text_input("Góp ý thêm (không bắt buộc)", max_chars=500)
            if st.form_submit_button("Gửi phản hồi"):
                _send_feedback(query_id, -1, FEEDBACK_REASONS[reason], comment or None)


def _send_feedback(query_id: str, rating: int, reason: str | None, comment: str | None = None) -> None:
    try:
        api.feedback(query_id, rating, reason, comment)
        st.session_state["feedback_sent"].add(query_id)
        st.toast("Đã ghi nhận phản hồi.")
    except api.ApiError as exc:
        st.error(exc.message)
