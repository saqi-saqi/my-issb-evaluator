"""
Comprehensive Test Suite for the Learning & Improvement Phase (MY_ISSB_Evaluator).
Verifies all 14 requirements from the specification:
1. Learning phase receives evaluator output correctly.
2. Weaknesses produce relevant learning recommendations.
3. Insufficient evidence does not produce unsupported negative judgments.
4. Strong answers receive reinforcement.
5. Retry evaluation compares before and after correctly.
6. Recurring weaknesses are detected across multiple questions.
7. Improvement is not falsely claimed when answer is unimproved or worse.
8. Candidate experiences are never fabricated (uses structural placeholders).
9. Learning recommendations contain evidence IDs where applicable.
10. Existing test suite remains intact.
11. Learning output conforms to the defined JSON schema.
12. Learning recommendations do not contradict the evaluator.
13. Priority levels are assigned consistently according to evidence.
14. Session-level learning profile updates correctly over session lifecycle.
"""

import pytest
from src.evaluator.rubric_engine import PerAnswerEvidence, RubricEvaluationEngine
from src.interview.orchestrator import InterviewOrchestrator
from src.learning.learning_engine import LearningEngine
from src.learning.models import (
    BeforeAfterComparison,
    CandidateLearningProfile,
    ImprovementArea,
    LearningPhaseResult,
    SessionLearningReport,
    StrengthItem,
)
from src.learning.progress_tracker import LearningProgressTracker
from src.question_bank.loader import QuestionBank
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def test_setup():
    qb = QuestionBank()
    retriever = KnowledgeRetriever(use_chroma=False)
    engine = LearningEngine()
    tracker = LearningProgressTracker()
    orchestrator = InterviewOrchestrator(question_bank=qb, retriever=retriever)
    return {
        "qb": qb,
        "retriever": retriever,
        "engine": engine,
        "tracker": tracker,
        "orchestrator": orchestrator,
    }


def test_learning_phase_receives_evaluator_output(test_setup):
    """1. Learning phase receives evaluator output correctly and generates structured feedback."""
    engine = test_setup["engine"]
    evidence = PerAnswerEvidence(
        question_id="dp_sm_002",
        category="self_reflection",
        dimension="Motivation & Integrity",
        score=65.0,
        confidence=0.85,
        evidence_confidence="MEDIUM",
        positive_indicators=["Engaged directly with question prompt."],
        weaknesses=["Relied heavily on abstract assertions; recommend citing concrete personal examples."],
        evidence_text="Leadership means being honest and dedicated.",
        citations=["Official ISSB Candidate Guidelines"],
        source_ids=["official_issb_guidelines"],
    )
    qa_pair = {
        "question_id": "dp_sm_002",
        "category": "self_reflection",
        "evaluation_dimension": "Motivation & Integrity",
        "question": "What is your biggest personal weakness?",
        "intent": "Assess candidate self-awareness and honesty",
        "answer": "Leadership means being honest and dedicated.",
    }

    result = engine.generate_feedback(qa_pair, evidence)

    assert isinstance(result, LearningPhaseResult)
    assert result.overall_assessment
    assert len(result.improvement_areas) >= 1
    assert result.learning_summary.top_priority
    assert result.retry.enabled is True
    assert "practice coaching" in result.disclaimer.lower()


def test_weaknesses_produce_relevant_recommendations(test_setup):
    """2. Weaknesses produce relevant, actionable learning recommendations without generic platitudes."""
    engine = test_setup["engine"]

    # Test Team pronoun deflection -> Ownership / Accountability recommendation
    qa_pair = {
        "question_id": "dp_dm_001",
        "category": "decision_making",
        "question": "Tell me about a time your team faced a major delay.",
        "answer": "We organized everything and our team stayed late to fix the deadline.",
    }
    evidence = PerAnswerEvidence(
        question_id="dp_dm_001",
        category="decision_making",
        dimension="Social Adaptability & Teamwork",
        score=60.0,
        confidence=0.75,
        evidence_confidence="MEDIUM",
        positive_indicators=["Demonstrated collaborative team orientation and shared mission alignment."],
        weaknesses=["The candidate described team actions but did not clearly identify their personal contribution."],
        evidence_text="We organized everything and our team stayed late.",
        citations=["Official ISSB Guidelines"],
        source_ids=["official_guidelines"],
    )

    result = engine.generate_feedback(qa_pair, evidence)
    areas = [ia.area for ia in result.improvement_areas]
    assert "Ownership / Accountability" in areas

    ownership_item = next(ia for ia in result.improvement_areas if ia.area == "Ownership / Accountability")
    assert "first-person" in ownership_item.how_to_improve.lower() or "personally" in ownership_item.how_to_improve.lower()
    assert "technique" in ownership_item.to_dict()
    assert "i decided" in ownership_item.technique.lower() or "i took" in ownership_item.technique.lower()


