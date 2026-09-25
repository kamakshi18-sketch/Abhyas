"""
Decision Service (Phase 5).
Orchestrates adaptive state lifecycle, links Answer Evaluations with the Adaptive Decision Engine,
and translates InterviewDecisions into StrategyPlans for Question Generation.
"""

import logging
from typing import Optional, List
from app.schemas.interview import (
    InterviewConfig,
    InterviewState,
    InterviewDecision,
    DecisionAction,
    StrategyPlan,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    Difficulty,
    QuestionType,
)
from app.ai.ollama_client import LLMService
from app.core.decision_engine import AdaptiveDecisionEngine
from app.core.question_strategy import QuestionStrategyService

logger = logging.getLogger(__name__)


class DecisionService:
    """Service governing state transitions and pedagogical decision-making."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        decision_engine: Optional[AdaptiveDecisionEngine] = None,
    ):
        self.llm_service = llm_service
        self.decision_engine = decision_engine or AdaptiveDecisionEngine(llm_service=self.llm_service)

    def initialize_state(self, config: InterviewConfig) -> InterviewState:
        """
        Create a clean, initialized InterviewState from InterviewConfig.
        """
        all_topics = list(config.topics) if config.topics else [config.role or "Software Engineering"]
        initial_diff = Difficulty.MEDIUM if config.difficulty == Difficulty.ADAPTIVE else config.difficulty
        
        return InterviewState(
            current_topic=all_topics[0] if all_topics else "General",
            topics_covered=[],
            topics_remaining=list(all_topics),
            strengths=[],
            weaknesses=[],
            previous_questions=[],
            previous_answers=[],
            previous_evaluations=[],
            difficulty=initial_diff,
            question_count=0,
            interview_progress=0.0,
            max_questions=config.num_questions,
            consecutive_high_scores=0,
            consecutive_low_scores=0,
            topic_question_counts={},
        )

    def record_interaction(
        self,
        state: InterviewState,
        question: Question,
        answer: CandidateAnswer,
        evaluation: AnswerEvaluation,
    ) -> InterviewState:
        """
        Update state with the latest question, answer submission, and evaluation.
        """
        state.update(question=question, answer=answer, evaluation=evaluation)
        logger.info(
            f"Updated InterviewState: Q{state.question_count}/{state.max_questions} | "
            f"Topic: {state.current_topic} | Score: {evaluation.score:.1f} | "
            f"Progress: {state.interview_progress * 100:.0f}%"
        )
        return state

    def decide_next_step(
        self,
        state: InterviewState,
        config: InterviewConfig,
    ) -> InterviewDecision:
        """
        Execute Adaptive Decision Engine to determine the next interview action.
        """
        decision = self.decision_engine.decide_next_action(state=state, config=config)
        logger.info(
            f"Decision Engine Action: [{decision.action.value}] -> Topic: '{decision.target_topic}' | "
            f"Diff: {decision.target_difficulty.value} | Reason: {decision.reason}"
        )
        return decision

    def create_strategy_from_decision(
        self,
        decision: InterviewDecision,
        question_number: int,
        config: InterviewConfig,
    ) -> StrategyPlan:
        """
        Translate an InterviewDecision into an executable StrategyPlan for QuestionGeneratorService.
        """
        q_type = decision.suggested_question_type or QuestionType.TECHNICAL
        category = f"{config.interview_type.value} - {decision.target_topic}"

        return StrategyPlan(
            question_number=question_number,
            question_type=q_type,
            target_topic=decision.target_topic,
            category=category,
            difficulty=decision.target_difficulty,
            objective=decision.objective,
        )
