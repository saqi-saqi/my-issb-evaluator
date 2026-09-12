"""
Unit tests for InterviewOrchestrator session flow.
"""

import pytest
from src.interview.orchestrator import InterviewOrchestrator
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def orchestrator():
    retriever = KnowledgeRetriever(use_chroma=False)
    return InterviewOrchestrator(retriever=retriever)


def test_interview_lifecycle(orchestrator):
    session = orchestrator.start_session(
        candidate_name="Tariq Mahmood",
        persona="deputy_president",
        num_questions=3,
    )

    assert session.candidate_name == "Tariq Mahmood"
    assert session.total_questions == 3
    assert session.current_index == 0
    assert not session.completed

    # First question
    q1 = session.current_question
    assert q1 is not None

    # Candidate answers with enough detail
    has_follow_up, follow_up = orchestrator.submit_primary_answer(
        session,
        "I am passionate about aviation and aeronautical engineering. In my spare time I build radio-controlled planes and lead our college physics club.",
    )

    # Session state updated
    assert len(session.qa_history) == 1
    assert session.qa_history[0].question_id == q1.id


def test_session_completion_and_report_generation(orchestrator):
    session = orchestrator.start_session(
        candidate_name="Usman Tariq",
        persona="psychologist",
        num_questions=2,
    )

    # Answer all questions
    while not session.completed:
        curr_q = session.current_question
        if curr_q:
            has_follow_up, follow_up = orchestrator.submit_primary_answer(
                session,
                "I believe in taking personal responsibility and remaining composed under challenge.",
            )
            if has_follow_up:
                orchestrator.submit_follow_up_answer(session, "I discussed the issue directly with my team.")
        else:
            break

    assert session.completed

    # Generate evaluation report
    report = orchestrator.generate_final_report(session)
    assert report.candidate_name == "Usman Tariq"
    assert report.persona == "psychologist"
    assert 0 <= report.overall_practice_score <= 100