def test_insufficient_evidence_neutral_handling(test_setup):
    """3. Insufficient evidence does not produce unsupported negative personality judgments."""
    engine = test_setup["engine"]
    evidence = PerAnswerEvidence(
        question_id="q_short",
        category="general",
        dimension="Intellect & Reasoning",
        score=25.0,
        confidence=0.85,
        evidence_confidence="LOW",
        positive_indicators=[],
        weaknesses=["Response was very brief; lacked detailed supporting context or examples."],
        evidence_text="Just trying.",
        citations=["Project Rubric"],
        source_ids=["rubric"],
    )
    qa_pair = {
        "question_id": "q_short",
        "question": "Why do you want to join the Armed Forces?",
        "answer": "Just trying.",
    }

    result = engine.generate_feedback(qa_pair, evidence)

    # Must NOT infer cowardice, mental instability, or dishonesty
    lower_text = (
        result.overall_assessment
        + " "
        + " ".join(ia.problem + " " + ia.why_it_matters for ia in result.improvement_areas)
    ).lower()

    forbidden_terms = ["coward", "dishonest", "unstable", "mental illness", "subconscious defect", "liar", "fraud"]
    for term in forbidden_terms:
        assert term not in lower_text, f"Forbidden judgmental term '{term}' found in feedback!"

    assert "insufficient evidence" in lower_text or "brief" in lower_text or "context" in lower_text
    for ia in result.improvement_areas:
        assert ia.priority in ("MEDIUM", "LOW"), f"Priority for low evidence should not be HIGH, got {ia.priority}"


def test_strong_answers_receive_reinforcement(test_setup):
    """4. Strong answers receive reinforcement explaining why they worked and how to maintain them."""
    engine = test_setup["engine"]
    evidence = PerAnswerEvidence(
        question_id="dp_strong_01",
        category="self_reflection",
        dimension="Motivation & Integrity",
        score=88.0,
        confidence=0.90,
        evidence_confidence="HIGH",
        positive_indicators=[
            "Demonstrated direct personal accountability and ownership without evasiveness.",
            "Structured thoughts logically with causal justification.",
        ],
        weaknesses=[],
        evidence_text="I accept full responsibility for the team missing the deadline because I misjudged the prep time.",
        citations=["Official Guidelines"],
        source_ids=["official_guidelines"],
    )
    qa_pair = {
        "question_id": "dp_strong_01",
        "question": "What happened during that project failure?",
        "answer": "I accept full responsibility for the team missing the deadline because I misjudged the prep time.",
    }

    result = engine.generate_feedback(qa_pair, evidence)

    assert len(result.strengths) >= 1
    strength = result.strengths[0]
    assert strength.area in ("Ownership / Accountability", "Reasoning Ability")
    assert "why this worked" in strength.reinforcement.lower()
    assert strength.observation != ""


def test_retry_before_after_comparison(test_setup):
    """5. Retry evaluation compares before and after correctly with verifiable metric diffs."""
    tracker = test_setup["tracker"]

    before_qa = {
        "question_id": "dp_01",
        "question": "Describe a major mistake you made.",
        "answer": "The project was delayed because other members did not finish on time.",
    }
    before_ev = PerAnswerEvidence(
        question_id="dp_01",
        category="self_reflection",
        dimension="Motivation & Integrity",
        score=52.0,
        confidence=0.75,
        evidence_confidence="MEDIUM",
        positive_indicators=["Engaged directly with question prompt."],
        weaknesses=["Exhibited external attribution or defensive tendency under challenge."],
        evidence_text=before_qa["answer"],
        citations=["Rubric"],
        source_ids=["rubric"],
    )

    after_qa = {
        "question_id": "dp_01",
        "question": "Describe a major mistake you made.",
        "answer": "I accept full responsibility for the project delay. Specifically, when I was team leader, I failed to set intermediate milestones, which caused the delay. I learned to track progress daily.",
    }
    after_ev = PerAnswerEvidence(
        question_id="dp_01",
        category="self_reflection",
        dimension="Motivation & Integrity",
        score=82.0,
        confidence=0.90,
        evidence_confidence="HIGH",
        positive_indicators=[
            "Demonstrated direct personal accountability and ownership without evasiveness.",
            "Grounded statements in concrete personal experience or specific examples.",
        ],
        weaknesses=[],
        evidence_text=after_qa["answer"],
        citations=["Rubric"],
        source_ids=["rubric"],
    )

    comparison = tracker.compare_before_after(before_qa, before_ev, after_qa, after_ev)

    assert isinstance(comparison, BeforeAfterComparison)
    assert comparison.previous_score == 52.0
    assert comparison.new_score == 82.0
    assert comparison.change == 30.0
    assert "Ownership / Accountability" in comparison.improved_areas
    assert "Specificity" in comparison.improved_areas
    assert "+30.0" in comparison.explanation or "improvement" in comparison.explanation.lower()
    assert "Ownership / Accountability" in tracker.profile.improving_areas


