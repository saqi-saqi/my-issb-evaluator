"""
Consolidated Question Bank Loader & Calibrated Sequence Builder.
Loads from question_bank/questions.json and provides calibrated progression sequences.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Calibrated category sequence mirroring real ISSB board progression
CALIBRATED_PROGRESSION = [
    "personal",
    "education",
    "motivation",
    "leadership",
    "teamwork",
    "stress",
    "situational",
    "decision_making",
    "general_knowledge",
    "confidence",
    "responsibility",
    "communication",
    "family",
]


@dataclass
class Question:
    id: str
    category: str
    question: str
    difficulty: int = 1
    persona: str = "both"
    intent: str = ""
    evaluation_dimension: str = "general"
    follow_up_pool: List[str] = field(default_factory=list)

    @property
    def category_label(self) -> str:
        return self.category.replace("_", " ").title()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "category_label": self.category_label,
            "question": self.question,
            "difficulty": self.difficulty,
            "persona": self.persona,
            "intent": self.intent,
            "evaluation_dimension": self.evaluation_dimension,
            "follow_up_pool": self.follow_up_pool,
        }


class QuestionBank:
    """Loads and queries the consolidated 47-question ISSB question bank."""

    def __init__(self, json_path: Optional[Path] = None):
        if json_path is None:
            # Default to project root question_bank/questions.json
            self.json_path = Path(__file__).resolve().parent.parent / "question_bank" / "questions.json"
        else:
            self.json_path = Path(json_path)

        self.questions: List[Question] = []
        self._by_id: Dict[str, Question] = {}
        self.categories: Dict[str, List[Question]] = {}
        self.load()

    def load(self) -> None:
        if not self.json_path.exists():
            logger.error("Question bank file not found at %s", self.json_path)
            return

        with open(self.json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        self.questions = []
        self._by_id = {}
        self.categories = {}

        for item in raw_data:
            q = Question(
                id=item["id"],
                category=item.get("category", "general"),
                question=item.get("question", ""),
                difficulty=int(item.get("difficulty", 1)),
                persona=item.get("persona", "both"),
                intent=item.get("intent", ""),
                evaluation_dimension=item.get("evaluation_dimension", "general"),
                follow_up_pool=item.get("follow_up_pool", []),
            )
            self.questions.append(q)
            self._by_id[q.id] = q
            self.categories.setdefault(q.category, []).append(q)

        logger.info("Loaded %d questions across %d categories", len(self.questions), len(self.categories))

    def get_question(self, q_id: str) -> Optional[Question]:
        return self._by_id.get(q_id)

    def filter_questions(
        self,
        category: Optional[str] = None,
        persona: Optional[str] = None,
        max_difficulty: Optional[int] = None,
    ) -> List[Question]:
        results = self.questions
        if category:
            results = [q for q in results if q.category.lower() == category.lower()]
        if persona:
            norm_persona = "deputy_president" if "deputy" in persona.lower() else "psychologist"
            results = [
                q for q in results
                if q.persona in ("both", norm_persona) or (q.persona == "commander" and norm_persona == "deputy_president")
            ]
        if max_difficulty:
            results = [q for q in results if q.difficulty <= max_difficulty]
        return results

    def build_interview_sequence(
        self,
        persona: str = "deputy_president",
        num_questions: int = 5,
    ) -> List[Question]:
        """Builds a calibrated sequence following the 13-stage ISSB progression blueprint."""
        selected: List[Question] = []
        seen_ids = set()

        for cat in CALIBRATED_PROGRESSION:
            if len(selected) >= num_questions:
                break
            candidates = self.filter_questions(category=cat, persona=persona)
            for c in candidates:
                if c.id not in seen_ids:
                    selected.append(c)
                    seen_ids.add(c.id)
                    break

        # Fallback if still under requested question count
        if len(selected) < num_questions:
            remaining = self.filter_questions(persona=persona)
            for r in remaining:
                if r.id not in seen_ids:
                    selected.append(r)
                    seen_ids.add(r.id)
                    if len(selected) >= num_questions:
                        break

        return selected[:num_questions]
