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
        return conn

    def _init_db(self) -> None:
        """Initializes database schema with required tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id TEXT PRIMARY KEY,
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
                    candidate_name TEXT,
                    report_data TEXT,
                    created_at TEXT
                )
                """
            )
            conn.commit()

    # --- Session Operations ---

    def save_session(self, session_dict: Dict[str, Any]) -> None:
        session_id = session_dict["session_id"]
        candidate_name = session_dict.get("candidate_name", "Candidate")
        persona = session_dict.get("persona", "deputy_president")
        completed = 1 if session_dict.get("completed", False) else 0
        current_index = session_dict.get("current_index", 0)
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(session_dict)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO interview_sessions 
                    (session_id, candidate_name, persona, completed, current_index, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    candidate_name = excluded.candidate_name,
                    persona = excluded.persona,
                    completed = excluded.completed,
                    current_index = excluded.current_index,
                    updated_at = excluded.updated_at,
                    data = excluded.data
                """,
                (session_id, candidate_name, persona, completed, current_index, now, now, data_json),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_id, candidate_name, persona, completed, current_index, created_at, updated_at
                FROM interview_sessions ORDER BY updated_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- Profile Operations ---

    def save_profile(self, session_id: str, profile_dict: Dict[str, Any]) -> None:
        candidate_name = profile_dict.get("candidate_name", "Candidate")
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(profile_dict)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO learning_profiles
                    (session_id, candidate_name, profile_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    candidate_name = excluded.candidate_name,
                    profile_data = excluded.profile_data,
                    updated_at = excluded.updated_at
                """,
                (session_id, candidate_name, data_json, now, now),
            )
            conn.commit()

    def get_profile(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
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

    def save_report(self, session_id: str, candidate_name: str, report_dict: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps(report_dict)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evaluation_reports
                    (session_id, candidate_name, report_data, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    candidate_name = excluded.candidate_name,
                    report_data = excluded.report_data
                """,
                (session_id, candidate_name, data_json, now),
            )
            conn.commit()

    def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT report_data FROM evaluation_reports WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["report_data"])
        return None
