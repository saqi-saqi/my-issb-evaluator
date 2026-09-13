"""
Test suite verifying that RAG retrieval is load-bearing in scoring, indicators, and narrative synthesis.
Acceptance test for Task 1: Changing retrieved evaluation tier content changes score/narrative.
"""

from unittest.mock import MagicMock
import pytest

from core.evaluator import RubricEvaluator
from core.rag import KnowledgeRetriever


class MockRetriever:
    """Mock retriever returning configurable rubric chunks."""

    def __init__(self, rubric_text: str):
        self.rubric_text = rubric_text

    def retrieve(self, query: str, top_k: int = 3, tier: str = None):
        return [
            {
                "id": "mock_eval_001",
                "text": self.rubric_text,
                "source_file": "evaluation/leadership.md",
                "tier": "evaluation",
                "title": "Leadership Rubric",
                "citation": "[Evaluation Rubric | Mock Leadership]",
            }
        ]


def test_rag_retrieval_influences_score_and_indicators():
    """Asserts that changing the retrieved evaluation rubric changes the resulting score and indicators."""
    rubric_strategic = """
# EVALUATION RUBRIC: LEADERSHIP
## Observable Positive Indicators
- Strategic Foresight: Anticipates future risks and formulates backup plans under pressure.
## Observable Potential Weaknesses
- Narrow Focus: Ignores long-term consequences.
"""

    rubric_physical = """
# EVALUATION RUBRIC: LEADERSHIP
## Observable Positive Indicators
- Physical Stamina: Demonstrates athletic speed and rapid physical execution during tasks.
## Observable Potential Weaknesses
- Sluggish Movement: Displays physical hesitation.
"""

    candidate_answer = (
        "In our major team project, I actively analyzed future risks and formulated backup plans "
        "because our initial timeline had unexpected technical obstacles."
    )

    evaluator_strategic = RubricEvaluator(retriever=MockRetriever(rubric_strategic))
    evaluator_physical = RubricEvaluator(retriever=MockRetriever(rubric_physical))

    ev_strategic = evaluator_strategic.evaluate_answer_evidence(
        question_id="Q_LEAD_01",
        question_text="Describe how you handled unexpected challenges in a project.",
        category="leadership",
        dimension="leadership",
        intent="initiative",
        primary_answer=candidate_answer,
    )

    ev_physical = evaluator_physical.evaluate_answer_evidence(
        question_id="Q_LEAD_01",
        question_text="Describe how you handled unexpected challenges in a project.",
        category="leadership",
        dimension="leadership",
        intent="initiative",
        primary_answer=candidate_answer,
    )

    # 1. The strategic rubric matched candidate's risk/planning words, awarding bonus points
    assert ev_strategic.score > ev_physical.score, (
        f"Expected strategic rubric score ({ev_strategic.score}) > physical rubric score ({ev_physical.score})"
    )

    # 2. Indicators must reflect the retrieved rubric benchmark
    assert any("Strategic Foresight" in p for p in ev_strategic.positive_indicators)
    assert not any("Strategic Foresight" in p for p in ev_physical.positive_indicators)


def test_rag_retrieval_influences_narrative_prompt_injection():
    """Asserts that retrieved benchmark chunks for weakest dimensions are injected into the LLM narrative prompt."""
    benchmark_text = "MILITARY CRITERIA 101: Candidate must exhibit non-defensive poise under direct challenge."
    mock_retriever = MockRetriever(benchmark_text)

    mock_ai = MagicMock()
    captured_prompts = []

    def capture_generate_json(prompt, system=None, temperature=0.1):
        captured_prompts.append(prompt)
        return {
            "executive_summary": "Candidate demonstrated solid reasoning.",
            "key_strengths": ["Clear structure"],
            "primary_shortcomings": ["Needs more specific ownership"],
            "actionable_recommendations": ["Use STAR framework"],
        }

    mock_ai.generate_json.side_effect = capture_generate_json
    mock_ai.is_available.return_value = True

    evaluator = RubricEvaluator(retriever=mock_retriever, ai=mock_ai)

    # Run pass 2 narrative generation
    evaluator._generate_qualitative_narrative(
        candidate_name="Cadet Hamza",
        persona="deputy_president",
        overall_score=65.0,
        band_tier="Consistent Competence",
        dimension_scores={"Emotional Stability": 52.0, "Planning Ability": 75.0},
        positives=["Took initiative"],
        weaknesses=["Brief reply"],
    )

    assert len(captured_prompts) == 1
    sent_prompt = captured_prompts[0]

    # Benchmark text from retrieval must be present in the prompt
    assert "MILITARY CRITERIA 101" in sent_prompt
    assert "non-defensive poise" in sent_prompt
    assert "Benchmark Evaluation Rubric Criteria" in sent_prompt


def test_rag_graceful_degradation_when_retrieval_empty():
    """Asserts that if the retriever returns no chunks, evaluation completes without crashing."""
    empty_retriever = MagicMock()
    empty_retriever.retrieve.return_value = []

    evaluator = RubricEvaluator(retriever=empty_retriever)
    ev = evaluator.evaluate_answer_evidence(
        question_id="Q_EMPTY_01",
        question_text="Tell me about a challenge you solved.",
        category="personal",
        dimension="integrity",
        intent="ownership",
        primary_answer="Specifically, in my college I led our team and resolved the dispute.",
    )

    assert ev.score >= 50.0
    assert ev.citations == []
    assert len(ev.positive_indicators) > 0
