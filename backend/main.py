"""
Streamlined FastAPI REST API for MY_ISSB_Evaluator.
Connects the modern React/Vite frontend directly to the simplified Python Core AI Engine.
Exposes the 7 core FYP endpoints with full input validation and clean error handling.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from core.ai import ai_client
from core.interview import InterviewService
from core.questions import QuestionBank
from core.rag import KnowledgeRetriever

app = FastAPI(
    title="MY_ISSB_Evaluator API",
    description="Streamlined Production Backend for ISSB AI Interview & Defensible Evaluation",
    version="2.1.0",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LLMRateLimitMiddleware:
    """Small in-process sliding-window limiter for expensive routes."""

    protected_prefixes = (
        "/api/interview/start",
        "/api/interview/answer",
        "/api/interview/followup",
        "/api/interview/follow-up",
        "/api/learning/",
        "/api/interview/report/",
    )

    def __init__(self, app):
        self.app = app
        self.events = defaultdict(deque)
        self.lock = Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if not path.startswith(self.protected_prefixes):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        ip = client[0] if client else "unknown"
        now = time.monotonic()
        minute_limit = int(os.getenv("LLM_OPS_PER_MINUTE", "30"))
        daily_limit = int(os.getenv("SESSIONS_PER_DAY", "8"))
        with self.lock:
            bucket = self.events[(ip, "minute")]
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= minute_limit:
                retry_after = max(1, int(60 - (now - bucket[0])))
                await self._send_429(send, retry_after, scope)
                return
            bucket.append(now)
            if path == "/api/interview/start":
                day_bucket = self.events[(ip, "day")]
                while day_bucket and now - day_bucket[0] >= 86400:
                    day_bucket.popleft()
                if len(day_bucket) >= daily_limit:
                    retry_after = max(1, int(86400 - (now - day_bucket[0])))
                    await self._send_429(send, retry_after, scope)
                    return
                day_bucket.append(now)
        await self.app(scope, receive, send)

    @staticmethod
    async def _send_429(send, retry_after: int, scope=None):
        headers = [
            (b"content-type", b"application/json"),
            (b"retry-after", str(retry_after).encode()),
        ]
        # Echo the request origin on 429s so cross-origin frontends can read
        # the rate-limit detail instead of an opaque CORS failure.
        origin = None
        for name, value in (scope or {}).get("headers", []):
            if name == b"origin":
                origin = value.decode("latin-1")
                break
        if origin and origin in allowed_origins:
            headers.append((b"access-control-allow-origin", origin.encode("latin-1")))
        body = b'{"detail":"Rate limit exceeded. Please try again shortly."}'
        await send({"type": "http.response.start", "status": 429, "headers": headers})
        await send({"type": "http.response.body", "body": body})


app.add_middleware(LLMRateLimitMiddleware)

# Core singletons
qb = QuestionBank()
retriever = KnowledgeRetriever()
interview_service = InterviewService(question_bank=qb, retriever=retriever, ai=ai_client)
_status_cache: Optional[Dict[str, Any]] = None
_status_cache_at = 0.0
_status_cache_lock = Lock()


# --- Request Models ---

class StartInterviewRequest(BaseModel):
    candidate_name: str = Field(default="Candidate", max_length=200, description="Full name of candidate")
    target_branch: Optional[str] = Field(default=None, max_length=200)
    candidate_id: Optional[str] = Field(default=None, max_length=100)
    persona: str = Field(default="deputy_president", description="'deputy_president' or 'psychologist'")
    num_questions: int = Field(default=5, ge=2, le=10, description="Number of questions in session")


class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: str = Field(max_length=4000)


class SubmitFollowUpRequest(BaseModel):
    session_id: str
    follow_up_answer: str = Field(max_length=4000)


class LearningFeedbackRequest(BaseModel):
    session_id: str
    question_id: Optional[str] = None


class RetryAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    retry_answer: str = Field(max_length=4000)


class LLMSettingsRequest(BaseModel):
    provider: Optional[str] = "groq"
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 3
    tier: Optional[str] = None
    source_type: Optional[str] = None
    prefer_official: Optional[bool] = True


# --- Core 7 Endpoints ---

@app.get("/api/status")
def get_system_status() -> Dict[str, Any]:
    """1. System Health & Environment Status."""
    global _status_cache, _status_cache_at
    now = time.monotonic()
    with _status_cache_lock:
        if _status_cache is not None and now - _status_cache_at < 60:
            return _status_cache
        conn_ok, conn_msg = ai_client.test_connection()
        _status_cache = {
            "status": "online",
            "question_bank_total": len(qb.questions),
            "categories_total": len(qb.categories),
            "knowledge_base_chunks": len(retriever.chunks),
            "llm_provider": "Groq",
            "llm_model": ai_client.model,
            "llm_override_allowed": os.getenv("ALLOW_LLM_OVERRIDE", "").lower() in {"1", "true", "yes"},
            "llm_status": {
                "provider": "Groq",
                "model": ai_client.model,
                "connected": conn_ok,
                "message": conn_msg,
                "badge": "success" if conn_ok else "warning",
            },
        }
        _status_cache_at = now
        return _status_cache


@app.post("/api/interview/start")
def start_interview(req: StartInterviewRequest) -> Dict[str, Any]:
    """2. Start a new calibrated interview session."""
    session = interview_service.start_session(
        candidate_name=req.candidate_name,
        persona=req.persona,
        num_questions=req.num_questions,
        target_branch=req.target_branch,
        candidate_id=req.candidate_id,
    )
    interview_service.learning.initialize_profile(session.session_id, session.candidate_name)
    first_q = session.current_question
    if not first_q:
        raise HTTPException(status_code=500, detail="Failed to initialize question sequence")

    return {
        "session_id": session.session_id,
        "candidate_name": session.candidate_name,
        "persona": session.persona,
        "persona_title": "Deputy President" if session.persona == "deputy_president" else "Senior Psychologist",
        "current_index": session.current_index,
        "total_questions": session.total_questions,
        "target_branch": session.target_branch,
        "candidate_id": session.candidate_id,
        "current_question": {
            **first_q.to_dict(),
            "raw_question": first_q.question,
            "natural_prompt": first_q.question,
        },
    }


@app.post("/api/interview/answer")
def submit_primary_answer(req: SubmitAnswerRequest) -> Dict[str, Any]:
    """3. Submit candidate's answer; checks if targeted probe is required."""
    session = interview_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    has_follow_up, follow_up_text = interview_service.submit_primary_answer(session, req.answer)

    response: Dict[str, Any] = {
        "session_id": session.session_id,
        "has_follow_up": has_follow_up,
        "follow_up_question": follow_up_text,
        "is_completed": session.completed,
        "current_index": session.current_index,
        "total_questions": session.total_questions,
        "target_branch": session.target_branch,
        "candidate_id": session.candidate_id,
    }

    if not has_follow_up and not session.completed:
        next_q = session.current_question
        if next_q:
            response["next_question"] = {
                **next_q.to_dict(),
                "raw_question": next_q.question,
                "natural_prompt": next_q.question,
            }

    return response