def test_recurring_weakness_detection(test_setup):
    """6. Recurring weaknesses are detected and escalated in priority across multiple questions."""
    engine = test_setup["engine"]
    tracker = test_setup["tracker"]

    for i in range(1, 4):
        qa = {
            "question_id": f"q_test_{i}",
            "question": f"Question {i}",
            "answer": "I believe in working hard and achieving success through dedication.",
        }
        ev = PerAnswerEvidence(
            question_id=f"q_test_{i}",
            category="general",
            dimension="Intellect & Reasoning",
            score=62.0,
            confidence=0.80,
            evidence_confidence="MEDIUM",
            positive_indicators=["Engaged directly with question prompt."],
            weaknesses=["Relied heavily on abstract assertions; recommend citing concrete personal examples."],
            evidence_text=qa["answer"],
            citations=["Rubric"],
            source_ids=["rubric"],
        )
        fb = engine.generate_feedback(qa, ev, tracker.profile)
        tracker.record_answer_evaluation(qa, ev, fb)

    # After 3 questions with abstract assertions, Specificity must be recognized as recurring
    assert "Specificity" in tracker.profile.recurring_weaknesses
    assert tracker.profile.weakness_counts["Specificity"] >= 2

    # Verify priority escalation on subsequent evaluation
    next_fb = engine.generate_feedback(
        {"question_id": "q_test_4", "question": "Another Q", "answer": "Success is great."},
        PerAnswerEvidence(
            question_id="q_test_4",
            category="general",
            dimension="Intellect",
            score=60.0,
            confidence=0.85,
            evidence_confidence="MEDIUM",
            positive_indicators=["Engaged directly with question prompt."],
            weaknesses=["Relied heavily on abstract assertions; recommend citing concrete personal examples."],
            evidence_text="Success is great.",
            citations=["Rubric"],
            source_ids=["rubric"],
        ),
        tracker.profile,
    )
    specificity_item = next(ia for ia in next_fb.improvement_areas if ia.area == "Specificity")
    assert specificity_item.priority == "HIGH"
    assert "recurring" in specificity_item.problem.lower()


def test_no_false_improvement_claims(test_setup):
    """7. Improvement is not falsely claimed when second evaluation is identical or worse."""
    tracker = test_setup["tracker"]

    before_qa = {"question_id": "q1", "answer": "I decided to handle the problem."}
    before_ev = PerAnswerEvidence(
        question_id="q1",
        category="general",
        dimension="Motivation",
        score=75.0,
        confidence=0.85,
        evidence_confidence="HIGH",
        positive_indicators=["Demonstrated direct personal accountability and ownership without evasiveness."],
        weaknesses=[],
        evidence_text="I decided to handle the problem.",
        citations=["Rubric"],
        source_ids=["rubric"],
    )

    # Second answer is identical or worse
    after_qa = {"question_id": "q1", "answer": "I don't know."}
    after_ev = PerAnswerEvidence(
        question_id="q1",
        category="general",
        dimension="Motivation",
        score=20.0,
        confidence=0.90,
        evidence_confidence="NONE",
        positive_indicators=[],
        weaknesses=["Severely non-responsive / monosyllabic reply ('yes/no'); failed to articulate thoughts."],
        evidence_text="I don't know.",
        citations=["Rubric"],
        source_ids=["rubric"],
    )

    comparison = tracker.compare_before_after(before_qa, before_ev, after_qa, after_ev)
    assert comparison.change < 0
    assert len(comparison.improved_areas) == 0
    assert "scored lower" in comparison.explanation.lower() or "did not" in comparison.explanation.lower()


