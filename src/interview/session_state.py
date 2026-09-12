"""
Interview Session State Tracker for MY_ISSB_Evaluator.
Maintains structured multi-turn conversation state, session ID, question history,
per-answer evidence records, and category coverage tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import uuid

from src.question_bank.loader import QuestionItem


@dataclass
class QAPair:
    question_id: str
    category: str
    question: str
    intent: str
    difficulty: int
    evaluation_dimension: str
    answer: str = ""
    follow_up: Optional[str] = None
    follow_up_answer: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "category": self.category,
            "question": self.question,
            "intent": self.intent,
            "difficulty": self.difficulty,
            "evaluation_dimension": self.evaluation_dimension,
            "answer": self.answer,
            "follow_up": self.follow_up,
            "follow_up_answer": self.follow_up_answer,
            "timestamp": self.timestamp,
        }


@dataclass
class InterviewSession:
    candidate_name: str
    persona: str  # 'deputy_president' or 'psychologist'
    questions: List[QuestionItem]
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_index: int = 0
    awaiting_follow_up: bool = False
    qa_history: List[QAPair] = field(default_factory=list)
    per_answer_evaluations: List[Dict[str, Any]] = field(default_factory=list)
    completed: bool = False
    session_start: str = field(default_factory=lambda: datetime.now().isoformat())
    learning_profile: Optional[Dict[str, Any]] = None
    learning_results: List[Dict[str, Any]] = field(default_factory=list)
    retry_history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def current_question(self) -> Optional[QuestionItem]:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def progress_percentage(self) -> float:
        if not self.questions:
            return 100.0
        return (self.current_index / len(self.questions)) * 100.0

    @property
    def questions_asked_ids(self) -> List[str]:
        """Returns list of question IDs that have been asked so far."""
        return [qa.question_id for qa in self.qa_history]

    @property
    def categories_covered(self) -> List[str]:
        """Returns list of unique categories covered so far in the session."""
        seen = []
        for qa in self.qa_history:
            if qa.category not in seen:
                seen.append(qa.category)
        return seen

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "candidate_name": self.candidate_name,
            "persona": self.persona,
            "current_index": self.current_index,
            "total_questions": self.total_questions,
            "completed": self.completed,
            "session_start": self.session_start,
            "categories_covered": self.categories_covered,
            "questions_asked_ids": self.questions_asked_ids,
            "qa_history": [qa.to_dict() for qa in self.qa_history],
            "per_answer_evaluations": self.per_answer_evaluations,
            "learning_profile": self.learning_profile,
            "learning_results": self.learning_results,
            "retry_history": self.retry_history,
        }