@app.post("/api/interview/followup")
@app.post("/api/interview/follow-up")
def submit_follow_up_answer(req: SubmitFollowUpRequest) -> Dict[str, Any]:
    """4. Submit answer to the follow-up probe and advance."""
    session = interview_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    interview_service.submit_follow_up_answer(session, req.follow_up_answer)

    response: Dict[str, Any] = {
        "session_id": session.session_id,
        "is_completed": session.completed,
        "current_index": session.current_index,
        "total_questions": session.total_questions,
        "target_branch": session.target_branch,
        "candidate_id": session.candidate_id,
    }

    if not session.completed:
        next_q = session.current_question
        if next_q:
            response["next_question"] = {
                **next_q.to_dict(),
                "raw_question": next_q.question,
                "natural_prompt": next_q.question,
            }

    return response


@app.get("/api/interview/report/{session_id}")
def get_interview_report(session_id: str) -> Dict[str, Any]:
    """5. Generate and return the 2-Pass evaluation report."""
    session = interview_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    stored_report = interview_service.storage.get_report(session_id)
    if stored_report is None:
        report = interview_service.generate_final_report(session)
        res = report.to_dict()
    else:
        res = stored_report
    res["session_metadata"] = {
        "session_id": session.session_id,
        "candidate_name": session.candidate_name,
        "persona": session.persona,
        "total_questions": session.total_questions,
        "target_branch": session.target_branch,
        "candidate_id": session.candidate_id,
    }
    return res


