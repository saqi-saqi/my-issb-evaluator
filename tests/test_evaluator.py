"""
Unit tests for RubricEvaluationEngine and Score Calculator.
Verifies observable indicator extraction, citations, and defensible wording guardrails.
"""

import pytest
from src.evaluator.rubric_engine import RubricEvaluationEngine
from src.evaluator.score_calculator import get_performance_band, format_radar_chart_data
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def evaluator():
    retriever = KnowledgeRetriever(use_chroma=False)
    return RubricEvaluationEngine(retriever)


def test_evaluator_guardrails_and_citations(evaluator):
    sample_transcript = [
        {
            "question_id": "PER_001",
            "category": "personal",
            "question": "Tell me about yourself.",
            "answer": "I wake up at 5:30 AM every morning for physical training and running. I prioritize my academic studies and spend time playing football with my college squad.",
        },
        {
            "question_id": "LEA_001",
            "category": "leadership",
            "question": "Tell me about leading a team.",
            "answer": "When our team project had a major disagreement, we sat together to deconstruct the problem. As the group leader, I took responsibility for the initial delay and organized clear tasks for everyone.",
        },
    ]

    report = evaluator.evaluate_interview_session(
        candidate_name="Ali Khan",
        persona="deputy_president",
        qa_pairs=sample_transcript,
    )

    # Check overall score range
    assert 40.0 <= report.overall_practice_score <= 100.0

    # Ensure all 5 core dimensions are evaluated
    expected_dims = {
        "Intellect & Reasoning",
        "Emotional Composure",
        "Social Adaptability & Teamwork",
        "Communication & Expression",
        "Motivation & Integrity",
    }
    assert set(report.dimension_scores.keys()) == expected_dims

    # CRITICAL GUARDRAIL CHECKS:
    # 1. Must contain disclaimer that it is NOT an official selection prediction
    assert "formative coaching feedback and does NOT represent an official selection prediction" in report.methodological_disclaimer

    # 2. Must cite official guidelines and academic/project rubric
    found_official_phrase = False
    found_rubric_phrase = False
    for eval_item in report.dimension_evaluations.values():
        if "According to official ISSB guidelines" in eval_item.detailed_feedback:
            found_official_phrase = True
        if "Based on the project's behavioral evaluation rubric" in eval_item.detailed_feedback:
            found_rubric_phrase = True

    assert found_official_phrase, "Evaluation must cite official ISSB guidelines"
    assert found_rubric_phrase, "Evaluation must distinguish project rubric"


def test_performance_band():
    band_high = get_performance_band(88.0)
    assert band_high["tier"] == "High Practice Readiness"

    band_mid = get_performance_band(72.0)
    assert band_mid["tier"] == "Solid Competency Demonstrated"

    band_dev = get_performance_band(60.0)
    assert band_dev["tier"] == "Developing Readiness"
