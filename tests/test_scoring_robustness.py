"""
Test suite verifying flexible, less-brittle semantic and LLM rubric scoring.
Acceptance tests for Task 5:
1. Paraphrased ownership answers score appropriately higher without hardcoded substrings.
2. Offline mode (no GROQ_API_KEY) produces reasonable, valid scores.
3. LLM-grounded scoring operates when available.
"""

from unittest.mock import MagicMock
import pytest

from core.evaluator import RubricEvaluator
from core.scoring import get_performance_band


def test_paraphrased_ownership_scores_appropriately_without_hardcoded_substrings():
    """
    Tests that an answer demonstrating genuine personal ownership and initiative
    using natural, paraphrased vocabulary (not matching the old 8 hardcoded substrings)
    is recognized and receives an appropriately high score.
    """
    # This answer avoids: "i took", "i decided", "my fault", "my mistake", "i led", "i organized", "i took responsibility", "i resolved"
    paraphrased_answer = (
        "When unexpected challenges arose during our university competition, "
        "I personally assumed charge of the operation and directed the recovery with my squad. "
        "The principal lapse was my duty to bear; therefore, I intervened, managed the crisis, "
        "and guided everyone toward our mutual objective."
    )

    # Ensure none of the old hardcoded substrings are present
    old_hardcoded_phrases = [
        "i took", "i decided", "my fault", "my mistake", "i led", "i organized", "i took responsibility", "i resolved"
    ]
    assert not any(p in paraphrased_answer.lower() for p in old_hardcoded_phrases), "Test setup: answer must not match old substrings"

    # Offline evaluator using semantic concept matching
    mock_ai = MagicMock()
    mock_ai.is_available.return_value = False

    evaluator = RubricEvaluator(ai=mock_ai)
    ev = evaluator.evaluate_answer_evidence(
        question_id="Q_PARAPHRASE_01",
        question_text="Tell me about a time you handled a crisis.",
        category="leadership",
        dimension="leadership",
        intent="initiative",
        primary_answer=paraphrased_answer,
    )

    # Must detect personal accountability and score strongly
    assert ev.score >= 80.0
    assert ev.evidence_confidence == "HIGH"
    assert any("accountability" in p.lower() or "ownership" in p.lower() for p in ev.positive_indicators)
    assert not any("Lacked explicit personal ownership" in w for w in ev.weaknesses)


def test_offline_mode_produces_reasonable_score():
    """
    Verifies that offline mode (no API key) produces a valid, reasonable score
    and does not fail or collapse to the lowest band for a competent response.
    """
    offline_ai = MagicMock()
    offline_ai.is_available.return_value = False
    offline_ai.generate_json.return_value = {}
    offline_ai.generate_text.return_value = ""

    evaluator = RubricEvaluator(ai=offline_ai)
    ev = evaluator.evaluate_answer_evidence(
        question_id="Q_OFFLINE_01",
        question_text="Why do you wish to join the Pakistan Army?",
        category="motivation",
        dimension="moral_integrity",
        intent="authenticity",
        primary_answer="I wish to serve the nation with honor and discipline. In my college days, I committed myself to ethical teamwork.",
    )

    assert ev.score >= 60.0
    band = get_performance_band(ev.score)
    # Must not collapse to lowest band
    assert band["tier"] in ["Solid Competency Demonstrated", "Developing Readiness", "High Practice Readiness"]
    assert band["tier"] != "Substantial Preparation Required"


def test_online_llm_rubric_scoring_pass():
    """
    Verifies that when online, the evaluator integrates LLM structured rubric ratings.
    """
    online_ai = MagicMock()
    online_ai.is_available.return_value = True
    online_ai.generate_json.return_value = {
        "has_ownership": True,
        "has_example": True,
        "has_reasoning": True,
        "has_teamwork": True,
        "positive_indicators": ["Exhibited decisive moral courage under pressure"],
        "weaknesses": [],
    }

    evaluator = RubricEvaluator(ai=online_ai)
    ev = evaluator.evaluate_answer_evidence(
        question_id="Q_ONLINE_01",
        question_text="Describe a failure and what you learned.",
        category="personal",
        dimension="integrity",
        intent="ownership",
        primary_answer="I made a calculation error during the project and acknowledged it immediately to the board.",
    )

    assert ev.score >= 85.0
    assert any("moral courage" in p.lower() for p in ev.positive_indicators)
