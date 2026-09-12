"""
Deterministic Score Calculator, 14-OLQ Engine, and Evidence Aggregator for MY_ISSB_Evaluator (V2).
Implements 3-tier scoring hierarchy:
Tier 1: Evidence Score (Relevance × Specificity × EvidenceQuality)
Tier 2: 14 Officer Like Qualities (OLQ) Layer
Tier 3: 5 Derived Dashboard Dimensions
"""

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
    """
    Returns a defensible performance readiness band.
    Avoids false claims of passing probabilities.
    """
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
    elif score >= 35.0:
        return {
            "tier": "Preparatory Stage",
            "badge_color": "red",
            "summary": "Further preparatory study on general awareness, structured speaking, and confidence building is recommended.",
        }
    else:
        return {
            "tier": "Unsatisfactory / Non-Responsive",
            "badge_color": "darkred",
            "summary": "Demonstrated critical deficiencies, monosyllabic responses ('yes/no'), or failure to address interview questions with substance.",
        }


def format_radar_chart_data(dimension_scores: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Formats dimension scores for radar chart visualization.
    """
    return [
        {"dimension": dim, "score": score}
        for dim, score in dimension_scores.items()
    ]


def calculate_14_olq_scores(
    per_answer_evidence: List[Dict[str, Any]],
    base_baseline: float = 70.0,
) -> Dict[str, float]:
    """
    Layer 2 Scoring: Computes scores for all 14 Officer Like Qualities (OLQs)
    by aggregating relevant evidence items.
    """
    olq_evidence_weights: Dict[str, float] = {olq: 0.0 for olq in FOURTEEN_OLQS}
    olq_evidence_sums: Dict[str, float] = {olq: 0.0 for olq in FOURTEEN_OLQS}

    for ev in per_answer_evidence:
        cat = ev.get("category", "general").lower()
        score = float(ev.get("score", base_baseline))
        conf = float(ev.get("confidence", 0.7))
        target_olqs = CATEGORY_TO_OLQS.get(cat, ["Reasoning Ability", "Power of Expression"])

        for olq in target_olqs:
            olq_evidence_weights[olq] += conf
            olq_evidence_sums[olq] += score * conf

    # Behavioral offsets for unobserved OLQs to reflect realistic variance across dimensions
    unobserved_offsets: Dict[str, float] = {
        "Reasoning Ability": 0.0,
        "Organizing Ability": -2.0,
        "Practical Common Sense": 1.0,
        "Social Adaptability": 2.0,
        "Cooperation": 3.0,
        "Sense of Responsibility": 1.0,
        "Initiative": -1.0,
        "Courage": 0.0,
        "Self-Confidence": -2.0,
        "Determination": 1.0,
        "Stamina": 2.0,
        "Integrity": 3.0,
        "Emotional Stability": 4.0,
        "Power of Expression": -5.0,
    }

    olq_scores: Dict[str, float] = {}
    for olq in FOURTEEN_OLQS:
        total_w = olq_evidence_weights[olq]
        if total_w > 0:
            olq_scores[olq] = round(max(10.0, min(95.0, olq_evidence_sums[olq] / total_w)), 1)
        else:
            # If no direct evidence for this specific OLQ, assign overall session average with subtle natural offset
            avg_ev_score = (
                sum(ev.get("score", base_baseline) for ev in per_answer_evidence) / len(per_answer_evidence)
                if per_answer_evidence else base_baseline
            )
            offset = unobserved_offsets.get(olq, 0.0)
            olq_scores[olq] = round(max(10.0, min(95.0, avg_ev_score + offset)), 1)

    return olq_scores


def calculate_dashboard_dimensions_from_olqs(
    olq_scores: Dict[str, float]
) -> Dict[str, float]:
    """
    Layer 3 Scoring: Computes the 5 Derived Executive Dashboard Dimensions
    from the 14 OLQ scores using explicit weighted combination.
    """
    dim_scores: Dict[str, float] = {}
    for dim_name, mapping in OLQ_TO_DASHBOARD_MAPPING.items():
        dim_score = 0.0
        total_weight = sum(mapping.values())
        for olq, w in mapping.items():
            olq_score = olq_scores.get(olq, 70.0)
            dim_score += olq_score * w
        dim_scores[dim_name] = round(max(10.0, min(95.0, dim_score / total_weight)), 1)
    return dim_scores


def calculate_weighted_overall_score(
    dimension_scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculates deterministic weighted overall practice score from dimension scores.
    """
    if not dimension_scores:
        return 0.0

    default_weights = {
        "Intellect & Reasoning": 0.25,
        "Emotional Composure": 0.20,
        "Social Adaptability & Teamwork": 0.20,
        "Communication & Expression": 0.20,
        "Motivation & Integrity": 0.15,
    }
    applied_weights = weights or default_weights

    total_weight = 0.0
    weighted_sum = 0.0

    for dim, score in dimension_scores.items():
        w = applied_weights.get(dim, 1.0 / len(dimension_scores))
        weighted_sum += score * w
        total_weight += w

    if total_weight > 0:
        return round(weighted_sum / total_weight, 1)
    return round(sum(dimension_scores.values()) / len(dimension_scores), 1)


def calculate_confidence_weighted_score(
    evidences: List[Dict[str, Any]],
    base_score: float = 72.0,
) -> float:
    """
    Aggregates per-answer evidence into a dimension score using evidence confidence weighting.
    """
    if not evidences:
        return base_score

    has_explicit_scores = any("score" in ev for ev in evidences)
    if has_explicit_scores:
        total_conf = sum(float(ev.get("confidence", 0.5)) for ev in evidences)
        if total_conf > 0:
            weighted_sum = sum(float(ev.get("score", base_score)) * float(ev.get("confidence", 0.5)) for ev in evidences)
            return round(max(10.0, min(95.0, weighted_sum / total_conf)), 1)
        scores = [float(ev.get("score", base_score)) for ev in evidences]
        return round(max(10.0, min(95.0, sum(scores) / len(scores))), 1)

    # Indicator delta calculation when only positive/negative indicators are provided
    total_conf = 0.0
    weighted_delta = 0.0
    for ev in evidences:
        conf = float(ev.get("confidence", 0.5))
        pos_count = len(ev.get("positive_indicators", []))
        neg_count = len(ev.get("weaknesses", []))
        raw_delta = (pos_count * 5.0) - (neg_count * 5.0)
        weighted_delta += raw_delta * conf
        total_conf += conf

    adjustment = (weighted_delta / total_conf) if total_conf > 0 else 0.0
    return round(max(10.0, min(95.0, base_score + adjustment)), 1)


def format_evidence_table(per_question_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Formats raw per-question evidence into clean structured tabular data for display.
    """
    table = []
    for idx, item in enumerate(per_question_evidence, 1):
        table.append({
            "No": idx,
            "Question ID": item.get("question_id", f"Q{idx}"),
            "Category": item.get("category", "").replace("_", " ").title(),
            "Assessed Dimension": item.get("dimension", ""),
            "Score": f"{item.get('score', 0):.0f}%",
            "Evidence Confidence": item.get("evidence_confidence", "MEDIUM"),
            "Indicators": ", ".join(item.get("positive_indicators", [])[:2]) or "Baseline response",
            "Weaknesses": ", ".join(item.get("weaknesses", [])) or "None observed",
        })
    return table
