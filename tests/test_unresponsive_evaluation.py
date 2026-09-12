"""
Unit tests for unresponsive / monosyllabic answer handling, irrelevance detection,
and expanded RAG knowledge base integration.
"""

import pytest
from src.evaluator.rubric_engine import RubricEvaluationEngine
from src.evaluator.score_calculator import get_performance_band
from src.rag.retriever import KnowledgeRetriever


@pytest.fixture
def retriever():
    return KnowledgeRetriever(use_chroma=False)


@pytest.fixture
def evaluator(retriever):
    return RubricEvaluationEngine(retriever=retriever)


def test_yes_no_monosyllabic_answers_fail(evaluator):
    """
    Test that answering only 'yes', 'no', 'idk' results in an appropriately low score
    (< 30%) and does NOT hallucinate strengths or award 68%.
    """
    monosyllabic_qa = [
        {
            "question_id": "GK_001",
            "category": "general_knowledge",
            "evaluation_dimension": "intellect",
            "question": "What is the primary cause of Pakistan's balance-of-payments challenges?",
            "answer": "no",
            "follow_up": "Could you explain your reasoning?",
            "follow_up_answer": "idk",
        },
        {
            "question_id": "LEA_001",
            "category": "leadership",
            "evaluation_dimension": "leadership",
            "question": "Tell me about leading a team under pressure.",
            "answer": "yes",
            "follow_up": "What was the specific outcome?",
            "follow_up_answer": "fine",
        },
        {
            "question_id": "COM_001",
            "category": "communication",
            "evaluation_dimension": "communication",
            "question": "Describe an instance where you gave a presentation.",
            "answer": "no",
        },
    ]

    report = evaluator.evaluate_interview_session(
        candidate_name="Terse Candidate",
        persona="deputy_president",
        qa_pairs=monosyllabic_qa,
    )

    # Must be heavily penalized, strictly under 35.0%
    assert report.overall_practice_score <= 30.0, f"Expected <= 30.0, got {report.overall_practice_score}"

    # Performance band must be Unsatisfactory / Non-Responsive
    band = get_performance_band(report.overall_practice_score)
    assert band["tier"] == "Unsatisfactory / Non-Responsive"

    # Must NOT hallucinate positive strengths
    assert any("None observed" in s for s in report.key_strengths)

    # Weaknesses must explicitly identify monosyllabic evasion
    all_weaknesses = " ".join(report.growth_areas).lower()
    assert "monosyllabic" in all_weaknesses or "yes" in all_weaknesses

    # Per-question scores must be failing (< 30)
    for ev in report.per_question_evidence:
        assert ev["score"] <= 25.0


def test_irrelevant_off_topic_answers_penalized(evaluator):
    """
    Test that answers completely irrelevant to the question asked are flagged and penalized.
    """
    irrelevant_qa = [
        {
            "question_id": "GK_003",
            "category": "general_knowledge",
            "evaluation_dimension": "intellect",
            "intent": "Assesses foundational national geography, water security, and treaty knowledge.",
            "question": "Name the five major rivers of Pakistan and why the Indus Water Treaty is important.",
            "answer": "I love eating chocolate ice cream and going to the cinema on weekends with friends.",
        }
    ]

    evidence = evaluator.evaluate_single_answer(irrelevant_qa[0])
    assert evidence.score <= 30.0
    assert any("off-topic" in w.lower() or "irrelevant" in w.lower() for w in evidence.weaknesses)
    assert len(evidence.positive_indicators) == 0


def test_substantive_structured_answers_succeed(evaluator):
    """
    Test that well-reasoned, substantive answers with concrete examples continue to score well.
    """
    substantive_qa = [
        {
            "question_id": "LEA_001",
            "category": "leadership",
            "evaluation_dimension": "leadership",
            "question": "Describe a crisis you handled as a team leader.",
            "answer": (
                "Specifically, during our college flood relief drive, our primary supply truck broke down. "
                "I took personal responsibility as group leader, divided our squad into two teams, and negotiated "
                "with local transport authorities for backup vans. Because we acted swiftly, we delivered supplies to 200 families."
            ),
        }
    ]

    evidence = evaluator.evaluate_single_answer(substantive_qa[0])
    assert evidence.score >= 75.0
    assert len(evidence.positive_indicators) >= 2
    assert any("concrete personal experience" in p for p in evidence.positive_indicators)


def test_expanded_knowledge_base_coverage(retriever):
    """
    Test that newly added knowledge base domains (Indus Water Treaty, Hormuz, 14 OLQs, SIFC) are properly indexed.
    """
    # 1. Total chunks should now be significantly expanded
    assert len(retriever.chunks) >= 30, f"Expected >= 30 chunks, got {len(retriever.chunks)}"

    # 2. Check retrieval for Indus Waters Treaty
    water_results = retriever.retrieve("Indus Waters Treaty 1960 rivers allocation", top_k=2)
    assert len(water_results) > 0
    assert any("1960" in r["text"] or "treaty" in r["text"].lower() for r in water_results)

    # 3. Check retrieval for Strait of Hormuz and maritime trade
    hormuz_results = retriever.retrieve("Strait of Hormuz petroleum maritime choke point", top_k=2)
    assert len(hormuz_results) > 0
    assert any("hormuz" in r["text"].lower() for r in hormuz_results)

    # 4. Check retrieval for 14 OLQs
    olq_results = retriever.retrieve("14 officer like qualities planning dynamic character", top_k=2)
    assert len(olq_results) > 0
    assert any("qualities" in r["text"].lower() for r in olq_results)
