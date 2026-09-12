"""
Question Bank Loader and Manager for MY_ISSB_Evaluator.
Decouples interview questioning logic from RAG knowledge base.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Optional


@dataclass
class QuestionItem:
    id: str
    category: str
    question: str
    difficulty: int
    persona: str
    intent: str
    evaluation_dimension: str
    follow_up_pool: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "question": self.question,
            "difficulty": self.difficulty,
            "persona": self.persona,
            "intent": self.intent,
            "evaluation_dimension": self.evaluation_dimension,
            "follow_up_pool": self.follow_up_pool,
        }


class QuestionBank:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent / "question_bank"
        else:
            self.base_dir = Path(base_dir)
        self.questions: Dict[str, QuestionItem] = {}
        self.categories: Dict[str, List[QuestionItem]] = {}
        self.load_all()

    def load_all(self) -> None:
        self.questions.clear()
        self.categories.clear()

        if not self.base_dir.exists():
            return

        for file_path in self.base_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            q = QuestionItem(
                                id=item.get("id", ""),
                                category=item.get("category", file_path.stem),
                                question=item.get("question", ""),
                                difficulty=int(item.get("difficulty", 1)),
                                persona=item.get("persona", "both"),
                                intent=item.get("intent", ""),
                                evaluation_dimension=item.get("evaluation_dimension", "general"),
                                follow_up_pool=item.get("follow_up_pool", []),
                            )
                            self.questions[q.id] = q
                            self.categories.setdefault(q.category, []).append(q)
            except Exception as e:
                print(f"Error loading question file {file_path}: {e}")

    def get_by_id(self, question_id: str) -> Optional[QuestionItem]:
        return self.questions.get(question_id)

    def filter_questions(
        self,
        persona: Optional[str] = None,
        category: Optional[str] = None,
        max_difficulty: Optional[int] = None,
    ) -> List[QuestionItem]:
        results = list(self.questions.values())

        if persona:
            target = persona.lower()
            results = [
                q for q in results
                if q.persona.lower() == "both" or q.persona.lower() == target
            ]

        if category:
            results = [q for q in results if q.category.lower() == category.lower()]

        if max_difficulty:
            results = [q for q in results if q.difficulty <= max_difficulty]

        return results

    def build_interview_flow(
        self,
        persona: str = "deputy_president",
        num_questions: int = 5,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[QuestionItem]:
        """
        Builds a structured ISSB interview progression sequence.
        Deputy President: Military motivation, strategic awareness, command leadership, situational crisis, decisiveness.
        Psychologist: Upbringing, emotional balance, stress coping, interpersonal dynamics, self-reflection.
        """
        exclude = set(exclude_ids or [])
        target_persona = (persona or "deputy_president").lower()

        if target_persona == "psychologist":
            progression_blueprint = [
                ("personal", 1),
                ("family", 1),
                ("education", 2),
                ("stress", 3),
                ("teamwork", 2),
                ("communication", 2),
                ("responsibility", 3),
                ("decision_making", 3),
                ("motivation", 2),
                ("confidence", 3),
                ("situational", 3),
                ("general_knowledge", 3),
            ]
        else:
            progression_blueprint = [
                ("motivation", 2),
                ("general_knowledge", 3),
                ("leadership", 3),
                ("situational", 3),
                ("decision_making", 4),
                ("responsibility", 3),
                ("confidence", 3),
                ("communication", 2),
                ("teamwork", 2),
                ("education", 2),
                ("personal", 1),
                ("stress", 3),
            ]

        selected: List[QuestionItem] = []

        for category, target_diff in progression_blueprint:
            if len(selected) >= num_questions:
                break

            candidates = [
                q for q in self.filter_questions(persona=target_persona, category=category)
                if q.id not in exclude and q.id not in {s.id for s in selected}
            ]

            if candidates:
                # Prioritize persona-exclusive questions first, then closeness to target difficulty
                candidates.sort(
                    key=lambda q: (
                        0 if q.persona.lower() == target_persona else 1,
                        abs(q.difficulty - target_diff),
                    )
                )
                best_persona_prio = 0 if candidates[0].persona.lower() == target_persona else 1
                min_diff = abs(candidates[0].difficulty - target_diff)
                top_tier = [
                    q for q in candidates
                    if (0 if q.persona.lower() == target_persona else 1) == best_persona_prio
                    and abs(q.difficulty - target_diff) <= min_diff + 1
                ]
                chosen = random.choice(top_tier)
                selected.append(chosen)

        # If we still need more questions to reach target count:
        if len(selected) < num_questions:
            remaining = [
                q for q in self.filter_questions(persona=target_persona)
                if q.id not in exclude and q.id not in {s.id for s in selected}
            ]
            if not remaining and exclude:
                # Relax exclusion only if available pool is exhausted
                remaining = [
                    q for q in self.filter_questions(persona=target_persona)
                    if q.id not in {s.id for s in selected}
                ]
            random.shuffle(remaining)
            selected.extend(remaining[: num_questions - len(selected)])

        return selected[:num_questions]

    def validate_bank_integrity(self) -> Dict[str, Any]:
        """
        Validates the integrity of the question bank:
        checks for ID uniqueness, schema compliance, and category distribution.
        """
        issues = []
        categories_count: Dict[str, int] = {}
        for q_id, q in self.questions.items():
            if not q.id:
                issues.append("Question with empty ID found")
            if not q.question or len(q.question.strip()) < 5:
                issues.append(f"Question {q_id} has invalid question text")
            if q.difficulty not in (1, 2, 3, 4, 5):
                issues.append(f"Question {q_id} has out-of-range difficulty: {q.difficulty}")
            if not q.follow_up_pool or len(q.follow_up_pool) < 1:
                issues.append(f"Question {q_id} has empty follow_up_pool")
            categories_count[q.category] = categories_count.get(q.category, 0) + 1

        return {
            "total_questions": len(self.questions),
            "categories_count": categories_count,
            "is_valid": len(issues) == 0,
            "issues": issues,
        }

