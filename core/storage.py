"""
SQLite Persistence Layer for MY_ISSB_Evaluator.
Provides lightweight, reliable local persistence for interview sessions and candidate learning profiles.
Uses Python standard library sqlite3 (zero new external dependencies).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
from contextlib import closing
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "issb_evaluator.db"


class StorageManager:
    """Manages SQLite persistence for interview sessions, reports, and learning profiles."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path)

        if self.db_path != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        """Initializes database schema with required tables and indexes."""
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id TEXT PRIMARY KEY,
                    candidate_id TEXT,
                    candidate_name TEXT,
                    persona TEXT,
                    completed INTEGER DEFAULT 0,
                    current_index INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    data TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_profiles (
                    session_id TEXT PRIMARY KEY,
                    candidate_id TEXT,
                    candidate_name TEXT,
                    profile_data TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_reports (
                    session_id TEXT PRIMARY KEY,
                    candidate_id TEXT,
                    candidate_name TEXT,
                    report_data TEXT,
                    created_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            for table in ("interview_sessions", "learning_profiles", "evaluation_reports"):
                columns = {row["name"] for row in cursor.execute(f"PRAGMA table_info({table})")}
                if "candidate_id" not in columns:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN candidate_id TEXT")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_candidate_id ON {table}(candidate_id)")
            conn.commit()

    # --- Session Operations ---

    def save_session(self, session_dict: Dict[str, Any]) -> None:
        session_id = session_dict["session_id"]
        candidate_name = session_dict.get("candidate_name", "Candidate")
        candidate_id = session_dict.get("candidate_id")
        persona = session_dict.get("persona", "deputy_president")
        completed = 1 if session_dict.get("completed", False) else 0
        current_index = session_dict.get("current_index", 0)
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(session_dict)

        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO interview_sessions 
                    (session_id, candidate_id, candidate_name, persona, completed, current_index, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    candidate_name = excluded.candidate_name,
                    candidate_id = excluded.candidate_id,
                    persona = excluded.persona,
                    completed = excluded.completed,
                    current_index = excluded.current_index,
                    updated_at = excluded.updated_at,
                    data = excluded.data
                """,
                (session_id, candidate_id, candidate_name, persona, completed, current_index, now, now, data_json),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM interview_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["data"])
        return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT                 session_id, candidate_id, candidate_name, persona, completed, current_index, created_at, updated_at
                FROM interview_sessions ORDER BY updated_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- Profile Operations ---

    def save_profile(self, session_id: str, profile_dict: Dict[str, Any]) -> None:
        candidate_name = profile_dict.get("candidate_name", "Candidate")
        candidate_id = profile_dict.get("candidate_id")
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(profile_dict)

        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO learning_profiles
                    (session_id, candidate_id, candidate_name, profile_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    candidate_name = excluded.candidate_name,
                    candidate_id = excluded.candidate_id,
                    profile_data = excluded.profile_data,
                    updated_at = excluded.updated_at
                """,
                (session_id, candidate_id, candidate_name, data_json, now, now),
            )
            conn.commit()

    def get_profile(self, session_id: str) -> Optional[Dict[str, Any]]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT profile_data FROM learning_profiles WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["profile_data"])
        return None

    # --- Report Operations ---

    def save_report(self, session_id: str, candidate_name: str, report_dict: Dict[str, Any], candidate_id: Optional[str] = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(report_dict)

        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evaluation_reports
                    (session_id, candidate_id, candidate_name, report_data, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    candidate_name = excluded.candidate_name,
                    candidate_id = excluded.candidate_id,
                    report_data = excluded.report_data
                """,
                (session_id, candidate_id, candidate_name, data_json, now),
            )
            conn.commit()

    def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT report_data FROM evaluation_reports WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["report_data"])
        return None

    def upsert_candidate(self, candidate_id: str, display_name: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._get_connection()) as conn:
            conn.execute(
                """
                INSERT INTO candidates (candidate_id, display_name, created_at, last_seen_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    last_seen_at = excluded.last_seen_at
                """,
                (candidate_id, display_name, now, now),
            )
            conn.commit()

    def get_progress(self, candidate_id: str) -> Dict[str, Any]:
        with closing(self._get_connection()) as conn:
            rows = conn.execute(
                """
                SELECT r.session_id, r.candidate_name, r.created_at, s.persona, r.report_data
                FROM evaluation_reports r
                LEFT JOIN interview_sessions s ON s.session_id = r.session_id
                WHERE r.candidate_id = ?
                ORDER BY r.created_at ASC
                """,
                (candidate_id,),
            ).fetchall()
        sessions = []
        trend = []
        for row in rows:
            report = json.loads(row["report_data"])
            sessions.append({
                "session_id": row["session_id"],
                "candidate_name": row["candidate_name"],
                "persona": row["persona"],
                "date": row["created_at"],
                "score": report.get("overall_practice_score", 0),
                "performance_band": report.get("performance_band", {}),
            })
            trend.append({
                "session_id": row["session_id"],
                "date": row["created_at"],
                "score": report.get("overall_practice_score", 0),
                "olq_scores": report.get("fourteen_olq_scores", {}),
            })
        return {
            "candidate_id": candidate_id,
            "total_sessions": len(sessions),
            "sessions": sessions,
            "trend": trend,
            "latest": sessions[-1] if sessions else None,
        }
