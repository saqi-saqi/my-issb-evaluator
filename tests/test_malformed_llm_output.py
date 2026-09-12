"""
Unit tests for malformed LLM output handling, JSON schema parsing, and graceful degradation.
"""

from unittest.mock import MagicMock
import pytest

from src.evaluator.rubric_engine import RubricEvaluationEngine
from src.llm.client import LLMClient
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def mock_llm():
    client = LLMClient()
    client.is_configured = MagicMock(return_value=True)
    return client


@pytest.fixture
def retriever():
    return KnowledgeRetriever(use_chroma=False)


def test_llm_returns_garbage_text(retriever, mock_llm):
    """Test that when LLM returns pure non-JSON garbage, engine degrades gracefully to heuristic evaluation."""
    mock_llm.generate_response = MagicMock(return_value="I am an AI and I cannot evaluate this candidate because reasons.")

    engine = RubricEvaluationEngine(retriever=retriever, llm_client=mock_llm)
    qa_sample = [
        {
            "question_id": "LEA_001",
            "category": "leadership",
            "evaluation_dimension": "leadership",
            "question": "Tell me about leading a team.",
            "answer": "I organized our team project and took responsibility when issues arose.",
        }
    ]

    report = engine.evaluate_interview_session("Test Candidate", "deputy_president", qa_sample)
    assert report is not None
    assert 45.0 <= report.overall_practice_score <= 95.0
    for dim_eval in report.dimension_evaluations.values():
        assert 45.0 <= dim_eval.dimension_score <= 95.0
        assert len(dim_eval.positive_indicators_observed) > 0


def test_llm_returns_markdown_wrapped_json(retriever, mock_llm):
    """Test that markdown code blocks (```json ... ```) are correctly parsed."""
    valid_json_in_md = """
    ```json
    {
        "dimension_score": 82.5,
        "positive_indicators_observed": ["Clear logical deconstruction", "Calm demeanor"],
        "weaknesses_observed": ["Could cite more specific examples"],
        "detailed_feedback": "The candidate presented clear logical deconstruction."
    }
    ```
    """
    mock_llm.generate_response = MagicMock(return_value=valid_json_in_md)

    engine = RubricEvaluationEngine(retriever=retriever, llm_client=mock_llm)
    qa_sample = [
        {
            "question_id": "DEC_001",
            "category": "decision_making",
            "evaluation_dimension": "decision_making",
            "question": "How do you make difficult choices under pressure?",
            "answer": "I analyze the facts, weigh priorities, and choose the most effective path.",
        }
    ]

    report = engine.evaluate_interview_session("Candidate", "deputy_president", qa_sample)
    assert report is not None
    # Verify citations guardrail was injected automatically
    for dim_eval in report.dimension_evaluations.values():
        assert "**According to official ISSB guidelines**" in dim_eval.detailed_feedback
        assert "**Based on the project's behavioral evaluation rubric**" in dim_eval.detailed_feedback


def test_llm_score_clamping_guardrail(retriever, mock_llm):
    """Test that out-of-bounds scores (e.g. 150.0 or -20.0) are clamped into [45.0, 95.0]."""
    crazy_score_json = """
    {
        "dimension_score": 150.0,
        "positive_indicators_observed": ["Superhuman"],
        "weaknesses_observed": [],
        "detailed_feedback": "Exceeded all known limits."
    }
    """
    mock_llm.generate_response = MagicMock(return_value=crazy_score_json)

    engine = RubricEvaluationEngine(retriever=retriever, llm_client=mock_llm)
    qa_sample = [{"question_id": "PER_001", "category": "personal", "question": "Hi", "answer": "Hello"}]

    report = engine.evaluate_interview_session("Candidate", "deputy_president", qa_sample)
    for dim_eval in report.dimension_evaluations.values():
        assert dim_eval.dimension_score <= 95.0
        assert dim_eval.dimension_score >= 45.0
