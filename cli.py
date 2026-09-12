"""
Interactive Terminal CLI for MY_ISSB_Evaluator.
Allows immediate, full-featured interview practice and defensible scoring directly in terminal.
"""

import io
import sys
from typing import List

# Ensure safe output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.evaluator.score_calculator import get_performance_band
from src.interview.orchestrator import InterviewOrchestrator
from src.question_bank.loader import QuestionBank
from src.rag.retriever import KnowledgeRetriever


def print_banner():
    print("=" * 72)
    print("        MY_ISSB_Evaluator -- Defensible AI Interview System")
    print("        Inter Services Selection Board Practice Simulation")
    print("=" * 72)


def run_cli_interview():
    print_banner()
    retriever = KnowledgeRetriever(use_chroma=False)
    qb = QuestionBank()
    orchestrator = InterviewOrchestrator(question_bank=qb, retriever=retriever)

    print(f"\n[+] Loaded {len(qb.questions)} curated questions across {len(qb.categories)} categories.")
    print(f"[+] Loaded {len(retriever.chunks)} authoritative knowledge chunks into RAG index.\n")

    name = input("Enter Candidate Full Name [Muhammad Ali]: ").strip() or "Muhammad Ali"

    print("\nSelect Interview Evaluative Dimension:")
    print("  1. Deputy President Dimension (Intellect, Emotional Pattern, Social Behavior)")
    print("  2. Psychologist Dimension (Inner Motivation, Self-Concept, Projective Traits)")
    dim_choice = input("Choice [1/2, default 1]: ").strip()
    persona = "deputy_president" if dim_choice != "2" else "psychologist"
    persona_label = "Deputy President" if persona == "deputy_president" else "Psychologist"

    num_q_str = input("Number of Questions for this session [3-8, default 3]: ").strip()
    try:
        num_q = int(num_q_str)
        num_q = max(2, min(8, num_q))
    except ValueError:
        num_q = 3

    print(f"\n--- Commencing {persona_label}-Style Interview for {name} ({num_q} Questions) ---\n")
    session = orchestrator.start_session(candidate_name=name, persona=persona, num_questions=num_q)

    while not session.completed:
        curr_q = session.current_question
        q_idx = session.current_index + 1
        print(f"\n{'-' * 60}")
        print(f"QUESTION {q_idx}/{session.total_questions} | Category: {curr_q.category.upper()} | Difficulty: {'*' * curr_q.difficulty}")
        print(f"{'-' * 60}")

        natural_q = orchestrator.get_natural_question_prompt(session, curr_q)
        print(f"\n[Interviewer]:\n{natural_q}\n")

        answer = input("[Your Answer]: ").strip()
        while not answer:
            print("Please provide an answer to proceed.")
            answer = input("[Your Answer]: ").strip()

        has_fu, follow_up = orchestrator.submit_primary_answer(session, answer)

        if has_fu and follow_up:
            print(f"\n[Interviewer - Probing Follow-Up]:\n{follow_up}\n")
            fu_answer = input("[Your Follow-Up Response]: ").strip()
            while not fu_answer:
                print("Please provide a response to the follow-up.")
                fu_answer = input("[Your Follow-Up Response]: ").strip()
            orchestrator.submit_follow_up_answer(session, fu_answer)

    print("\n" + "=" * 72)
    print("                   SESSION CONCLUDED -- GENERATING REPORT")
    print("=" * 72 + "\n")

    report = orchestrator.generate_final_report(session)
    band = get_performance_band(report.overall_practice_score)

    print(f"Candidate: {report.candidate_name}")
    print(f"Interview Dimension: {report.persona.replace('_', ' ').title()}")
    print(f"Practice Readiness Score: {report.overall_practice_score}% ({band['tier']})")
    print(f"\nSummary: {band['summary']}\n")

    print("-" * 72)
    print("COMPETENCY DIMENSION SCORES:")
    print("-" * 72)
    for dim, score in report.dimension_scores.items():
        bar = "#" * int(score / 5)
        print(f"  {dim:<32} {score:>5.1f}%  {bar}")

    print("\n" + "-" * 72)
    print("DEMONSTRATED POSITIVE INDICATORS:")
    print("-" * 72)
    for s in report.key_strengths:
        print(f"  [+] {s}")

    print("\n" + "-" * 72)
    print("TARGETED GROWTH AREAS:")
    print("-" * 72)
    for g in report.growth_areas:
        print(f"  [-] {g}")

    print("\n" + "-" * 72)
    print("DETAILED RUBRIC EVALUATION & CITATIONS:")
    print("-" * 72)
    for dim, item in report.dimension_evaluations.items():
        print(f"\n>>> {dim} (Score: {item.dimension_score}%)")
        print(f"Feedback: {item.detailed_feedback}")
        print(f"Citations: {', '.join(item.official_citations + item.academic_citations)}")

    print("\n" + "-" * 72)
    print("ACTIONABLE PREPARATION RECOMMENDATIONS:")
    print("-" * 72)
    for idx, rec in enumerate(report.preparation_recommendations, 1):
        print(f"  {idx}. {rec}")

    print("\n" + "=" * 72)
    print(report.methodological_disclaimer)
    print("=" * 72 + "\n")



if __name__ == "__main__":
    run_cli_interview()
