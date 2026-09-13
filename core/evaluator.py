"""
Streamlined 2-Pass Rubric Evaluation Engine for MY_ISSB_Evaluator.
Pass 1: Deterministic Per-Answer Evidence & Observable Indicators with RAG provenance citations.
Pass 2: Deterministic 14-OLQ + 5-Dimension aggregation, concluded by a single LLM narrative synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional

from core.ai import AIClient, ai_client
from core.rag import KnowledgeRetriever
from core.scoring import (
    FOURTEEN_OLQS,
    calculate_14_olq_scores,
    calculate_dashboard_dimensions,
    calculate_overall_score,
    get_performance_band,
)

logger = logging.getLogger(__name__)


@dataclass
class PerAnswerEvidence:
    question_id: str
    question_text: str
    category: str
    dimension: str
    score: float
    confidence: float
    evidence_confidence: str  # 'HIGH', 'MEDIUM', 'LOW', 'NONE'
    positive_indicators: List[str]
    weaknesses: List[str]
    evidence_text: str
    citations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "category": self.category,
            "dimension": self.dimension,
            "score": self.score,
            "confidence": self.confidence,
            "evidence_confidence": self.evidence_confidence,
            "positive_indicators": self.positive_indicators,
            "weaknesses": self.weaknesses,
            "evidence_text": self.evidence_text,
            "citations": self.citations,
        }


@dataclass
class EvaluationReport:
    candidate_name: str
    persona: str
    overall_practice_score: float
    performance_band: Dict[str, str]
    dimension_scores: Dict[str, float]
    fourteen_olq_scores: Dict[str, float]
    per_question_evidence: List[PerAnswerEvidence]
    executive_summary: str
    key_strengths: List[str]
    primary_shortcomings: List[str]
    actionable_recommendations: List[str]
    radar_chart_data: List[Dict[str, Any]] = field(default_factory=list)
    fourteen_olq_radar_data: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "persona": self.persona,
            "overall_practice_score": self.overall_practice_score,
            "performance_band": self.performance_band,
            "dimension_scores": self.dimension_scores,
            "fourteen_olq_scores": self.fourteen_olq_scores,
            "per_question_evidence": [e.to_dict() for e in self.per_question_evidence],
            "formatted_evidence_table": [e.to_dict() for e in self.per_question_evidence],
            "executive_summary": self.executive_summary,
            "key_strengths": self.key_strengths,
            "primary_shortcomings": self.primary_shortcomings,
            "actionable_recommendations": self.actionable_recommendations,
            "radar_chart_data": self.radar_chart_data,
            "fourteen_olq_radar_data": self.fourteen_olq_radar_data,
        }


class RubricEvaluator:
    """Evaluates interview sessions using a defensible 2-Pass pipeline."""

    def __init__(self, retriever: Optional[KnowledgeRetriever] = None, ai: Optional[AIClient] = None):
        self.retriever = retriever or KnowledgeRetriever()
        self.ai = ai or ai_client

    def _extract_rubric_criteria(
        self, chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Parses observable positive indicators and potential weaknesses from retrieved rubric chunks."""
        positives: List[Dict[str, str]] = []
        weaknesses: List[Dict[str, str]] = []

        for chunk in chunks:
            text = chunk.get("text", "")
            current_section = None
            for line in text.splitlines():
                line_str = line.strip()
                if "Observable Positive Indicators" in line_str:
                    current_section = "positive"
                    continue
                elif "Observable Potential Weaknesses" in line_str:
                    current_section = "weakness"
                    continue
                elif line_str.startswith("## "):
                    current_section = None
                    continue

                if line_str.startswith("- ") and current_section:
                    item_text = line_str[2:].strip()
                    if ":" in item_text:
                        name, desc = item_text.split(":", 1)
                        entry = {"name": name.strip(), "description": desc.strip()}
                    else:
                        entry = {"name": item_text, "description": item_text}

                    if current_section == "positive":
                        positives.append(entry)
                    elif current_section == "weakness":
                        weaknesses.append(entry)

        return positives, weaknesses

    def _detect_indicators(
        self,
        combined_text: str,
        question_text: str,
        category: str,
        dimension: str,
        rubric_text: str,
    ) -> Dict[str, Any]:
        """
        Detects ownership, concrete examples, logical reasoning, and teamwork.
        Uses LLM rubric scoring pass when available; otherwise uses robust semantic pattern and concept matching.
        """
        # 1. Option A: Structured LLM scoring pass when Groq is available
        if self.ai.is_available():
            try:
                prompt = f"""
You are an expert military psychology assessor for ISSB.
Evaluate candidate response against the retrieved rubric criteria.
Question: "{question_text}"
Category: {category} | Target Dimension: {dimension}
Candidate Response: "{combined_text}"

Retrieved Rubric Criteria:
{rubric_text[:600] if rubric_text else "General ISSB Leadership & Personal Accountability standards."}

Evaluate if the candidate demonstrates:
1. ownership: Personal agency, accountability, or responsibility (even if paraphrased).
2. example: Grounding in concrete personal experiences or specific real-life situations.
3. reasoning: Structured causal thinking ('because', 'therefore', logical progression).
4. teamwork: Collaborative team orientation or peer alignment.

Return JSON:
{{
  "has_ownership": true,
  "has_example": true,
  "has_reasoning": true,
  "has_teamwork": true,
  "positive_indicators": ["1-2 concise observations grounded in rubric"],
  "weaknesses": ["1 concise constructive gap if applicable"]
}}
"""
                res = self.ai.generate_json(prompt, system="You are an expert military psychology assessor for ISSB.", temperature=0.1)
                if res and isinstance(res, dict) and "has_ownership" in res:
                    return {
                        "has_ownership": bool(res.get("has_ownership")),
                        "has_example": bool(res.get("has_example")),
                        "has_reasoning": bool(res.get("has_reasoning")),
                        "has_teamwork": bool(res.get("has_teamwork")),
                        "llm_positives": res.get("positive_indicators", []),
                        "llm_weaknesses": res.get("weaknesses", []),
                        "mode": "llm_grounded",
                    }
            except Exception as e:
                logger.warning("LLM indicator scoring fallback to semantic matcher: %s", e)

        # 2. Option B: Semantic Offline Pattern & Concept Matcher
        # Ownership: First-person agentic actions, accountability, responsibility
        ownership_patterns = [
            r"\b(i\s+took|i\s+decided|my\s+fault|my\s+mistake|i\s+led|i\s+organized|i\s+took\s+responsibility|i\s+resolved)\b",
            r"\b(i|my)\s+(stepped\s+in|assumed|accepted|initiated|managed|directed|spearheaded|oversaw|coordinated|handled|confronted|fixed|owned|chose|acted|arranged|volunteered|tackled)\b",
            r"\b(personally\s+(assumed|handled|stepped|led|took|managed|resolved))\b",
            r"\b(full\s+responsibility|take\s+responsibility|took\s+responsibility|admit\s+my|acknowledged\s+my)\b",
            r"\b(accountab(le|ility)|responsib(le|ility))\b",
            r"\bmy\s+(duty|role|task|obligation|lapse|charge|judgment)\b",
            r"\b(held\s+myself|stood\s+up|claimed\s+responsibility)\b",
        ]
        has_ownership = any(re.search(pat, combined_text) for pat in ownership_patterns)

        # Examples: Specific experiences, situational narrative anchors
        example_patterns = [
            r"\b(for\s+example|specifically|for\s+instance|in\s+particular|namely)\b",
            r"\b(in\s+my\s+college|during\s+my|when\s+i\s+was|in\s+our\s+team|at\s+my\s+university|in\s+my\s+school|in\s+my\s+workplace)\b",
            r"\b(on\s+one\s+occasion|back\s+in|while\s+serving|in\s+our\s+project|during\s+the\s+tournament|during\s+a\s+crisis)\b",
            r"\b(last\s+year|two\s+months\s+ago|at\s+that\s+time|in\s+that\s+situation)\b",
        ]
        has_example = any(re.search(pat, combined_text) for pat in example_patterns)

        # Reasoning: Causal logic and structural progression
        reasoning_patterns = [
            r"\b(because|therefore|as\s+a\s+result|consequently|firstly|secondly|furthermore)\b",
            r"\b(the\s+reason\s+was|which\s+led\s+to|in\s+order\s+to|due\s+to|hence|thus)\b",
        ]
        has_reasoning = any(re.search(pat, combined_text) for pat in reasoning_patterns)

        # Teamwork: Collaborative mission alignment and peer engagement
        teamwork_patterns = [
            r"\b(we\s|our\s+team|together|helped|colleague|colleagues|group\s+goal)\b",
            r"\b(collaborat(ed|ive|ion)|cooperat(ed|ive|ion)|peers?|squad|united|mutual\s+support)\b",
        ]
        has_teamwork = any(re.search(pat, combined_text) for pat in teamwork_patterns)

        return {
            "has_ownership": has_ownership,
            "has_example": has_example,
            "has_reasoning": has_reasoning,
            "has_teamwork": has_teamwork,
            "llm_positives": [],
            "llm_weaknesses": [],
            "mode": "semantic_offline",
        }

    # -------------------------------------------------------------------------
    # PASS 1: Per-Answer Evidence Calculation
    # -------------------------------------------------------------------------
    def evaluate_answer_evidence(
        self,
        question_id: str,
        question_text: str,
        category: str,
        dimension: str,
        intent: str,
        primary_answer: str,
        follow_up_answer: Optional[str] = None,
    ) -> PerAnswerEvidence:
        """Evaluates a single question turn against observable indicators and RAG context."""
        ans = (primary_answer or "").strip()
        fu = (follow_up_answer or "").strip()
        combined_text = f"{ans} {fu}".strip().lower()
        word_count = len(combined_text.split())

        positives: List[str] = []
        weaknesses: List[str] = []

        # Retrieve grounding RAG benchmarks (evaluation tier first, plus general context)
        rubric_chunks = self.retriever.retrieve(
            f"{category} {dimension} evaluation rubric",
            top_k=2,
            tier="evaluation",
        )
        general_chunks = self.retriever.retrieve(f"{question_text} {category}", top_k=2)

        # Combine unique citations for frontend evidence display
        seen_citations = set()
        citations: List[str] = []
        for c in (rubric_chunks + general_chunks):
            cit = c.get("citation", "")
            if cit and cit not in seen_citations:
                seen_citations.add(cit)
                citations.append(cit)
        citations = citations[:3]

        # Extract observable criteria directly from retrieved rubric text
        rubric_positives, rubric_weaknesses = self._extract_rubric_criteria(rubric_chunks or general_chunks)

        # Monosyllabic / evasive checks
        monosyllabic = {"yes", "no", "yeah", "nope", "dont know", "skip", "idk", "pass", "ok", "fine"}
        clean_words = re.findall(r"\b[a-z]+\b", combined_text)

        is_evasive = (
            word_count == 0
            or (word_count <= 4 and all(w in monosyllabic for w in clean_words))
            or any(p in combined_text for p in ["dont care", "dont want to", "i decline", "no idea"])
        )

        # Indicator detection: LLM rubric pass when online, semantic concept matcher when offline
        rubric_text = "\n".join(c.get("text", "") for c in (rubric_chunks or general_chunks))
        indicators = self._detect_indicators(
            combined_text=combined_text,
            question_text=question_text,
            category=category,
            dimension=dimension,
            rubric_text=rubric_text,
        )
        has_ownership = indicators["has_ownership"]
        has_example = indicators["has_example"]
        has_reasoning = indicators["has_reasoning"]
        has_teamwork = indicators["has_teamwork"]
        if indicators.get("llm_positives"):
            positives.extend(indicators["llm_positives"])
        if indicators.get("llm_weaknesses"):
            weaknesses.extend(indicators["llm_weaknesses"])

        if is_evasive and not has_ownership:
            weaknesses.append("Severely brief or evasive reply; provided no supporting context or personal narrative.")
            return PerAnswerEvidence(
                question_id=question_id,
                question_text=question_text,
                category=category,
                dimension=dimension,
                score=20.0,
                confidence=0.95,
                evidence_confidence="NONE",
                positive_indicators=[],
                weaknesses=weaknesses,
                evidence_text=ans[:120],
                citations=citations,
            )

        # Baseline scoring by depth
        if word_count < 15 and not has_ownership:
            score = 50.0
            ev_conf = "LOW"
            num_conf = 0.60
            weaknesses.append("Response was very brief; lacked detailed supporting context or examples.")
        elif word_count < 35:
            score = 68.0
            ev_conf = "MEDIUM"
            num_conf = 0.75
        else:
            score = 74.0
            ev_conf = "MEDIUM"
            num_conf = 0.85

        # Modifiers based on observable indicators
        if has_ownership:
            positives.append("Demonstrated direct personal accountability and ownership without evasiveness.")
            score += 12.0
            ev_conf = "HIGH"
            num_conf = 0.90
        elif word_count >= 15:
            weaknesses.append("Lacked explicit personal ownership or individual accountability; recommend highlighting your specific personal decisions.")

        if has_example:
            positives.append("Grounded assertions in concrete personal experiences or specific examples.")
            score += 8.0
            ev_conf = "HIGH"
        elif word_count >= 30 and not has_example:
            weaknesses.append("Relied heavily on abstract assertions; recommend citing concrete personal examples.")

        if has_reasoning:
            positives.append("Structured thoughts logically with causal justification.")
            score += 6.0

        if has_teamwork:
            positives.append("Demonstrated collaborative team orientation and shared mission alignment.")
            score += 5.0

        # Grounding evaluation: match candidate answer against retrieved rubric criteria
        rubric_positive_matches: List[str] = []
        rubric_weakness_matches: List[str] = []
        stop_words = {
            "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "as",
            "is", "was", "are", "were", "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "shall", "will", "should", "would", "may", "might", "must", "can", "could",
            "their", "his", "her", "its", "our", "your", "my", "this", "that", "these", "those"
        }

        for p_crit in rubric_positives:
            name_words = {w for w in re.findall(r"\b[a-z]{3,}\b", p_crit["name"].lower()) if w not in stop_words}
            desc_words = {w for w in re.findall(r"\b[a-z]{4,}\b", p_crit["description"].lower()) if w not in stop_words}
            quotes = [q.lower().strip('"\'') for q in re.findall(r'"([^"]+)"', p_crit["description"])]
            quote_matched = any(q in combined_text for q in quotes if len(q) > 3)
            target_words = name_words | desc_words
            overlap_count = sum(1 for w in target_words if re.search(r"\b" + re.escape(w) + r"\b", combined_text))
            if quote_matched or overlap_count >= 2:
                rubric_positive_matches.append(f"[Rubric Standard] {p_crit['name']}: {p_crit['description']}")

        for w_crit in rubric_weaknesses:
            name_words = {w for w in re.findall(r"\b[a-z]{3,}\b", w_crit["name"].lower()) if w not in stop_words}
            desc_words = {w for w in re.findall(r"\b[a-z]{4,}\b", w_crit["description"].lower()) if w not in stop_words}
            quotes = [q.lower().strip('"\'') for q in re.findall(r'"([^"]+)"', w_crit["description"])]
            quote_matched = any(q in combined_text for q in quotes if len(q) > 3)
            target_words = name_words | desc_words
            overlap_count = sum(1 for w in target_words if re.search(r"\b" + re.escape(w) + r"\b", combined_text))
            if quote_matched or overlap_count >= 2:
                rubric_weakness_matches.append(f"[Rubric Concern] {w_crit['name']}: {w_crit['description']}")

        # Score adjustment influenced directly by retrieved rubric benchmarks
        if rubric_positive_matches:
            rubric_bonus = min(15.0, len(rubric_positive_matches) * 6.0)
            score += rubric_bonus
            positives.extend(rubric_positive_matches)
            ev_conf = "HIGH"
            num_conf = min(0.95, num_conf + 0.05)

        if rubric_weakness_matches:
            rubric_penalty = min(15.0, len(rubric_weakness_matches) * 6.0)
            score -= rubric_penalty
            weaknesses.extend(rubric_weakness_matches)

        score = max(15.0, min(100.0, round(score, 1)))

        return PerAnswerEvidence(
            question_id=question_id,
            question_text=question_text,
            category=category,
            dimension=dimension,
            score=score,
            confidence=num_conf,
            evidence_confidence=ev_conf,
            positive_indicators=positives,
            weaknesses=weaknesses,
            evidence_text=ans[:150],
            citations=citations,
        )

    # -------------------------------------------------------------------------
    # PASS 2: Deterministic Aggregation & Single Narrative Synthesis
    # -------------------------------------------------------------------------
    def evaluate_session(
        self,
        candidate_name: str,
        persona: str,
        evidence_list: List[PerAnswerEvidence],
    ) -> EvaluationReport:
        """Aggregates scores deterministically and invokes a single LLM call for narrative report."""
        if not evidence_list:
            default_band = get_performance_band(50.0)
            return EvaluationReport(
                candidate_name=candidate_name,
                persona=persona,
                overall_practice_score=50.0,
                performance_band=default_band,
                dimension_scores={},
                fourteen_olq_scores={},
                per_question_evidence=[],
                executive_summary="No answers recorded for this session.",
                key_strengths=[],
                primary_shortcomings=["Interview was terminated before answers were provided."],
                actionable_recommendations=["Complete a full practice session."],
            )

        # 1. Deterministic math layer
        olq_scores = calculate_14_olq_scores(evidence_list)
        dim_scores = calculate_dashboard_dimensions(olq_scores)
        overall_score = calculate_overall_score(dim_scores)
        band = get_performance_band(overall_score)

        # 2. Extract aggregated positive indicators and weaknesses
        all_positives = [p for e in evidence_list for p in e.positive_indicators]
        all_weaknesses = [w for e in evidence_list for w in e.weaknesses]

        # 3. Single Groq LLM call for qualitative narrative
        narrative = self._generate_qualitative_narrative(
            candidate_name=candidate_name,
            persona=persona,
            overall_score=overall_score,
            band_tier=band["tier"],
            dimension_scores=dim_scores,
            positives=all_positives,
            weaknesses=all_weaknesses,
        )

        # Format radar data for frontend
        radar_data = [
            {"subject": dim, "dimension": dim, "score": score, "fullMark": 100}
            for dim, score in dim_scores.items()
        ]
        olq_radar_data = [
            {"subject": olq, "olq": olq, "score": score, "fullMark": 100}
            for olq, score in olq_scores.items()
        ]

        return EvaluationReport(
            candidate_name=candidate_name,
            persona=persona,
            overall_practice_score=overall_score,
            performance_band=band,
            dimension_scores=dim_scores,
            fourteen_olq_scores=olq_scores,
            per_question_evidence=evidence_list,
            executive_summary=narrative.get(
                "executive_summary",
                f"Candidate completed the session with an overall practice score of {overall_score}%. "
                f"Evaluation band: {band['tier']}.",
            ),
            key_strengths=narrative.get("key_strengths", list(set(all_positives))[:4]),
            primary_shortcomings=narrative.get("primary_shortcomings", list(set(all_weaknesses))[:4]),
            actionable_recommendations=narrative.get(
                "actionable_recommendations",
                [
                    "Ground responses in specific personal actions rather than abstract generalizations.",
                    "Articulate causal structure ('because', 'therefore') when explaining decisions.",
                    "Practice expanding answers beyond monosyllabic assertions.",
                ],
            ),
            radar_chart_data=radar_data,
            fourteen_olq_radar_data=olq_radar_data,
        )

    def _generate_qualitative_narrative(
        self,
        candidate_name: str,
        persona: str,
        overall_score: float,
        band_tier: str,
        dimension_scores: Dict[str, float],
        positives: List[str],
        weaknesses: List[str],
    ) -> Dict[str, Any]:
        """Executes a single concise Groq LLM call to synthesize the qualitative report grounded in retrieved benchmarks."""
        # Retrieve benchmark rubric excerpts for the candidate's weakest dimension(s)
        benchmark_excerpts = []
        if dimension_scores:
            lowest_dims = sorted(dimension_scores.items(), key=lambda x: x[1])[:2]
            for dim_name, _ in lowest_dims:
                b_chunks = self.retriever.retrieve(f"{dim_name} assessment rubric criteria", top_k=2, tier="evaluation")
                if not b_chunks:
                    b_chunks = self.retriever.retrieve(f"{dim_name} competencies", top_k=1, tier="academic")
                for bc in b_chunks:
                    cit = bc.get("citation", "[Evaluation Rubric]")
                    text_snip = bc.get("text", "")[:350].strip()
                    benchmark_excerpts.append(f"{cit}:\n{text_snip}")

        benchmark_block = (
            "\n\n".join(benchmark_excerpts)
            if benchmark_excerpts
            else "Standard ISSB Officer Like Quality criteria and behavioral indicators."
        )

        prompt = f"""
You are a senior ISSB assessor. Synthesize a structured, constructive qualitative evaluation report grounded in the benchmark criteria below.
Candidate: {candidate_name}
Interviewer Persona: {persona}
Overall Practice Score: {overall_score:.1f}% ({band_tier})

Dimension Breakdown:
{chr(10).join(f"- {k}: {v:.1f}%" for k, v in dimension_scores.items())}

Benchmark Evaluation Rubric Criteria:
{benchmark_block}

Observed Strengths:
{chr(10).join(f"- {p}" for p in set(positives[:6])) if positives else "- None recorded"}

Observed Shortcomings:
{chr(10).join(f"- {w}" for w in set(weaknesses[:6])) if weaknesses else "- None recorded"}

Return a JSON object with exactly these keys:
{{
  "executive_summary": "Concise 2-3 sentence overview of candidate performance grounded in the benchmark criteria.",
  "key_strengths": ["3-4 specific strengths demonstrated"],
  "primary_shortcomings": ["2-3 specific behavioral gaps relative to the benchmark criteria"],
  "actionable_recommendations": ["3 practical coaching tips based on the benchmark criteria"]
}}
"""
        res = self.ai.generate_json(prompt, system="You are an expert military psychology assessor for ISSB.")
        return res if res else {}
