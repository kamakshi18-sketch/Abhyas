"""
NVIDIA Nemotron (NVIDIA NIM) API LLM Service implementation.
Provides structured generation, text generation, and health checks via OpenAI-compatible NIM endpoints.
Optimized with persistent connection pooling and instrumentation.
"""

import json
import re
import logging
from typing import List, Dict, Optional, Type, TypeVar, Tuple
import httpx
from pydantic import BaseModel, ValidationError

from app.config.settings import get_settings
from app.ai.ollama_client import LLMService, LLMConnectionError, LLMValidationError
from app.performance.timers import Timer

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class NvidiaService(LLMService):
    """NVIDIA NIM (Nemotron) API implementation of LLMService."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else (settings.nvidia_api_key or "")
        self.model = model or settings.nvidia_model or "nvidia/llama-3.1-nemotron-70b-instruct"
        self.base_url = (base_url or settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.timeout = timeout or settings.llm_timeout_seconds
        self.default_temperature = settings.llm_temperature
        self.max_retries = settings.max_llm_retries
        self._client: Optional[httpx.Client] = None
        logger.info(f"Initialized NvidiaService with model='{self.model}' at '{self.base_url}'")

    def _get_client(self) -> httpx.Client:
        """Get or lazily initialize reusable httpx.Client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    def close(self) -> None:
        """Close underlying HTTP client if open."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __del__(self):
        self.close()

    def set_model(self, model_name: str) -> None:
        """Dynamically switch NVIDIA Nemotron model."""
        self.model = model_name
        logger.info(f"Switched NVIDIA model to: {model_name}")

    def set_api_key(self, key: str) -> None:
        """Update active API key."""
        self.api_key = key.strip()

    def health_check(self) -> Tuple[bool, str]:
        """Check if NVIDIA API key is configured and endpoint responds."""
        if not self.api_key:
            return False, "NVIDIA API key is missing. Set NVIDIA_API_KEY in .env or enter it in Setup."

        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            client = self._get_client()
            resp = client.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                return True, f"NVIDIA NIM is connected ({self.model} ready)."
            elif resp.status_code == 401 or resp.status_code == 403:
                return False, "NVIDIA API authentication failed: Invalid or expired API key."
            else:
                return False, f"NVIDIA API returned status {resp.status_code}: {resp.text[:150]}"
        except Exception as e:
            return False, f"Cannot reach NVIDIA NIM endpoint: {str(e)}"

    def list_models(self) -> List[str]:
        """Return popular Nemotron and related models available on NVIDIA NIM."""
        return [
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "nvidia/nemotron-4-340b-instruct",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "meta/llama-3.1-70b-instruct",
            "mistralai/mistral-large-2-instruct",
        ]

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate plain text using NVIDIA NIM chat completions."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self.chat(messages, temperature=temperature)

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """Generate structured JSON adhering to Pydantic schema using NVIDIA NIM."""
        if not self.api_key:
            raise LLMConnectionError("NVIDIA API key is not configured.")

        temp = temperature if temperature is not None else self.default_temperature
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        json_system = (system or "") + "\n\nCRITICAL: Respond ONLY with a valid JSON object matching the required schema. Do not output markdown fences or commentary."

        messages = [
            {"role": "system", "content": json_system},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "response_format": {"type": "json_object"},
        }

        client = self._get_client()
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                with Timer("nvidia_structured_request"):
                    resp = client.post(url, headers=headers, json=payload, timeout=self.timeout)
                if resp.status_code != 200:
                    raise LLMConnectionError(f"NVIDIA API error ({resp.status_code}): {resp.text}")

                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"].strip()
                cleaned_json = self._extract_json_string(raw_text)
                return schema.model_validate_json(cleaned_json)

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.warning(f"NVIDIA structured output parsing error on attempt {attempt + 1}: {e}")
                payload["messages"].append(
                    {"role": "user", "content": f"Fix JSON validation errors: {e}. Output clean valid JSON matching the schema."}
                )
            except Exception as e:
                logger.error(f"NVIDIA connection error: {e}")
                raise LLMConnectionError(f"NVIDIA API call failed: {e}") from e

        raise LLMValidationError(
            f"Failed to produce valid structured output for schema '{schema.__name__}' after {self.max_retries + 1} attempts. Error: {last_error}"
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Chat interaction via NVIDIA NIM OpenAI-compatible endpoint."""
        if not self.api_key:
            raise LLMConnectionError("NVIDIA API key is not configured.")

        temp = temperature if temperature is not None else self.default_temperature
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
        }

        try:
            client = self._get_client()
            with Timer("nvidia_chat_request"):
                resp = client.post(url, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                raise LLMConnectionError(f"NVIDIA API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"NVIDIA chat error: {e}")
            raise LLMConnectionError(f"NVIDIA chat failed: {e}") from e

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
