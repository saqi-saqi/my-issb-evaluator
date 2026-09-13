"""
Consolidated Learning Engine & Progress Tracker for MY_ISSB_Evaluator.
Provides personalized coaching feedback, practice retry tasks, and honest before-vs-after comparisons.
Fully matches frontend LearningPhaseResult and BeforeAfterComparison schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional

from core.ai import AIClient, ai_client
from core.evaluator import PerAnswerEvidence
from core.storage import StorageManager

logger = logging.getLogger(__name__)


@dataclass
class StrengthItem:
    area: str
    observation: str
    evidence_ids: List[str] = field(default_factory=list)
    reinforcement: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "observation": self.observation,
            "evidence_ids": self.evidence_ids,
            "reinforcement": self.reinforcement,
        }


@dataclass
class ImprovementArea:
    area: str
    priority: str  # 'HIGH', 'MEDIUM', 'LOW'
    problem: str
    evidence_ids: List[str]
    why_it_matters: str
    how_to_improve: str
    technique: str
    practice_task: str
    example_structure: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "priority": self.priority,
            "problem": self.problem,
            "evidence_ids": self.evidence_ids,
            "why_it_matters": self.why_it_matters,
            "how_to_improve": self.how_to_improve,
            "technique": self.technique,
            "recommended_technique": self.technique,
            "practice_task": self.practice_task,
            "example_structure": self.example_structure,
        }


@dataclass
class BeforeAfterComparison:
    previous_score: float
    new_score: float
    change: float
    improved_areas: List[str]
    unchanged_areas: List[str]
    new_weaknesses: List[str]
    explanation: str
    metrics: Dict[str, Any]

    @property
    def improved(self) -> bool:
        return self.change > 0

    @property
    def score_delta(self) -> float:
        return self.change

    @property
    def changes_detected(self) -> List[str]:
        return self.improved_areas

    @property
    def remaining_weaknesses(self) -> List[str]:
        return self.new_weaknesses

    @property
    def coaching_feedback(self) -> str:
        return self.explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "previous_score": self.previous_score,
            "new_score": self.new_score,
            "change": self.change,
            "improved_areas": self.improved_areas,
            "unchanged_areas": self.unchanged_areas,
            "new_weaknesses": self.new_weaknesses,
            "explanation": self.explanation,
            "metrics": self.metrics,
            "improved": self.improved,
            "score_delta": self.score_delta,
            "changes_detected": self.changes_detected,
            "remaining_weaknesses": self.remaining_weaknesses,
            "coaching_feedback": self.coaching_feedback,
        }


class LearningService:
    """Manages candidate improvement coaching, retry evaluations, and learning profiles."""

    def __init__(self, ai: Optional[AIClient] = None, storage: Optional[StorageManager] = None):
        self.ai = ai or ai_client
        self.storage = storage
        self.profiles: Dict[str, Dict[str, Any]] = {}

    def generate_feedback(self, evidence: PerAnswerEvidence) -> Dict[str, Any]:
        """Generates evidence-grounded coaching feedback matching frontend LearningPhaseResult."""
        weaknesses = evidence.weaknesses
        dimension = evidence.dimension
        positives = evidence.positive_indicators
        q_id = evidence.question_id

        # Convert positives into StrengthItem list
        strengths: List[Dict[str, Any]] = []
        for idx, pos in enumerate(positives):
            strengths.append(
                StrengthItem(
                    area=dimension,
                    observation=pos,
                    evidence_ids=[f"{q_id}_pos_{idx+1}"],
                    reinforcement="Maintain this authentic personal clarity in future answers.",
                ).to_dict()
            )

        if not strengths:
            strengths.append(
                StrengthItem(
                    area=dimension,
                    observation="Engaged with the selection question and attempted response under pressure.",
                    evidence_ids=[q_id],
                    reinforcement="Building consistency will strengthen this dimension.",
                ).to_dict()
            )

        # Convert weaknesses into ImprovementArea list
        improvement_areas: List[Dict[str, Any]] = []
        for idx, w in enumerate(weaknesses[:2]):
            priority = "HIGH" if any(k in w.lower() for k in ["monosyllabic", "evasive", "refusal"]) else "MEDIUM"
            if "brief" in w.lower() or "monosyllabic" in w.lower() or "evasive" in w.lower():
                area_name = "Expression & Substance Depth"
                problem = w
                why = "At ISSB, brevity is often interpreted as hesitation, lack of conviction, or evasiveness."
                how = "Structure response in 3 layers: 1) Direct answer, 2) Specific real-life example, 3) Outcome/Lesson."
                technique = "Use the 3-sentence rule: Direct Answer → Contextual Example → Personal Result."
                task = "Expand your response to at least 3-4 sentences detailing an actual instance from your background."
                structure = "I believe [Direct Answer]. Specifically, when I was in [Situation], I [Action]. Consequently, [Result]."
            elif "ownership" in w.lower() or "abstract" in w.lower():
                area_name = "Ownership / Accountability"
                problem = w
                why = "The selection board evaluates personal leadership agency, not theoretical or passive opinions."
                how = "Speak in active first-person voice ('I decided', 'I organized', 'My responsibility was')."
                technique = "Active Ownership Framing: State personal accountability without passing blame."
                task = "Rewrite your answer using first-person active phrasing and state your exact role."
                structure = "In that situation, I took personal responsibility for [Task]. I decided to [Action], which resulted in [Outcome]."
            else:
                area_name = "Structured Reasoning"
                problem = w
                why = "Assessing officers look for structured, causal logic under pressure."
                how = "Provide explicit causal justifications ('because', 'therefore', 'consequently')."
                technique = "STAR Framework: Situation → Task → Action → Result."
                task = "State why you took that action and explain the resulting outcome."
                structure = "The situation was [Situation]. My goal was [Task]. I chose to [Action] because [Reason]. The result was [Outcome]."

            improvement_areas.append(
                ImprovementArea(
                    area=area_name,
                    priority=priority,
                    problem=problem,
                    evidence_ids=[f"{q_id}_wk_{idx+1}"],
                    why_it_matters=why,
                    how_to_improve=how,
                    technique=technique,
                    practice_task=task,
                    example_structure=structure,
                ).to_dict()
            )

        if not improvement_areas:
            improvement_areas.append(
                ImprovementArea(
                    area="Ownership / Accountability",
                    priority="MEDIUM",
                    problem="Response can be strengthened with more explicit personal agency and individual contribution.",
                    evidence_ids=[q_id],
                    why_it_matters="The selection board assesses personal leadership agency and individual impact.",
                    how_to_improve="Highlight what you personally decided, organized, or took responsibility for.",
                    technique="Active Ownership Framing: State personal accountability without passing blame.",
                    practice_task="Rewrite your response focusing on your specific role and decisions.",
                    example_structure="In that situation, I took personal responsibility for [Task]. I decided to [Action], which resulted in [Outcome].",
                ).to_dict()
            )

        top_p = improvement_areas[0]["area"] if improvement_areas else "Maintain Current Standard"
        retry_task = (
            improvement_areas[0]["practice_task"]
            if improvement_areas
            else "Provide a more concrete personal response with real-life examples."
        )

        overall = (
            f"Response evaluated in {dimension}. Identified key opportunities to strengthen observable behavioral indicators."
            if improvement_areas
            else f"Strong performance in {dimension}. Authentic alignment with observable positive indicators."
        )

        return {
            "overall_assessment": overall,
            "status": "needs_practice" if improvement_areas else "strong",
            "dimension": dimension,
            "strengths": strengths,
            "improvement_areas": improvement_areas,
            "retry_task": retry_task,
            "learning_summary": {
                "top_priority": top_p,
                "secondary_priority": improvement_areas[1]["area"] if len(improvement_areas) > 1 else "Depth & Specificity",
                "strength_to_maintain": strengths[0]["observation"] if strengths else "Engagement under pressure",
            },
            "retry": {
                "enabled": True,
                "instruction": retry_task,
                "target_area": top_p,
            },
            "disclaimer": "Formative practice guidance generated from observable indicators. Not an official board evaluation.",
        }

    def evaluate_retry(
        self,
        question_id: str,
        original_answer: str,
        retry_answer: str,
        original_score: float,
    ) -> BeforeAfterComparison:
        """Compares retry response against initial response and returns BeforeAfterComparison."""
        orig = (original_answer or "").strip()
        retry = (retry_answer or "").strip()
        orig_words = len(orig.split())
        retry_words = len(retry.split())

        improved_areas: List[str] = []
        unchanged_areas: List[str] = []
        new_weaknesses: List[str] = []

        # 1. Word count expansion
        if retry_words >= orig_words + 10:
            improved_areas.append(f"Substantive Detail Expansion ({orig_words} → {retry_words} words)")
        elif retry_words < orig_words - 5:
            new_weaknesses.append("Response brevity decreased further")
        else:
            unchanged_areas.append("Length and detail remained similar")

        # 2. Ownership check
        retry_lower = retry.lower()
        has_new_ownership = any(
            p in retry_lower for p in [
                "i decided", "my responsibility", "i led", "i organized", "my mistake",
                "i take full responsibility", "take full responsibility", "i stepped in",
                "resolved the problem", "i resolved"
            ]
        )
        if has_new_ownership and not any(p in orig.lower() for p in ["i decided", "my responsibility", "i led", "i take full responsibility"]):
            improved_areas.append("Ownership / Accountability")
        elif not has_new_ownership:
            unchanged_areas.append("Personal ownership framing")

        # 3. Example check
        has_new_example = any(
            p in retry_lower for p in ["specifically", "for example", "in my college", "during my", "when i"]
        )
        if has_new_example and not any(p in orig.lower() for p in ["specifically", "for example"]):
            improved_areas.append("Concrete Real-Life Context and Examples")
        elif not has_new_example:
            unchanged_areas.append("Grounded examples")

        # 4. Structured reasoning
        has_new_reasoning = any(p in retry_lower for p in ["because", "therefore", "as a result", "firstly"])
        if has_new_reasoning and not any(p in orig.lower() for p in ["because", "therefore"]):
            improved_areas.append("Logical Causal Reasoning ('because', 'therefore')")

        # Calculate delta honestly
        score_boost = len(improved_areas) * 8.0
        if not improved_areas and retry_words <= orig_words:
            retry_score = max(20.0, original_score - 5.0 if retry_words < orig_words else original_score)
            unchanged_areas.append("Observable behavioral indicators")
        else:
            retry_score = min(95.0, original_score + score_boost)

        delta = round(retry_score - original_score, 1)

        explanation = (
            f"Demonstrated measurable improvement (+{delta} points). Incorporated specific details and personal ownership."
            if delta > 0
            else "Retry did not show measurable progression. Make sure to cite a specific instance and your exact actions."
        )

        return BeforeAfterComparison(
            previous_score=round(original_score, 1),
            new_score=round(retry_score, 1),
            change=delta,
            improved_areas=improved_areas,
            unchanged_areas=unchanged_areas,
            new_weaknesses=new_weaknesses,
            explanation=explanation,
            metrics={
                "before": {"word_count": orig_words, "score": round(original_score, 1)},
                "after": {"word_count": retry_words, "score": round(retry_score, 1)},
                "improvement": {"score_change": delta, "word_delta": retry_words - orig_words},
            },
        )

    def initialize_profile(self, session_id: str, candidate_name: str) -> None:
        """Initializes a new profile for a candidate session."""
        if session_id not in self.profiles:
            profile_data = {
                "session_id": session_id,
                "candidate_name": candidate_name or "Candidate",
                "overall_score": 70.0,
                "performance_band": "Consistent Competence",
                "key_strengths": ["Authentic engagement under pressure"],
                "primary_shortcomings": [],
                "strengths": ["Authentic engagement under pressure"],
                "recurring_weaknesses": [],
                "improving_areas": [],
                "priority_areas": ["Active Ownership"],
                "practice_history": [],
                "weakness_counts": {},
            }
            self.profiles[session_id] = profile_data
            if self.storage:
                self.storage.save_profile(session_id, profile_data)

    def record_retry(
        self,
        session_id: str,
        candidate_name: str,
        comparison: BeforeAfterComparison,
        question_id: str,
    ) -> None:
        """Updates candidate learning profile after a retry attempt."""
        if session_id not in self.profiles:
            self.initialize_profile(session_id, candidate_name)

        prof = self.profiles[session_id]
        if candidate_name:
            prof["candidate_name"] = candidate_name
        for area in comparison.improved_areas:
            if area not in prof["improving_areas"]:
                prof["improving_areas"].append(area)
        prof["practice_history"].append(comparison.to_dict())
        if self.storage:
            self.storage.save_profile(session_id, prof)

    def record_session(self, session_id: str, candidate_name: str, report_dict: Dict[str, Any]) -> None:
        """Stores or updates session learning profile."""
        current_improving = self.profiles.get(session_id, {}).get("improving_areas", ["Expression", "Reasoning"])
        history = self.profiles.get(session_id, {}).get("practice_history", [])
        profile_data = {
            "session_id": session_id,
            "candidate_name": candidate_name,
            "overall_score": report_dict.get("overall_practice_score", 0),
            "performance_band": report_dict.get("performance_band", {}).get("tier", "Unknown"),
            "key_strengths": report_dict.get("key_strengths", []),
            "primary_shortcomings": report_dict.get("primary_shortcomings", []),
            "strengths": report_dict.get("key_strengths", []),
            "recurring_weaknesses": report_dict.get("primary_shortcomings", []),
            "improving_areas": current_improving,
            "priority_areas": ["Active Ownership"],
            "practice_history": history,
            "weakness_counts": {},
        }
        self.profiles[session_id] = profile_data
        if self.storage:
            self.storage.save_profile(session_id, profile_data)

    def get_profile(self, session_id: str) -> Dict[str, Any]:
        if session_id in self.profiles:
            return self.profiles[session_id]
        if self.storage:
            saved = self.storage.get_profile(session_id)
            if saved:
                self.profiles[session_id] = saved
                return saved
        return {
            "session_id": session_id,
            "candidate_name": "Candidate",
            "overall_score": 70,
            "strengths": ["Authentic engagement"],
            "recurring_weaknesses": [],
            "improving_areas": [],
            "priority_areas": [],
            "practice_history": [],
            "weakness_counts": {},
        }
