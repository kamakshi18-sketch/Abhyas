"""
LLM Service abstraction and Ollama implementation.
Provides robust text generation, structured JSON extraction, and connection monitoring.
"""

import json
import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Type, TypeVar, Tuple
from pydantic import BaseModel, ValidationError
import ollama

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMServiceError(Exception):
    """Base exception for LLM operations."""
    pass


class LLMConnectionError(LLMServiceError):
    """Raised when Ollama server is unreachable or offline."""
    pass


class LLMValidationError(LLMServiceError):
    """Raised when LLM output fails schema validation."""
    pass


class LLMService(ABC):
    """Abstract interface for LLM operations across the application."""

    @abstractmethod
    def health_check(self) -> Tuple[bool, str]:
        """Verify LLM service availability. Returns (is_healthy, message)."""
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """List models currently available in the runtime."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate raw text response."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """Generate structured response validated against a Pydantic schema."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Multi-turn chat interaction."""
        pass


class OllamaService(LLMService):
    """Ollama-backed implementation of LLMService."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.llm_timeout_seconds
        self.default_temperature = settings.llm_temperature
        self.max_retries = settings.max_llm_retries
        self._client = ollama.Client(host=self.host)
        logger.info(f"Initialized OllamaService with host='{self.host}', model='{self.model}'")

    def set_model(self, model_name: str) -> None:
        """Dynamically update model target (e.g. switching between Qwen and Nemotron)."""
        self.model = model_name
        logger.info(f"Switched Ollama model to: {model_name}")

    def health_check(self) -> Tuple[bool, str]:
        """Check if Ollama server is responding and if configured model is available."""
        try:
            models_response = self._client.list()
            # Extract available model tags
            available_models: List[str] = []
            if hasattr(models_response, "models"):
                for m in models_response.models:
                    model_name = getattr(m, "model", None) or getattr(m, "name", "")
                    if model_name:
                        available_models.append(model_name)
            elif isinstance(models_response, dict) and "models" in models_response:
                available_models = [m.get("name", "") for m in models_response["models"]]

            if not available_models:
                return (
                    True,
                    f"Ollama is connected at {self.host}, but no models are installed yet. Run `ollama pull {self.model}`.",
                )

            # Check if current model is in available models (matching prefix or tag)
            model_found = any(
                self.model == m or self.model.split(":")[0] == m.split(":")[0]
                for m in available_models
            )

            if model_found:
                return True, f"Ollama is connected ({self.model} ready)."
            else:
                return (
                    True,
                    f"Ollama connected. Active model '{self.model}' not found in installed: {', '.join(available_models[:3])}...",
                )

        except Exception as e:
            err_msg = f"Cannot reach Ollama at {self.host}. Please ensure Ollama is running. Error: {str(e)}"
            logger.warning(err_msg)
            return False, err_msg

    def list_models(self) -> List[str]:
        """Retrieve list of available model names."""
        try:
            resp = self._client.list()
            models: List[str] = []
            if hasattr(resp, "models"):
                for m in resp.models:
                    name = getattr(m, "model", None) or getattr(m, "name", "")
                    if name:
                        models.append(name)
            elif isinstance(resp, dict) and "models" in resp:
                models = [m.get("name", "") for m in resp["models"]]
            return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate plain text from prompt."""
        temp = temperature if temperature is not None else self.default_temperature
        try:
            options = {"temperature": temp}
            response = self._client.generate(
                model=self.model,
                prompt=prompt,
                system=system or "",
                options=options,
            )
            return response.get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            raise LLMConnectionError(f"Failed to generate text with Ollama model '{self.model}': {e}") from e

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """
        Generate structured JSON output adhering to the provided Pydantic schema.
        Handles JSON formatting requests, code fence stripping, and automatic retries.
        """
        temp = temperature if temperature is not None else self.default_temperature

        # Augment system instructions with explicit JSON requirement and schema representation
        json_system = (system or "") + "\n\nCRITICAL: Respond ONLY with valid JSON matching the expected structure. Do not wrap in markdown or include conversational text."

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Use format="json" for models supporting native JSON mode in Ollama
                options = {"temperature": temp}
                resp = self._client.generate(
                    model=self.model,
                    prompt=prompt,
                    system=json_system,
                    format="json",
                    options=options,
                )
                raw_text = resp.get("response", "").strip()
                cleaned_json = self._extract_json_string(raw_text)
                parsed_obj = schema.model_validate_json(cleaned_json)
                return parsed_obj

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.warning(
                    f"Structured output parse error on attempt {attempt + 1}/{self.max_retries + 1}: {e}\nRaw output: {raw_text[:200]}"
                )
                # If retry available, adjust prompt to point out json issue
                prompt = (
                    f"{prompt}\n\n[Previous response had syntax or validation errors: {str(e)}. "
                    f"Please output clean, strictly valid JSON matching the schema.]"
                )
            except Exception as e:
                logger.error(f"Ollama connection error during structured generation: {e}")
                raise LLMConnectionError(f"LLM connection error: {e}") from e

        raise LLMValidationError(
            f"Failed to produce valid structured output for schema '{schema.__name__}' after {self.max_retries + 1} attempts. Error: {last_error}"
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Chat conversation endpoint."""
        temp = temperature if temperature is not None else self.default_temperature
        try:
            options = {"temperature": temp}
            response = self._client.chat(
                model=self.model,
                messages=messages,
                options=options,
            )
            msg = response.get("message", {})
            return msg.get("content", "").strip()
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise LLMConnectionError(f"Failed during Ollama chat: {e}") from e

    @staticmethod
    def _extract_json_string(text: str) -> str:
        """Extract and clean raw JSON from LLM output, handling markdown code blocks."""
        text = text.strip()

        # Handle ```json ... ``` code blocks
        json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if json_block_match:
            text = json_block_match.group(1).strip()

        # Handle text with leading or trailing non-json characters: find outermost { ... }
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            text = text[brace_start : brace_end + 1]

        return text


_global_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Retrieve singleton LLM service instance."""
    global _global_llm_service
    if _global_llm_service is None:
        _global_llm_service = OllamaService()
    return _global_llm_service
