"""
Evidence-Grounded Learning & Improvement Engine for MY_ISSB_Evaluator.
Consumes evaluation evidence, diagnoses specific weaknesses, generates actionable coaching,
enforces zero-hallucination of candidate experiences, and handles abstentions neutrally.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Set

from src.evaluator.rubric_engine import PerAnswerEvidence
from src.learning.models import (
    CandidateLearningProfile,
    ImprovementArea,
    LearningPhaseResult,
    LearningSummary,
    RetryPrompt,
    StrengthItem,
)


class LearningEngine:
    """
    Translates observable evaluation evidence into actionable, personalized coaching recommendations.
    Never hallucinates candidate life stories, strictly adheres to structural templates,
    and assigns priorities based on evidence grounding and recurrence.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client

    def generate_feedback(
        self,
        qa_pair: Dict[str, Any],
        evidence: PerAnswerEvidence,
        learning_profile: Optional[CandidateLearningProfile] = None,
        retrieved_context: Optional[List[Dict[str, Any]]] = None,
    ) -> LearningPhaseResult:
        """
        Builds a comprehensive LearningPhaseResult from evaluator output and question context.
        """
        question_text = qa_pair.get("question", "")
        intent = qa_pair.get("intent", "")
        answer = qa_pair.get("answer", "")
        follow_up_answer = qa_pair.get("follow_up_answer", "")
        combined_text = f"{answer} {follow_up_answer}".strip().lower()

        evidence_ids = [f"EV{i+1}" for i in range(len(evidence.source_ids or [1]))] or ["EV1"]

        # 1. Identify Strengths and formulate reinforcement
        strengths = self._extract_strengths(evidence, combined_text, evidence_ids)

        # 2. Diagnose Improvement Areas directly from observed evaluation evidence
        improvement_areas = self._diagnose_improvement_areas(
            qa_pair=qa_pair,
            evidence=evidence,
            combined_text=combined_text,
            evidence_ids=evidence_ids,
            learning_profile=learning_profile,
        )

        # 3. Create high-level learning summary
        learning_summary = self._build_learning_summary(strengths, improvement_areas)

        # 4. Generate Retry prompt and instructions
        retry_prompt = self._build_retry_prompt(improvement_areas, question_text)

        # 5. Formulate overall coaching assessment
        overall_assessment = self._build_overall_assessment(
            evidence=evidence,
            strengths=strengths,
            improvement_areas=improvement_areas,
            candidate_answer=answer,
            question_text=question_text,
        )

        return LearningPhaseResult(
            overall_assessment=overall_assessment,
            strengths=strengths,
            improvement_areas=improvement_areas,
            learning_summary=learning_summary,
            retry=retry_prompt,
        )

    def _extract_strengths(
        self,
        evidence: PerAnswerEvidence,
        combined_text: str,
        evidence_ids: List[str],
    ) -> List[StrengthItem]:
        """Extracts observed positive indicators and reinforces why they were effective."""
        # If candidate was non-responsive, evasive, or low-scoring (< 45.0), NO strengths can be awarded
        is_evasive_or_nonresponsive = (
            evidence.score < 45.0
            or evidence.evidence_confidence == "NONE"
            or any(
                "non-responsive" in w.lower()
                or "monosyllabic" in w.lower()
                or "evasive" in w.lower()
                or "refusal" in w.lower()
                for w in evidence.weaknesses
            )
        )
        if is_evasive_or_nonresponsive:
            return []

        strengths: List[StrengthItem] = []
        for indicator in evidence.positive_indicators:
            lower_ind = indicator.lower()

            if "accountability" in lower_ind or "ownership" in lower_ind:
                strengths.append(
                    StrengthItem(
                        area="Ownership / Accountability",
                        observation="You accepted personal responsibility directly without shifting blame or using evasive language.",
                        evidence_ids=evidence_ids[:1],
                        reinforcement=(
                            "Why this worked: Taking direct responsibility provides unequivocal evidence of integrity "
                            "and emotional maturity. In future answers, preserve this by clearly stating your decisions "
                            "before discussing team coordination."
                        ),
                    )
                )
            elif "concrete" in lower_ind or "personal experience" in lower_ind:
                strengths.append(
                    StrengthItem(
                        area="Specificity & Evidence",
                        observation="You anchored your statements in a concrete situation or tangible experience.",
                        evidence_ids=evidence_ids[:1],
                        reinforcement=(
                            "Why this worked: Concrete examples demonstrate authentic readiness rather than memorized theory. "
                            "Continue using the Situation → Action → Result framework to keep answers grounded."
                        ),
                    )
                )
            elif "structured" in lower_ind or "causal" in lower_ind or "logical" in lower_ind:
                strengths.append(
                    StrengthItem(
                        area="Reasoning Ability",
                        observation="You structured your reasoning logically with causal justification ('because', 'therefore').",
                        evidence_ids=evidence_ids[:1],
                        reinforcement=(
                            "Why this worked: Clear cause-and-effect thinking demonstrates intellectual faculty and analytical rigor. "
                            "Maintain this logical chain when addressing complex dilemmas."
                        ),
                    )
                )
            elif "collaborative" in lower_ind or "team orientation" in lower_ind:
                strengths.append(
                    StrengthItem(
                        area="Social Adaptability & Teamwork",
                        observation="You emphasized cooperative spirit, shared goals, and mutual support.",
                        evidence_ids=evidence_ids[:1],
                        reinforcement=(
                            "Why this worked: The board values candidates who foster group cohesion. "
                            "Pair team accomplishments with your distinct individual initiative."
                        ),
                    )
                )
            elif "factual alignment" in lower_ind or "strategic data" in lower_ind:
                strengths.append(
                    StrengthItem(
                        area="General Awareness",
                        observation="You accurately integrated strategic, defense, or economic context.",
                        evidence_ids=evidence_ids[:1],
                        reinforcement=(
                            "Why this worked: Accurate factual grasp demonstrates intellectual curiosity and professional preparation. "
                            "Continue reading reputable defense and current affairs journals."
                        ),
                    )
                )
            elif "engaged directly" in lower_ind or "respectful engagement" in lower_ind:
                if not strengths and evidence.score >= 55.0 and len(combined_text.split()) >= 8:
                    strengths.append(
                        StrengthItem(
                            area="Prompt Engagement",
                            observation="You addressed the interviewer's prompt directly without evading the question.",
                            evidence_ids=evidence_ids[:1],
                            reinforcement="Why this worked: Prompt responsiveness shows basic composure and attentiveness.",
                        )
                    )

        return strengths

    def _diagnose_improvement_areas(
        self,
        qa_pair: Dict[str, Any],
        evidence: PerAnswerEvidence,
        combined_text: str,
        evidence_ids: List[str],
        learning_profile: Optional[CandidateLearningProfile],
    ) -> List[ImprovementArea]:
        """Diagnoses actionable improvement recommendations directly linked to evaluation weaknesses."""
        items: List[ImprovementArea] = []
        words = combined_text.split()
        word_count = len(words)

        # Check for insufficient evidence neutral handling
        is_insufficient_evidence = (
            evidence.evidence_confidence in ("NONE", "LOW")
            and word_count < 15
            and not any("severely" in w.lower() or "off-topic" in w.lower() for w in evidence.weaknesses)
        )

        # 1. Monosyllabic / Extreme Evasiveness / Refusal
        is_refusal_or_evasive = any(
            "monosyllabic" in w.lower()
            or "non-responsive" in w.lower()
            or "evasive" in w.lower()
            or "refusal" in w.lower()
            for w in evidence.weaknesses
        )
        if is_refusal_or_evasive:
            priority = "HIGH"
            problem = "The response consisted of an evasive reply, refusal to respond ('i dont want to'), or monosyllabic single words ('nothing' / 'no'), failing to engage constructively with the prompt."
            why_it_matters = "ISSB selectors evaluate emotional composure, maturity, and reasoning ability. Refusing to answer or giving dismissive replies provides zero evidence for assessment and reflects emotional withdrawal."
            how_to_improve = "Formulate a constructive, complete response stating your perspective or decision, followed by 2 distinct supporting reasons and a brief real-life example."
            technique = "Use the Direct Assertion + Dual Support technique: 'Regarding [Topic], I believe [Stance] because of two key reasons: First, [Reason 1]. Second, [Reason 2]. For example, [Brief concrete instance].'"
            practice_task = "Answer the question again constructively using at least 3 full sentences articulating your personal reasoning."
            example_structure = (
                "Stance: [State your direct stance or decision]\n"
                "Reasoning: [Explain WHY you take this stance using 1-2 points]\n"
                "Evidence: [Briefly mention an experience or observation supporting it]"
            )
            items.append(
                ImprovementArea(
                    area="Power of Expression",
                    priority=priority,
                    problem=problem,
                    evidence_ids=evidence_ids[:1],
                    why_it_matters=why_it_matters,
                    how_to_improve=how_to_improve,
                    technique=technique,
                    practice_task=practice_task,
                    example_structure=example_structure,
                )
            )
            return items

        # 2. Off-Topic / Relevance Drift
        if any("off-topic" in w.lower() or "irrelevant" in w.lower() for w in evidence.weaknesses):
            priority = "HIGH"
            problem = "The response diverged from the specific topic and core intent of the interviewer's question."
            why_it_matters = "A military officer must demonstrate active listening and address operational issues directly without digression."
            how_to_improve = "Listen carefully for the question keyword (e.g. 'decision', 'causes', 'priority') and state your position directly in the very first sentence."
            technique = "Echo and Answer: Incorporate the core question term into your opening sentence before elaborating."
            practice_task = "Answer the question again focusing strictly and directly on the subject requested."
            example_structure = (
                "Direct Answer: [Directly address the primary question topic]\n"
                "Supporting Points: [Provide 1-2 points directly relevant to that topic]"
            )
            items.append(
                ImprovementArea(
                    area="Relevance & Active Listening",
                    priority=priority,
                    problem=problem,
                    evidence_ids=evidence_ids[:1],
                    why_it_matters=why_it_matters,
                    how_to_improve=how_to_improve,
                    technique=technique,
                    practice_task=practice_task,
                    example_structure=example_structure,
                )
            )

        # 3. Ownership / Accountability
        # Triggered if candidate described team or external factors without personal ownership
        has_ownership_marker = any(k in combined_text for k in [
            "responsibility", "fault", "admit", "apologiz", "took charge",
            "learned from", "own up", "mistake", "regret"
        ])
        has_first_person_action = any(k in combined_text for k in [
            "i decided", "i handled", "i stepped in", "i initiated", "i organized", "i took", "my role"
        ])
        has_collective_pronouns = any(k in combined_text for k in ["we ", "our team", "they ", "the group"])

        if (has_collective_pronouns and not has_first_person_action and not has_ownership_marker) or any(
            "external attribution" in w.lower() or "blam" in w.lower() for w in evidence.weaknesses
        ):
            area_name = "Ownership / Accountability"
            # Calculate priority (escalate if recurring)
            recurrence_count = self._get_recurrence_count(area_name, learning_profile)
            priority = "HIGH" if (recurrence_count >= 1 or evidence.evidence_confidence == "HIGH") else "MEDIUM"

            if any("external attribution" in w.lower() for w in evidence.weaknesses):
                problem = "The response exhibited defensive posturing or external attribution under challenge."
                why_it_matters = "Officers must demonstrate emotional composure and mature accountability rather than blaming peers or circumstances."
                how_to_improve = "Acknowledge the setback or challenge directly, focus on your sphere of control, and explain what you learned."
                technique = "Internal Locus of Control: Replace 'they didn't cooperate' with 'I recognized the gap and adjusted my communication to resolve it.'"
                practice_task = "Reframe the scenario by focusing strictly on what was within your control and how you addressed it."
                example_structure = (
                    "Acknowledgment: [Accept the challenge or mistake directly]\n"
                    "Personal Action: [What YOU chose to do to resolve it]\n"
                    "Constructive Lesson: [What you learned for future situations]"
                )
            else:
                problem = "The candidate described what the team or group did, but did not clearly identify their personal contribution or decisions."
                why_it_matters = "The board conference assesses YOUR officer potential, not your team's. The response provides insufficient evidence of individual responsibility."
                how_to_improve = "Use first-person ownership. Clearly state what you personally decided, executed, or took responsibility for."
                technique = "Use first-person ownership phrasing: 'I decided...', 'I handled...', 'I took responsibility...', 'My role was...'"
                practice_task = "Answer the same question again while explicitly describing your personal contribution."
                example_structure = (
                    "Context: [Briefly set the team or organizational objective]\n"
                    "Personal Action: [State what YOU personally initiated, decided, or resolved]\n"
                    "Outcome & Accountability: [Explain the outcome and how you took responsibility]"
                )

            items.append(
                ImprovementArea(
                    area=area_name,
                    priority=priority,
                    problem=problem,
                    evidence_ids=evidence_ids[:1],
                    why_it_matters=why_it_matters,
                    how_to_improve=how_to_improve,
                    technique=technique,
                    practice_task=practice_task,
                    example_structure=example_structure,
                )
            )

        # 4. Specificity & Evidence (Abstract assertions without concrete examples)
        if any("abstract assertions" in w.lower() or "concrete" in w.lower() for w in evidence.weaknesses):
            area_name = "Specificity"
            recurrence_count = self._get_recurrence_count(area_name, learning_profile)
            priority = "HIGH" if recurrence_count >= 1 else "MEDIUM"
            if evidence.evidence_confidence in ("LOW", "NONE"):
                priority = "LOW"

            items.append(
                ImprovementArea(
                    area=area_name,
                    priority=priority,
                    problem="The candidate gave general or abstract claims without providing a concrete real-life example.",
                    evidence_ids=evidence_ids[:1],
                    why_it_matters="Abstract statements can sound memorized. Concrete examples prove authentic behavioral habits under observation.",
                    how_to_improve="Support your claim with a specific real-life example using Situation → Action → Result.",
                    technique="STAR Technique (Situation, Task, Action, Result): Describe the exact context, what you did, and what happened.",
                    practice_task="Answer the question again with a specific example from your college, sports, or personal life.",
                    example_structure=(
                        "Situation: [Briefly describe the actual situation or challenge]\n"
                        "Action: [Explain what YOU personally did]\n"
                        "Result: [Explain the actual outcome]"
                    ),
                )
            )

        # 5. Completeness / Brief Answers (Neutral Handling on Insufficient Evidence)
        if any("very brief" in w.lower() or "lacked detailed" in w.lower() for w in evidence.weaknesses):
            area_name = "Completeness"
            recurrence_count = self._get_recurrence_count(area_name, learning_profile)
            # When evidence is low/none, rule 12 & 13 dictate priority cannot be HIGH
            priority = "HIGH" if (recurrence_count >= 2 and evidence.evidence_confidence != "LOW") else "MEDIUM"
            if evidence.evidence_confidence in ("LOW", "NONE"):
                priority = "LOW"

            problem = "The answer was concise and lacked sufficient supporting context or depth."
            why_it_matters = "Insufficient evidence was available to evaluate this area from this answer. Providing adequate context allows the board to assess your reasoning."
            how_to_improve = "Elaborate with why and how: define your core conclusion, explain the rationale behind it, and illustrate with one practical scenario."
            technique = "Rule of Three: State your stance, provide two supporting reasons, and mention one practical application."
            practice_task="Expand your response to provide more detailed reasoning and context."
            example_structure=(
                "Stance: [State your direct answer]\n"
                "Rationale: [Explain the core reason behind this choice]\n"
                "Application: [Describe how this approach works in practice]"
            )
            items.append(
                ImprovementArea(
                    area=area_name,
                    priority=priority,
                    problem=problem,
                    evidence_ids=evidence_ids[:1],
                    why_it_matters=why_it_matters,
                    how_to_improve=how_to_improve,
                    technique=technique,
                    practice_task=practice_task,
                    example_structure=example_structure,
                )
            )

        # 6. Fallback if no specific weakness was matched but score is moderate/low
        if not items and evidence.score < 75.0:
            area_name = "Clarity & Structure"
            items.append(
                ImprovementArea(
                    area=area_name,
                    priority="LOW",
                    problem="The response communicated the main idea, but structure and elaboration can be refined for greater punch.",
                    evidence_ids=evidence_ids[:1],
                    why_it_matters="Crisp, structured delivery reflects confidence and organized thinking.",
                    how_to_improve="Organize your answer into three clear steps: Situation, Action, and Result.",
                    technique="Deliver your conclusion in the first sentence before supporting it.",
                    practice_task="Re-articulate your answer following a clear 3-point structure.",
                    example_structure=(
                        "1. Situation: [Briefly describe the context]\n"
                        "2. Personal Action: [What you personally did]\n"
                        "3. Key Takeaway: [What the outcome was]"
                    ),
                )
            )

        # Check for recurrence across learning profile to mark recurring areas
        for item in items:
            rec_count = self._get_recurrence_count(item.area, learning_profile)
            if rec_count >= 1:
                item.problem = f"[Recurring Focus]: {item.problem}"
                # Recurrence escalates priority unless evidence is LOW/NONE
                if evidence.evidence_confidence not in ("LOW", "NONE"):
                    item.priority = "HIGH"

        return items

    def _get_recurrence_count(
        self, area_name: str, profile: Optional[CandidateLearningProfile]
    ) -> int:
        if not profile:
            return 0
        return profile.weakness_counts.get(area_name, 0)

    def _build_learning_summary(
        self, strengths: List[StrengthItem], improvement_areas: List[ImprovementArea]
    ) -> LearningSummary:
        top_pri = "Maintain positive response engagement."
        sec_pri = "Continue practicing clear and grounded articulation."
        str_maint = "Active engagement with question prompts."

        if improvement_areas:
            # Sort by HIGH > MEDIUM > LOW
            pri_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            sorted_areas = sorted(
                improvement_areas, key=lambda x: pri_order.get(x.priority, 3)
            )
            top_pri = f"{sorted_areas[0].area} ({sorted_areas[0].priority}): {sorted_areas[0].how_to_improve}"
            if len(sorted_areas) > 1:
                sec_pri = f"{sorted_areas[1].area} ({sorted_areas[1].priority}): {sorted_areas[1].how_to_improve}"
            else:
                sec_pri = "Support conclusions with concrete details."

        if strengths:
            str_maint = f"{strengths[0].area}: {strengths[0].observation}"

        return LearningSummary(
            top_priority=top_pri,
            secondary_priority=sec_pri,
            strength_to_maintain=str_maint,
        )

    def _build_retry_prompt(
        self, improvement_areas: List[ImprovementArea], question_text: str
    ) -> RetryPrompt:
        if not improvement_areas:
            return RetryPrompt(
                enabled=True,
                instruction="Try answering again to polish your delivery and reinforce your strong indicators.",
                target_area="Delivery & Polish",
            )

        # Target the highest priority area
        pri_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        target = min(improvement_areas, key=lambda x: pri_order.get(x.priority, 3))

        return RetryPrompt(
            enabled=True,
            instruction=target.practice_task,
            target_area=target.area,
        )

    def _build_overall_assessment(
        self,
        evidence: PerAnswerEvidence,
        strengths: List[StrengthItem],
        improvement_areas: List[ImprovementArea],
        candidate_answer: str = "",
        question_text: str = "",
    ) -> str:
        is_evasive_or_nonresponsive = (
            evidence.score < 35.0
            or evidence.evidence_confidence == "NONE"
            or any(
                "non-responsive" in w.lower()
                or "monosyllabic" in w.lower()
                or "evasive" in w.lower()
                or "refusal" in w.lower()
                for w in evidence.weaknesses
            )
        )
        if is_evasive_or_nonresponsive:
            return (
                "Insufficient evidence was available to evaluate your response in depth. "
                "In an ISSB interview, refusing to answer, evading, or giving dismissive single-word replies prevents the board from assessing your "
                "maturity, emotional composure, and reasoning ability. Practice addressing questions candidly and constructively with complete reasoning."
            )

        # If a live LLM is configured and answer has substance, request a tailored coaching comment
        if self.llm and getattr(self.llm, "is_configured", lambda: False)() and candidate_answer and len(candidate_answer.split()) >= 8:
            try:
                sys_prompt = (
                    "You are an expert ISSB candidate mentor. "
                    "Provide a 2-sentence encouraging, constructive coaching summary directly addressing the candidate. "
                    "Acknowledge what they stated, point out what to deepen, and advise on officer qualities. "
                    "Never predict pass/fail and do not diagnose psychological traits."
                )
                usr_prompt = (
                    f"Question: {question_text}\n"
                    f"Candidate Answer: {candidate_answer}\n"
                    f"Identified Strengths: {', '.join([s.area for s in strengths]) if strengths else 'Direct engagement'}\n"
                    f"Focus Areas: {', '.join([ia.area for ia in improvement_areas]) if improvement_areas else 'Refining depth'}\n"
                    "Provide concise coaching advice in 2 sentences."
                )
                res = self.llm.generate_response(sys_prompt, usr_prompt, temperature=0.3)
                clean_res = res.strip()
                if clean_res and len(clean_res) > 20 and not clean_res.lower().startswith("understood"):
                    return clean_res
            except Exception:
                pass

        parts: List[str] = []
        if strengths:
            parts.append(
                f"You demonstrated good {strengths[0].area.lower()} in your initial answer."
            )
        elif is_evasive_or_nonresponsive:
            parts.append("Your response offered zero demonstrable evidence due to evasiveness or extreme brevity.")
        else:
            parts.append("You addressed the prompt.")

        if improvement_areas:
            pri_areas = [f"{ia.area.lower()}" for ia in improvement_areas[:2]]
            parts.append(
                f"Your primary developmental focus is to enhance {' and '.join(pri_areas)}."
            )
            parts.append(improvement_areas[0].how_to_improve)
        else:
            parts.append(
                "Your response is well-grounded. Keep refining your clarity and confidence."
            )

        return " ".join(parts)
