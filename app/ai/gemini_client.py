"""
Google Gemini API LLM Service implementation.
Provides structured generation, text generation, and health checks via Gemini REST API.
"""

import json
import re
import logging
from typing import List, Dict, Optional, Type, TypeVar, Tuple
import httpx
from pydantic import BaseModel, ValidationError

from app.config.settings import get_settings
from app.ai.ollama_client import LLMService, LLMConnectionError, LLMValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiService(LLMService):
    """Google Gemini API implementation of LLMService."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else (settings.gemini_api_key or "")
        self.model = model or settings.gemini_model or "gemini-3.6-flash"
        self.timeout = timeout or settings.llm_timeout_seconds
        self.default_temperature = settings.llm_temperature
        self.max_retries = settings.max_llm_retries
        logger.info(f"Initialized GeminiService with model='{self.model}'")

    def set_model(self, model_name: str) -> None:
        """Dynamically switch Gemini model (e.g. gemini-1.5-flash -> gemini-2.0-flash)."""
        self.model = model_name
        logger.info(f"Switched Gemini model to: {model_name}")

    def set_api_key(self, key: str) -> None:
        """Update active API key."""
        self.api_key = key.strip()

    def health_check(self) -> Tuple[bool, str]:
        """Check if Gemini API key is configured and can reach the service."""
        if not self.api_key:
            return False, "Google Gemini API key is missing. Set GEMINI_API_KEY in .env or enter it in Setup."

        url = f"{self.BASE_URL}/models?key={self.api_key}"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return True, f"Google Gemini is connected ({self.model} ready)."
                elif resp.status_code == 400 or resp.status_code == 403:
                    err_json = resp.json().get("error", {})
                    return False, f"Gemini API authentication failed: {err_json.get('message', 'Invalid API key')}"
                else:
                    return False, f"Gemini API returned status {resp.status_code}: {resp.text[:150]}"
        except Exception as e:
            return False, f"Cannot reach Google Gemini API: {str(e)}"

    def list_models(self) -> List[str]:
        """Return popular available Gemini models."""
        return [
            "gemini-3.1-flash-lite",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
        ]

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate plain text using Gemini API."""
        if not self.api_key:
            raise LLMConnectionError("Google Gemini API key is not configured.")

        temp = temperature if temperature is not None else self.default_temperature
        models_to_try = list(dict.fromkeys([self.model, "gemini-3.1-flash-lite", "gemini-3.7-flash", "gemini-3.6-flash"]))

        for model_candidate in models_to_try:
            url = f"{self.BASE_URL}/models/{model_candidate}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temp},
            }
            if system:
                payload["system_instruction"] = {"parts": [{"text": system}]}

            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return text.strip()
                    elif resp.status_code in (404, 429, 503):
                        logger.warning(f"Gemini model {model_candidate} returned {resp.status_code}. Fast-switching to next model...")
                        continue
                    else:
                        logger.warning(f"Gemini model {model_candidate} error ({resp.status_code}): {resp.text[:120]}")
                        continue
            except Exception as e:
                logger.warning(f"Gemini request exception with {model_candidate}: {e}")
                continue

        raise LLMConnectionError(f"Failed to generate text with all Gemini model candidates: {models_to_try}")

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """Generate structured JSON adhering to the Pydantic schema using Gemini native JSON mode."""
        if not self.api_key:
            raise LLMConnectionError("Google Gemini API key is not configured.")

        temp = temperature if temperature is not None else self.default_temperature
        
        # Build schema guidelines for exact field matching
        try:
            schema_props = list(schema.model_json_schema().get("properties", {}).keys())
            schema_hint = f"Required JSON fields: {', '.join(schema_props)}"
        except Exception:
            schema_hint = ""

        json_system = (
            (system or "")
            + f"\n\nCRITICAL: Respond ONLY with a valid JSON object matching the schema. {schema_hint}. Do not wrap in markdown or add conversational filler."
        )

        models_to_try = list(dict.fromkeys([self.model, "gemini-3.1-flash-lite", "gemini-3.7-flash", "gemini-3.6-flash"]))

        last_error = None
        for model_candidate in models_to_try:
            candidate_url = f"{self.BASE_URL}/models/{model_candidate}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temp,
                    "response_mime_type": "application/json",
                },
                "system_instruction": {"parts": [{"text": json_system}]},
            }

            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(candidate_url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise LLMValidationError(f"No candidates returned from {model_candidate}: {data}")
                        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        cleaned_json = self._extract_json_string(raw_text)
                        return schema.model_validate_json(cleaned_json)
                    elif resp.status_code in (404, 429, 503):
                        logger.warning(f"Model {model_candidate} returned HTTP {resp.status_code}. Immediately trying next candidate...")
                        last_error = f"HTTP {resp.status_code} from {model_candidate}"
                        continue
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
                        logger.warning(f"Model {model_candidate} unexpected status {resp.status_code}: {resp.text[:120]}")
                        continue
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.warning(f"Model {model_candidate} JSON validation error: {e}. Trying fallback model...")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_candidate} network/request error: {e}. Trying next candidate...")
                continue

        raise LLMValidationError(
            f"Failed to produce valid structured output for schema '{schema.__name__}'. Last error: {last_error}"
        )


    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Chat interaction using Gemini format."""
        if not self.api_key:
            raise LLMConnectionError("Google Gemini API key is not configured.")

        temp = temperature if temperature is not None else self.default_temperature
        url = f"{self.BASE_URL}/models/{self.model}:generateContent?key={self.api_key}"

        # Convert standard OpenAI-style messages to Gemini contents format
        contents = []
        for m in messages:
            role = "user" if m.get("role") in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temp},
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    raise LLMConnectionError(f"Gemini chat error ({resp.status_code}): {resp.text}")
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            raise LLMConnectionError(f"Gemini chat failed: {e}") from e

    @staticmethod
    def _extract_json_string(text: str) -> str:
        """Extract and clean raw JSON from LLM output."""
        text = text.strip()
        json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if json_block_match:
            text = json_block_match.group(1).strip()
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            text = text[brace_start : brace_end + 1]
        return text
