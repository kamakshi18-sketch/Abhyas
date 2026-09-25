"""
Question Generator engine.
Delegates to QuestionGeneratorService with strategy planning, quality control, and robust structured output.
"""

import logging
from typing import List, Optional
from app.ai.ollama_client import LLMService, get_llm_service
from app.schemas.interview import (
    InterviewConfig,
    Question,
    Difficulty,
    QuestionEvaluationPair,
)
class QuestionGenerator:
    """Core question generator delegating to QuestionGeneratorService."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()
        from app.services.question_generator_service import QuestionGeneratorService
        self.generator_service = QuestionGeneratorService(llm_service=self.llm_service)

    def determine_effective_difficulty(
        self,
        config: InterviewConfig,
        history: Optional[List[QuestionEvaluationPair]] = None,
    ) -> Difficulty:
        """
        Compute effective difficulty for the next question.
        For Phase 3, if not adaptive, returns config.difficulty.
        """
        if config.difficulty != Difficulty.ADAPTIVE:
            return config.difficulty

        if not history:
            return Difficulty.MEDIUM

        last_score = history[-1].evaluation.score
        if last_score >= 8.0:
            return Difficulty.HARD
        elif last_score >= 5.5:
            return Difficulty.MEDIUM
        else:
            return Difficulty.EASY

    def generate_question(
        self,
        config: InterviewConfig,
        question_number: int,
        previous_questions: Optional[List[Question]] = None,
        history: Optional[List[QuestionEvaluationPair]] = None,
        strategy: Optional["StrategyPlan"] = None,
    ) -> Question:
        """
        Generate a structured question by delegating to QuestionGeneratorService.
        """
        return self.generator_service.generate_question(
            config=config,
            question_number=question_number,
            previous_questions=previous_questions,
            strategy=strategy,
        )

