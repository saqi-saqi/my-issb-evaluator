"""
Learning Progress Tracker & Retry Evaluator for MY_ISSB_Evaluator.
Maintains longitudinal candidate learning profile, detects recurring improvement areas,
honestly compares before/after retry attempts, and synthesizes session-level coaching reports.
"""

from typing import Any, Dict, List, Optional, Set

from src.evaluator.rubric_engine import PerAnswerEvidence
from src.learning.models import (
    BeforeAfterComparison,
    CandidateLearningProfile,
    LearningPhaseResult,
    SessionLearningReport,
)


class LearningProgressTracker:
    """
    Manages longitudinal learning profiles, evaluates retries, and compiles session coaching reports.
    Guarantees no false claims of improvement: improvements are only credited when backed by evidence.
    """

    def __init__(self, profile: Optional[CandidateLearningProfile] = None):
        self.profile = profile or CandidateLearningProfile()

    def record_answer_evaluation(
        self,
        qa_pair: Dict[str, Any],
        evidence: PerAnswerEvidence,
        learning_result: LearningPhaseResult,
    ) -> None:
        """
        Updates candidate learning profile after an answer is evaluated.
        Tracks recurring weaknesses and updates priority areas.
        """
        # 1. Update strengths
        for s in learning_result.strengths:
            if s.area not in self.profile.strengths:
                self.profile.strengths.append(s.area)

        # 2. Update weaknesses & detect recurrence
        for ia in learning_result.improvement_areas:
            area = ia.area
            current_count = self.profile.weakness_counts.get(area, 0) + 1
            self.profile.weakness_counts[area] = current_count

            # If weakness occurs 2 or more times, mark as recurring
            if current_count >= 2 and area not in self.profile.recurring_weaknesses:
                self.profile.recurring_weaknesses.append(area)

            # Record in priority areas if HIGH or MEDIUM priority
            if ia.priority in ("HIGH", "MEDIUM") and area not in self.profile.priority_areas:
                self.profile.priority_areas.append(area)

        # 3. Append to practice history
        self.profile.practice_history.append({
            "question_id": qa_pair.get("question_id", ""),
            "question": qa_pair.get("question", ""),
            "score": evidence.score,
            "evidence_confidence": evidence.evidence_confidence,
            "strengths": [s.area for s in learning_result.strengths],
            "improvement_areas": [ia.area for ia in learning_result.improvement_areas],
            "is_retry": False,
        })

    def compare_before_after(
        self,
        before_qa: Dict[str, Any],
        before_evidence: PerAnswerEvidence,
        after_qa: Dict[str, Any],
        after_evidence: PerAnswerEvidence,
    ) -> BeforeAfterComparison:
        """
        Performs strict, honest comparison between initial answer and retry attempt.
        Only reports improvement if the second evaluation provides verifiable evidence for it.
        """
        prev_score = float(before_evidence.score)
        new_score = float(after_evidence.score)
        change = round(new_score - prev_score, 1)

        before_text = f"{before_qa.get('answer', '')} {before_qa.get('follow_up_answer', '')}".strip().lower()
        after_text = f"{after_qa.get('answer', '')} {after_qa.get('follow_up_answer', '')}".strip().lower()

        # Detailed marker metrics
        before_has_ownership = any(k in before_text for k in ["responsibility", "fault", "admit", "apologiz", "took charge", "i decided", "my mistake"])
        after_has_ownership = any(k in after_text for k in ["responsibility", "fault", "admit", "apologiz", "took charge", "i decided", "my mistake"])

        before_has_example = any(k in before_text for k in ["for example", "specifically", "in my", "when i", "during"])
        after_has_example = any(k in after_text for k in ["for example", "specifically", "in my", "when i", "during"])

        before_has_causal = any(k in before_text for k in ["because", "reason", "therefore", "as a result"])
        after_has_causal = any(k in after_text for k in ["because", "reason", "therefore", "as a result"])

        before_words = len(before_text.split())
        after_words = len(after_text.split())

        improved_areas: List[str] = []
        unchanged_areas: List[str] = []
        new_weaknesses: List[str] = []

        # Check for genuine improvements
        if change > 0:
            if not before_has_ownership and after_has_ownership:
                improved_areas.append("Ownership / Accountability")
            if not before_has_example and after_has_example:
                improved_areas.append("Specificity")
            if not before_has_causal and after_has_causal:
                improved_areas.append("Reasoning Ability")
            if before_words <= 5 and after_words >= 15:
                improved_areas.append("Power of Expression")
            if before_evidence.evidence_confidence in ("LOW", "NONE") and after_evidence.evidence_confidence in ("MEDIUM", "HIGH"):
                improved_areas.append("Evidence & Completeness")

            # If score improved but specific markers above didn't catch it, credit overall answer quality
            if not improved_areas:
                improved_areas.append("Overall Answer Adequacy")

        # Check for areas that remained weak or unchanged
        for w in after_evidence.weaknesses:
            if w in before_evidence.weaknesses:
                area_label = "Specificity" if "concrete" in w.lower() else ("Ownership" if "attribution" in w.lower() or "ownership" in w.lower() else "Clarity")
                if area_label not in unchanged_areas and area_label not in improved_areas:
                    unchanged_areas.append(area_label)
            else:
                new_weaknesses.append(w)

        # Build honest qualitative explanation
        if change > 5.0 and improved_areas:
            explanation = (
                f"Your retry answer demonstrated noticeable improvement (+{change} points). "
                f"Specifically, you enhanced {', '.join(improved_areas)} by providing "
                f"{'clear personal ownership' if 'Ownership / Accountability' in improved_areas else 'more concrete substance and structured reasoning'}."
            )
        elif change > 0:
            explanation = (
                f"Your retry showed slight improvement (+{change} points). "
                f"You showed progress in {', '.join(improved_areas)}, but continue refining your delivery with concrete examples."
            )
        elif change == 0.0:
            explanation = (
                "Your retry answer received an identical score (change: 0 points). "
                "The revised answer did not introduce new evidence or address the identified improvement areas."
            )
        else:
            explanation = (
                f"Your retry answer scored lower than your initial attempt ({change} points). "
                "The revision omitted supporting rationale or introduced new weaknesses. Review the coaching guidance and try again."
            )

        # Update learning profile with retry progression
        for imp in improved_areas:
            if imp not in self.profile.improving_areas:
                self.profile.improving_areas.append(imp)

        self.profile.practice_history.append({
            "question_id": after_qa.get("question_id", ""),
            "previous_score": prev_score,
            "new_score": new_score,
            "change": change,
            "improved_areas": improved_areas,
            "is_retry": True,
        })

        metrics = {
            "before": {
                "score": prev_score,
                "word_count": before_words,
                "has_ownership": before_has_ownership,
                "has_concrete_example": before_has_example,
                "confidence": before_evidence.evidence_confidence,
            },
            "after": {
                "score": new_score,
                "word_count": after_words,
                "has_ownership": after_has_ownership,
                "has_concrete_example": after_has_example,
                "confidence": after_evidence.evidence_confidence,
            },
            "improvement": {
                "overall_score": f"+{change}" if change > 0 else f"{change}",
                "word_count": f"+{after_words - before_words}" if after_words >= before_words else f"{after_words - before_words}",
            },
        }

        return BeforeAfterComparison(
            previous_score=prev_score,
            new_score=new_score,
            change=change,
            improved_areas=improved_areas,
            unchanged_areas=unchanged_areas,
            new_weaknesses=new_weaknesses,
            explanation=explanation,
            metrics=metrics,
        )

    def generate_session_learning_report(
        self,
        candidate_name: str,
        session_id: str,
        overall_score: float,
        dimension_scores: Dict[str, float],
        fourteen_olq_scores: Dict[str, float],
    ) -> SessionLearningReport:
        """
        Compiles the complete 12-point session learning report for candidate self-study and coaching.
        """
        # Strongest and weakest dashboard dimensions
        sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)
        strongest_areas = [f"{d[0]} ({d[1]:.1f})" for d in sorted_dims[:2]] if sorted_dims else ["Direct Engagement"]
        weakest_areas = [f"{d[0]} ({d[1]:.1f})" for d in sorted_dims[-2:]] if sorted_dims else ["Answer Elaboration"]

        # 14-OLQ Evidence Breakdown
        olqs_strong = [name for name, sc in fourteen_olq_scores.items() if sc >= 70.0]
        olqs_need_practice = [name for name, sc in fourteen_olq_scores.items() if sc < 70.0]

        # Recommended Practice Exercises
        exercises: List[str] = []
        if "Power of Expression" in self.profile.recurring_weaknesses or "Power of Expression" in self.profile.priority_areas:
            exercises.append("30-Second Rapid Structuring: Practice stating your core conclusion in sentence 1, followed by 2 distinct rationales.")
        if "Ownership / Accountability" in self.profile.recurring_weaknesses or "Ownership / Accountability" in self.profile.priority_areas:
            exercises.append("Ownership Reframing Drills: Convert 5 past group projects into personal contribution statements using 'I decided', 'I organized'.")
        if "Specificity" in self.profile.recurring_weaknesses or "Specificity" in self.profile.priority_areas or not exercises:
            exercises.append("STAR Technique Drills: Formulate 3 personal stories (college, sports, community) using Situation → Action → Result.")
        if "Emotional Composure" in weakest_areas:
            exercises.append("Stress Interrogation Resilience: Practice accepting challenge questions without defensive justification or external blaming.")

        # Behavioral patterns observed
        comm_pattern = (
            "Concise and responsive. Tends to state conclusions quickly; benefits from deliberately elaborating with structured supporting points."
            if "Completeness" in self.profile.weakness_counts or "Power of Expression" in self.profile.weakness_counts
            else "Articulate and substantive. Consistently communicates with sufficient detail and clarity."
        )

        reasoning_pattern = (
            "Relies on practical intuition. Developing stronger explicit cause-and-effect chains ('because', 'therefore') will bolster intellectual presentation."
            if "Reasoning Ability" in self.profile.weakness_counts
            else "Structured and analytical. Demonstrates logical cause-and-effect justification across responses."
        )

        structuring_pattern = (
            "Variable structure. Practicing the STAR (Situation → Action → Result) template will eliminate abstract drifting."
            if "Specificity" in self.profile.weakness_counts or self.profile.recurring_weaknesses
            else "Well-organized with clear progression from premise to outcome."
        )

        suggested_next_session = (
            f"Focus next practice session on {self.profile.priority_areas[0] if self.profile.priority_areas else 'Situational Dilemmas'} "
            f"under the Deputy President persona. Complete 4-6 questions with mandatory first-person ownership and STAR structuring."
        )

        return SessionLearningReport(
            candidate_name=candidate_name,
            session_id=session_id,
            strongest_areas=strongest_areas,
            weakest_areas=weakest_areas,
            recurring_weaknesses=self.profile.recurring_weaknesses,
            improvements_achieved=self.profile.improving_areas,
            areas_requiring_further_practice=self.profile.priority_areas or [weakest_areas[0].split(" (")[0]],
            recommended_practice_exercises=exercises,
            olqs_with_strong_evidence=olqs_strong,
            olqs_requiring_more_evidence=olqs_need_practice,
            communication_patterns=comm_pattern,
            reasoning_patterns=reasoning_pattern,
            answer_structuring_patterns=structuring_pattern,
            suggested_next_practice_session=suggested_next_session,
        )
