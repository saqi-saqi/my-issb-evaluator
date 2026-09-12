"""
Unit tests for FastAPI REST backend endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["knowledge_base_chunks"] > 0
    assert data["question_bank_total"] >= 47
    assert data["categories_total"] == 13


def test_api_categories(client):
    res = client.get("/api/categories")
    assert res.status_code == 200
    cats = res.json()
    assert len(cats) == 13
    cat_names = {c["category"] for c in cats}
    assert "teamwork" in cat_names
    assert "communication" in cat_names
    assert "confidence" in cat_names
    assert "responsibility" in cat_names


def test_api_questions_filter(client):
    res = client.get("/api/questions?category=leadership")
    assert res.status_code == 200
    qs = res.json()
    assert len(qs) > 0
    for q in qs:
        assert q["category"] == "leadership"


def test_api_rag_search(client):
    payload = {
        "query": "qualities of an officer clear thinking",
        "top_k": 3,
        "prefer_official": True,
    }
    res = client.post("/api/rag/search", json=payload)
    assert res.status_code == 200
    chunks = res.json()
    assert len(chunks) > 0
    assert "citation" in chunks[0]


def test_api_interview_flow_and_report(client):
    # 1. Start interview
    start_payload = {
        "candidate_name": "Test Cadet",
        "persona": "deputy_president",
        "num_questions": 2,
    }
    start_res = client.post("/api/interview/start", json=start_payload)
    assert start_res.status_code == 200
    session_data = start_res.json()
    session_id = session_data["session_id"]
    assert len(session_id) > 10
    assert "current_question" in session_data

    # 2. Submit primary answer
    answer_payload = {
        "session_id": session_id,
        "answer": "I believe in personal accountability and systematic planning.",
    }
    ans_res = client.post("/api/interview/answer", json=answer_payload)
    assert ans_res.status_code == 200
    ans_data = ans_res.json()

    # If follow-up triggered, submit follow-up
    if ans_data["has_follow_up"]:
        fu_payload = {
            "session_id": session_id,
            "follow_up_answer": "Specifically in our team project I distributed tasks evenly.",
        }
        fu_res = client.post("/api/interview/follow-up", json=fu_payload)
        assert fu_res.status_code == 200

    # 3. Answer remaining questions until completed
    # (or answer second question)
    second_ans_payload = {
        "session_id": session_id,
        "answer": "In situational challenges I keep calm and deconstruct priorities.",
    }
    ans_res2 = client.post("/api/interview/answer", json=second_ans_payload)
    assert ans_res2.status_code == 200

    if ans_res2.json().get("has_follow_up"):
        client.post("/api/interview/follow-up", json={
            "session_id": session_id,
            "follow_up_answer": "I resolved the issue by open dialogue.",
        })

    # 4. Generate final report
    report_res = client.get(f"/api/interview/report/{session_id}")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["candidate_name"] == "Test Cadet"
    assert "overall_practice_score" in report
    assert "radar_chart_data" in report
    assert "formatted_evidence_table" in report
    assert len(report["radar_chart_data"]) == 5


def test_api_learning_endpoints(client):
    # 1. Start interview
    start_payload = {
        "candidate_name": "Test Cadet Learning",
        "persona": "deputy_president",
        "num_questions": 2,
    }
    start_res = client.post("/api/interview/start", json=start_payload)
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]
    q_id = start_res.json()["current_question"]["id"]

    # 2. Submit initial answer lacking personal ownership
    ans_res = client.post("/api/interview/answer", json={
        "session_id": session_id,
        "answer": "During our college project, our team faced a delay and we worked overtime every evening to finish the work.",
    })
    assert ans_res.status_code == 200
    if ans_res.json().get("has_follow_up"):
        client.post("/api/interview/follow-up", json={
            "session_id": session_id,
            "follow_up_answer": "The team agreed together to stay late.",
        })

    # 3. Request learning feedback
    fb_res = client.post("/api/learning/feedback", json={
        "session_id": session_id,
        "question_id": q_id,
    })
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert "learning_phase" in fb_data
    lp = fb_data["learning_phase"]
    assert len(lp["improvement_areas"]) >= 1
    assert lp["retry"]["enabled"] is True

    # 4. Submit retry answer with strong personal accountability
    retry_res = client.post("/api/learning/retry", json={
        "session_id": session_id,
        "question_id": q_id,
        "retry_answer": "I take full responsibility for the delay because I did not allocate tasks properly. I stepped in, organized a new schedule, and resolved the problem.",
    })
    assert retry_res.status_code == 200
    retry_data = retry_res.json()
    assert "before_after" in retry_data
    assert retry_data["before_after"]["change"] > 0
    assert "Ownership / Accountability" in retry_data["before_after"]["improved_areas"]

    # 5. Get learning profile & session learning report
    prof_res = client.get(f"/api/learning/profile/{session_id}")
    assert prof_res.status_code == 200
    prof_data = prof_res.json()
    assert "learning_profile" in prof_data
    assert "session_learning_report" in prof_data
    assert "Ownership / Accountability" in prof_data["learning_profile"]["improving_areas"]
    assert prof_data["session_learning_report"]["candidate_name"] == "Test Cadet Learning"
