"""
Unit tests for contextual follow-up question generation and trigger logic.
"""

import pytest
from src.interview.orchestrator import InterviewOrchestrator
from src.question_bank.loader import QuestionBank, QuestionItem


@pytest.fixture
def orchestrator():
    return InterviewOrchestrator()


def test_follow_up_triggers_on_brief_answer(orchestrator):
    """Test that a short/terse answer automatically triggers a follow-up."""
    session = orchestrator.start_session("Candidate", num_questions=2)
    # Ensure current question has follow_ups
    assert len(session.current_question.follow_up_pool) > 0

    has_fu, fu_text = orchestrator.submit_primary_answer(session, "Yes, I like teamwork.")
    assert has_fu is True
    assert fu_text is not None
    assert len(fu_text) > 10
    assert session.awaiting_follow_up is True


def test_follow_up_response_lifecycle(orchestrator):
    """Test the complete round-trip: primary answer -> follow-up generated -> follow-up answered -> advance."""
    session = orchestrator.start_session("Candidate", num_questions=2)
    initial_q = session.current_question

    has_fu, fu_text = orchestrator.submit_primary_answer(session, "Very brief reply.")
    assert has_fu is True
    assert session.qa_history[-1].question_id == initial_q.id
    assert session.qa_history[-1].follow_up == fu_text

    # Candidate answers follow-up
    fu_reply = "To be specific, during our college project I allocated tasks according to each peer's strength."
    orchestrator.submit_follow_up_answer(session, fu_reply)

    assert session.awaiting_follow_up is False
    assert session.qa_history[0].follow_up_answer == fu_reply
    # Should advance to question 2
    assert session.current_index == 1
