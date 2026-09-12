"""
Unit tests for 14-OLQ scoring layer, 3-tier mapping, and claim-level evidence grounding.
"""

import pytest
from src.evaluator.score_calculator import (
    FOURTEEN_OLQS,
    calculate_14_olq_scores,
    calculate_dashboard_dimensions_from_olqs,
    calculate_weighted_overall_score,
)
from src.evaluator.rubric_engine import RubricEvaluationEngine
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def rubric_engine():
    retriever = KnowledgeRetriever(use_chroma=False)
    return RubricEvaluationEngine(retriever=retriever)


def test_fourteen_olqs_count():
    """Verify exactly 14 OLQs are defined."""
    assert len(FOURTEEN_OLQS) == 14
    assert "Reasoning Ability" in FOURTEEN_OLQS
    assert "Integrity" in FOURTEEN_OLQS
    assert "Emotional Stability" in FOURTEEN_OLQS


def test_3_tier_scoring_aggregation():
    """Test 14-OLQ calculation from evidence items and mapping to 5 dashboard dimensions."""
    sample_evidence = [
        {
            "question_id": "Q1",
            "category": "leadership",
            "dimension": "deputy_president",
            "score": 85.0,
            "confidence": 0.90,
        },
        {
            "question_id": "Q2",
            "category": "responsibility",
            "dimension": "psychologist",
            "score": 80.0,
            "confidence": 0.85,
        },
        {
            "question_id": "Q3",
            "category": "stress",
            "dimension": "psychologist",
            "score": 78.0,
            "confidence": 0.80,
        },
    ]

    olq_scores = calculate_14_olq_scores(sample_evidence)
    assert len(olq_scores) == 14
    for olq, score in olq_scores.items():
        assert 10.0 <= score <= 95.0

    # Test derived dashboard dimensions
    dashboard = calculate_dashboard_dimensions_from_olqs(olq_scores)
    assert len(dashboard) == 5
    assert "Intellect & Reasoning" in dashboard
    assert "Emotional Composure" in dashboard
    assert "Social Adaptability & Teamwork" in dashboard
    assert "Communication & Expression" in dashboard
    assert "Motivation & Integrity" in dashboard


def test_substance_over_length_scoring(rubric_engine):
    """Test that a short answer with clear ownership receives strong evidence score, not a length penalty."""
    short_responsible_answer = {
        "question_id": "Q_resp_1",
        "category": "responsibility",
        "evaluation_dimension": "psychologist",
        "question": "Tell me about a time your team failed a project deadline.",
        "intent": "Evaluate personal accountability and honesty",
        "answer": "Yes, I accept full responsibility for that failure. I miscalculated the schedule and apologized to the team.",
        "follow_up": "",
        "follow_up_answer": "",
    }

    evidence = rubric_engine.evaluate_single_answer(short_responsible_answer)
    assert evidence.score >= 75.0, "Short answer with direct ownership must not receive arbitrary word-count penalty"
    assert evidence.evidence_confidence == "HIGH"
    assert any("accountability" in p.lower() or "ownership" in p.lower() for p in evidence.positive_indicators)
