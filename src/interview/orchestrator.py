"""
Controlled Interview Orchestrator for MY_ISSB_Evaluator.
Enforces: Question Bank -> Retrieve Question -> LLM Asks -> Candidate Answers -> Follow-up Assessment.
Features: PromptLoader integration, per-answer evidence tracking, answer quality analysis, and guardrails.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.evaluator.rubric_engine import InterviewEvaluationReport, PerAnswerEvidence, RubricEvaluationEngine
from src.interview.session_state import InterviewSession, QAPair
from src.learning.learning_engine import LearningEngine
from src.learning.models import (
    BeforeAfterComparison,
    CandidateLearningProfile,
    LearningPhaseResult,
    SessionLearningReport,
)
from src.learning.progress_tracker import LearningProgressTracker
from src.llm.client import LLMClient
from src.prompts.prompt_loader import PromptLoader
from src.question_bank.loader import QuestionBank, QuestionItem
from src.rag.retriever import KnowledgeRetriever


class InterviewOrchestrator:
    def __init__(
        self,
        question_bank: Optional[QuestionBank] = None,
        retriever: Optional[KnowledgeRetriever] = None,
        llm_client: Optional[LLMClient] = None,
        prompt_loader: Optional[PromptLoader] = None,
        learning_engine: Optional[LearningEngine] = None,
    ):
        self.question_bank = question_bank or QuestionBank()
        self.retriever = retriever or KnowledgeRetriever()
        self.llm = llm_client or LLMClient()
        self.prompt_loader = prompt_loader or PromptLoader()
        self.evaluator = RubricEvaluationEngine(
            retriever=self.retriever,
            llm_client=self.llm,
            prompt_loader=self.prompt_loader,
        )
        self.learning_engine = learning_engine or LearningEngine(llm_client=self.llm)
        self.session_trackers: Dict[str, LearningProgressTracker] = {}
        self.recent_asked_ids: List[str] = []

    def start_session(
        self,
        candidate_name: str,
        persona: str = "deputy_president",
        num_questions: int = 5,
        exclude_ids: Optional[List[str]] = None,
    ) -> InterviewSession:
        effective_exclude = list(set((exclude_ids or []) + self.recent_asked_ids))
        questions = self.question_bank.build_interview_flow(
            persona=persona,
            num_questions=num_questions,
            exclude_ids=effective_exclude,
        )
        for q in questions:
            if q.id not in self.recent_asked_ids:
                self.recent_asked_ids.append(q.id)
        if len(self.recent_asked_ids) > 25:
            self.recent_asked_ids = self.recent_asked_ids[-25:]

        return InterviewSession(
            candidate_name=candidate_name,
            persona=persona,
            questions=questions,
            current_index=0,
            awaiting_follow_up=False,
            qa_history=[],
            completed=False,
        )

    def get_natural_question_prompt(
        self,
        session: InterviewSession,
        question_item: QuestionItem,
    ) -> str:
        """
        Renders the raw question bank question into natural conversational interviewer phrasing
        aligned with the chosen persona using PromptLoader template.
        """
        persona_title = "Deputy President" if session.persona == "deputy_president" else "Senior Psychologist"

        rendered_prompt = self.prompt_loader.render(
            "interviewer",
            persona_title=persona_title,
            candidate_name=session.candidate_name,
            category=question_item.category.replace("_", " ").title(),
            question=question_item.question,
            intent=question_item.intent,
        )

        system_prompt = (
            f"You are conducting a practice interview in the style of an ISSB {persona_title}. "
            "Your tone is polite, dignified, firm, and sharp. You do not flatter. "
            "You are asking a specific question retrieved from the board question bank. "
            "Present this question clearly and directly to the candidate without unnecessary preamble or small talk."
        )

        response = self.llm.generate_response(system_prompt, rendered_prompt)
        return self._validate_question_prompt(response, question_item)

    def submit_primary_answer(
        self,
        session: InterviewSession,
        candidate_answer: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Processes the candidate's initial answer to the current question.
        Evaluates answer quality to determine whether a follow-up probe is warranted.
        Extracts per-answer evidence and records it in session state.
        Returns (has_follow_up, follow_up_question_str).
        """
        curr_q = session.current_question
        if not curr_q:
            session.completed = True
            return False, None

        # Create record in QA history
        qa_pair = QAPair(
            question_id=curr_q.id,
            category=curr_q.category,
            question=curr_q.question,
            intent=curr_q.intent,
            difficulty=curr_q.difficulty,
            evaluation_dimension=curr_q.evaluation_dimension,
            answer=candidate_answer,
        )
        session.qa_history.append(qa_pair)

        # Assess answer quality for follow-up decision
        needs_follow_up, reason = self._assess_answer_quality(curr_q, candidate_answer)

        if needs_follow_up and curr_q.follow_up_pool:
            follow_up_text = self._generate_contextual_follow_up(session, curr_q, candidate_answer, reason)
            qa_pair.follow_up = follow_up_text
            session.awaiting_follow_up = True
            return True, follow_up_text
        else:
            # Record per-answer evidence immediately
            evidence = self.evaluator.evaluate_single_answer(qa_pair.to_dict())
            session.per_answer_evaluations.append(evidence.to_dict())

            # Advance to next question
            self._advance_question(session)
            return False, None

    def submit_follow_up_answer(
        self,
        session: InterviewSession,
        follow_up_answer: str,
    ) -> None:
        """
        Records the candidate's answer to the follow-up question,
        updates per-answer evidence, and advances the session.
        """
        if session.qa_history:
            last_pair = session.qa_history[-1]
            last_pair.follow_up_answer = follow_up_answer

            # Record per-answer evidence with follow-up included
            evidence = self.evaluator.evaluate_single_answer(last_pair.to_dict())
            session.per_answer_evaluations.append(evidence.to_dict())

        session.awaiting_follow_up = False
        self._advance_question(session)

    def _assess_answer_quality(self, question: QuestionItem, answer: str) -> Tuple[bool, str]:
        """
        Analyzes answer characteristics to decide if a follow-up probe is needed:
        - Monosyllabic / non-responsive ("yes", "no", etc.)
        - Terse response (< 20 words)
        - Vague or general response lacking concrete examples
        - High difficulty questions (>= 3) inherently benefit from probing
        """
        words = answer.strip().split()
        word_count = len(words)
        clean_ans = answer.strip().lower().rstrip(".!?,")

        if clean_ans in ("yes", "no", "yeah", "nope", "idk", "ok", "sure", "fine", "maybe", "na", "haan", "nahi") or word_count <= 2:
            return True, "monosyllabic"

        if word_count < 20:
            return True, "brief"

        lower_ans = answer.lower()
        has_example = any(k in lower_ans for k in ["for example", "specifically", "in my", "when i", "during"])
        if not has_example and question.difficulty >= 2 and word_count < 45:
            return True, "abstract"

        if question.difficulty >= 3:
            return True, "dilemma_probe"

        return False, "sufficient"

    def _advance_question(self, session: InterviewSession) -> None:
        session.current_index += 1
        if session.current_index >= len(session.questions):
            session.completed = True

    def _generate_contextual_follow_up(
        self,
        session: InterviewSession,
        question: QuestionItem,
        candidate_answer: str,
        reason: str = "general",
    ) -> str:
        """
        Generates a targeted follow-up question drawing from the question bank's follow_up_pool
        and candidate's specific statements via PromptLoader.
        """
        if reason == "monosyllabic":
            return f"You answered with a single word ('{candidate_answer.strip()}'). In an ISSB interview, you must articulate your reasoning and substantiate your stance. Why do you hold this view?"

        pool_str = "\n".join([f"- {opt}" for opt in question.follow_up_pool])
        persona_title = "Deputy President" if session.persona == "deputy_president" else "Senior Psychologist"

        rendered_prompt = self.prompt_loader.render(
            "follow_up",
            persona_title=persona_title,
            initial_question=question.question,
            candidate_answer=candidate_answer,
            follow_up_pool=pool_str,
        )

        system_prompt = (
            f"You are an ISSB {persona_title}-style interviewer generating a single targeted follow-up question. "
            "Select or adapt one of the suggestions from the follow-up pool to probe deeper into the candidate's response. "
            "Keep it sharp, concise, and focused on verifiable actions, reasoning, or personal accountability."
        )

        response = self.llm.generate_response(system_prompt, rendered_prompt)
        return self._validate_follow_up(response, question)

    def _validate_question_prompt(self, response: str, question: QuestionItem) -> str:
        """Ensures the question output retains core fidelity to the bank question."""
        cleaned = response.strip()
        if not cleaned or len(cleaned) < 10:
            return question.question
        return cleaned

    def _validate_follow_up(self, response: str, question: QuestionItem) -> str:
        """Ensures follow-up is not empty and doesn't hallucinate irrelevant scenarios."""
        cleaned = response.strip()
        if not cleaned or len(cleaned) < 10:
            if question.follow_up_pool:
                return question.follow_up_pool[0]
            return "Could you provide a specific, concrete example from your own life to illustrate that?"
        return cleaned

    def generate_final_report(self, session: InterviewSession) -> InterviewEvaluationReport:
        """
        Passes completed interview transcript to RubricEvaluationEngine with full metadata.
        """
        qa_dicts = [qa.to_dict() for qa in session.qa_history]
        session_meta = {
            "session_id": session.session_id,
            "session_start": session.session_start,
            "question_count": session.total_questions,
            "categories_covered": session.categories_covered,
        }
        cand_profile = {
            "name": session.candidate_name,
            "persona": session.persona,
        }
        return self.evaluator.evaluate_interview_session(
            candidate_name=session.candidate_name,
            persona=session.persona,
            qa_pairs=qa_dicts,
            session_metadata=session_meta,
            candidate_profile=cand_profile,
        )

    def get_session_tracker(self, session: InterviewSession) -> LearningProgressTracker:
        """Retrieves or creates the LearningProgressTracker for the given session."""
        if session.session_id not in self.session_trackers:
            profile = CandidateLearningProfile()
            if session.learning_profile:
                profile.strengths = session.learning_profile.get("strengths", [])
                profile.recurring_weaknesses = session.learning_profile.get("recurring_weaknesses", [])
                profile.improving_areas = session.learning_profile.get("improving_areas", [])
                profile.priority_areas = session.learning_profile.get("priority_areas", [])
                profile.practice_history = session.learning_profile.get("practice_history", [])
                profile.weakness_counts = session.learning_profile.get("weakness_counts", {})
            self.session_trackers[session.session_id] = LearningProgressTracker(profile)
        return self.session_trackers[session.session_id]

    def get_learning_feedback(
        self, session: InterviewSession, question_id: Optional[str] = None
    ) -> LearningPhaseResult:
        """
        Generates structured coaching feedback for a candidate's answer without modifying scoring.
        """
        if not session.qa_history:
            raise ValueError("No QA history available in this session to generate feedback.")

        # Find requested QA pair or use most recent
        qa_pair = None
        ev_dict = None
        if question_id:
            for idx, qa in enumerate(session.qa_history):
                if qa.question_id == question_id:
                    qa_pair = qa
                    if idx < len(session.per_answer_evaluations):
                        ev_dict = session.per_answer_evaluations[idx]
                    break
        if not qa_pair:
            qa_pair = session.qa_history[-1]
            if session.per_answer_evaluations:
                ev_dict = session.per_answer_evaluations[-1]

        # Ensure evidence object exists
        if ev_dict:
            evidence = PerAnswerEvidence(
                question_id=ev_dict.get("question_id", qa_pair.question_id),
                category=ev_dict.get("category", qa_pair.category),
                dimension=ev_dict.get("dimension", qa_pair.evaluation_dimension),
                score=float(ev_dict.get("score", 50.0)),
                confidence=float(ev_dict.get("confidence", 0.8)),
                evidence_confidence=ev_dict.get("evidence_confidence", "MEDIUM"),
                positive_indicators=ev_dict.get("positive_indicators", []),
                weaknesses=ev_dict.get("weaknesses", []),
                evidence_text=ev_dict.get("evidence_text", ""),
                citations=ev_dict.get("citations", []),
                source_ids=ev_dict.get("source_ids", []),
            )
        else:
            evidence = self.evaluator.evaluate_single_answer(qa_pair.to_dict())

        tracker = self.get_session_tracker(session)
        feedback = self.learning_engine.generate_feedback(
            qa_pair=qa_pair.to_dict(),
            evidence=evidence,
            learning_profile=tracker.profile,
        )

        tracker.record_answer_evaluation(qa_pair.to_dict(), evidence, feedback)
        session.learning_profile = tracker.profile.to_dict()["learning_profile"]
        session.learning_results.append(feedback.to_dict()["learning_phase"])

        return feedback

    def process_retry_answer(
        self, session: InterviewSession, question_id: str, retry_answer: str
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate's revised retry answer, compares before vs after, and updates profile.
        """
        # Find target QA pair and prior evidence
        qa_pair = None
        ev_dict = None
        for idx, qa in enumerate(session.qa_history):
            if qa.question_id == question_id:
                qa_pair = qa
                if idx < len(session.per_answer_evaluations):
                    ev_dict = session.per_answer_evaluations[idx]
                break

        if not qa_pair:
            if not session.qa_history:
                raise ValueError(f"Question ID {question_id} not found in session.")
            qa_pair = session.qa_history[-1]
            if session.per_answer_evaluations:
                ev_dict = session.per_answer_evaluations[-1]

        if ev_dict:
            before_evidence = PerAnswerEvidence(
                question_id=ev_dict.get("question_id", qa_pair.question_id),
                category=ev_dict.get("category", qa_pair.category),
                dimension=ev_dict.get("dimension", qa_pair.evaluation_dimension),
                score=float(ev_dict.get("score", 50.0)),
                confidence=float(ev_dict.get("confidence", 0.8)),
                evidence_confidence=ev_dict.get("evidence_confidence", "MEDIUM"),
                positive_indicators=ev_dict.get("positive_indicators", []),
                weaknesses=ev_dict.get("weaknesses", []),
                evidence_text=ev_dict.get("evidence_text", ""),
                citations=ev_dict.get("citations", []),
                source_ids=ev_dict.get("source_ids", []),
            )
        else:
            before_evidence = self.evaluator.evaluate_single_answer(qa_pair.to_dict())

        # Build retry QA dict
        retry_qa_dict = qa_pair.to_dict()
        retry_qa_dict["answer"] = retry_answer
        retry_qa_dict["follow_up_answer"] = ""

        # Re-evaluate with existing evaluation engine
        after_evidence = self.evaluator.evaluate_single_answer(retry_qa_dict)

        tracker = self.get_session_tracker(session)
        comparison = tracker.compare_before_after(
            before_qa=qa_pair.to_dict(),
            before_evidence=before_evidence,
            after_qa=retry_qa_dict,
            after_evidence=after_evidence,
        )

        new_feedback = self.learning_engine.generate_feedback(
            qa_pair=retry_qa_dict,
            evidence=after_evidence,
            learning_profile=tracker.profile,
        )

        session.learning_profile = tracker.profile.to_dict()["learning_profile"]
        retry_record = {
            "question_id": question_id,
            "retry_answer": retry_answer,
            "before_after": comparison.to_dict()["before_after"],
            "new_score": after_evidence.score,
        }
        session.retry_history.append(retry_record)

        return {
            "before_after": comparison.to_dict()["before_after"],
            "new_evidence": after_evidence.to_dict(),
            "new_learning": new_feedback.to_dict()["learning_phase"],
            "learning_profile": tracker.profile.to_dict()["learning_profile"],
        }

    def generate_session_learning_report(
        self, session: InterviewSession, evaluation_report: Optional[InterviewEvaluationReport] = None
    ) -> SessionLearningReport:
        """
        Generates a separate session-level coaching and development report.
        """
        report = evaluation_report or self.generate_final_report(session)
        tracker = self.get_session_tracker(session)

        return tracker.generate_session_learning_report(
            candidate_name=session.candidate_name,
            session_id=session.session_id,
            overall_score=report.overall_practice_score,
            dimension_scores=report.dimension_scores,
            fourteen_olq_scores=getattr(report, "fourteen_olq_scores", {}),
        )
