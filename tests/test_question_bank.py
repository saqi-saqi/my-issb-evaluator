"""
Unit tests for Question Bank Loader & Schema.
"""

from pathlib import Path
import pytest

from src.question_bank.loader import QuestionBank, QuestionItem


@pytest.fixture
def question_bank():
    return QuestionBank()


def test_question_bank_loads_questions(question_bank):
    assert len(question_bank.questions) >= 47
    # Ensure all expected 13 categories exist
    expected_categories = {
        "personal", "education", "family", "motivation",
        "leadership", "decision_making", "stress", "situational", "general_knowledge",
        "teamwork", "communication", "confidence", "responsibility"
    }
    loaded_categories = set(question_bank.categories.keys())
    assert expected_categories.issubset(loaded_categories)

    # Validate bank integrity
    integrity = question_bank.validate_bank_integrity()
    assert integrity["is_valid"], f"Question bank integrity issues: {integrity['issues']}"
    assert integrity["total_questions"] >= 47



def test_question_items_valid_schema(question_bank):
    for q_id, item in question_bank.questions.items():
        assert item.id == q_id
        assert len(item.question.strip()) > 10
        assert item.difficulty in (1, 2, 3, 4, 5)
        assert item.persona in ("deputy_president", "psychologist", "both")
        assert len(item.intent.strip()) > 0
        assert isinstance(item.follow_up_pool, list)


def test_filter_by_persona(question_bank):
    dp_questions = question_bank.filter_questions(persona="deputy_president")
    for q in dp_questions:
        assert q.persona in ("deputy_president", "both")

    psych_questions = question_bank.filter_questions(persona="psychologist")
    for q in psych_questions:
        assert q.persona in ("psychologist", "both")


def test_build_interview_flow(question_bank):
    flow = question_bank.build_interview_flow(persona="deputy_president", num_questions=5)
    assert len(flow) == 5
    # IDs must be unique
    ids = [q.id for q in flow]
    assert len(ids) == len(set(ids))
