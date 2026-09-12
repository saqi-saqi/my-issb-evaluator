"""
Unit tests for duplicate question prevention and session history tracking.
"""

import pytest
from src.interview.orchestrator import InterviewOrchestrator
from src.question_bank.loader import QuestionBank


@pytest.fixture
def question_bank():
    return QuestionBank()


@pytest.fixture
def orchestrator():
    return InterviewOrchestrator()


def test_build_interview_flow_no_internal_duplicates(question_bank):
    """Test that a single flow never contains duplicate questions."""
    for persona in ["deputy_president", "psychologist"]:
        flow = question_bank.build_interview_flow(persona=persona, num_questions=8)
        ids = [q.id for q in flow]
        assert len(ids) == len(set(ids)), f"Duplicate question IDs detected in single flow: {ids}"


def test_cross_session_duplicate_prevention(question_bank):
    """Test that passing exclude_ids prevents already-asked questions from recurring."""
    # Session 1
    session1_flow = question_bank.build_interview_flow(persona="deputy_president", num_questions=5)
    session1_ids = [q.id for q in session1_flow]

    # Session 2 excludes Session 1 questions
    session2_flow = question_bank.build_interview_flow(
        persona="deputy_president",
        num_questions=5,
        exclude_ids=session1_ids,
    )
    session2_ids = [q.id for q in session2_flow]

    # Ensure 0 overlap between the two sessions
    overlap = set(session1_ids) & set(session2_ids)
    assert len(overlap) == 0, f"Cross-session duplicate questions found: {overlap}"


def test_session_state_tracks_asked_ids(orchestrator):
    """Test that InterviewSession accurately tracks questions asked as answers are submitted."""
    session = orchestrator.start_session(candidate_name="Test Candidate", num_questions=3)

    assert session.questions_asked_ids == []
    assert session.categories_covered == []

    # Submit first answer
    q1 = session.current_question
    orchestrator.submit_primary_answer(session, "First answer with substantial reasoning and clear examples.")

    assert q1.id in session.questions_asked_ids
    assert q1.category in session.categories_covered
