"""
Tests for public-deployment hardening behaviors:
LLM settings gating, request bounds, report idempotence, evaluation meta
stripping, SPA catch-all serving, and the rate limiter (including the
CORS echo on 429 responses).
"""

import pytest
from fastapi.testclient import TestClient

import backend.main as backend_main
from backend.api import app


@pytest.fixture
def client():
    return TestClient(app)


def _adequate_answer() -> str:
    """Long, ownership-heavy answer that avoids the follow-up probe branch."""
    return (
        "I led my section through the task because I planned each step in advance, "
        "briefed my teammates clearly, and adjusted the plan when we hit obstacles."
    )


def _complete_session(client) -> str:
    start = client.post(
        "/api/interview/start",
        json={"candidate_name": "Hardening Test", "num_questions": 2},
    )
    assert start.status_code == 200
    session_id = start.json()["session_id"]
    for _ in range(2):
        res = client.post(
            "/api/interview/answer",
            json={"session_id": session_id, "answer": _adequate_answer()},
        )
        assert res.status_code == 200
    return session_id


# --- 1. LLM settings endpoint gating ---

def test_settings_rejected_without_override(client, monkeypatch):
    monkeypatch.delenv("ALLOW_LLM_OVERRIDE", raising=False)
    monkeypatch.setattr(backend_main.ai_client, "_init_client", lambda: None)
    monkeypatch.setattr(backend_main.ai_client, "test_connection", lambda: (True, "ok"))
    res = client.post("/api/settings/llm", json={"api_key": "gsk_test_key"})
    assert res.status_code == 403


def test_settings_allowed_with_override(client, monkeypatch):
    monkeypatch.setenv("ALLOW_LLM_OVERRIDE", "true")
    monkeypatch.setattr(backend_main.ai_client, "_init_client", lambda: None)
    monkeypatch.setattr(backend_main.ai_client, "test_connection", lambda: (True, "ok"))
    res = client.post("/api/settings/llm", json={"api_key": "gsk_test_key"})
    assert res.status_code == 200
    assert res.json()["success"] is True


# --- 2. Request bounds ---

def test_answer_rejected_over_max_length(client):
    res = client.post(
        "/api/interview/answer",
        json={"session_id": "any", "answer": "a" * 4001},
    )
    assert res.status_code == 422


def test_follow_up_rejected_over_max_length(client):
    res = client.post(
        "/api/interview/followup",
        json={"session_id": "any", "follow_up_answer": "a" * 4001},
    )
    assert res.status_code == 422


def test_retry_rejected_over_max_length(client):
    res = client.post(
        "/api/learning/retry",
        json={"session_id": "any", "question_id": "TEA_001", "retry_answer": "a" * 4001},
    )
    assert res.status_code == 422


# --- 3. Report idempotence (single narrative generation per session) ---

def test_report_get_is_idempotent(client, monkeypatch):
    call_count = {"n": 0}
    original_generate = backend_main.interview_service.generate_final_report

    def counting_generate(session):
        call_count["n"] += 1
        return original_generate(session)

    monkeypatch.setattr(
        backend_main.interview_service, "generate_final_report", counting_generate
    )

    session_id = _complete_session(client)

    first = client.get(f"/api/interview/report/{session_id}")
    assert first.status_code == 200
    assert call_count["n"] == 1

    second = client.get(f"/api/interview/report/{session_id}")
    assert second.status_code == 200
    assert call_count["n"] == 1  # served from storage — no regeneration
    assert (
        second.json()["overall_practice_score"]
        == first.json()["overall_practice_score"]
    )


# --- 4. Evaluation meta stripping on /api/questions ---

def test_questions_meta_stripped_by_default(client, monkeypatch):
    monkeypatch.delenv("EXPOSE_EVALUATION_META", raising=False)
    res = client.get("/api/questions?category=teamwork")
    assert res.status_code == 200
    questions = res.json()
    assert questions
    for question in questions:
        assert "intent" not in question
        assert "follow_up_pool" not in question
        assert question["question"]


def test_questions_meta_exposed_with_override(client, monkeypatch):
    monkeypatch.setenv("EXPOSE_EVALUATION_META", "true")
    res = client.get("/api/questions?category=teamwork")
    assert res.status_code == 200
    questions = res.json()
    assert questions
    for question in questions:
        assert "intent" in question
        assert "follow_up_pool" in question


# --- 5. SPA catch-all serving ---

def test_spa_serves_index_at_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "MY_ISSB_Evaluator" in res.text or "<div id=\"root\">" in res.text


def test_spa_fallback_for_unknown_path(client):
    res = client.get("/some/unknown/client/route")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


# --- 6. Rate limiter ---

def _find_rate_limiter():
    node = backend_main.app.middleware_stack
    while node is not None:
        if isinstance(node, backend_main.LLMRateLimitMiddleware):
            return node
        node = getattr(node, "app", None)
    return None


def test_rate_limiter_returns_429_with_cors_header(client, monkeypatch):
    monkeypatch.setenv("LLM_OPS_PER_MINUTE", "2")
    # Warm up the ASGI stack so the middleware instance is reachable.
    client.get("/api/status")
    limiter = _find_rate_limiter()
    assert limiter is not None
    limiter.events.clear()

    headers = {"Origin": "http://localhost:5173"}
    for _ in range(2):
        res = client.get("/api/interview/report/does-not-exist", headers=headers)
        assert res.status_code == 404

    limited = client.get("/api/interview/report/does-not-exist", headers=headers)
    assert limited.status_code == 429
    assert "retry-after" in {k.lower() for k in limited.headers}
    assert limited.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert limited.json()["detail"] == "Rate limit exceeded. Please try again shortly."