def test_no_hallucinated_candidate_stories(test_setup):
    """8. Candidate experiences are never fabricated; example structures use placeholders only."""
    engine = test_setup["engine"]
    qa = {"question_id": "q_lead", "question": "Give an example of leadership.", "answer": "I am a leader."}
    ev = PerAnswerEvidence(
        question_id="q_lead",
        category="leadership",
        dimension="Motivation",
        score=45.0,
        confidence=0.70,
        evidence_confidence="LOW",
        positive_indicators=["Engaged directly with question prompt."],
        weaknesses=["Response was very brief; lacked detailed supporting context or examples."],
        evidence_text="I am a leader.",
        citations=["Rubric"],
        source_ids=["rubric"],
    )

    result = engine.generate_feedback(qa, ev)

    for ia in result.improvement_areas:
        if ia.example_structure:
            # Check for structural placeholder brackets
            assert "[" in ia.example_structure and "]" in ia.example_structure
            # Ensure no fake stories or specific made-up achievements
            for fabricated in ["captain of the football team", "won first prize", "my father", "grade 10 topper"]:
                assert fabricated not in ia.example_structure.lower()


def test_evidence_ids_in_recommendations(test_setup):
    """9. Learning recommendations contain traceable evidence IDs."""
    engine = test_setup["engine"]
    qa = {"question_id": "q_ev", "question": "Why ISSB?", "answer": "Yes."}
    ev = PerAnswerEvidence(
        question_id="q_ev",
        category="general",
        dimension="Expression",
        score=15.0,
        confidence=0.95,
        evidence_confidence="NONE",
        positive_indicators=[],
        weaknesses=["Severely non-responsive / monosyllabic reply ('yes/no'); failed to articulate thoughts."],
        evidence_text="Yes.",
        citations=["Rubric"],
        source_ids=["rubric_source_1"],
    )

    result = engine.generate_feedback(qa, ev)
    for ia in result.improvement_areas:
        assert len(ia.evidence_ids) >= 1
        assert any(eid.startswith("EV") for eid in ia.evidence_ids)


def test_existing_test_suite_intact(test_setup):
    """10. Existing evaluation engine and score calculator remain functioning as expected."""
    orchestrator = test_setup["orchestrator"]
    session = orchestrator.start_session("Candidate Tariq", persona="deputy_president", num_questions=2)
    has_f, f_q = orchestrator.submit_primary_answer(
        session,
        "During my college project, I served as the team lead. When we faced a scheduling delay, I took full responsibility, restructured our timelines, and successfully delivered the project on time."
    )
    if has_f:
        orchestrator.submit_follow_up_answer(session, "I personally coordinated the tasks and accepted full responsibility.")
    assert len(session.qa_history) == 1
    assert len(session.per_answer_evaluations) == 1
    assert session.per_answer_evaluations[0]["score"] >= 75.0


def test_schema_conformance(test_setup):
    """11. Learning output conforms to the specified JSON schema."""
    engine = test_setup["engine"]
    qa = {"question_id": "q_sc", "question": "Describe a challenge.", "answer": "I resolved a dispute in my class."}
    ev = PerAnswerEvidence(
        question_id="q_sc",
        category="conflict",
        dimension="Social",
        score=72.0,
        confidence=0.85,
        evidence_confidence="MEDIUM",
        positive_indicators=["Demonstrated collaborative team orientation and shared mission alignment."],
        weaknesses=["Relied heavily on abstract assertions; recommend citing concrete personal examples."],
        evidence_text="I resolved a dispute in my class.",
        citations=["Rubric"],
        source_ids=["rubric"],
    )

    result = engine.generate_feedback(qa, ev)
    data = result.to_dict()

    assert "learning_phase" in data
    lp = data["learning_phase"]
    assert "overall_assessment" in lp
    assert "strengths" in lp and isinstance(lp["strengths"], list)
    assert "improvement_areas" in lp and isinstance(lp["improvement_areas"], list)
    assert "learning_summary" in lp and isinstance(lp["learning_summary"], dict)
    assert "retry" in lp and isinstance(lp["retry"], dict)
    assert "disclaimer" in lp and isinstance(lp["disclaimer"], str)


