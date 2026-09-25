"""
LLM Service Factory.
Provides instantiation, caching, and runtime provider switching (Gemini, NVIDIA Nemotron, Ollama, Mock).
Optimized to reuse active client singletons.
"""

import logging
from typing import Optional, Dict, Tuple
from app.config.settings import get_settings
from app.ai.ollama_client import LLMService, OllamaService
from app.ai.gemini_client import GeminiService
from app.ai.nvidia_client import NvidiaService
from app.ai.mock_client import MockService

logger = logging.getLogger(__name__)

_global_service: Optional[LLMService] = None
_service_cache: Dict[Tuple[str, str, str], LLMService] = {}


def create_llm_service(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMService:
    """Create or retrieve a cached LLMService instance based on the specified provider."""
    settings = get_settings()
    active_provider = (provider or settings.llm_provider).lower().strip()
    active_key = (api_key or "").strip()
    active_model = (model or "").strip()

    cache_key = (active_provider, active_key, active_model)
    if cache_key in _service_cache:
        return _service_cache[cache_key]

    if active_provider == "gemini":
        service = GeminiService(api_key=api_key or settings.gemini_api_key, model=model or settings.gemini_model)
    elif active_provider in ("nvidia", "nemotron"):
        service = NvidiaService(api_key=api_key or settings.nvidia_api_key, model=model or settings.nvidia_model)
    elif active_provider == "mock":
        service = MockService()
    else:
        # Default to Ollama
        service = OllamaService(model=model or settings.ollama_model)

    _service_cache[cache_key] = service
    return service


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
