"""
Test suite verifying SQLite persistence for interview sessions, reports, and learning profiles.
Acceptance test for Task 4: State survives service/process restarts.
"""

from pathlib import Path
import pytest

from core.interview import InterviewService
from core.learning import LearningService
from core.questions import QuestionBank
from core.rag import KnowledgeRetriever
from core.storage import StorageManager


def test_session_and_profile_survive_restart(tmp_path):
    db_file = tmp_path / "test_issb.db"

    # 1. First process: Start interview session, submit answers, generate report & retry
    storage_1 = StorageManager(db_path=db_file)
    qb = QuestionBank()
    retriever = KnowledgeRetriever()
    interview_service_1 = InterviewService(question_bank=qb, retriever=retriever, storage=storage_1)

    session = interview_service_1.start_session(
        candidate_name="Cadet Bilal",
        persona="deputy_president",
        num_questions=2,
    )
    session_id = session.session_id
    q1 = session.current_question

    # Submit answer 1
    interview_service_1.submit_primary_answer(
        session,
        "Specifically, in my college I led our technical team and took responsibility for system outages.",
    )
    # Submit answer 2
    interview_service_1.submit_primary_answer(
        session,
        "I decided to join the armed forces because of personal dedication to integrity and service.",
    )
    assert session.completed is True

    # Generate final report
    report = interview_service_1.generate_final_report(session)
    assert report.candidate_name == "Cadet Bilal"

    # Submit a retry
    comparison = interview_service_1.learning.evaluate_retry(
        question_id=q1.id,
        original_answer="In my college we had a problem.",
        retry_answer="Specifically, I take full responsibility for the project delay. I stepped in, organized a new schedule, and resolved the problem.",
        original_score=50.0,
    )
    interview_service_1.learning.record_retry(
        session_id=session_id,
        candidate_name="Cadet Bilal",
        comparison=comparison,
        question_id=q1.id,
    )

    # Verify state was saved to SQLite file
    assert db_file.exists()
    assert db_file.stat().st_size > 0

    # 2. Simulate complete application restart (new instances, zero in-memory cache)
    storage_2 = StorageManager(db_path=db_file)
    learning_service_2 = LearningService(storage=storage_2)
    interview_service_2 = InterviewService(
        question_bank=qb,
        retriever=retriever,
        learning=learning_service_2,
        storage=storage_2,
    )

    # In-memory dict must be empty initially
    assert session_id not in interview_service_2.sessions
    assert session_id not in learning_service_2.profiles

    # Retrieve session from cold storage
    restored_session = interview_service_2.get_session(session_id)
    assert restored_session is not None
    assert restored_session.session_id == session_id
    assert restored_session.candidate_name == "Cadet Bilal"
    assert restored_session.persona == "deputy_president"
    assert restored_session.completed is True
    assert len(restored_session.evidence_records) == 2
    assert restored_session.evidence_records[0].question_id == q1.id

    # Retrieve report from cold storage
    restored_report = storage_2.get_report(session_id)
    assert restored_report is not None
    assert restored_report["candidate_name"] == "Cadet Bilal"
    assert restored_report["overall_practice_score"] > 0.0

    # Retrieve learning profile & retry history from cold storage
    restored_profile = learning_service_2.get_profile(session_id)
    assert restored_profile is not None
    assert restored_profile["candidate_name"] == "Cadet Bilal"
    assert "Ownership / Accountability" in restored_profile["improving_areas"]
    assert len(restored_profile["practice_history"]) == 1
    assert restored_profile["practice_history"][0]["score_delta"] > 0
