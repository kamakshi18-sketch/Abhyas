"""
Pytest configuration and shared test fixtures.
"""

import pytest
from typing import List, Dict, Optional, Type, TypeVar
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel

from app.database.database import Base
from app.ai.ollama_client import LLMService
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    Question,
    CandidateAnswer,
    EvaluationMetrics,
    AnswerEvaluation,
    InterviewSummary,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMService(LLMService):
    """Mock LLM Service implementation for deterministic unit testing."""

    def __init__(self):
        self.healthy = True
        self.models = ["qwen2.5:7b", "nemotron-mini:latest"]
        self.generated_questions: List[Question] = []
        self.generated_evaluations: List[AnswerEvaluation] = []
        self.generated_summaries: List[InterviewSummary] = []

    def health_check(self):
        if self.healthy:
            return True, "Mock Ollama is healthy and ready."
        return False, "Mock Ollama is offline."

    def list_models(self) -> List[str]:
        return self.models

    def generate(self, prompt: str, system: Optional[str] = None, temperature: Optional[float] = None) -> str:
        return "Mock plain text response from LLM."

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        if schema == Question:
            q = Question(
                question_number=1,
                text="Explain Python memory management and the GIL.",
                question_text="Explain Python memory management and the GIL.",
                category="Python Internals",
                topic="Python",
                difficulty=Difficulty.MEDIUM,
                expected_concepts=["Reference counting", "Garbage collection cycles", "GIL synchronization"],
                expected_points=["Reference counting", "Garbage collection cycles", "GIL synchronization"],
                evaluation_criteria=["Reference counting depth", "GIL trade-offs"],
            )
            self.generated_questions.append(q)
            return q  # type: ignore

        elif schema == AnswerEvaluation:
            ev = AnswerEvaluation(
                score=8.5,
                metrics=EvaluationMetrics(
                    relevance=9,
                    correctness=8,
                    completeness=8,
                    clarity=9,
                    depth=8,
                ),
                strengths=["Clear explanation of reference counting", "Mentioned cyclic GC"],
                weaknesses=["Did not elaborate on free-threaded Python 3.13+"],
                feedback="Strong technical answer demonstrating solid foundational understanding.",
                suggested_improvement="Mention generational collection heuristics and recent PEP improvements.",
            )
            self.generated_evaluations.append(ev)
            return ev  # type: ignore

        elif schema == InterviewSummary:
            summ = InterviewSummary(
                overall_score=8.2,
                strengths_summary=["Solid Python core knowledge", "Strong problem-solving framework"],
                weaknesses_summary=["Could provide deeper system-level edge cases"],
                overall_feedback="Candidate performed well across technical and architectural questions.",
                areas_to_improve=["Deep dive into concurrency internals"],
            )
            self.generated_summaries.append(summ)
            return summ  # type: ignore

        raise ValueError(f"Unsupported schema in MockLLMService: {schema}")

    def chat(self, messages: List[Dict[str, str]], temperature: Optional[float] = None) -> str:
        return "Mock chat response."


@pytest.fixture
def mock_llm() -> MockLLMService:
    """Fixture providing a mock LLM service."""
    return MockLLMService()


@pytest.fixture
def sample_config() -> InterviewConfig:
    """Fixture providing a standard interview configuration."""
    return InterviewConfig(
        candidate_name="Jane Doe",
        role="Senior Backend Engineer",
        experience_level=ExperienceLevel.TWO_TO_FIVE,
        interview_type=InterviewType.TECHNICAL,
        difficulty=Difficulty.HARD,
        num_questions=3,
    )


@pytest.fixture
def db_session():
    """In-memory SQLite database session fixture for isolated testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
