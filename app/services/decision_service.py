"""
Decision Service for Adaptive Interviews.
High-level service interface coordinating DecisionEngine, telemetry tracking, and LLM advice interpretation.
"""

import logging
from typing import Optional
from app.schemas.interview import (
    InterviewConfig,
    InterviewState,
    InterviewDecision,
    DecisionAction,
    AnswerEvaluation,
    StrategyPlan,
)
from app.core.decision_engine import DecisionEngine
from app.ai.ollama_client import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class DecisionService:
    """Service governing interview state updates and decision routing."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.engine = DecisionEngine()

    def initialize_interview_state(self, config: InterviewConfig) -> InterviewState:
        """Initialize a fresh InterviewState for a new interview session."""
        return self.engine.initialize_state(config)

    def evaluate_and_decide(
        self,
        state: InterviewState,
        config: InterviewConfig,
        latest_evaluation: Optional[AnswerEvaluation] = None,
    ) -> InterviewDecision:
        """
        Evaluate current state and determine next strategic action.
        Guarantees safety, topic coverage, and termination invariants.
        """
        decision = self.engine.decide_next_action(
            state=state,
            config=config,
            latest_evaluation=latest_evaluation,
        )
        state.latest_decision = decision
        state.difficulty = decision.target_difficulty
        logger.info(f"Decision Engine Action: [{decision.action.value}] -> Topic: {decision.target_topic} | Difficulty: {decision.target_difficulty.value} | Reason: {decision.reason}")
        return decision

    def generate_strategy_plan(
        self,
        decision: InterviewDecision,
        state: InterviewState,
        config: InterviewConfig,
        question_number: int,
    ) -> StrategyPlan:
        """Translate decision into strategy blueprint for question generation."""
        return self.engine.map_decision_to_strategy(
            decision=decision,
            state=state,
            config=config,
            question_number=question_number,
        )
