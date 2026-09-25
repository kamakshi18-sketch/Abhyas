"""
Follow-Up Service (Phase 6).
Coordinates candidate answer analysis, FollowUpPlan formulation, and contextual follow-up question generation.
"""

import logging
from typing import Optional
from app.schemas.interview import (
    InterviewConfig,
    Question,
    AnswerEvaluation,
    FollowUpType,
    FollowUpPlan,
)
from app.ai.ollama_client import LLMService
from app.core.followup_engine import FollowUpEngine

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service governing follow-up inquiry, anchoring, and generation."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        followup_engine: Optional[FollowUpEngine] = None,
    ):
        self.llm_service = llm_service
        self.followup_engine = followup_engine or FollowUpEngine(llm_service=self.llm_service)

    def plan_follow_up(
        self,
        parent_question: Question,
        candidate_answer: str,
        config: InterviewConfig,
        evaluation: Optional[AnswerEvaluation] = None,
        follow_up_type: Optional[FollowUpType] = None,
    ) -> FollowUpPlan:
        """
        Analyze the candidate's answer and produce a FollowUpPlan.
        """
        plan = self.followup_engine.create_follow_up_plan(
            parent_question=parent_question,
            candidate_answer=candidate_answer,
            config=config,
            evaluation=evaluation,
            follow_up_type=follow_up_type,
        )
        logger.info(
            f"Planned Follow-Up: Type=[{plan.follow_up_type.value}] | Anchor='{plan.anchor_concept_or_quote}' | Topic='{plan.target_topic}'"
        )
        return plan

    def generate_follow_up_question(
        self,
        config: InterviewConfig,
        parent_question: Question,
        candidate_answer: str,
        question_number: int,
        evaluation: Optional[AnswerEvaluation] = None,
        follow_up_type: Optional[FollowUpType] = None,
    ) -> Question:
        """
        Generate a contextual follow-up question referencing the candidate's answer.
        """
        question = self.followup_engine.generate_follow_up(
            config=config,
            parent_question=parent_question,
            candidate_answer=candidate_answer,
            question_number=question_number,
            evaluation=evaluation,
            follow_up_type=follow_up_type,
        )
        return question
