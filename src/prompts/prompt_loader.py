"""
Prompt Template Loader for MY_ISSB_Evaluator.
Loads markdown-based prompt templates with variable interpolation and fallback protection.
"""

from pathlib import Path
from typing import Any, Dict, Optional


class PromptLoader:
    def __init__(self, prompts_dir: Optional[Path] = None):
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).resolve().parent.parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def get_template(self, template_name: str) -> str:
        """Retrieves raw template string by name (e.g. 'interviewer', 'follow_up', 'evaluator')."""
        if template_name in self._cache:
            return self._cache[template_name]

        file_name = template_name if template_name.endswith(".md") else f"{template_name}.md"
        file_path = self.prompts_dir / file_name

        if file_path.exists():
            template_text = file_path.read_text(encoding="utf-8")
            self._cache[template_name] = template_text
            return template_text

        # Built-in fallbacks if template file is absent
        return self._get_fallback_template(template_name)

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Loads and formats a prompt template with provided keyword arguments."""
        template = self.get_template(template_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Missing placeholder key: replace missing keys safely
            return template

    def _get_fallback_template(self, template_name: str) -> str:
        if "interviewer" in template_name:
            return (
                "You are an ISSB {persona_title}. Conduct the interview firmly and politely.\n"
                "Candidate Name: {candidate_name}\nCategory: {category}\n"
                "Question: {question}\nIntent: {intent}\nAsk this question directly."
            )
        elif "follow_up" in template_name:
            return (
                "You are an ISSB {persona_title}. Generate a sharp follow-up probe.\n"
                "Initial Question: {initial_question}\nCandidate Answer: {candidate_answer}\n"
                "Options:\n{follow_up_pool}\nFormulate a direct follow-up:"
            )
        elif "evaluator" in template_name:
            return (
                "Evaluate '{dimension}' using benchmarks:\n{benchmarks}\n\n"
                "Transcript:\n{transcript}\n\n"
                "Output JSON with dimension_score, positive_indicators_observed, weaknesses_observed, detailed_feedback."
            )
        return "{prompt}"
