"""
Data Models for the Learning & Improvement Phase in MY_ISSB_Evaluator.
Defines typed schemas for learning recommendations, strengths, retries,
before/after comparisons, candidate learning profiles, and session reports.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StrengthItem:
    """Represents an observed strength reinforced with explanation of why it was effective."""
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
    """Actionable improvement recommendation directly grounded in observed evaluation evidence."""
    area: str
    priority: str  # 'HIGH', 'MEDIUM', 'LOW'
    problem: str
    evidence_ids: List[str] = field(default_factory=list)
    why_it_matters: str = ""
    how_to_improve: str = ""
    technique: str = ""
    practice_task: str = ""
    example_structure: Optional[str] = None  # Structural template with placeholders ONLY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.area,
            "priority": self.priority,
            "problem": self.problem,
            "evidence_ids": self.evidence_ids,
            "why_it_matters": self.why_it_matters,
            "how_to_improve": self.how_to_improve,
            "technique": self.technique,
            "practice_task": self.practice_task,
            "example_structure": self.example_structure,
        }


@dataclass
class LearningSummary:
    """High-level summary of the most critical focus areas for immediate coaching."""
    top_priority: str
    secondary_priority: str
    strength_to_maintain: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "top_priority": self.top_priority,
            "secondary_priority": self.secondary_priority,
            "strength_to_maintain": self.strength_to_maintain,
        }


@dataclass
class RetryPrompt:
    """Practice task and guidance for immediate answer revision."""
    enabled: bool = True
    instruction: str = ""
    target_area: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "instruction": self.instruction,
            "target_area": self.target_area,
        }


@dataclass
class LearningPhaseResult:
    """Complete per-question coaching output produced by the Learning Engine."""
    overall_assessment: str
    strengths: List[StrengthItem] = field(default_factory=list)
    improvement_areas: List[ImprovementArea] = field(default_factory=list)
    learning_summary: LearningSummary = field(
        default_factory=lambda: LearningSummary(
            top_priority="N/A", secondary_priority="N/A", strength_to_maintain="N/A"
        )
    )
    retry: RetryPrompt = field(default_factory=RetryPrompt)
    disclaimer: str = (
        "This is a practice coaching and feedback feature based on the supplied transcript, "
        "evaluation rubric, and knowledge-base evidence. It is not an official ISSB assessment "
        "or prediction of selection."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_phase": {
                "overall_assessment": self.overall_assessment,
                "strengths": [s.to_dict() for s in self.strengths],
                "improvement_areas": [ia.to_dict() for ia in self.improvement_areas],
                "learning_summary": self.learning_summary.to_dict(),
                "retry": self.retry.to_dict(),
                "disclaimer": self.disclaimer,
            }
        }


@dataclass
class BeforeAfterComparison:
    """Verifiable comparison between candidate's initial answer and revised retry answer."""
    previous_score: float
    new_score: float
    change: float
    improved_areas: List[str] = field(default_factory=list)
    unchanged_areas: List[str] = field(default_factory=list)
    new_weaknesses: List[str] = field(default_factory=list)
    explanation: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "before_after": {
                "previous_score": self.previous_score,
                "new_score": self.new_score,
                "change": self.change,
                "improved_areas": self.improved_areas,
                "unchanged_areas": self.unchanged_areas,
                "new_weaknesses": self.new_weaknesses,
                "explanation": self.explanation,
                "metrics": self.metrics,
            }
        }


@dataclass
class CandidateLearningProfile:
    """Longitudinal session-level learning profile tracking candidate development across questions."""
    strengths: List[str] = field(default_factory=list)
    recurring_weaknesses: List[str] = field(default_factory=list)
    improving_areas: List[str] = field(default_factory=list)
    priority_areas: List[str] = field(default_factory=list)
    practice_history: List[Dict[str, Any]] = field(default_factory=list)
    weakness_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_profile": {
                "strengths": self.strengths,
                "recurring_weaknesses": self.recurring_weaknesses,
                "improving_areas": self.improving_areas,
                "priority_areas": self.priority_areas,
                "practice_history": self.practice_history,
                "weakness_counts": self.weakness_counts,
            }
        }


@dataclass
class SessionLearningReport:
    """Comprehensive end-of-session coaching report summarizing learning progression and practice roadmap."""
    candidate_name: str
    session_id: str
    strongest_areas: List[str] = field(default_factory=list)
    weakest_areas: List[str] = field(default_factory=list)
    recurring_weaknesses: List[str] = field(default_factory=list)
    improvements_achieved: List[str] = field(default_factory=list)
    areas_requiring_further_practice: List[str] = field(default_factory=list)
    recommended_practice_exercises: List[str] = field(default_factory=list)
    olqs_with_strong_evidence: List[str] = field(default_factory=list)
    olqs_requiring_more_evidence: List[str] = field(default_factory=list)
    communication_patterns: str = ""
    reasoning_patterns: str = ""
    answer_structuring_patterns: str = ""
    suggested_next_practice_session: str = ""
    methodological_disclaimer: str = (
        "IMPORTANT METHODOLOGICAL NOTICE: This learning and improvement report provides educational "
        "and developmental coaching based on practice simulation. It does NOT represent an official "
        "ISSB selection evaluation or psychological diagnosis."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_learning_report": {
                "candidate_name": self.candidate_name,
                "session_id": self.session_id,
                "strongest_areas": self.strongest_areas,
                "weakest_areas": self.weakest_areas,
                "recurring_weaknesses": self.recurring_weaknesses,
                "improvements_achieved": self.improvements_achieved,
                "areas_requiring_further_practice": self.areas_requiring_further_practice,
                "recommended_practice_exercises": self.recommended_practice_exercises,
                "olqs_with_strong_evidence": self.olqs_with_strong_evidence,
                "olqs_requiring_more_evidence": self.olqs_requiring_more_evidence,
                "communication_patterns": self.communication_patterns,
                "reasoning_patterns": self.reasoning_patterns,
                "answer_structuring_patterns": self.answer_structuring_patterns,
                "suggested_next_practice_session": self.suggested_next_practice_session,
                "methodological_disclaimer": self.methodological_disclaimer,
            }
        }
