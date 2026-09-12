"""
Comprehensive test suite for the consolidated core architecture (MY_ISSB_Evaluator FYP).
Verifies:
1. QuestionBank single-file loader & calibrated progression.
2. RAG TF-IDF retriever across all 5 tiers with citations.
3. Deterministic 14-OLQ & 5-Dimension scoring.
4. 2-Pass rubric evaluator with observable indicators.
5. LearningService feedback & honest before/after retry comparisons.
6. InterviewService state machine & adaptive probing triggers.
7. FastAPI REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from core.ai import AIClient
from core.evaluator import RubricEvaluator
from core.interview import InterviewService
from core.learning import LearningService
from core.questions import QuestionBank
from core.rag import KnowledgeRetriever
from core.scoring import (
    FOURTEEN_OLQS,
    calculate_14_olq_scores,
    calculate_dashboard_dimensions,
    calculate_overall_score,
    get_performance_band,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def qb():
    return QuestionBank()


@pytest.fixture
def retriever():
    return KnowledgeRetriever()


@pytest.fixture
def evaluator(retriever):
    return RubricEvaluator(retriever=retriever)


@pytest.fixture
def learning():
    return LearningService()


@pytest.fixture
def interview_service(qb, retriever, evaluator, learning):
    return InterviewService(question_bank=qb, retriever=retriever, evaluator=evaluator, learning=learning)


# --- 1. Question Bank Tests ---

def test_question_bank_loads_47_questions(qb):
    assert len(qb.questions) == 47
    assert len(qb.categories) >= 12
    q1 = qb.get_question("PER_001")
    assert q1 is not None
    assert q1.category == "personal"
    assert len(q1.follow_up_pool) > 0


def test_calibrated_sequence_builder(qb):
    seq = qb.build_interview_sequence(persona="deputy_president", num_questions=5)
    assert len(seq) == 5
    # Sequence follows calibrated stages
    assert seq[0].category == "personal"
    assert seq[1].category == "education"


# --- 2. RAG Knowledge Retriever Tests ---

def test_rag_retrieves_chunks_with_citations(retriever):
    assert len(retriever.chunks) > 0
    results = retriever.retrieve("leadership in crisis decision making", top_k=2)
    assert len(results) > 0
    first = results[0]
    assert "citation" in first
    assert first["tier"] in ["official", "academic", "evaluation", "preparation", "current_affairs"]
    assert first["score"] > 0.0


def test_rag_metadata_tier_filter(retriever):
    results = retriever.retrieve("selection criteria", top_k=3, tier="official")
    for r in results:
        assert r["tier"] == "official"


# --- 3. Deterministic Scoring Tests ---

def test_scoring_bounds_and_bands():
    band_high = get_performance_band(88.0)
    assert band_high["tier"] == "High Practice Readiness"
    band_low = get_performance_band(40.0)
    assert band_low["tier"] == "Substantial Preparation Required"

    dims = {
        "Intellect & Reasoning": 80.0,
        "Emotional Composure": 75.0,
        "Social Adaptability & Teamwork": 85.0,
        "Communication & Expression": 70.0,
        "Motivation & Integrity": 80.0,
    }
    overall = calculate_overall_score(dims)
    assert 70.0 <= overall <= 85.0


# --- 4. 2-Pass Evaluator Tests ---

def test_evaluator_evasive_monosyllabic(evaluator):
    ev = evaluator.evaluate_answer_evidence(
        question_id="Q001",
        question_text="Tell me about a time you made a mistake.",
        category="personal",
        dimension="integrity",
        intent="ownership",
        primary_answer="no",
    )
    assert ev.score <= 30.0
    assert ev.evidence_confidence == "NONE"
    assert any("evasive" in w.lower() or "brief" in w.lower() for w in ev.weaknesses)


def test_evaluator_ownership_and_concrete_example(evaluator):
    ev = evaluator.evaluate_answer_evidence(
        question_id="Q002",
        question_text="Tell me about a time you led a team.",
        category="leadership",
        dimension="leadership",
        intent="initiative",
        primary_answer="Specifically, in my college football team, I led our squad through a tough tournament. My mistake was poor communication initially, so I decided to organize daily strategy sessions. Consequently, we achieved second place.",
    )
    assert ev.score >= 80.0
    assert ev.evidence_confidence == "HIGH"
    assert any("accountability" in p.lower() or "ownership" in p.lower() for p in ev.positive_indicators)


def test_evaluator_pass2_session_report(evaluator):
    ev1 = evaluator.evaluate_answer_evidence(
        question_id="Q001",
        question_text="Tell me about yourself.",
        category="personal",
        dimension="communication",
        intent="background",
        primary_answer="I am an undergraduate student who took responsibility for our community service drive.",
    )
    report = evaluator.evaluate_session(
        candidate_name="Cadet Ali",
        persona="deputy_president",
        evidence_list=[ev1],
    )
    assert report.candidate_name == "Cadet Ali"
    assert len(report.fourteen_olq_scores) == len(FOURTEEN_OLQS)
    assert len(report.dimension_scores) == 5
    assert report.overall_practice_score > 0.0


# --- 5. Learning & Retry Service Tests ---

def test_learning_generates_actionable_technique(learning, evaluator):
    ev = evaluator.evaluate_answer_evidence(
        question_id="Q003",
        question_text="Describe your weaknesses.",
        category="personal",
        dimension="self_awareness",
        intent="honesty",
        primary_answer="I don't really have any weakness.",
    )
    feedback = learning.generate_feedback(ev)
    assert feedback["status"] == "needs_practice"
    assert len(feedback["improvement_areas"]) > 0
    first_area = feedback["improvement_areas"][0]
    assert "recommended_technique" in first_area
    assert "why_it_matters" in first_area


def test_learning_retry_honest_delta(learning):
    # Unimproved retry
    comp_bad = learning.evaluate_retry(
        question_id="Q004",
        original_answer="no comments",
        retry_answer="none",
        original_score=30.0,
    )
    assert not comp_bad.improved
    assert comp_bad.score_delta <= 0.0

    # Genuine improved retry
    comp_good = learning.evaluate_retry(
        question_id="Q004",
        original_answer="no comments",
        retry_answer="Specifically, in my college project I decided to take personal responsibility for the code deadline because our team was falling behind, and we succeeded.",
        original_score=30.0,
    )
    assert comp_good.improved
    assert comp_good.score_delta > 0.0
    assert len(comp_good.changes_detected) > 0


# --- 6. InterviewService State Machine Tests ---

def test_interview_service_adaptive_probe(interview_service):
    session = interview_service.start_session(candidate_name="Hamza", persona="deputy_president", num_questions=3)
    assert session.current_index == 0
    assert not session.completed

    # Very short answer triggers follow-up probe
    has_fu, probe_text = interview_service.submit_primary_answer(session, "yes")
    assert has_fu
    assert probe_text is not None
    assert session.current_index == 0  # Still on first question awaiting probe answer

    # Submit probe answer
    interview_service.submit_follow_up_answer(session, "Specifically, I mean that during my exams I managed my routine strictly.")
    assert session.current_index == 1  # Advanced to second question


# --- 7. FastAPI Endpoint Tests ---

def test_api_system_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["question_bank_total"] == 47


def test_api_full_interview_lifecycle(client):
    # 1. Start
    res_start = client.post("/api/interview/start", json={"candidate_name": "Tariq", "persona": "deputy_president", "num_questions": 2})
    assert res_start.status_code == 200
    start_data = res_start.json()
    session_id = start_data["session_id"]
    q1_id = start_data["current_question"]["id"]

    # 2. Answer Question 1
    res_ans1 = client.post("/api/interview/answer", json={
        "session_id": session_id,
        "answer": "Specifically, in my college I led our debate team and took responsibility for mentoring junior debaters.",
    })
    assert res_ans1.status_code == 200
    ans1_data = res_ans1.json()
    assert not ans1_data["has_follow_up"]
    assert ans1_data["current_index"] == 1

    # 3. Answer Question 2
    res_ans2 = client.post("/api/interview/answer", json={
        "session_id": session_id,
        "answer": "I decided to pursue the armed forces because of personal motivation and a desire to serve with integrity.",
    })
    assert res_ans2.status_code == 200
    ans2_data = res_ans2.json()
    assert ans2_data["is_completed"]

    # 4. Fetch Final Report
    res_report = client.get(f"/api/interview/report/{session_id}")
    assert res_report.status_code == 200
    report_data = res_report.json()
    assert report_data["candidate_name"] == "Tariq"
    assert report_data["overall_practice_score"] > 0.0
    assert len(report_data["fourteen_olq_scores"]) == 14
    assert len(report_data["radar_chart_data"]) == 5

    # 5. Get Learning Feedback & Retry
    res_fb = client.post("/api/learning/feedback", json={"session_id": session_id, "question_id": q1_id})
    assert res_fb.status_code == 200

    res_retry = client.post("/api/learning/retry", json={
        "session_id": session_id,
        "question_id": q1_id,
        "retry_answer": "Specifically, in my college I led our debate team and took personal responsibility for daily training drills.",
    })
    assert res_retry.status_code == 200
    retry_data = res_retry.json()
    assert "before_after" in retry_data
