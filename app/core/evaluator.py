"""
Answer Evaluation engine.
Delegates to dedicated AnswerEvaluationService while maintaining backward-compatible API.
"""

import logging
from typing import List, Optional
from app.ai.ollama_client import LLMService, get_llm_service
from app.schemas.interview import (
    InterviewConfig,
    Question,
    AnswerEvaluation,
    QuestionEvaluationPair,
    EvaluationSummary,
    InterviewSummary,
)
from app.services.evaluation_service import AnswerEvaluationService

logger = logging.getLogger(__name__)


class AnswerEvaluator:
    """Evaluates candidate answers and generates interview feedback and summaries."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        evaluation_service: Optional[AnswerEvaluationService] = None,
    ):
        self.llm_service = llm_service or get_llm_service()
        self.evaluation_service = evaluation_service or AnswerEvaluationService(llm_service=self.llm_service)

    def evaluate_answer(
        self,
        config: InterviewConfig,
        question: Question,
        candidate_answer: str,
    ) -> AnswerEvaluation:
        """Evaluate a candidate's answer against the question, rubrics, and criteria."""
        return self.evaluation_service.evaluate_answer(
            config=config,
            question=question,
            candidate_answer=candidate_answer,
        )

    def generate_summary(
        self,
        config: InterviewConfig,
        pairs: List[QuestionEvaluationPair],
    ) -> EvaluationSummary:
        """Synthesize individual evaluations into an overarching executive summary."""
        return self.evaluation_service.generate_summary(
            config=config,
            pairs=pairs,
        )

