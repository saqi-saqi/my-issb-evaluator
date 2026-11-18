"""
Shared pytest configuration for the MY_ISSB_Evaluator test suite.

Forces deterministic, offline, rate-limit-free conditions for every test:
- The AI client runs in offline mode (no LLM network calls) so local runs
  behave exactly like CI, where GROQ_API_KEY is never set.
- Rate-limit environment variables are relaxed so the shared TestClient IP
  is never throttled across the suite (individual tests that exercise the
  limiter override these locally).
"""

import pytest

import backend.main as backend_main


@pytest.fixture(autouse=True)
def _deterministic_test_environment(monkeypatch):
    monkeypatch.setattr(backend_main.ai_client, "api_key", "")
    monkeypatch.setenv("LLM_OPS_PER_MINUTE", "1000")
    monkeypatch.setenv("SESSIONS_PER_DAY", "1000")
    yield