def test_no_evaluator_contradiction(test_setup):
    """12. Learning recommendations do not contradict the evaluator."""
    engine = test_setup["engine"]
    qa = {
        "question_id": "q_honesty",
        "question": "Have you ever failed?",
        "answer": "Yes, I failed my intermediate physics exam because I didn't study consistently. I retook it and passed.",
    }
    # Evaluator scores this as honest and accountable (Score: 84)
    ev = PerAnswerEvidence(
        question_id="q_honesty",
        category="self_reflection",
        dimension="Motivation & Integrity",
        score=84.0,
        confidence=0.90,
        evidence_confidence="HIGH",
        positive_indicators=["Demonstrated direct personal accountability and ownership without evasiveness."],
        weaknesses=[],
        evidence_text=qa["answer"],
        citations=["Rubric"],
        source_ids=["rubric"],
    )

    result = engine.generate_feedback(qa, ev)
    # Must NOT claim candidate was dishonest or lacked accountability
    assert any("Ownership / Accountability" in s.area for s in result.strengths)
    assert not any(ia.area == "Ownership / Accountability" for ia in result.improvement_areas)


def test_priority_assignment_rules(test_setup):
    """13. Priority levels are assigned consistently based on evidence strength."""
    engine = test_setup["engine"]

    # Low evidence answer: Priority cannot be HIGH
    low_ev = PerAnswerEvidence(
        question_id="q_low",
        category="general",
        dimension="Intellect",
        score=48.0,
        confidence=0.55,
        evidence_confidence="LOW",
        positive_indicators=["Engaged directly with question prompt."],
        weaknesses=["Response was very brief; lacked detailed supporting context or examples."],
        evidence_text="Some answer.",
        citations=["Rubric"],
        source_ids=["rubric"],
    )
    result_low = engine.generate_feedback({"question_id": "q_low", "question": "Q?", "answer": "Some answer."}, low_ev)
    for ia in result_low.improvement_areas:
        assert ia.priority in ("LOW", "MEDIUM")

    # Extreme monosyllabic evasion: Priority MUST be HIGH
    mono_ev = PerAnswerEvidence(
        question_id="q_mono",
        category="general",
        dimension="Expression",
        score=15.0,
        confidence=0.95,
        evidence_confidence="NONE",
        positive_indicators=[],
        weaknesses=["Severely non-responsive / monosyllabic reply ('yes/no'); failed to articulate thoughts, reasoning, or context."],
        evidence_text="No.",
        citations=["Rubric"],
        source_ids=["rubric"],
    )
    result_mono = engine.generate_feedback({"question_id": "q_mono", "question": "Q?", "answer": "No."}, mono_ev)
    mono_item = next(ia for ia in result_mono.improvement_areas if ia.area == "Power of Expression")
    assert mono_item.priority == "HIGH"


def test_session_learning_profile_lifecycle(test_setup):
    """14. Session-level learning profile updates correctly over multiple questions and retries."""
    orchestrator = test_setup["orchestrator"]
    session = orchestrator.start_session("Candidate Bilal", persona="deputy_president", num_questions=2)

    # Q1: Initial answer with missing ownership (team focus)
    has_f, _ = orchestrator.submit_primary_answer(
        session, "During our engineering project, our team faced a delay and we worked overtime every evening to complete the deliverables."
    )
    if has_f:
        orchestrator.submit_follow_up_answer(session, "The whole group agreed to divide the remaining work together.")
    fb1 = orchestrator.get_learning_feedback(session, session.questions[0].id)
    assert session.learning_profile is not None
    assert "Ownership / Accountability" in session.learning_profile["priority_areas"]

    # Retry Q1 with first-person ownership
    retry_res = orchestrator.process_retry_answer(
        session,
        session.questions[0].id,
        "I take full responsibility for the delay because I did not allocate tasks efficiently. I stepped in, organized a new timetable, and resolved the schedule.",
    )
    assert retry_res["before_after"]["change"] > 0
    assert "Ownership / Accountability" in retry_res["before_after"]["improved_areas"]
    assert "Ownership / Accountability" in session.learning_profile["improving_areas"]

    # Generate session learning report
    session_report = orchestrator.generate_session_learning_report(session)
    assert isinstance(session_report, SessionLearningReport)
    assert session_report.candidate_name == "Candidate Bilal"
    assert len(session_report.recommended_practice_exercises) >= 1
    assert session_report.suggested_next_practice_session != ""
