"""
Clean, single-provider AI client for MY_ISSB_Evaluator using Groq.
Exposes generate_text() and generate_json() with robust error handling and fallback resilience.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
FALLBACK_GROQ_MODEL = "openai/gpt-oss-20b"


class AIClient:
    """Consolidated Groq AI Client for text generation and structured JSON extraction."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = FALLBACK_GROQ_MODEL,
        timeout: float = 30.0,
    ):
        self.api_key = (api_key or os.getenv("GROQ_API_KEY", "")).strip()
        env_model = os.getenv("GROQ_MODEL") or os.getenv("LLM_MODEL") or DEFAULT_GROQ_MODEL
        self.model = (model or env_model).strip()
        self.fallback_model = fallback_model
        self.timeout = timeout
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        if self.api_key:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key, timeout=self.timeout, max_retries=2)
            except Exception as e:
                logger.warning("Failed to initialize Groq client: %s", e)
                self._client = None
        else:
            self._client = None

    def is_available(self) -> bool:
        """Returns True if a valid API key is present."""
        return bool(self.api_key)

    def test_connection(self) -> tuple[bool, str]:
        """Tests live connectivity to the Groq API."""
        if not self.api_key:
            return False, "Groq API key is not configured in .env (GROQ_API_KEY)"
        if not self._client:
            self._init_client()
            if not self._client:
                return False, "Failed to initialize Groq SDK"
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=60,
            )
            return True, f"Connected to Groq ({self.model})"
        except Exception as e:
            # Try fallback model
            if self.fallback_model and self.fallback_model != self.model:
                try:
                    self._client.chat.completions.create(
                        model=self.fallback_model,
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=60,
                    )
                    self.model = self.fallback_model
                    return True, f"Connected to Groq via fallback ({self.fallback_model})"
                except Exception:
                    pass
            return False, f"Groq connection error: {str(e)}"

    def generate_text(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> str:
        """Generates plain text response using Groq."""
        if not self._client:
            logger.warning("Groq client unavailable; returning empty response")
            return ""

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Try primary model first, then fallback model
        for candidate_model in [self.model, self.fallback_model]:
            if not candidate_model:
                continue
            try:
                response = self._client.chat.completions.create(
                    model=candidate_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (response.choices[0].message.content or "").strip()
            except Exception as exc:
                logger.warning("Groq request failed on model %s: %s", candidate_model, exc)

        return ""

    def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2500,
    ) -> Dict[str, Any]:
        """Generates structured JSON response with defensive Markdown/block parsing."""
        if not self._client:
            logger.warning("Groq client unavailable for JSON generation")
            return {}

        messages: List[Dict[str, str]] = []
        sys_msg = (system or "") + "\nRespond with valid JSON only. Do not include extra conversational text."
        messages.append({"role": "system", "content": sys_msg.strip()})
        messages.append({"role": "user", "content": prompt})

        for candidate_model in [self.model, self.fallback_model]:
            if not candidate_model:
                continue
            try:
                response = self._client.chat.completions.create(
                    model=candidate_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                raw = (response.choices[0].message.content or "").strip()
                return self._parse_json_defensive(raw)
            except Exception as exc:
                logger.warning("Groq JSON generation failed on model %s: %s", candidate_model, exc)

        return {}

    @staticmethod
    def _parse_json_defensive(raw: str) -> Dict[str, Any]:
        """Defensively parses JSON string even if wrapped in markdown code blocks."""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Match markdown ```json ... ``` blocks
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Find first '{' and last '}'
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from AI response: %s", raw[:200])
        return {}


# Module-level singleton
ai_client = AIClient()
