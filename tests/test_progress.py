"""
Tests for device-token candidate progress tracking:
candidate persistence, session linkage, the /api/progress endpoint, and the
learning-profile storage fallback that preserves retry history across restarts.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import backend.main as backend_main
from backend.api import app
from core.interview import InterviewService
from core.learning import LearningService
from core.questions import QuestionBank
from core.rag import KnowledgeRetriever
from core.storage import StorageManager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def isolated_service(tmp_path):
    """Replaces the module-level interview service with one on a temp DB."""
    storage = StorageManager(db_path=tmp_path / "progress.db")
    service = InterviewService(
        question_bank=QuestionBank(),
        retriever=KnowledgeRetriever(),
        ai=backend_main.ai_client,
        storage=storage,
    )
    original = backend_main.interview_service
    backend_main.interview_service = service
    yield service
    backend_main.interview_service = original


def _adequate_answer() -> str:
    return (
        "I led my section through the task because I planned each step in advance, "
        "briefed my teammates clearly, and adjusted the plan when we hit obstacles."
    )


def test_progress_tracks_completed_session(client, isolated_service):
    start = client.post(
        "/api/interview/start",
        json={
            "candidate_name": "Progress Test",
            "candidate_id": "cand-test-1",
            "num_questions": 2,
        },
    )
    assert start.status_code == 200
    session_id = start.json()["session_id"]
    assert start.json()["candidate_id"] == "cand-test-1"

    # No report yet — progress exists but is empty.
    empty = isolated_service.storage.get_progress("cand-test-1")
    assert empty["total_sessions"] == 0

    for _ in range(2):
        res = client.post(
            "/api/interview/answer",
            json={"session_id": session_id, "answer": _adequate_answer()},
        )
        assert res.status_code == 200

    report = client.get(f"/api/interview/report/{session_id}")
    assert report.status_code == 200

    res = client.get("/api/progress/cand-test-1")
    assert res.status_code == 200
    progress = res.json()
    assert progress["candidate_id"] == "cand-test-1"
    assert progress["total_sessions"] == 1
    assert progress["latest"]["candidate_name"] == "Progress Test"
    assert 0 <= progress["latest"]["score"] <= 100
    assert progress["latest"]["performance_band"]
    assert progress["trend"][0]["olq_scores"]
    assert progress["sessions"][0]["session_id"] == session_id


def test_progress_unknown_candidate_is_empty(client):
    res = client.get("/api/progress/no-such-candidate")
    assert res.status_code == 200
    assert res.json()["total_sessions"] == 0
    assert res.json()["latest"] is None


def test_progress_blank_candidate_id_rejected(client):
    res = client.get("/api/progress/%20")
    assert res.status_code == 400


def test_upsert_candidate_updates_display_name(tmp_path):
    storage = StorageManager(db_path=tmp_path / "candidates.db")
    storage.upsert_candidate("cand-1", "Ali")
    storage.upsert_candidate("cand-1", "Ali Raza")

    rows = storage.get_progress("cand-1")  # candidate row exists even without sessions
    assert rows["candidate_id"] == "cand-1"


def test_record_session_preserves_history_from_storage(tmp_path):
    """After a cold restart, regenerating a profile must not wipe retry history."""
    storage = StorageManager(db_path=tmp_path / "restart.db")
    storage.save_profile(
        "sess-1",
        {
            "session_id": "sess-1",
            "candidate_id": "cand-1",
            "candidate_name": "Ali",
            "improving_areas": ["Expression"],
            "practice_history": [{"question_id": "TEA_001", "improved": True}],
        },
    )

    # Brand-new in-memory state, same database — the simulated restart.
    fresh_service = LearningService(ai=MagicMock(), storage=storage)
    fresh_service.record_session(
        "sess-1",
        "Ali",
        {
            "overall_practice_score": 82,
            "performance_band": {"tier": "Strong Potential"},
            "key_strengths": ["ownership"],
            "primary_shortcomings": [],
        },
    )

    profile = storage.get_profile("sess-1")
    assert len(profile["practice_history"]) == 1
    assert profile["practice_history"][0]["question_id"] == "TEA_001"
    assert profile["candidate_id"] == "cand-1"
    assert profile["improving_areas"] == ["Expression"]
