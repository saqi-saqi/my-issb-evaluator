"""
MY_ISSB_Evaluator - Streamlit Interactive Application
Defensible AI Interviewer & Multi-Tier RAG Evaluator for ISSB Preparation.
"""

import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from src.evaluator.rubric_engine import InterviewEvaluationReport, RubricEvaluationEngine
from src.evaluator.score_calculator import (
    format_evidence_table,
    format_radar_chart_data,
    get_performance_band,
)

from src.interview.orchestrator import InterviewOrchestrator
from src.interview.session_state import InterviewSession
from src.llm.client import LLMClient
from src.question_bank.loader import QuestionBank
from src.rag.retriever import KnowledgeRetriever

# Page configuration
st.set_page_config(
    page_title="MY_ISSB_Evaluator | Defensible AI Interviewer",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a365d;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4a5568;
        margin-bottom: 1.5rem;
    }
    .persona-badge {
        padding: 4px 12px;
        border-radius: 12px;
        background-color: #ebf8ff;
        color: #2b6cb0;
        font-weight: 600;
        display: inline-block;
    }
    .citation-box {
        background-color: #f7fafc;
        border-left: 4px solid #3182ce;
        padding: 10px 14px;
        margin: 8px 0;
        font-size: 0.9rem;
    }
    .official-tag {
        background-color: #c6f6d5;
        color: #22543d;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .academic-tag {
        background-color: #e9d8fd;
        color: #44337a;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .score-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_backend_services():
    qb = QuestionBank()
    retriever = KnowledgeRetriever(use_chroma=False)
    llm = LLMClient()
    orchestrator = InterviewOrchestrator(question_bank=qb, retriever=retriever, llm_client=llm)
    return qb, retriever, llm, orchestrator


qb, retriever, llm, orchestrator = get_backend_services()

# Session State Initialization
if "interview_session" not in st.session_state:
    st.session_state.interview_session = None
if "evaluation_report" not in st.session_state:
    st.session_state.evaluation_report = None
if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = "Candidate"
if "current_follow_up" not in st.session_state:
    st.session_state.current_follow_up = None

# Sidebar Configuration
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Flag_of_Pakistan.svg/1200px-Flag_of_Pakistan.svg.png", width=50)
    st.title("ISSB Evaluator")
    st.caption("Inter Services Selection Board Preparation")
    st.divider()

    st.subheader("Candidate Profile")
    candidate_name = st.text_input("Candidate Full Name", value=st.session_state.candidate_name)
    st.session_state.candidate_name = candidate_name

    target_service = st.selectbox(
        "Target Service Commission",
        ["Pakistan Army (PMA Long Course)", "Pakistan Navy (Cadet Entry)", "Pakistan Air Force (GD Pilot / CAE)"],
    )

    st.subheader("Interview Dimension")
    persona_choice = st.radio(
        "Select Evaluative Dimension:",
        [
            "Deputy President Dimension",
            "Psychologist Dimension",
        ],
        help="Deputy President assesses intellect, emotional patterns, and social behavior through interview. Psychologist assesses deep motivation, self-concept, and projective traits.",
    )
    persona_key = "deputy_president" if "Deputy" in persona_choice else "psychologist"

    num_questions = st.slider("Session Question Count", min_value=3, max_value=8, value=5)

    st.divider()
    st.subheader("⚡ LLM Frontier Engine")
    provider_sel = st.selectbox(
        "Select Model Provider:",
        [
            "Google Gemini (Recommended)",
            "Groq (Qwen 2.5 72B / Llama 3.3)",
            "Local Ollama (Offline Qwen 2.5)",
            "OpenAI / DeepSeek / Custom",
            "Local Rule Fallback",
        ],
    )

    if "Gemini" in provider_sel:
        llm.provider = "gemini"
        api_key_val = st.text_input(
            "Gemini API Key:",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Get free API key at: https://aistudio.google.com/app/apikey",
        )
        if api_key_val:
            llm.api_key = api_key_val
            os.environ["GEMINI_API_KEY"] = api_key_val
        st.caption("[Get Free Gemini API Key](https://aistudio.google.com/app/apikey)")

    elif "Groq" in provider_sel:
        llm.provider = "groq"
        api_key_val = st.text_input(
            "Groq API Key (Runs Qwen 2.5 72B):",
            value=os.getenv("GROQ_API_KEY", ""),
            type="password",
            help="Get free Groq key at: https://console.groq.com/keys",
        )
        if api_key_val:
            llm.api_key = api_key_val
            os.environ["GROQ_API_KEY"] = api_key_val
        st.caption("[Get Free Groq API Key](https://console.groq.com/keys)")

    elif "Ollama" in provider_sel:
        llm.provider = "ollama"
        ollama_url = st.text_input("Ollama Endpoint:", value="http://localhost:11434/v1")
        llm.base_url = ollama_url
        llm.model_name = st.text_input("Ollama Model:", value="qwen2.5:7b")

    elif "OpenAI" in provider_sel:
        llm.provider = "openai"
        openai_val = st.text_input("OpenAI / DeepSeek API Key:", type="password")
        if openai_val:
            llm.api_key = openai_val
        base_u = st.text_input("Custom Base URL (optional):", value="https://api.openai.com/v1")
        llm.base_url = base_u
        llm.model_name = st.text_input("Model Name:", value="gpt-4o-mini")

    else:
        llm.provider = "local"
        llm.api_key = ""

    if st.button("🔍 Test Model Connection", use_container_width=True):
        success, msg = llm.test_connection()
        if success:
            st.success(f"✓ {msg}")
        else:
            st.error(f"✕ {msg}")

    st.divider()
    status_info = llm.get_status_info()
    if status_info["badge"] == "success":
        st.success(f"🟢 **{status_info['status']}**\n\n{status_info['detail']}")
    else:
        st.warning(f"🟡 **{status_info['status']}**\n\n{status_info['detail']}")

    st.divider()
    st.caption(f"📚 Knowledge Base: {len(retriever.chunks)} Chunks indexed")
    st.caption(f"❓ Question Bank: {len(qb.questions)} Curated questions")


# Header
st.markdown('<div class="main-header">MY_ISSB_Evaluator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Tier RAG & Defensible Behavioral Interview Evaluation System</div>', unsafe_allow_html=True)

tab_interview, tab_report, tab_rag, tab_qb = st.tabs([
    "🎙️ Mock Interview Session",
    "📊 Practice Evaluation Report",
    "📖 RAG Knowledge Base (Provenance)",
    "🗃️ Curated Question Bank",
])


# ==========================================
# TAB 1: MOCK INTERVIEW
# ==========================================
with tab_interview:
    col_start1, col_start2 = st.columns([3, 1])
    with col_start1:
        st.info(
            f"**Selected Dimension:** {persona_choice}\n\n"
            f"Evaluates intellect, emotional stability, and social adjustment through structured questioning. "
            f"Questions are drawn strictly from the verified Question Bank."
        )
    with col_start2:
        if st.button("🚀 Start New Interview", type="primary", use_container_width=True):
            session = orchestrator.start_session(
                candidate_name=candidate_name,
                persona=persona_key,
                num_questions=num_questions,
            )
            st.session_state.interview_session = session
            st.session_state.evaluation_report = None
            st.session_state.current_follow_up = None
            st.rerun()

    session: InterviewSession = st.session_state.interview_session

    if session is None:
        st.warning("Click **'Start New Interview'** above to begin your practice session.")
    elif session.completed:
        st.success("🎉 **Interview Session Concluded!**")
        st.write("All questions and follow-ups have been answered. Your performance has been analyzed against official ISSB qualities and academic rubrics.")
        if st.button("📈 View Detailed Evaluation Report", type="primary"):
            report = orchestrator.generate_final_report(session)
            st.session_state.evaluation_report = report
            st.switch_page = "tab_report"
            st.rerun()
    else:
        # Active interview in progress
        current_q = session.current_question
        progress = session.current_index / session.total_questions
        st.progress(progress, text=f"Question {session.current_index + 1} of {session.total_questions}")

        st.markdown(f"#### Question {session.current_index + 1}: Category - `{current_q.category.replace('_', ' ').title()}`")
        st.caption(f"Difficulty Level: {'⭐' * current_q.difficulty} | Assessed Dimension: {current_q.evaluation_dimension.title()}")

        # Natural question box
        question_display = orchestrator.get_natural_question_prompt(session, current_q)
        st.chat_message("assistant").write(question_display)

        # Show previous answer if we are on follow-up
        if session.awaiting_follow_up and st.session_state.current_follow_up:
            last_pair = session.qa_history[-1]
            st.chat_message("user").write(last_pair.answer)
            st.chat_message("assistant").write(f"**Follow-up Question:** {st.session_state.current_follow_up}")

            follow_up_input = st.text_area(
                "Your Response to Follow-up:",
                placeholder="Address the follow-up directly with clear reasoning and specific actions...",
                key=f"fu_input_{session.current_index}",
                height=100,
            )
            col_fu1, col_fu2 = st.columns([1, 4])
            with col_fu1:
                if st.button("Submit Follow-up", type="primary"):
                    if follow_up_input.strip():
                        orchestrator.submit_follow_up_answer(session, follow_up_input.strip())
                        st.session_state.current_follow_up = None
                        if session.completed:
                            report = orchestrator.generate_final_report(session)
                            st.session_state.evaluation_report = report
                        st.rerun()
                    else:
                        st.error("Please enter a response before submitting.")
        else:
            candidate_input = st.text_area(
                "Your Answer:",
                placeholder="State your answer clearly and honestly. Highlight concrete life examples where relevant...",
                key=f"q_input_{session.current_index}",
                height=130,
            )

            col_sub1, col_sub2 = st.columns([1, 4])
            with col_sub1:
                if st.button("Submit Answer", type="primary"):
                    if candidate_input.strip():
                        has_fu, fu_text = orchestrator.submit_primary_answer(session, candidate_input.strip())
                        if has_fu:
                            st.session_state.current_follow_up = fu_text
                        else:
                            st.session_state.current_follow_up = None
                            if session.completed:
                                report = orchestrator.generate_final_report(session)
                                st.session_state.evaluation_report = report
                        st.rerun()
                    else:
                        st.error("Please provide an answer before proceeding.")


# ==========================================
# TAB 2: EVALUATION REPORT (15-SECTION DEFENSIVE REPORT)
# ==========================================
with tab_report:
    report: InterviewEvaluationReport = st.session_state.evaluation_report

    if report is None:
        st.info("No completed session report available yet. Complete an interview in the 'Mock Interview Session' tab.")
    else:
        st.markdown(f"### 📋 Practice Performance Evaluation: {report.candidate_name}")
        st.caption(f"Evaluative Dimension: {report.persona.replace('_', ' ').title()} Interview Simulation")

        # Section 1 & 2: Candidate Profile & Session Metadata
        col_prof1, col_prof2, col_prof3, col_prof4 = st.columns(4)
        with col_prof1:
            st.metric("Candidate Name", report.candidate_name)
        with col_prof2:
            st.metric("Session Mode", report.persona.replace("_", " ").title())
        with col_prof3:
            q_cnt = len(report.per_question_evidence) or len(report.dimension_scores)
            st.metric("Questions Assessed", q_cnt)
        with col_prof4:
            s_date = report.session_metadata.get("session_date", "Today")
            st.metric("Session Date", s_date)

        st.divider()

        # Section 3: Top Metric Banner & Performance Band
        band = get_performance_band(report.overall_practice_score)
        col_m1, col_m2 = st.columns([1, 2])

        with col_m1:
            st.markdown(f"""
            <div class="score-card">
                <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px;">Overall Practice Score</div>
                <div style="font-size: 3.2rem; font-weight: 800;">{report.overall_practice_score}%</div>
                <div style="font-size: 1.1rem; font-weight: 600; margin-top: 5px;">{band['tier']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_m2:
            st.markdown("#### Performance Band Summary")
            st.write(band["summary"])
            st.warning(report.methodological_disclaimer)

        st.divider()

        # Section 4: Radar Chart & Strengths/Growth
        col_chart, col_highlights = st.columns([1, 1])

        with col_chart:
            st.markdown("#### 🎯 Competency Radar Assessment")
            dims = list(report.dimension_scores.keys())
            scores = list(report.dimension_scores.values())

            angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
            scores_closed = scores + [scores[0]]
            angles_closed = angles + [angles[0]]

            fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
            ax.fill(angles_closed, scores_closed, color='#3182ce', alpha=0.25)
            ax.plot(angles_closed, scores_closed, color='#1e3c72', linewidth=2)
            ax.set_ylim(0, 100)
            ax.set_xticks(angles)
            ax.set_xticklabels([d.replace(" & ", "\n& ") for d in dims], fontsize=8, fontweight='bold')
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=7)
            ax.grid(color='#cbd5e0', linestyle='--', linewidth=0.5)
            st.pyplot(fig)

        with col_highlights:
            st.markdown("#### 🌟 Key Demonstrated Strengths")
            for s in report.key_strengths:
                st.success(f"✓ {s}")

            st.markdown("#### 🔍 Targeted Areas for Growth")
            for g in report.growth_areas:
                st.error(f"△ {g}")

        st.divider()

        # Section 5: Per-Question Evidence Table
        if report.per_question_evidence:
            st.markdown("### 📝 Per-Question Behavioral Evidence Table")
            ev_table = format_evidence_table(report.per_question_evidence)
            st.dataframe(ev_table, use_container_width=True, hide_index=True)
            st.divider()

        # Sections 6 - 11: In-Depth Competency Assessments
        st.markdown("### 🔍 Dedicated Competency Assessments")
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("##### 💬 Communication & Articulation")
            st.write(report.communication_assessment or "Candidate maintained consistent verbal poise throughout.")

            st.markdown("##### 🧭 Decision Making Under Pressure")
            st.write(report.decision_making_assessment or "Demonstrated structured deconstruction of ethical and situational dilemmas.")

            st.markdown("##### 🎯 Service Motivation & Authenticity")
            st.write(report.motivation_assessment or "Articulated genuine career service motivation grounded in personal values.")

        with col_c2:
            st.markdown("##### 👥 Leadership & Accountability")
            st.write(report.leadership_assessment or "Demonstrated readiness to shoulder personal responsibility and inspire peers.")

            st.markdown("##### 🤝 Teamwork & Group Dynamics")
            st.write(report.teamwork_assessment or "Reflected peer cohesion, collective goal prioritization, and mutual support.")

            st.markdown("##### 🧘 Emotional Composure & Stress Response")
            st.write(report.stress_response_assessment or "Maintained equilibrium and composure during intensive probing.")

        st.divider()

        # Section 12: Multi-Dimensional Rubric Breakdown with Citations
        st.markdown("### 🔬 Multi-Dimensional Rubric Breakdown")
        for dim_name, eval_item in report.dimension_evaluations.items():
            conf_val = getattr(eval_item, "confidence", 0.8)
            with st.expander(f"{dim_name} — Score: {eval_item.dimension_score}% (Confidence: {int(conf_val * 100)}%)", expanded=False):
                col_d1, col_d2 = st.columns([2, 1])
                with col_d1:
                    st.markdown(eval_item.detailed_feedback)
                    st.markdown("**Observable Positive Indicators:**")
                    for p in eval_item.positive_indicators_observed:
                        st.markdown(f"- {p}")
                    if eval_item.weaknesses_observed:
                        st.markdown("**Observable Weaknesses:**")
                        for w in eval_item.weaknesses_observed:
                            st.markdown(f"- {w}")

                with col_d2:
                    st.markdown("**Source Provenance & Authority Citations:**")
                    for c in eval_item.official_citations:
                        st.markdown(f"<span class='official-tag'>Official ISSB</span> {c}", unsafe_allow_html=True)
                    for c in eval_item.academic_citations:
                        st.markdown(f"<span class='academic-tag'>Academic/Rubric</span> {c}", unsafe_allow_html=True)

        st.divider()

        # Section 13: Actionable Preparation Recommendations
        st.markdown("### 💡 Actionable Preparation Recommendations")
        for idx, rec in enumerate(report.preparation_recommendations, 1):
            st.info(f"**{idx}.** {rec}")

        # Section 14: Methodological Disclaimer Footer
        st.caption(f"🛡️ {report.methodological_disclaimer}")



# ==========================================
# TAB 3: RAG KNOWLEDGE BASE EXPLORER
# ==========================================
with tab_rag:
    st.markdown("### 📖 Multi-Tier RAG Knowledge Base Explorer")
    st.write("Browse and query the verified knowledge base chunks with strict source provenance metadata.")

    col_q1, col_q2, col_q3 = st.columns([2, 1, 1])
    with col_q1:
        rag_query = st.text_input("Search Knowledge Base:", value="leadership decision making under stress")
    with col_q2:
        src_filter = st.selectbox(
            "Filter by Source Type:",
            ["All", "official", "academic", "evaluation", "preparation", "current_affairs"],
        )
    with col_q3:
        prefer_off = st.checkbox("Prioritize Official ISSB", value=True)

    filter_val = None if src_filter == "All" else src_filter
    rag_results = retriever.retrieve(rag_query, top_k=6, source_type=filter_val, prefer_official=prefer_off)

    st.markdown(f"**Retrieved {len(rag_results)} authoritative chunks:**")
    for r in rag_results:
        tag_class = "official-tag" if r["source_type"] == "official" else "academic-tag"
        with st.container():
            st.markdown(f"""
            <div class="citation-box">
                <span class="{tag_class}">{r['source_type'].upper()} (Level {r['authority_level']})</span>
                <strong>{r['title']}</strong> | File: <code>{r['source_file']}</code> | Topic: <em>{r['topic']}</em>
                <p style="margin-top: 6px;">{r['text'][:400]}...</p>
                <small style="color: #718096;">Citation: {r['citation']}</small>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# TAB 4: QUESTION BANK EXPLORER
# ==========================================
with tab_qb:
    st.markdown("### 🗃️ Curated Structured Question Bank")
    st.write("Examine structured question bank items decoupled from the RAG knowledge base.")

    cat_list = ["All"] + sorted(list(qb.categories.keys()))
    selected_cat = st.selectbox("Filter Question Category:", cat_list)

    if selected_cat == "All":
        display_questions = list(qb.questions.values())
    else:
        display_questions = qb.categories.get(selected_cat, [])

    st.write(f"Showing **{len(display_questions)}** questions:")
    for q in display_questions:
        with st.expander(f"[{q.id}] {q.question[:90]}... (Difficulty: {q.difficulty}/5)"):
            st.markdown(f"**Full Question:** {q.question}")
            st.markdown(f"**Category:** `{q.category}` | **Persona:** `{q.persona}` | **Dimension:** `{q.evaluation_dimension}`")
            st.markdown(f"**Assessment Intent:** {q.intent}")
            if q.follow_up_pool:
                st.markdown("**Structured Follow-up Probes:**")
                for f in q.follow_up_pool:
                    st.markdown(f"- {f}")
