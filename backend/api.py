"""
FastAPI REST API for MY_ISSB_Evaluator.
Connects modern frontend to Python ISSB Orchestrator, RAG Retriever, and Evaluation Engine.
"""

from typing import Any, Dict, List, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.evaluator.rubric_engine import InterviewEvaluationReport
from src.evaluator.score_calculator import format_evidence_table, get_performance_band
from src.interview.orchestrator import InterviewOrchestrator
from src.interview.session_state import InterviewSession
from src.llm.client import LLMClient
from src.question_bank.loader import QuestionBank
from src.rag.retriever import KnowledgeRetriever

app = FastAPI(
    title="MY_ISSB_Evaluator API",
    description="Backend API for Defensible AI Interviewer and ISSB Evaluation System",
    version="2.0.0",
)

# Enable CORS for local modern web frontends (Vite default port 5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared in-memory singletons
qb = QuestionBank()
retriever = KnowledgeRetriever(use_chroma=False)
llm = LLMClient()
orchestrator = InterviewOrchestrator(question_bank=qb, retriever=retriever, llm_client=llm)

# Active interview sessions store (session_id -> InterviewSession)
active_sessions: Dict[str, InterviewSession] = {}


# --- Pydantic Request Models ---

class StartInterviewRequest(BaseModel):
    candidate_name: str = Field(default="Candidate", description="Full name of candidate")
    persona: str = Field(default="deputy_president", description="'deputy_president' or 'psychologist'")
    num_questions: int = Field(default=5, ge=2, le=8, description="Number of questions in session")


class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: str


class SubmitFollowUpRequest(BaseModel):
    session_id: str
    follow_up_answer: str


class RagSearchRequest(BaseModel):
    query: str
    source_type: Optional[str] = None
    dimension: Optional[str] = None
    prefer_official: bool = True
    top_k: int = 4


class LLMSettingsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None


class LearningFeedbackRequest(BaseModel):
    session_id: str
    question_id: Optional[str] = None


class RetryAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    retry_answer: str


# --- Endpoints ---

@app.get("/api/status")
def get_system_status() -> Dict[str, Any]:
    """Returns general system health, RAG chunk count, questions count, and active LLM status."""
    status_info = llm.get_status_info()
    return {
        "status": "online",
        "knowledge_base_chunks": len(retriever.chunks),
        "question_bank_total": len(qb.questions),
        "categories_total": len(qb.categories),
        "llm_status": status_info,
    }


@app.get("/api/categories")
def get_categories() -> List[Dict[str, Any]]:
    """Returns all 13 question bank categories with question counts."""
    result = []
    for cat_name, q_list in sorted(qb.categories.items()):
        result.append({
            "category": cat_name,
            "label": cat_name.replace("_", " ").title(),
            "count": len(q_list),
        })
    return result


