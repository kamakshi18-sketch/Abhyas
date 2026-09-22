"""
Unit tests for Cloud LLM Providers (Gemini, NVIDIA Nemotron, Mock) and LLM Factory.
"""

import pytest
from app.ai.gemini_client import GeminiService
from app.ai.nvidia_client import NvidiaService
from app.ai.mock_client import MockService
from app.ai.factory import create_llm_service, get_llm_service
from app.schemas.interview import Question, AnswerEvaluation, Difficulty


def test_mock_service_structured_generation():
    """Test offline mock service returns compliant schemas."""
    mock = MockService()
    healthy, msg = mock.health_check()
    assert healthy is True

    q = mock.generate_structured("prompt", schema=Question)
    assert isinstance(q, Question)
    assert q.question_number == 1
    assert "System Design" in q.category

    ev = mock.generate_structured("prompt", schema=AnswerEvaluation)
    assert isinstance(ev, AnswerEvaluation)
    assert ev.score == 8.0
    assert ev.metrics.relevance == 8


def test_llm_factory_instantiation():
    """Test LLM factory creates correct provider instances."""
    gemini = create_llm_service(provider="gemini", api_key="dummy_key", model="gemini-1.5-flash")
    assert isinstance(gemini, GeminiService)
    assert gemini.model == "gemini-1.5-flash"

    nvidia = create_llm_service(provider="nvidia", api_key="dummy_key", model="nvidia/llama-3.1-nemotron-70b-instruct")
    assert isinstance(nvidia, NvidiaService)
    assert "nemotron" in nvidia.model

    mock = create_llm_service(provider="mock")
    assert isinstance(mock, MockService)


def test_gemini_missing_api_key_health_check():
    """Test Gemini health check detects missing API key gracefully."""
    service = GeminiService(api_key="")
    healthy, msg = service.health_check()
    assert healthy is False
    assert "missing" in msg.lower()


def test_nvidia_missing_api_key_health_check():
    """Test NVIDIA health check detects missing API key gracefully."""
    service = NvidiaService(api_key="")
    healthy, msg = service.health_check()
    assert healthy is False
    assert "missing" in msg.lower()
