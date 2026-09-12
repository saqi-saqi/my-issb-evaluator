"""
Streamlined 2-Pass Rubric Evaluation Engine for MY_ISSB_Evaluator.
Pass 1: Deterministic Per-Answer Evidence & Observable Indicators with RAG provenance citations.
Pass 2: Deterministic 14-OLQ + 5-Dimension aggregation, concluded by a single LLM narrative synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional

from core.ai import AIClient, ai_client
from core.rag import KnowledgeRetriever
from core.scoring import (
    FOURTEEN_OLQS,
    calculate_14_olq_scores,
    calculate_dashboard_dimensions,
    calculate_overall_score,
    get_performance_band,
)

logger = logging.getLogger(__name__)


@dataclass
class PerAnswerEvidence:
    question_id: str
    question_text: str
    category: str
    dimension: str
    score: float
    confidence: float
    evidence_confidence: str  # 'HIGH', 'MEDIUM', 'LOW', 'NONE'
    positive_indicators: List[str]
    weaknesses: List[str]
    evidence_text: str
    citations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "category": self.category,
            "dimension": self.dimension,
            "score": self.score,
            "confidence": self.confidence,
            "evidence_confidence": self.evidence_confidence,
            "positive_indicators": self.positive_indicators,
            "weaknesses": self.weaknesses,
            "evidence_text": self.evidence_text,
            "citations": self.citations,
        }


@dataclass
class EvaluationReport:
    candidate_name: str
    persona: str
    overall_practice_score: float
    performance_band: Dict[str, str]
    dimension_scores: Dict[str, float]
    fourteen_olq_scores: Dict[str, float]
    per_question_evidence: List[PerAnswerEvidence]
    executive_summary: str
    key_strengths: List[str]
    primary_shortcomings: List[str]
    actionable_recommendations: List[str]
    radar_chart_data: List[Dict[str, Any]] = field(default_factory=list)
    fourteen_olq_radar_data: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "persona": self.persona,
            "overall_practice_score": self.overall_practice_score,
            "performance_band": self.performance_band,
            "dimension_scores": self.dimension_scores,
            "fourteen_olq_scores": self.fourteen_olq_scores,
            "per_question_evidence": [e.to_dict() for e in self.per_question_evidence],
            "executive_summary": self.executive_summary,
            "key_strengths": self.key_strengths,
            "primary_shortcomings": self.primary_shortcomings,
            "actionable_recommendations": self.actionable_recommendations,
            "radar_chart_data": self.radar_chart_data,
            "fourteen_olq_radar_data": self.fourteen_olq_radar_data,
        }


class RubricEvaluator:
    """Evaluates interview sessions using a defensible 2-Pass pipeline."""

    def __init__(self, retriever: Optional[KnowledgeRetriever] = None, ai: Optional[AIClient] = None):
        self.retriever = retriever or KnowledgeRetriever()
        self.ai = ai or ai_client

    # -------------------------------------------------------------------------
    # PASS 1: Per-Answer Evidence Calculation
    # -------------------------------------------------------------------------
    def evaluate_answer_evidence(
        self,
        question_id: str,
        question_text: str,
        category: str,
        dimension: str,
        intent: str,
        primary_answer: str,
        follow_up_answer: Optional[str] = None,
    ) -> PerAnswerEvidence:
        """Evaluates a single question turn against observable indicators and RAG context."""
        ans = (primary_answer or "").strip()
        fu = (follow_up_answer or "").strip()
        combined_text = f"{ans} {fu}".strip().lower()
        word_count = len(combined_text.split())

        positives: List[str] = []
        weaknesses: List[str] = []

        # Retrieve grounding RAG benchmarks
        rag_chunks = self.retriever.retrieve(f"{question_text} {category}", top_k=2)
        citations = [c["citation"] for c in rag_chunks]

        # Monosyllabic / evasive checks
        monosyllabic = {"yes", "no", "yeah", "nope", "dont know", "skip", "idk", "pass", "ok", "fine"}
        clean_words = re.findall(r"\b[a-z]+\b", combined_text)

        is_evasive = (
            word_count == 0
            or (word_count <= 4 and all(w in monosyllabic for w in clean_words))
            or any(p in combined_text for p in ["dont care", "dont want to", "i decline", "no idea"])
        )

        has_ownership = any(
            p in combined_text
            for p in ["i took", "i decided", "my fault", "my mistake", "i led", "i organized", "i took responsibility", "i resolved"]
        )
        has_example = any(
            p in combined_text
            for p in ["for example", "specifically", "in my college", "during my", "when i was", "for instance", "in our team"]
        )
        has_reasoning = any(
            p in combined_text
            for p in ["because", "reason", "therefore", "as a result", "firstly", "secondly"]
        )
        has_teamwork = any(
            p in combined_text
            for p in ["we ", "our team", "together", "helped", "colleague", "group goal"]
        )

        if is_evasive and not has_ownership:
            weaknesses.append("Severely brief or evasive reply; provided no supporting context or personal narrative.")
            return PerAnswerEvidence(
                question_id=question_id,
                question_text=question_text,
                category=category,
                dimension=dimension,
                score=20.0,
                confidence=0.95,
                evidence_confidence="NONE",
                positive_indicators=[],
                weaknesses=weaknesses,
                evidence_text=ans[:120],
                citations=citations,
            )

        # Baseline scoring by depth
        if word_count < 15 and not has_ownership:
            score = 50.0
            ev_conf = "LOW"
            num_conf = 0.60
            weaknesses.append("Response was very brief; lacked detailed supporting context or examples.")
        elif word_count < 35:
            score = 68.0
            ev_conf = "MEDIUM"
            num_conf = 0.75
        else:
            score = 74.0
            ev_conf = "MEDIUM"
            num_conf = 0.85

        # Modifiers based on observable indicators
        if has_ownership:
            positives.append("Demonstrated direct personal accountability and ownership without evasiveness.")
            score += 12.0
            ev_conf = "HIGH"
            num_conf = 0.90

        if has_example:
            positives.append("Grounded assertions in concrete personal experiences or specific examples.")
            score += 8.0
            ev_conf = "HIGH"
        elif word_count >= 30 and not has_example:
            weaknesses.append("Relied heavily on abstract assertions; recommend citing concrete personal examples.")

        if has_reasoning:
            positives.append("Structured thoughts logically with causal justification.")
            score += 6.0

        if has_teamwork:
            positives.append("Demonstrated collaborative team orientation and shared mission alignment.")
            score += 5.0

        score = max(15.0, min(100.0, round(score, 1)))

        return PerAnswerEvidence(
            question_id=question_id,
            question_text=question_text,
            category=category,
            dimension=dimension,
            score=score,
            confidence=num_conf,
            evidence_confidence=ev_conf,
            positive_indicators=positives,
            weaknesses=weaknesses,
            evidence_text=ans[:150],
            citations=citations,
        )

    # -------------------------------------------------------------------------
    # PASS 2: Deterministic Aggregation & Single Narrative Synthesis
    # -------------------------------------------------------------------------
    def evaluate_session(
        self,
        candidate_name: str,
        persona: str,
        evidence_list: List[PerAnswerEvidence],
    ) -> EvaluationReport:
        """Aggregates scores deterministically and invokes a single LLM call for narrative report."""
        if not evidence_list:
            default_band = get_performance_band(50.0)
            return EvaluationReport(
                candidate_name=candidate_name,
                persona=persona,
                overall_practice_score=50.0,
                performance_band=default_band,
                dimension_scores={},
                fourteen_olq_scores={},
                per_question_evidence=[],
                executive_summary="No answers recorded for this session.",
                key_strengths=[],
                primary_shortcomings=["Interview was terminated before answers were provided."],
                actionable_recommendations=["Complete a full practice session."],
            )

        # 1. Deterministic math layer
        olq_scores = calculate_14_olq_scores(evidence_list)
        dim_scores = calculate_dashboard_dimensions(olq_scores)
        overall_score = calculate_overall_score(dim_scores)
        band = get_performance_band(overall_score)

        # 2. Extract aggregated positive indicators and weaknesses
        all_positives = [p for e in evidence_list for p in e.positive_indicators]
        all_weaknesses = [w for e in evidence_list for w in e.weaknesses]

        # 3. Single Groq LLM call for qualitative narrative
        narrative = self._generate_qualitative_narrative(
            candidate_name=candidate_name,
            persona=persona,
            overall_score=overall_score,
            band_tier=band["tier"],
            dimension_scores=dim_scores,
            positives=all_positives,
            weaknesses=all_weaknesses,
        )

        # Format radar data for frontend
        radar_data = [
            {"subject": dim, "dimension": dim, "score": score, "fullMark": 100}
            for dim, score in dim_scores.items()
        ]
        olq_radar_data = [
            {"subject": olq, "olq": olq, "score": score, "fullMark": 100}
            for olq, score in olq_scores.items()
        ]

        return EvaluationReport(
            candidate_name=candidate_name,
            persona=persona,
            overall_practice_score=overall_score,
            performance_band=band,
            dimension_scores=dim_scores,
            fourteen_olq_scores=olq_scores,
            per_question_evidence=evidence_list,
            executive_summary=narrative.get(
                "executive_summary",
                f"Candidate completed the session with an overall practice score of {overall_score}%. "
                f"Evaluation band: {band['tier']}.",
            ),
            key_strengths=narrative.get("key_strengths", list(set(all_positives))[:4]),
            primary_shortcomings=narrative.get("primary_shortcomings", list(set(all_weaknesses))[:4]),
            actionable_recommendations=narrative.get(
                "actionable_recommendations",
                [
                    "Ground responses in specific personal actions rather than abstract generalizations.",
                    "Articulate causal structure ('because', 'therefore') when explaining decisions.",
                    "Practice expanding answers beyond monosyllabic assertions.",
                ],
            ),
            radar_chart_data=radar_data,
            fourteen_olq_radar_data=olq_radar_data,
        )

    def _generate_qualitative_narrative(
        self,
        candidate_name: str,
        persona: str,
        overall_score: float,
        band_tier: str,
        dimension_scores: Dict[str, float],
        positives: List[str],
        weaknesses: List[str],
    ) -> Dict[str, Any]:
        """Executes a single concise Groq LLM call to synthesize the qualitative report."""
        prompt = f"""
You are a senior ISSB assessor. Synthesize a structured, constructive qualitative evaluation report.
Candidate: {candidate_name}
Interviewer Persona: {persona}
Overall Practice Score: {overall_score:.1f}% ({band_tier})

Dimension Breakdown:
{chr(10).join(f"- {k}: {v:.1f}%" for k, v in dimension_scores.items())}

Observed Strengths:
{chr(10).join(f"- {p}" for p in set(positives[:6])) if positives else "- None recorded"}

Observed Shortcomings:
{chr(10).join(f"- {w}" for w in set(weaknesses[:6])) if weaknesses else "- None recorded"}

Return a JSON object with exactly these keys:
{{
  "executive_summary": "Concise 2-3 sentence overview of candidate performance, communication demeanor, and readiness.",
  "key_strengths": ["3-4 specific strengths demonstrated"],
  "primary_shortcomings": ["2-3 specific behavioral gaps to work on"],
  "actionable_recommendations": ["3 practical coaching tips for real ISSB"]
}}
"""
        res = self.ai.generate_json(prompt, system="You are an expert military psychology assessor for ISSB.")
        return res if res else {}
