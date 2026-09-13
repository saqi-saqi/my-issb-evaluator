"""
Streamlined Interview Service & State Machine for MY_ISSB_Evaluator.
Manages candidate sessions, calibrated question progression, deterministic answer-quality checks,
targeted follow-up probing, and final evaluation orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.ai import AIClient, ai_client
from core.evaluator import EvaluationReport, PerAnswerEvidence, RubricEvaluator
from core.learning import LearningService
from core.questions import Question, QuestionBank
from core.rag import KnowledgeRetriever
from core.storage import StorageManager

logger = logging.getLogger(__name__)


@dataclass
class InterviewSession:
    session_id: str
    candidate_name: str
    persona: str
    questions: List[Question]
    current_index: int = 0
    answers: Dict[str, str] = field(default_factory=dict)
    follow_up_answers: Dict[str, str] = field(default_factory=dict)
    evidence_records: List[PerAnswerEvidence] = field(default_factory=list)
    current_followup: Optional[str] = None
    completed: bool = False

    @property
    def current_question(self) -> Optional[Question]:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "candidate_name": self.candidate_name,
            "persona": self.persona,
            "current_index": self.current_index,
            "answers": self.answers,
            "follow_up_answers": self.follow_up_answers,
            "evidence_records": [e.to_dict() for e in self.evidence_records],
            "current_followup": self.current_followup,
            "completed": self.completed,
            "questions": [q.to_dict() for q in self.questions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InterviewSession:
        questions = [
            Question(
                id=q["id"],
                category=q.get("category", "general"),
                question=q.get("question", ""),
                difficulty=int(q.get("difficulty", 1)),
                persona=q.get("persona", "both"),
                intent=q.get("intent", ""),
                evaluation_dimension=q.get("evaluation_dimension", "general"),
                follow_up_pool=q.get("follow_up_pool", []),
            )
            for q in data.get("questions", [])
        ]
        evidence = [
            PerAnswerEvidence(
                question_id=e["question_id"],
                question_text=e["question_text"],
                category=e["category"],
                dimension=e["dimension"],
                score=float(e["score"]),
                confidence=float(e.get("confidence", 0.8)),
                evidence_confidence=e.get("evidence_confidence", "MEDIUM"),
                positive_indicators=e.get("positive_indicators", []),
                weaknesses=e.get("weaknesses", []),
                evidence_text=e.get("evidence_text", ""),
                citations=e.get("citations", []),
            )
            for e in data.get("evidence_records", [])
        ]
        return cls(
            session_id=data["session_id"],
            candidate_name=data.get("candidate_name", "Candidate"),
            persona=data.get("persona", "deputy_president"),
            questions=questions,
            current_index=data.get("current_index", 0),
            answers=data.get("answers", {}),
            follow_up_answers=data.get("follow_up_answers", {}),
            evidence_records=evidence,
            current_followup=data.get("current_followup"),
            completed=bool(data.get("completed", False)),
        )


class InterviewService:
    """Consolidated orchestrator managing the full interview lifecycle with SQLite persistence."""

    def __init__(
        self,
        question_bank: Optional[QuestionBank] = None,
        retriever: Optional[KnowledgeRetriever] = None,
        evaluator: Optional[RubricEvaluator] = None,
        learning: Optional[LearningService] = None,
        ai: Optional[AIClient] = None,
        storage: Optional[StorageManager] = None,
    ):
        self.qb = question_bank or QuestionBank()
        self.retriever = retriever or KnowledgeRetriever()
        self.ai = ai or ai_client
        self.storage = storage or StorageManager()
        self.evaluator = evaluator or RubricEvaluator(retriever=self.retriever, ai=self.ai)
        self.learning = learning or LearningService(ai=self.ai, storage=self.storage)
        if hasattr(self.learning, "storage") and self.learning.storage is None:
            self.learning.storage = self.storage
        self.sessions: Dict[str, InterviewSession] = {}

    def start_session(
        self,
        candidate_name: str = "Candidate",
        persona: str = "deputy_president",
        num_questions: int = 5,
    ) -> InterviewSession:
        """Initializes a new session with calibrated progression sequence."""
        session_id = str(uuid.uuid4())
        questions = self.qb.build_interview_sequence(persona=persona, num_questions=num_questions)

        session = InterviewSession(
            session_id=session_id,
            candidate_name=candidate_name.strip() or "Candidate",
            persona=persona,
            questions=questions,
            evidence_records=[],
        )
        self.sessions[session_id] = session
        self.storage.save_session(session.to_dict())
        self.learning.initialize_profile(session_id, session.candidate_name)
        logger.info("Session %s started for %s with %d questions", session_id, candidate_name, len(questions))
        return session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        if session_id in self.sessions:
            return self.sessions[session_id]
        saved = self.storage.get_session(session_id)
        if saved:
            sess = InterviewSession.from_dict(saved)
            self.sessions[session_id] = sess
            return sess
        return None

    def submit_primary_answer(self, session: InterviewSession, answer: str) -> Tuple[bool, Optional[str]]:
        """
        Evaluates candidate response.
        If answer is excessively brief or vague, generates a targeted probing follow-up.
        Otherwise records evidence and advances to the next question.
        """
        q = session.current_question
        if not q or session.completed:
            return False, None

        ans_clean = (answer or "").strip()
        session.answers[q.id] = ans_clean
        word_count = len(ans_clean.split())

        # Deterministic check for follow-up probe need
        needs_probe = (
            word_count < 6
            or ans_clean.lower() in {"yes", "no", "idk", "i don't know", "maybe", "skip", "pass", "ok"}
            or (word_count < 14 and not any(k in ans_clean.lower() for k in ["i", "my", "because", "when"]))
        )

        if needs_probe:
            follow_up = self._get_follow_up_probe(q, ans_clean, session.persona)
            session.current_followup = follow_up
            return True, follow_up

        # Answer is adequate; evaluate directly and advance
        self._record_evidence_and_advance(session, q, ans_clean, follow_up_answer=None)
        return False, None

    def submit_follow_up_answer(self, session: InterviewSession, follow_up_answer: str) -> None:
        """Records follow-up answer, completes evaluation for current question, and advances."""
        q = session.current_question
        if not q or session.completed:
            return

        fu_clean = (follow_up_answer or "").strip()
        session.follow_up_answers[q.id] = fu_clean
        primary_ans = session.answers.get(q.id, "")

        self._record_evidence_and_advance(session, q, primary_ans, follow_up_answer=fu_clean)
        session.current_followup = None

    def _record_evidence_and_advance(
        self,
        session: InterviewSession,
        question: Question,
        primary_answer: str,
        follow_up_answer: Optional[str] = None,
    ) -> None:
        """Runs Pass 1 evidence evaluation and advances pointer."""
        evidence = self.evaluator.evaluate_answer_evidence(
            question_id=question.id,
            question_text=question.question,
            category=question.category,
            dimension=question.evaluation_dimension,
            intent=question.intent,
            primary_answer=primary_answer,
            follow_up_answer=follow_up_answer,
        )
        session.evidence_records.append(evidence)
        session.current_index += 1

        if session.current_index >= session.total_questions:
            session.completed = True
            logger.info("Session %s marked completed", session.session_id)

        self.storage.save_session(session.to_dict())

    def _get_follow_up_probe(self, question: Question, answer: str, persona: str) -> str:
        """Selects from pre-curated pool or dynamically generates probe via Groq."""
        if question.follow_up_pool:
            return question.follow_up_pool[0]

        prompt = f"""
The candidate answered: "{answer}" to this ISSB question: "{question.question}".
As an ISSB {persona}, ask ONE natural, polite, but firm follow-up question to probe for a specific example or deeper reasoning.
Do not reveal scoring criteria. Max 25 words.
"""
        generated = self.ai.generate_text(prompt, system=f"You are an ISSB {persona}.")
        return generated.strip(' "') if generated else "Could you explain that in more detail with a specific example?"

    def generate_final_report(self, session: InterviewSession) -> EvaluationReport:
        """Runs Pass 2 evaluation, synthesizes final report, and records learning profile."""
        report = self.evaluator.evaluate_session(
            candidate_name=session.candidate_name,
            persona=session.persona,
            evidence_list=session.evidence_records,
        )
        report_dict = report.to_dict()
        self.learning.record_session(session.session_id, session.candidate_name, report_dict)
        self.storage.save_report(session.session_id, session.candidate_name, report_dict)
        return report
