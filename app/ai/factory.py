"""
LLM Service Factory.
Provides instantiation, caching, and runtime provider switching (Gemini, NVIDIA Nemotron, Ollama, Mock).
"""

import logging
from typing import Optional
from app.config.settings import get_settings
from app.ai.ollama_client import LLMService, OllamaService
from app.ai.gemini_client import GeminiService
from app.ai.nvidia_client import NvidiaService
from app.ai.mock_client import MockService

logger = logging.getLogger(__name__)

_global_service: Optional[LLMService] = None


def create_llm_service(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMService:
    """Create a new LLMService instance based on the specified provider."""
    settings = get_settings()
    active_provider = (provider or settings.llm_provider).lower().strip()

    if active_provider == "gemini":
        return GeminiService(api_key=api_key or settings.gemini_api_key, model=model or settings.gemini_model)
    elif active_provider in ("nvidia", "nemotron"):
        return NvidiaService(api_key=api_key or settings.nvidia_api_key, model=model or settings.nvidia_model)
    elif active_provider == "mock":
        return MockService()
    else:
        # Default to Ollama
        return OllamaService(model=model or settings.ollama_model)


def get_llm_service(provider: Optional[str] = None) -> LLMService:
    """Retrieve or create singleton LLM service instance."""
    global _global_service
    settings = get_settings()
    target_provider = (provider or settings.llm_provider).lower().strip()

    if _global_service is None:
        _global_service = create_llm_service(provider=target_provider)

    return _global_service


def set_global_llm_service(service: LLMService) -> None:
    """Explicitly set active global LLM service."""
    global _global_service
    _global_service = service