@app.get("/api/questions")
def get_questions(
    category: Optional[str] = None,
    persona: Optional[str] = None,
    max_difficulty: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Lists question bank items filtered by criteria."""
    items = qb.filter_questions(persona=persona, category=category, max_difficulty=max_difficulty)
    return [q.to_dict() for q in items]


@app.post("/api/rag/search")
def search_knowledge_base(req: RagSearchRequest) -> List[Dict[str, Any]]:
    """Performs relevance-filtered semantic search across the multi-tier ISSB knowledge base."""
    results = retriever.retrieve(
        query=req.query,
        top_k=req.top_k,
        source_type=req.source_type,
        dimension=req.dimension,
        prefer_official=req.prefer_official,
    )
    return results


@app.post("/api/interview/start")
def start_interview(req: StartInterviewRequest) -> Dict[str, Any]:
    """Starts a new mock interview session and returns initial question."""
    session = orchestrator.start_session(
        candidate_name=req.candidate_name,
        persona=req.persona,
        num_questions=req.num_questions,
    )
    active_sessions[session.session_id] = session

    first_q = session.current_question
    if not first_q:
        raise HTTPException(status_code=500, detail="Failed to initialize question flow")

    natural_prompt = orchestrator.get_natural_question_prompt(session, first_q)

    return {
        "session_id": session.session_id,
        "candidate_name": session.candidate_name,
        "persona": session.persona,
        "persona_title": "Deputy President" if session.persona == "deputy_president" else "Senior Psychologist",
        "current_index": session.current_index,
        "total_questions": session.total_questions,
        "current_question": {
            "id": first_q.id,
            "category": first_q.category,
            "category_label": first_q.category.replace("_", " ").title(),
            "difficulty": first_q.difficulty,
            "evaluation_dimension": first_q.evaluation_dimension,
            "intent": first_q.intent,
            "raw_question": first_q.question,
            "natural_prompt": natural_prompt,
        },
    }


@app.post("/api/interview/answer")
def submit_primary_answer(req: SubmitAnswerRequest) -> Dict[str, Any]:
    """Processes candidate's answer and checks if a follow-up probe is triggered."""
    session = active_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    has_follow_up, follow_up_text = orchestrator.submit_primary_answer(session, req.answer)

    response: Dict[str, Any] = {
        "session_id": session.session_id,
        "has_follow_up": has_follow_up,
        "follow_up_question": follow_up_text,
        "is_completed": session.completed,
        "current_index": session.current_index,
        "total_questions": session.total_questions,
    }

    # If no follow-up and session not completed, include next question details
    if not has_follow_up and not session.completed:
        next_q = session.current_question
        if next_q:
            natural_prompt = orchestrator.get_natural_question_prompt(session, next_q)
            response["next_question"] = {
                "id": next_q.id,
                "category": next_q.category,
                "category_label": next_q.category.replace("_", " ").title(),
                "difficulty": next_q.difficulty,
                "evaluation_dimension": next_q.evaluation_dimension,
                "intent": next_q.intent,
                "raw_question": next_q.question,
                "natural_prompt": natural_prompt,
            }

    return response


@app.post("/api/interview/follow-up")
def submit_follow_up_answer(req: SubmitFollowUpRequest) -> Dict[str, Any]:
    """Records candidate's answer to the follow-up question and advances session."""
    session = active_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    orchestrator.submit_follow_up_answer(session, req.follow_up_answer)

    response: Dict[str, Any] = {
        "session_id": session.session_id,
        "is_completed": session.completed,
        "current_index": session.current_index,
        "total_questions": session.total_questions,
    }

    if not session.completed:
        next_q = session.current_question
        if next_q:
            natural_prompt = orchestrator.get_natural_question_prompt(session, next_q)
            response["next_question"] = {
                "id": next_q.id,
                "category": next_q.category,
                "category_label": next_q.category.replace("_", " ").title(),
                "difficulty": next_q.difficulty,
                "evaluation_dimension": next_q.evaluation_dimension,
                "intent": next_q.intent,
                "raw_question": next_q.question,
                "natural_prompt": natural_prompt,
            }

    return response


@app.get("/api/interview/report/{session_id}")
def get_interview_report(session_id: str) -> Dict[str, Any]:
    """Generates and returns the complete 15-section practice performance evaluation report."""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    report = orchestrator.generate_final_report(session)
    band = get_performance_band(report.overall_practice_score)
    evidence_table = format_evidence_table(report.per_question_evidence)

    res = report.to_dict()
    res["performance_band"] = band
    res["formatted_evidence_table"] = evidence_table

    # Format radar chart coordinates for frontend Recharts
    radar_data = []
    for dim_name, score in report.dimension_scores.items():
        radar_data.append({
            "subject": dim_name.replace(" & ", "\n& "),
            "dimension": dim_name,
            "score": score,
            "fullMark": 100,
        })
    res["radar_chart_data"] = radar_data

    # Format 14-OLQ radar coordinates
    olq_radar_data = []
    for olq_name, score in getattr(report, "fourteen_olq_scores", {}).items():
        olq_radar_data.append({
            "subject": olq_name,
            "olq": olq_name,
            "score": score,
            "fullMark": 100,
        })
    res["fourteen_olq_radar_data"] = olq_radar_data

    return res


@app.get("/api/rag/benchmark")
def get_rag_benchmark() -> Dict[str, Any]:
    """Runs and returns the RAG quality evaluation benchmark metrics."""
    from src.rag.benchmark import run_rag_benchmark
    return run_rag_benchmark(verbose=False)


@app.post("/api/learning/feedback")
def get_learning_feedback_endpoint(req: LearningFeedbackRequest) -> Dict[str, Any]:
    """Generates personalized, evidence-grounded coaching recommendations for a candidate's answer."""
    session = active_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    try:
        feedback = orchestrator.get_learning_feedback(session, req.question_id)
        return feedback.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/learning/retry")
def submit_retry_answer_endpoint(req: RetryAnswerRequest) -> Dict[str, Any]:
    """Evaluates candidate's revised retry answer, generates honest before-vs-after comparison, and updates profile."""
    session = active_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    try:
        result = orchestrator.process_retry_answer(session, req.question_id, req.retry_answer)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/learning/profile/{session_id}")
def get_learning_profile_endpoint(session_id: str) -> Dict[str, Any]:
    """Returns candidate learning profile and session-level learning report."""
    session = active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    tracker = orchestrator.get_session_tracker(session)
    session_report = orchestrator.generate_session_learning_report(session)
    return {
        "session_id": session_id,
        "learning_profile": tracker.profile.to_dict()["learning_profile"],
        "session_learning_report": session_report.to_dict()["session_learning_report"],
    }


@app.post("/api/settings/llm")
def update_llm_settings(req: LLMSettingsRequest) -> Dict[str, Any]:
    """Configures the active LLM provider and tests live connection."""
    prov = req.provider.lower() if req.provider else "groq"
    api_key = req.api_key.strip() if req.api_key else None
    if api_key and api_key.startswith("gsk_"):
        prov = "groq"

    llm.provider = prov
    if api_key is not None:
        llm.api_key = api_key
    if req.model_name is not None:
        llm.model_name = req.model_name
    if req.base_url is not None:
        llm.base_url = req.base_url

    # Propagate to orchestrator sub-components
    orchestrator.llm = llm
    if hasattr(orchestrator, "evaluator"):
        orchestrator.evaluator.llm = llm
    if hasattr(orchestrator, "learning_engine"):
        orchestrator.learning_engine.llm = llm

    success, msg = llm.test_connection()
    status_info = llm.get_status_info()

    return {
        "success": success,
        "message": msg,
        "status_info": status_info,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
