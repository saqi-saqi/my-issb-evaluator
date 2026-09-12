"""
Deterministic Scoring Engine for MY_ISSB_Evaluator.
Implements the 3-tier hierarchy:
1. Per-Answer Evidence Scoring (Relevance, Specificity, Indicators)
2. 14 Official Officer Like Qualities (OLQ) Mapping
3. 5 Executive Dashboard Dimensions & Performance Bands
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# The 14 Official ISSB Officer Like Qualities (OLQs)
FOURTEEN_OLQS = [
    "Reasoning Ability",
    "Organizing Ability",
    "Power of Expression",
    "Social Adaptability",
    "Cooperation",
    "Sense of Responsibility",
    "Initiative",
    "Courage",
    "Self-Confidence",
    "Determination",
    "Stamina",
    "Integrity",
    "Emotional Stability",
    "Practical Common Sense",
]

# Mapping matrix from 14 OLQs to the 5 Derived Executive Dashboard Dimensions
OLQ_TO_DASHBOARD_MAPPING: Dict[str, Dict[str, float]] = {
    "Intellect & Reasoning": {
        "Reasoning Ability": 0.40,
        "Organizing Ability": 0.30,
        "Practical Common Sense": 0.30,
    },
    "Emotional Composure": {
        "Emotional Stability": 0.50,
        "Courage": 0.25,
        "Stamina": 0.25,
    },
    "Social Adaptability & Teamwork": {
        "Social Adaptability": 0.40,
        "Cooperation": 0.40,
        "Initiative": 0.20,
    },
    "Communication & Expression": {
        "Power of Expression": 0.60,
        "Self-Confidence": 0.40,
    },
    "Motivation & Integrity": {
        "Integrity": 0.40,
        "Determination": 0.30,
        "Sense of Responsibility": 0.30,
    },
}

# Category to primary OLQ relevance mapping
CATEGORY_TO_OLQS: Dict[str, List[str]] = {
    "personal": ["Power of Expression", "Integrity", "Self-Confidence"],
    "family": ["Social Adaptability", "Integrity", "Emotional Stability"],
    "education": ["Reasoning Ability", "Organizing Ability", "Determination"],
    "academics": ["Reasoning Ability", "Organizing Ability", "Practical Common Sense"],
    "motivation": ["Determination", "Integrity", "Sense of Responsibility"],
    "leadership": ["Initiative", "Organizing Ability", "Cooperation", "Courage"],
    "decision_making": ["Reasoning Ability", "Practical Common Sense", "Courage"],
    "stress": ["Emotional Stability", "Stamina", "Courage"],
    "situational": ["Practical Common Sense", "Initiative", "Reasoning Ability"],
    "general_knowledge": ["Reasoning Ability", "Power of Expression", "Practical Common Sense"],
    "current_affairs": ["Reasoning Ability", "Power of Expression"],
    "teamwork": ["Cooperation", "Social Adaptability", "Sense of Responsibility"],
    "communication": ["Power of Expression", "Self-Confidence", "Social Adaptability"],
    "confidence": ["Self-Confidence", "Courage", "Power of Expression"],
    "responsibility": ["Sense of Responsibility", "Integrity", "Determination"],
}


def get_performance_band(score: float) -> Dict[str, str]:
    """Returns a defensible performance readiness band. Avoids false claims of passing probabilities."""
    if score >= 85.0:
        return {
            "tier": "High Practice Readiness",
            "badge_color": "green",
            "summary": "Demonstrates strong alignment with observable positive indicators across communication, composure, and critical reasoning.",
        }
    elif score >= 70.0:
        return {
            "tier": "Solid Competency Demonstrated",
            "badge_color": "blue",
            "summary": "Exhibits good foundational capability with targeted opportunities for improvement in structured articulation and depth.",
        }
    elif score >= 55.0:
        return {
            "tier": "Developing Readiness",
            "badge_color": "orange",
            "summary": "Shows authentic effort, but answers would benefit from greater concrete evidence, less brevity, and clearer situational deconstruction.",
        }
    else:
        return {
            "tier": "Substantial Preparation Required",
            "badge_color": "red",
            "summary": "Responses exhibited recurring monosyllabic replies, evasiveness, or absence of structured reasoning and personal accountability.",
        }


def calculate_14_olq_scores(per_answer_evidence: List[Any]) -> Dict[str, float]:
    """Calculates scores for all 14 OLQs from per-answer evidence items."""
    olq_scores: Dict[str, List[Tuple[float, float]]] = {olq: [] for olq in FOURTEEN_OLQS}

    for ev in per_answer_evidence:
        score = getattr(ev, "score", 60.0)
        conf = getattr(ev, "confidence", 0.7)
        cat = getattr(ev, "category", "personal").lower()
        mapped_olqs = CATEGORY_TO_OLQS.get(cat, ["Power of Expression", "Reasoning Ability"])

        for olq in mapped_olqs:
            if olq in olq_scores:
                olq_scores[olq].append((score, conf))

    # Baseline score for questions not directly tested in this session
    base_session_score = (
        sum(getattr(e, "score", 60.0) for e in per_answer_evidence) / len(per_answer_evidence)
        if per_answer_evidence
        else 65.0
    )

    result: Dict[str, float] = {}
    for olq in FOURTEEN_OLQS:
        entries = olq_scores[olq]
        if entries:
            total_weight = sum(w for _, w in entries)
            if total_weight > 0:
                weighted_avg = sum(s * w for s, w in entries) / total_weight
                result[olq] = round(max(10.0, min(100.0, weighted_avg)), 1)
            else:
                result[olq] = round(base_session_score, 1)
        else:
            # Impute slightly moderated baseline
            result[olq] = round(base_session_score * 0.9, 1)

    return result


def calculate_dashboard_dimensions(olq_scores: Dict[str, float]) -> Dict[str, float]:
    """Calculates the 5 Core Dashboard Dimensions from the 14 OLQ scores."""
    dimension_scores: Dict[str, float] = {}
    for dim_name, weights in OLQ_TO_DASHBOARD_MAPPING.items():
        total_dim = sum(olq_scores.get(olq, 60.0) * weight for olq, weight in weights.items())
        dimension_scores[dim_name] = round(max(10.0, min(100.0, total_dim)), 1)
    return dimension_scores


def calculate_overall_score(dimension_scores: Dict[str, float]) -> float:
    """Calculates weighted overall Practice Performance Score (0-100%)."""
    if not dimension_scores:
        return 65.0
    weights = {
        "Intellect & Reasoning": 0.25,
        "Emotional Composure": 0.20,
        "Social Adaptability & Teamwork": 0.20,
        "Communication & Expression": 0.20,
        "Motivation & Integrity": 0.15,
    }
    total = sum(dimension_scores.get(dim, 60.0) * weight for dim, weight in weights.items())
    return round(max(0.0, min(100.0, total)), 1)
