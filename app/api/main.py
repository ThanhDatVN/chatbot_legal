"""FastAPI service: chat, search, sources, documents, feedback, health and readiness.

    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.agent.service import AnswerService
from app.config import ROOT
from app.errors import CiteAgentError, SourceNotFound
from app.runtime import Runtime, get_runtime
from app.schemas import AnswerResult, ChatRequest, FeedbackRequest, SearchRequest, SourceEvidence
from app.storage.sessions import SessionStore

log = logging.getLogger("citeagent.api")


def create_app(runtime_factory: Callable[[], Runtime] = get_runtime, sessions: SessionStore | None = None,
               llm_client=None) -> FastAPI:
    state: dict = {"runtime": None, "service": None, "sessions": sessions}

    def runtime() -> Runtime:
        if state["runtime"] is None:
            state["runtime"] = runtime_factory()
            state["service"] = AnswerService(state["runtime"], llm_client=llm_client)
            if state["sessions"] is None:
                state["sessions"] = SessionStore(state["runtime"].settings.runtime_dir / "sessions.sqlite3")
        return state["runtime"]

    def service() -> AnswerService:
        runtime()
        return state["service"]

    def store() -> SessionStore:
        runtime()
        return state["sessions"]

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if os.environ.get("WARMUP", "").lower() in ("1", "true", "yes"):
            try:
                runtime().retrieval.search("khởi động mô hình", top_k=1)
            except CiteAgentError as exc:  # stay up; /ready reports the problem
                log.warning("warm-up failed: %s", exc.code)
        yield

    app = FastAPI(title="CiteAgent VN API", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(CiteAgentError)
    async def typed_error(_: Request, exc: CiteAgentError):
        return JSONResponse(status_code=exc.status, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, exc: RequestValidationError):
        fields = [".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()]
        return JSONResponse(status_code=400, content={"error": "invalid_request",
                                                      "message": "Yêu cầu không hợp lệ: " + ", ".join(fields)})

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"error": "internal_error",
                                                      "message": "Hệ thống gặp lỗi không mong muốn. Vui lòng thử lại."})

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        try:
            report = runtime().readiness()
        except CiteAgentError as exc:
            return JSONResponse(status_code=503, content={"ready": False, "error": exc.code, "message": exc.message})
        return JSONResponse(status_code=200 if report["ready"] else 503, content=report)

    @app.post("/api/chat", response_model=AnswerResult)
    def chat(req: ChatRequest) -> AnswerResult:
        sessions = store()
        session_id = sessions.ensure_session(req.session_id, req.message)
        result = service().answer(req.message, session_id=session_id)
        payload = result.model_dump(mode="json")
        sessions.add_message(session_id, req.message, payload)
        if not req.debug:
            result.trace = []
        return result

    @app.post("/api/search")
    def search(req: SearchRequest) -> dict:
        rt = runtime()
        res = rt.retrieval.search(req.query, top_k=req.top_k, mode="rerank", document_ids=req.document_ids,
                                  include_ineligible=req.include_non_current, ineligible_k=req.top_k)
        items = []
        for s in res.eligible + res.ineligible:
            preview = rt.catalog.preview(s.chunk, s.score).model_dump()
            items.append({**preview, "dense_rank": s.dense_rank, "bm25_rank": s.bm25_rank, "rrf_score": s.rrf_score,
                          "reranker_score": s.reranker_score})
        items.sort(key=lambda x: (not x["eligible"], -(x["reranker_score"] or 0)))
        return {"query": req.query, "snapshot_id": rt.catalog.snapshot_id,
                "timings_ms": {k: round(v, 1) for k, v in res.timings_ms.items()}, "results": items}

    @app.get("/api/sources/{chunk_id}", response_model=SourceEvidence)
    def source(chunk_id: str, snapshot_id: str | None = None) -> SourceEvidence:
        rt = runtime()
        if snapshot_id and snapshot_id != rt.catalog.snapshot_id:
            raise SourceNotFound()
        return rt.catalog.source(chunk_id)

    @app.get("/api/documents")
    def documents(q: str | None = None, type: str | None = None, year: int | None = None,
                  issuer: str | None = None, limit: int = Query(50, ge=1, le=200),
                  offset: int = Query(0, ge=0)) -> dict:
        rt = runtime()
        docs = list(rt.catalog.documents.values())
        if q:
            needle = q.lower()
            docs = [d for d in docs if needle in d.title.lower() or needle in d.document_number.lower()
                    or needle in d.short_title.lower()]
        if type:
            docs = [d for d in docs if d.document_type == type]
        if year:
            docs = [d for d in docs if d.issued_date.startswith(str(year))]
        if issuer:
            docs = [d for d in docs if d.issuer == issuer]
        eligible = {cid: rt.catalog.is_eligible(c) for cid, c in rt.catalog.chunks.items()}
        rows = []
        for d in docs[offset:offset + limit]:
            n_eligible = sum(1 for cid, c in rt.catalog.chunks.items() if c.document_id == d.document_id
                             and eligible[cid])
            rows.append({**vars(d), "eligible_chunks": n_eligible})
        return {"total": len(docs), "offset": offset, "limit": limit, "documents": rows,
                "snapshot_id": rt.catalog.snapshot_id, "as_of_date": rt.catalog.as_of_date}

    @app.get("/api/documents/{document_id}")
    def document(document_id: str) -> dict:
        rt = runtime()
        doc = rt.catalog.documents.get(document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        sections: dict[str, dict] = {}
        for c in rt.catalog.chunks.values():
            if c.document_id != document_id:
                continue
            row = sections.setdefault(c.section_id, {
                "chunk_id": c.chunk_id, "section": c.section_label, "title": c.section_title,
                "kind": c.section_kind.value, "page_start": c.page_start, "parts": c.part_count,
                "currency_status": c.currency_status.value, "currency_statuses": []})
            if c.currency_status.value not in row["currency_statuses"]:  # clauses of one article can differ
                row["currency_statuses"].append(c.currency_status.value)
        return {**vars(doc), "sections": list(sections.values())}

    @app.post("/api/feedback", status_code=201)
    def feedback(req: FeedbackRequest) -> dict:
        sessions = store()
        if not sessions.has_query(req.query_id):
            raise HTTPException(status_code=404, detail="unknown query_id")
        sessions.add_feedback(req.query_id, req.rating, req.reason, req.comment)
        return {"status": "recorded"}

    @app.post("/api/sessions", status_code=201)
    def new_session() -> dict:
        return {"session_id": store().create_session()}

    @app.get("/api/sessions")
    def list_sessions() -> dict:
        return {"sessions": store().list_sessions()}

    @app.get("/api/sessions/{session_id}")
    def session_history(session_id: str) -> dict:
        return {"session_id": session_id, "messages": store().history(session_id)}

    @app.delete("/api/sessions/{session_id}")
    def delete_session(session_id: str) -> dict:
        if not store().delete_session(session_id):
            raise HTTPException(status_code=404, detail="unknown session")
        return {"status": "deleted"}

    @app.get("/api/evaluation")
    def evaluation() -> dict:
        reports = {}
        for name in ("retrieval_all", "answers_test_extractive", "answers_test_anthropic", "policy_tuning",
                     "security_extractive"):
            path = ROOT / "reports" / f"{name}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                data.pop("per_query", None)
                reports[name] = data
        rt = runtime()
        return {"reports": reports, "failed_cases": _failed_cases(), "feedback": store().feedback_summary(),
                "corpus": rt.catalog.stats()}

    def _failed_cases(limit: int = 30) -> list[dict]:
        traces = ROOT / "reports" / "answers_test_extractive_traces.jsonl"
        dataset = ROOT / "data" / "eval" / "questions_v2.jsonl"
        if not traces.exists() or not dataset.exists():
            return []
        questions = {}
        for line in dataset.open(encoding="utf-8"):
            q = json.loads(line)
            questions[q["id"]] = q
        out = []
        for line in traces.open(encoding="utf-8"):
            t = json.loads(line)
            if t["system"] != "D":
                continue
            q = questions.get(t["id"], {})
            answer = " ".join(t["answer"].lower().split())
            missing = [f for f in q.get("required_facts", []) if " ".join(f.lower().split()) not in answer]
            issue = None
            if t["decision"] not in t["acceptable"]:
                issue = f"quyết định {t['decision']}, kỳ vọng {'/'.join(t['acceptable'])}"
            elif missing and t["decision"] != "REFUSE":
                issue = "thiếu dữ kiện: " + ", ".join(missing)
            if issue:
                out.append({"id": t["id"], "type": t["type"], "question": t["question"], "decision": t["decision"],
                            "issue": issue, "citations": [" ".join(c) for c in t["citations"]]})
        return out[:limit]

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        messages = {404: "Không tìm thấy tài nguyên được yêu cầu."}
        return JSONResponse(status_code=exc.status_code,
                            content={"error": str(exc.detail).replace(" ", "_"),
                                     "message": messages.get(exc.status_code, "Yêu cầu không hợp lệ.")})

    return app


app = create_app()
