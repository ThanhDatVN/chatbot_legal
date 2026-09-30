"""SQLite store for chat sessions, answers and feedback (local demo, no authentication)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, title TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    query_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question TEXT NOT NULL, result_json TEXT NOT NULL, decision TEXT NOT NULL,
    snapshot_id TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT, query_id TEXT NOT NULL, rating INTEGER NOT NULL,
    reason TEXT, comment TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_by_session ON messages(session_id, created_at);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SessionStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._lock = threading.Lock()

    def create_session(self, title: str | None = None) -> str:
        sid = "s_" + uuid.uuid4().hex[:16]
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)", (sid, title, now(), now()))
        return sid

    def ensure_session(self, session_id: str | None, first_question: str) -> str:
        with self._lock:
            row = self._conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone() \
                if session_id else None
        return row[0] if row else self.create_session(first_question[:60])

    def add_message(self, session_id: str, question: str, result: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (result["query_id"], session_id, question, json.dumps(result, ensure_ascii=False),
                                result["decision"], result["corpus_snapshot_id"], now()))
            self._conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now(), session_id))

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT s.id, s.title, s.created_at, s.updated_at, COUNT(m.query_id) FROM sessions s "
                "LEFT JOIN messages m ON m.session_id = s.id GROUP BY s.id ORDER BY s.updated_at DESC LIMIT ?",
                (limit,)).fetchall()
        return [{"session_id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3], "messages": r[4]}
                for r in rows]

    def history(self, session_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT question, result_json, created_at FROM messages WHERE session_id = ? "
                                      "ORDER BY created_at", (session_id,)).fetchall()
        return [{"question": q, "result": json.loads(r), "created_at": t} for q, r, t in rows]

    def delete_session(self, session_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0

    def has_query(self, query_id: str) -> bool:
        with self._lock:
            return self._conn.execute("SELECT 1 FROM messages WHERE query_id = ?", (query_id,)).fetchone() is not None

    def add_feedback(self, query_id: str, rating: int, reason: str | None, comment: str | None) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO feedback (query_id, rating, reason, comment, created_at) VALUES (?,?,?,?,?)",
                               (query_id, rating, reason, comment, now()))

    def feedback_summary(self) -> dict:
        with self._lock:
            rows = self._conn.execute("SELECT rating, reason, COUNT(*) FROM feedback GROUP BY rating, reason").fetchall()
        return {"total": sum(r[2] for r in rows),
                "by_rating": {str(k): sum(r[2] for r in rows if r[0] == k) for k in (-1, 1)},
                "by_reason": {r[1]: r[2] for r in rows if r[1]}}
