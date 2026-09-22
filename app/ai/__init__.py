"""
AI / LLM Service package.
"""

from app.ai.ollama_client import (
    LLMService,
    OllamaService,
    LLMServiceError,
    LLMConnectionError,
    LLMValidationError,
)
from app.ai.gemini_client import GeminiService
from app.ai.nvidia_client import NvidiaService
from app.ai.mock_client import MockService
from app.ai.factory import create_llm_service, get_llm_service, set_global_llm_service

__all__ = [
    "LLMService",
    "OllamaService",
    "GeminiService",
    "NvidiaService",
    "MockService",
    "LLMServiceError",
    "LLMConnectionError",
    "LLMValidationError",
    "create_llm_service",
    "get_llm_service",
    "set_global_llm_service",
]
