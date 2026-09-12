"""
High-Level LLM Client Adapter for MY_ISSB_Evaluator.
Supports:
1. Google Gemini (Gemini 2.5 Flash / Pro via google-genai)
2. Groq (Ultra-fast Qwen 2.5 72B / Llama 3.3 70B)
3. Local Ollama (Offline Qwen 2.5 / Llama 3.1)
4. OpenAI / DeepSeek / OpenRouter
5. Rich Local Evaluator Fallback (when offline)
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

USER_AGENT = "MY_ISSB_Evaluator/2.0 (Windows NT 10.0; Win64; x64)"


class LLMClient:
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        groq_env_key = os.getenv("GROQ_API_KEY", "").strip()
        gemini_env_key = os.getenv("GEMINI_API_KEY", "").strip()
        openai_env_key = os.getenv("OPENAI_API_KEY", "").strip()

        passed_key = (api_key or "").strip()
        has_groq_key = bool(
            passed_key.startswith("gsk_")
            or "gsk_" in passed_key
            or groq_env_key
        )

        raw_prov = (provider or os.getenv("LLM_PROVIDER", "")).strip().lower()

        # Prioritize Groq by default whenever a Groq key is present
        if has_groq_key and (raw_prov in ("", "auto", "groq") or not provider):
            self.provider = "groq"
            self.api_key = passed_key if passed_key.startswith("gsk_") else (groq_env_key or passed_key)
        elif raw_prov:
            self.provider = raw_prov
            self.api_key = passed_key or groq_env_key or gemini_env_key or openai_env_key or ""
        elif has_groq_key:
            self.provider = "groq"
            self.api_key = groq_env_key or passed_key
        else:
            self.provider = "auto"
            self.api_key = passed_key or gemini_env_key or openai_env_key or ""

        self.model_name = model_name or os.getenv("LLM_MODEL", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "")
        self.last_error: str = ""
        self._groq_cooldown_until: float = 0.0

    def is_configured(self) -> bool:
        """Returns True if a live remote or local model endpoint is configured."""
        if self.provider == "local":
            return False
        if self.provider == "ollama":
            return True
        return bool(self.api_key)

    def get_status_info(self) -> Dict[str, str]:
        if not self.is_configured():
            return {
                "status": "Offline Fallback Mode",
                "detail": "Using local heuristic engine. Add a free Gemini or Groq key in sidebar to enable frontier intelligence.",
                "badge": "warning",
            }
        prov = self.provider
        if prov == "auto":
            prov = "Gemini" if self.api_key.startswith("AIza") else "Groq" if self.api_key.startswith("gsk_") else "OpenAI"

        default_model = "openai/gpt-oss-20b" if prov.lower() == "groq" else "gemini-2.5-flash" if prov.lower() == "gemini" else "Default"
        return {
            "status": "Frontier LLM Active",
            "detail": f"Connected via {prov.upper()} (Model: {self.model_name or default_model})",
            "badge": "success",
        }

    def test_connection(self) -> Tuple[bool, str]:
        """
        Tests live connectivity to the configured model.
        Crucially does NOT fall back to offline templates, so errors are truthfully surfaced to the user.
        """
        if not self.is_configured():
            return False, "No API key or Ollama host configured."

        self.last_error = ""
        test_system = "You are a helpful assistant."
        test_user = "Reply with the exact word 'READY' if you can read this."

        # Groq
        if self.provider == "groq" or (self.provider == "auto" and (self.api_key.startswith("gsk_") or os.getenv("GROQ_API_KEY"))):
            model = self.model_name if self.model_name else "openai/gpt-oss-20b"
            key = os.getenv("GROQ_API_KEY") or self.api_key
            res = self._call_openai_compatible(
                test_system, test_user, key, "https://api.groq.com/openai/v1", model, 0.1
            )
            if res:
                return True, f"Connected to Groq ({model})! Live inference active."
            return False, f"Groq connection failed: {self.last_error or 'Could not verify API key.'}"

        # Gemini
        elif self.provider == "gemini" or (self.provider == "auto" and not self.api_key.startswith("gsk_")):
            key = os.getenv("GEMINI_API_KEY") or self.api_key
            res = self._call_gemini(test_system, test_user, key, 0.1)
            if res:
                return True, f"Connected to Gemini ({self.model_name or 'gemini-2.5-flash'})! Live inference active."
            return False, f"Gemini connection failed: {self.last_error or 'Could not verify API key.'}"

        # Ollama
        elif self.provider == "ollama":
            url = self.base_url or "http://localhost:11434/v1"
            model = self.model_name or "qwen2.5:7b"
            res = self._call_openai_compatible(test_system, test_user, "ollama", url, model, 0.1)
            if res:
                return True, f"Connected to local Ollama ({model})! Live inference active."
            return False, f"Ollama connection failed: {self.last_error or f'Could not reach {url}'}"

        # OpenAI / DeepSeek
        elif self.provider in ("openai", "deepseek"):
            url = self.base_url or "https://api.openai.com/v1"
            model = self.model_name or "gpt-4o-mini"
            res = self._call_openai_compatible(test_system, test_user, self.api_key, url, model, 0.1)
            if res:
                return True, f"Connected to {self.provider.upper()} ({model})! Live inference active."
            return False, f"{self.provider.upper()} connection failed: {self.last_error or 'Could not reach endpoint.'}"

        return False, f"Unknown or unconfigured provider: {self.provider}"

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
    ) -> str:
        """Generates text using the best available configured LLM provider."""
        # 1. Groq Provider (Fast Llama / GPT-OSS / Qwen)
        is_groq = self.provider == "groq" or (self.provider == "auto" and (self.api_key.startswith("gsk_") or os.getenv("GROQ_API_KEY")))
        groq_key = os.getenv("GROQ_API_KEY") or (self.api_key if is_groq else "")
        import time
        if groq_key and time.time() >= self._groq_cooldown_until:
            model = self.model_name if self.model_name else "openai/gpt-oss-20b"
            res = self._call_openai_compatible(
                system_prompt,
                user_prompt,
                groq_key,
                base_url="https://api.groq.com/openai/v1",
                model=model,
                temperature=temperature,
            )
            if res:
                return res

        # 2. Google Gemini
        is_gemini = self.provider == "gemini" or (self.provider == "auto" and not self.api_key.startswith("gsk_") and (self.api_key or os.getenv("GEMINI_API_KEY")))
        gemini_key = os.getenv("GEMINI_API_KEY") or (self.api_key if is_gemini else "")
        if gemini_key:
            res = self._call_gemini(system_prompt, user_prompt, gemini_key, temperature)
            if res:
                return res

        # 3. Local Ollama
        if self.provider == "ollama" or (self.base_url and "localhost:11434" in self.base_url):
            url = self.base_url or "http://localhost:11434/v1"
            model = self.model_name or "qwen2.5:7b"
            res = self._call_openai_compatible(
                system_prompt,
                user_prompt,
                api_key="ollama",
                base_url=url,
                model=model,
                temperature=temperature,
            )
            if res:
                return res

        # 4. Standard OpenAI / DeepSeek / Custom endpoint
        is_openai = self.provider in ("openai", "deepseek") or bool(os.getenv("OPENAI_API_KEY"))
        openai_key = os.getenv("OPENAI_API_KEY") or (self.api_key if is_openai else "")
        if openai_key or self.base_url:
            url = self.base_url or "https://api.openai.com/v1"
            model = self.model_name or "gpt-4o-mini"
            res = self._call_openai_compatible(
                system_prompt,
                user_prompt,
                openai_key or self.api_key,
                base_url=url,
                model=model,
                temperature=temperature,
            )
            if res:
                return res

        # 5. Deterministic High-Yield Local Fallback
        return self._local_fallback_response(system_prompt, user_prompt)

    def _call_gemini(self, system_prompt: str, user_prompt: str, api_key: str, temperature: float) -> Optional[str]:
        # Try modern google-genai
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            model = self.model_name or "gemini-2.5-flash"
            response = client.models.generate_content(
                model=model,
                contents=f"System Instruction:\n{system_prompt}\n\nUser Input:\n{user_prompt}",
            )
            if response and hasattr(response, "text") and response.text:
                self.last_error = ""
                return response.text
        except Exception as e:
            self.last_error = str(e)

        # Try google.generativeai legacy
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel(
                model_name=self.model_name or "gemini-1.5-flash",
                system_instruction=system_prompt,
            )
            response = model.generate_content(user_prompt)
            if response and hasattr(response, "text") and response.text:
                self.last_error = ""
                return response.text
        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"Gemini error: {e}")
        return None

    def _call_openai_compatible(
        self,
        system_prompt: str,
        user_prompt: str,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float,
    ) -> Optional[str]:
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'no-key'}",
            "User-Agent": USER_AGENT,
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                self.last_error = ""
                return data["choices"][0]["message"]["content"]
            elif resp.status_code == 404 and "groq.com" in endpoint and model != "openai/gpt-oss-20b":
                logger.info(f"Model '{model}' not found on Groq, retrying with 'openai/gpt-oss-20b'...")
                payload["model"] = "openai/gpt-oss-20b"
                retry_resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
                if retry_resp.status_code == 200:
                    data = retry_resp.json()
                    self.last_error = ""
                    return data["choices"][0]["message"]["content"]
                resp = retry_resp
            elif resp.status_code == 429 and "groq.com" in endpoint:
                err_text = resp.text.lower()
                if "tpd" in err_text or "tokens per day" in err_text or "daily" in err_text:
                    import time
                    self._groq_cooldown_until = time.time() + 180
                    logger.warning("Groq daily token limit (TPD) reached. Cooling down Groq requests for 3 minutes...")
                    self.last_error = f"HTTP 429: Groq daily token limit reached ({resp.text})"
                    return None
                import time
                logger.info("Groq TPM rate limit reached (429). Waiting 2 seconds to replenish token bucket...")
                time.sleep(2)
                retry_resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
                if retry_resp.status_code == 200:
                    data = retry_resp.json()
                    self.last_error = ""
                    return data["choices"][0]["message"]["content"]
                resp = retry_resp

            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            self.last_error = f"HTTP {resp.status_code}: {err_msg}"
            logger.warning(f"OpenAI-compatible call error ({endpoint}): {self.last_error}")
            return None
        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"OpenAI-compatible call exception ({endpoint}): {e}")
            return None

    def _local_fallback_response(self, system_prompt: str, user_prompt: str) -> str:
        """Rich local fallback that extracts from question bank and structured pools."""
        # Follow-up generation
        if "follow-up" in system_prompt.lower() or "follow_up" in system_prompt.lower():
            options = []
            in_options_section = False
            for line in user_prompt.splitlines():
                clean = line.strip()
                if "follow-up options:" in clean.lower() or "follow_up_pool" in clean.lower():
                    in_options_section = True
                    continue
                if in_options_section and clean.startswith("- "):
                    options.append(clean.lstrip("- ").strip())
                elif in_options_section and clean.startswith("Formulate"):
                    in_options_section = False

            if options:
                return options[0]

            if len(user_prompt.strip()) < 50:
                return "That answer was rather brief. Could you give me a specific, concrete example from your own experience to back that up?"
            elif "team" in user_prompt.lower() or "led" in user_prompt.lower():
                return "What specific personal responsibility did you shoulder when friction arose within that group?"
            else:
                return "Understood. How would you handle a situation where circumstances completely contradicted your initial assumption?"


        # Interview questioning
        if "question bank question:" in user_prompt.lower() or "issb" in system_prompt.lower():
            for line in user_prompt.splitlines():
                if "question bank question:" in line.lower():
                    raw_q = line.split(":", 1)[1].strip()
                    return f"{raw_q}\n(Please take your time and answer clearly, grounding your response in your own real experiences.)"
            lines = [l for l in user_prompt.splitlines() if l.strip()]
            q_line = lines[0] if lines else "Could you tell me about yourself?"
            return f"{q_line}\n(Please take your time and answer clearly.)"

        return "Understood. Let us proceed to the next area."
