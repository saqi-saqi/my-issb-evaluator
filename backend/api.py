"""
FastAPI entry point re-exporting streamlined app from backend.main.
Provides backwards compatibility for launchers and existing tests.
"""

from backend.main import (
    app,
    qb,
    retriever,
    interview_service,
    ai_client,
    StartInterviewRequest,
    SubmitAnswerRequest,
    SubmitFollowUpRequest,
    LearningFeedbackRequest,
    RetryAnswerRequest,
    RagSearchRequest,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
