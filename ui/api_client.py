"""Thin HTTP client for the CiteAgent API; the UI never touches Qdrant or models directly."""

from __future__ import annotations

import os

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
CONNECTION_ERROR = "Không thể kết nối tới hệ thống truy xuất. Vui lòng thử lại."


class ApiError(Exception):
    def __init__(self, message: str, code: str = "api_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _call(method: str, path: str, timeout: float = 120, **kwargs) -> dict:
    try:
        response = requests.request(method, API_URL + path, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        raise ApiError(CONNECTION_ERROR, "connection_error") from exc
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 400:
        raise ApiError(body.get("message") or CONNECTION_ERROR, body.get("error", str(response.status_code)))
    return body


def chat(message: str, session_id: str | None, debug: bool = False) -> dict:
    return _call("POST", "/api/chat", json={"message": message, "session_id": session_id, "debug": debug})


def search(query: str, top_k: int = 8, include_non_current: bool = True) -> dict:
    return _call("POST", "/api/search", json={"query": query, "top_k": top_k,
                                              "include_non_current": include_non_current})


def source(chunk_id: str, snapshot_id: str | None = None) -> dict:
    params = {"snapshot_id": snapshot_id} if snapshot_id else None
    return _call("GET", f"/api/sources/{chunk_id}", params=params)


def documents(**filters) -> dict:
    return _call("GET", "/api/documents", params={k: v for k, v in filters.items() if v})


def document(document_id: str) -> dict:
    return _call("GET", f"/api/documents/{document_id}")


def feedback(query_id: str, rating: int, reason: str | None = None, comment: str | None = None) -> dict:
    return _call("POST", "/api/feedback", json={"query_id": query_id, "rating": rating, "reason": reason,
                                                "comment": comment})


def sessions() -> list[dict]:
    return _call("GET", "/api/sessions")["sessions"]


def history(session_id: str) -> list[dict]:
    return _call("GET", f"/api/sessions/{session_id}")["messages"]


def delete_session(session_id: str) -> None:
    _call("DELETE", f"/api/sessions/{session_id}")


def evaluation() -> dict:
    return _call("GET", "/api/evaluation")


def ready() -> dict:
    try:
        return _call("GET", "/ready", timeout=10)
    except ApiError as exc:
        return {"ready": False, "message": exc.message}
