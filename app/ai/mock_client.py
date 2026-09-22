"""
Offline Mock LLM Service implementation.
Enables local testing without API keys or local Ollama servers.
"""

from typing import List, Dict, Optional, Type, TypeVar, Tuple
from pydantic import BaseModel

from app.schemas.interview import (
    Question,
    AnswerEvaluation,
    EvaluationMetrics,
    InterviewSummary,
    Difficulty,
)
from app.ai.ollama_client import LLMService

T = TypeVar("T", bound=BaseModel)


class MockService(LLMService):
    """Offline deterministic simulation service."""

    def health_check(self) -> Tuple[bool, str]:
        return True, "Offline Simulation Mode (No external API needed)."

    def list_models(self) -> List[str]:
        return ["mock-simulator-v1"]

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        return "Simulated AI response."

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        if schema == Question:
            return Question(
                question_number=1,
                text="Explain key architectural considerations and trade-offs when designing a scalable system.",
                question_text="Explain key architectural considerations and trade-offs when designing a scalable system.",
                category="System Design & Architecture",
                topic="System Design",
                difficulty=Difficulty.MEDIUM,
                expected_concepts=["Horizontal scaling", "Load balancing", "Data persistence & caching"],
                expected_points=["Horizontal scaling", "Load balancing", "Data persistence & caching"],
                evaluation_criteria=["System scalability intuition", "Trade-off analysis"],
            )  # type: ignore
        elif schema == AnswerEvaluation:
            return AnswerEvaluation(
                score=8.0,
                metrics=EvaluationMetrics(relevance=8, correctness=8, completeness=8, clarity=8, depth=8),
                strengths=["Structured breakdown of components", "Identified key bottlenecks"],
                weaknesses=["Could explore database sharding in more depth"],
                feedback="Strong answer demonstrating practical architectural intuition.",
                suggested_improvement="Incorporate discussion of replication lag and consistency models.",
            )  # type: ignore
        elif schema == InterviewSummary:
            return InterviewSummary(
                overall_score=8.0,
                strengths_summary=["Solid problem solving", "Clear structured communication"],
                weaknesses_summary=["Explore deeper system trade-offs"],
                overall_feedback="Candidate demonstrated high competence across core interview areas.",
                areas_to_improve=["Distributed consensus protocols", "Microservice resiliency"],
            )  # type: ignore

        raise ValueError(f"Unsupported schema in MockService: {schema}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        return "Simulated chat response."