@app.post("/api/learning/feedback")
def get_learning_feedback(req: LearningFeedbackRequest) -> Dict[str, Any]:
    """6. Generate personalized improvement feedback and practice tasks."""
    session = interview_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find target evidence record
    evidence = None
    if req.question_id:
        evidence = next((e for e in session.evidence_records if e.question_id == req.question_id), None)
    if not evidence and session.evidence_records:
        evidence = session.evidence_records[-1]

    if not evidence:
        raise HTTPException(status_code=400, detail="No evidence records available for feedback")

    feedback = interview_service.learning.generate_feedback(evidence)
    return {
        **feedback,
        "learning_phase": feedback,
    }


@app.post("/api/learning/retry")
def submit_retry_answer(req: RetryAnswerRequest) -> Dict[str, Any]:
    """7. Evaluate revised retry attempt with honest before-vs-after delta."""
    session = interview_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    evidence = next((e for e in session.evidence_records if e.question_id == req.question_id), None)
    orig_score = evidence.score if evidence else 60.0
    orig_answer = session.answers.get(req.question_id, "")

    comparison = interview_service.learning.evaluate_retry(
        question_id=req.question_id,
        original_answer=orig_answer,
        retry_answer=req.retry_answer,
        original_score=orig_score,
    )
    interview_service.learning.record_retry(
        session_id=session.session_id,
        candidate_name=session.candidate_name,
        comparison=comparison,
        question_id=req.question_id,
    )
    profile = interview_service.learning.get_profile(req.session_id)
    new_learning = interview_service.learning.generate_feedback(evidence) if evidence else {}

    return {
        "before_after": comparison.to_dict(),
        "new_evidence": evidence.to_dict() if evidence else {},
        "new_learning": new_learning,
        "learning_profile": profile,
    }


@app.get("/api/learning/profile/{session_id}")
def get_learning_profile(session_id: str) -> Dict[str, Any]:
    """Return candidate learning profile."""
    profile = interview_service.learning.get_profile(session_id)
    return {
        "session_id": session_id,
        "learning_profile": profile,
        "session_learning_report": profile,
    }


@app.get("/api/progress/{candidate_id}")
def get_candidate_progress(candidate_id: str) -> Dict[str, Any]:
    if not candidate_id.strip():
        raise HTTPException(status_code=400, detail="Candidate identity is required")
    return interview_service.storage.get_progress(candidate_id.strip())


# --- Developer / Demonstration Endpoints (For UI Explorers) ---

@app.get("/api/categories")
def get_categories() -> List[Dict[str, Any]]:
    """Question bank categories with counts."""
    result = []
    for cat_name, q_list in sorted(qb.categories.items()):
        result.append({
            "category": cat_name,
            "label": cat_name.replace("_", " ").title(),
            "count": len(q_list),
        })
    return result


@app.get("/api/questions")
def list_questions(
    category: Optional[str] = None,
    persona: Optional[str] = None,
    max_difficulty: Optional[int] = None,
) -> List[Dict[str, Any]]:
    questions = [
        q.to_dict()
        for q in qb.filter_questions(category=category, persona=persona, max_difficulty=max_difficulty)
    ]
    if os.getenv("EXPOSE_EVALUATION_META", "").lower() not in {"1", "true", "yes"}:
        for question in questions:
            question.pop("intent", None)
            question.pop("follow_up_pool", None)
    return questions


@app.post("/api/rag/search")
def search_rag(req: RagSearchRequest) -> List[Dict[str, Any]]:
    target_tier = req.tier or (req.source_type if req.source_type != "all" else None)
    return retriever.retrieve(query=req.query, top_k=req.top_k, tier=target_tier)


@app.post("/api/settings/llm")
def update_llm_settings(req: LLMSettingsRequest) -> Dict[str, Any]:
    """Update Groq API key or model from SettingsModal."""
    if os.getenv("ALLOW_LLM_OVERRIDE", "").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=403, detail="LLM settings are managed by the server")
    if req.api_key:
        ai_client.api_key = req.api_key.strip()
    if req.model_name:
        ai_client.model = req.model_name.strip()
    ai_client._init_client()
    success, msg = ai_client.test_connection()
    return {
        "success": success,
        "message": msg,
        "status_info": {
            "provider": "Groq",
            "model": ai_client.model,
            "connected": success,
            "message": msg,
        },
    }


@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    """Serve the Vite build as a same-origin SPA when it exists."""
    dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    requested = dist / full_path
    if full_path and requested.is_file():
        return FileResponse(requested)
    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
