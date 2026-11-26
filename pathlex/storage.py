from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class Repository:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._write_lock, self.connection() as db:
            db.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS units (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    published INTEGER NOT NULL DEFAULT 0,
                    spec_json TEXT NOT NULL,
                    graph_json TEXT,
                    audit_json TEXT,
                    runtime_json TEXT,
                    error_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    unit_id TEXT NOT NULL REFERENCES units(id),
                    language TEXT NOT NULL,
                    current_node_id TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_units_published ON units(published, updated_at);
                CREATE INDEX IF NOT EXISTS idx_events_session ON session_events(session_id, id);
                """
            )
            db.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            db.commit()

    @staticmethod
    def _unit_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "published": bool(row["published"]),
            "spec": _loads(row["spec_json"], {}),
            "graph": _loads(row["graph_json"], None),
            "audit": _loads(row["audit_json"], None),
            "runtime": _loads(row["runtime_json"], {}),
            "error": _loads(row["error_json"], None),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_unit(self, spec: dict[str, Any], *, status: str = "DRAFT") -> dict[str, Any]:
        unit_id = uuid.uuid4().hex
        now = utc_now()
        title = str(spec.get("title") or "Untitled story unit").strip()[:200]
        with self._write_lock, self.connection() as db:
            db.execute(
                """
                INSERT INTO units(
                    id, title, status, spec_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (unit_id, title, status, _dumps(spec), now, now),
            )
            db.commit()
        return self.get_unit(unit_id)

    def update_unit(
        self,
        unit_id: str,
        *,
        status: str | None = None,
        graph: dict[str, Any] | None = None,
        audit: dict[str, Any] | None = None,
        runtime: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        clear_error: bool = False,
    ) -> dict[str, Any]:
        assignments: list[str] = ["updated_at = ?"]
        values: list[Any] = [utc_now()]
        for column, value in (
            ("status", status),
            ("graph_json", _dumps(graph) if graph is not None else None),
            ("audit_json", _dumps(audit) if audit is not None else None),
            ("runtime_json", _dumps(runtime) if runtime is not None else None),
            ("error_json", _dumps(error) if error is not None else None),
        ):
            if value is not None:
                assignments.append(f"{column} = ?")
                values.append(value)
        if clear_error:
            assignments.append("error_json = NULL")
        values.append(unit_id)
        with self._write_lock, self.connection() as db:
            cursor = db.execute(
                f"UPDATE units SET {', '.join(assignments)} WHERE id = ?", values
            )
            if cursor.rowcount != 1:
                raise NotFoundError(f"Unit {unit_id!r} was not found")
            db.commit()
        return self.get_unit(unit_id)

    def transition_unit_status(
        self, unit_id: str, *, expected: str, status: str, clear_error: bool = False
    ) -> dict[str, Any]:


        assignments = "status = ?, updated_at = ?"
        if clear_error:
            assignments += ", error_json = NULL"
        with self._write_lock, self.connection() as db:
            cursor = db.execute(
                f"UPDATE units SET {assignments} WHERE id = ? AND status = ?",
                (status, utc_now(), unit_id, expected),
            )
            if cursor.rowcount != 1:
                exists = db.execute(
                    "SELECT 1 FROM units WHERE id = ?", (unit_id,)
                ).fetchone()
                if exists is None:
                    raise NotFoundError(f"Unit {unit_id!r} was not found")
                raise ConflictError(
                    f"Unit {unit_id!r} is no longer in expected state {expected!r}"
                )
            db.commit()
        return self.get_unit(unit_id)

    def get_unit(self, unit_id: str) -> dict[str, Any]:
        with self.connection() as db:
            row = db.execute("SELECT * FROM units WHERE id = ?", (unit_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Unit {unit_id!r} was not found")
        return self._unit_from_row(row)

    def list_units(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute("SELECT * FROM units ORDER BY updated_at DESC").fetchall()
        return [self._unit_from_row(row) for row in rows]

    def publish_unit(self, unit_id: str) -> dict[str, Any]:
        unit = self.get_unit(unit_id)
        if unit["status"] != "VERIFIED" or not unit["graph"]:
            raise ConflictError("Only a fully generated VERIFIED unit can be published")
        with self._write_lock, self.connection() as db:
            db.execute(
                "UPDATE units SET published = 1, updated_at = ? WHERE id = ?",
                (utc_now(), unit_id),
            )
            db.commit()
        return self.get_unit(unit_id)

    def list_library(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                """
                SELECT * FROM units
                WHERE published = 1 AND status = 'VERIFIED'
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._unit_from_row(row) for row in rows]

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "unit_id": row["unit_id"],
            "language": row["language"],
            "current_node_id": row["current_node_id"],
            "completed": bool(row["completed"]),
            "state": _loads(row["state_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def create_session(
        self, unit_id: str, language: str, current_node_id: str, state: dict[str, Any]
    ) -> dict[str, Any]:
        unit = self.get_unit(unit_id)
        if not unit["published"] or unit["status"] != "VERIFIED":
            raise ConflictError("The requested unit is not available in the student library")
        session_id = uuid.uuid4().hex
        now = utc_now()
        language = "zh" if language == "zh" else "en"
        with self._write_lock, self.connection() as db:
            db.execute(
                """
                INSERT INTO sessions(
                    id, unit_id, language, current_node_id, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, unit_id, language, current_node_id, _dumps(state), now, now),
            )
            db.execute(
                """
                INSERT INTO session_events(session_id, event_type, payload_json, created_at)
                VALUES (?, 'session_started', ?, ?)
                """,
                (session_id, _dumps({"node_id": current_node_id}), now),
            )
            db.commit()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self.connection() as db:
            row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Session {session_id!r} was not found")
        return self._session_from_row(row)

    def update_session(
        self,
        session_id: str,
        *,
        current_node_id: str,
        state: dict[str, Any],
        completed: bool,
        event_type: str,
        event_payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = utc_now()
        with self._write_lock, self.connection() as db:
            cursor = db.execute(
                """
                UPDATE sessions
                SET current_node_id = ?, state_json = ?, completed = ?, updated_at = ?
                WHERE id = ?
                """,
                (current_node_id, _dumps(state), int(completed), now, session_id),
            )
            if cursor.rowcount != 1:
                raise NotFoundError(f"Session {session_id!r} was not found")
            db.execute(
                """
                INSERT INTO session_events(session_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, event_type, _dumps(event_payload), now),
            )
            db.commit()
        return self.get_session(session_id)

    def update_session_language(self, session_id: str, language: str) -> dict[str, Any]:


        language = "zh" if language == "zh" else "en"
        now = utc_now()
        with self._write_lock, self.connection() as db:
            cursor = db.execute(
                "UPDATE sessions SET language = ?, updated_at = ? WHERE id = ?",
                (language, now, session_id),
            )
            if cursor.rowcount != 1:
                raise NotFoundError(f"Session {session_id!r} was not found")
            db.execute(
                """
                INSERT INTO session_events(session_id, event_type, payload_json, created_at)
                VALUES (?, 'language_changed', ?, ?)
                """,
                (session_id, _dumps({"language": language}), now),
            )
            db.commit()
        return self.get_session(session_id)

    def session_events(self, session_id: str) -> list[dict[str, Any]]:
        self.get_session(session_id)
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM session_events WHERE session_id = ? ORDER BY id", (session_id,)
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "payload": _loads(row["payload_json"], {}),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

