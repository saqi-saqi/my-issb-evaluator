"""
Unit tests for structured per-answer evaluation, confidence weighting, and 15-section report compilation.
"""

import pytest
from src.evaluator.rubric_engine import PerAnswerEvidence, RubricEvaluationEngine
from src.evaluator.score_calculator import (
    calculate_confidence_weighted_score,
    calculate_weighted_overall_score,
    format_evidence_table,
    get_performance_band,
)
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def evaluator():
    retriever = KnowledgeRetriever(use_chroma=False)
    return RubricEvaluationEngine(retriever=retriever)


def test_per_answer_evidence_extraction(evaluator):
    """Test that individual answer evaluation extracts observable indicators and confidence."""
    short_pair = {
        "question_id": "TEA_001",
        "category": "teamwork",
        "evaluation_dimension": "social_behaviour",
        "answer": "I worked in a team.",
    }
    short_ev = evaluator.evaluate_single_answer(short_pair)
    assert isinstance(short_ev, PerAnswerEvidence)
    assert short_ev.confidence <= 0.60
    assert len(short_ev.weaknesses) > 0

    detailed_pair = {
        "question_id": "LEA_001",
        "category": "leadership",
        "evaluation_dimension": "leadership",
        "answer": (
            "Specifically, during my term as captain of our college football team, "
            "when two forwards had a severe tactical disagreement, I called a team meeting. "
            "I took personal responsibility for the miscommunication and restructured our practice drills. "
            "Because of this, we won the regional semifinal."
        ),
    }
    detailed_ev = evaluator.evaluate_single_answer(detailed_pair)
    assert detailed_ev.confidence >= 0.80
    assert len(detailed_ev.positive_indicators) >= 2
    assert detailed_ev.score >= 75.0


def test_confidence_weighted_scoring():
    """Test mathematical behavior of confidence-weighted scoring formula."""
    evidences = [
        {"confidence": 0.90, "positive_indicators": ["Pos 1", "Pos 2"], "weaknesses": []},
        {"confidence": 0.30, "positive_indicators": [], "weaknesses": ["Weak 1"]},
    ]
    score = calculate_confidence_weighted_score(evidences, base_score=70.0)
    # The high confidence positive evidence should outweigh the low confidence weakness
    assert score > 70.0
    assert score <= 95.0


def test_15_section_report_structure(evaluator):
    """Test that generated report contains all required 15 distinct sections."""
    sample_qa = [
        {
            "question_id": "PER_001",
            "category": "personal",
            "evaluation_dimension": "social_behaviour",
            "question": "Tell me about your daily routine.",
            "answer": "I wake up early, focus on studies, and lead physical workouts with colleagues.",
            "follow_up": "How do you manage setbacks?",
            "follow_up_answer": "I analyze the root cause and adapt my routine without losing composure.",
        },
        {
            "question_id": "COM_001",
            "category": "communication",
            "evaluation_dimension": "intellect",
            "question": "Describe an instance where you gave a presentation.",
            "answer": "Specifically, in our annual college seminar I presented on renewable energy policy.",
        },
    ]

    report = evaluator.evaluate_interview_session(
        candidate_name="Muhammad Hassan",
        persona="deputy_president",
        qa_pairs=sample_qa,
    )

    # 1. Candidate Name & Profile
    assert report.candidate_name == "Muhammad Hassan"
    assert "name" in report.candidate_profile

    # 2. Session Metadata
    assert "session_date" in report.session_metadata

    # 3. Overall Practice Score & Performance Band
    assert 45.0 <= report.overall_practice_score <= 95.0
    band = get_performance_band(report.overall_practice_score)
    assert band["tier"] is not None

    # 4. Dimension Evaluations (5 dimensions)
    assert len(report.dimension_scores) == 5

    # 5. Per-Question Evidence Table
    assert len(report.per_question_evidence) == 2
    table = format_evidence_table(report.per_question_evidence)
    assert len(table) == 2
    assert "Question ID" in table[0]

    # 6. Strengths
    assert len(report.key_strengths) > 0

    # 7. Growth Areas
    assert len(report.growth_areas) > 0

    # 8-13. Dedicated Competency Assessments
    assert len(report.communication_assessment) > 10
    assert len(report.leadership_assessment) > 10
    assert len(report.decision_making_assessment) > 10
    assert len(report.teamwork_assessment) > 10
    assert len(report.motivation_assessment) > 10
    assert len(report.stress_response_assessment) > 10

    # 14. Actionable Preparation Recommendations
    assert len(report.preparation_recommendations) >= 3

    # 15. Methodological Disclaimer
    assert "does NOT represent an official selection prediction" in report.methodological_disclaimer

    # Verify serialization
    report_dict = report.to_dict()
    assert report_dict["candidate_name"] == "Muhammad Hassan"
    assert "per_question_evidence" in report_dict
