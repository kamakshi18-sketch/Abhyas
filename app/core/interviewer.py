"""
Interview Engine.
Stateful orchestration layer managing the complete adaptive interview lifecycle (Phase 5),
coordinating Question Generation, Answer Evaluation, Interview State tracking,
Decision Engine routing, and Database Persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.ai.ollama_client import LLMService, get_llm_service
from app.database.database import get_db
from app.database.repository import InterviewRepository
from app.schemas.interview import (
    InterviewConfig,
    InterviewState,
    InterviewDecision,
    DecisionAction,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    QuestionEvaluationPair,
    InterviewSummary,
    InterviewResult,
    InterviewStatus,
)
from app.core.question_generator import QuestionGenerator
from app.core.evaluator import AnswerEvaluator
from app.core.decision_engine import DecisionEngine

logger = logging.getLogger(__name__)


class InterviewEngine:
    """Stateful interview session coordinator with adaptive decision engine."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        question_generator: Optional[QuestionGenerator] = None,
        evaluator: Optional[AnswerEvaluator] = None,
        decision_engine: Optional[DecisionEngine] = None,
    ):
        self.llm_service = llm_service or get_llm_service()
        self.question_generator = question_generator or QuestionGenerator(self.llm_service)
        self.evaluator = evaluator or AnswerEvaluator(self.llm_service)
        self.decision_engine = decision_engine or DecisionEngine()

        # Session State
        self.config: Optional[InterviewConfig] = None
        self.state: Optional[InterviewState] = None
        self.interview_id: Optional[int] = None
        self.candidate_id: Optional[int] = None
        self.status: InterviewStatus = InterviewStatus.CREATED

        self.current_question_number: int = 0
        self.current_question: Optional[Question] = None
        self.current_question_db_id: Optional[int] = None
        self.current_answer: Optional[CandidateAnswer] = None
        self.current_evaluation: Optional[AnswerEvaluation] = None

        self.previous_questions: List[Question] = []
        self.history: List[QuestionEvaluationPair] = []
        self.final_summary: Optional[InterviewSummary] = None

    @property
    def total_questions(self) -> int:
        return self.config.num_questions if self.config else 0

    @property
    def is_finished(self) -> bool:
        return self.status == InterviewStatus.COMPLETED

    @property
    def has_more_questions(self) -> bool:
        if not self.config:
            return False
        return self.current_question_number < self.config.num_questions

    @property
    def latest_decision(self) -> Optional[InterviewDecision]:
        return self.state.latest_decision if self.state else None

    def start_interview(self, config: InterviewConfig) -> Question:
        """
        Initialize the interview session, state snapshot, persist records to database,
        and generate the first question.
        """
        self.config = config
        self.status = InterviewStatus.IN_PROGRESS
        self.current_question_number = 1
        self.previous_questions = []
        self.history = []
        self.final_summary = None

        # Initialize Phase 5 Interview State
        self.state = self.decision_engine.initialize_state(config)

        # Persist Candidate and Interview in DB
        try:
            with get_db() as session:
                candidate = InterviewRepository.get_or_create_candidate(
                    session=session,
                    name=config.candidate_name,
                )
                self.candidate_id = candidate.id

                interview = InterviewRepository.create_interview(
                    session=session,
                    candidate_id=candidate.id,
                    config=config,
                )
                self.interview_id = interview.id
        except Exception as e:
            logger.error(f"Database error during interview initiation: {e}")

        # Generate first question
        question = self.question_generator.generate_question(
            config=self.config,
            question_number=1,
            previous_questions=[],
        )
        self.current_question = question
        self.previous_questions.append(question)
        self.current_answer = None
        self.current_evaluation = None

        # Save question to DB
        if self.interview_id:
            try:
                with get_db() as session:
                    q_model = InterviewRepository.save_question(
                        session=session,
                        interview_id=self.interview_id,
                        question=question,
                    )
                    self.current_question_db_id = q_model.id
                    question.question_id = q_model.id
            except Exception as e:
                logger.error(f"Database error saving question: {e}")

        return question

    def submit_answer(self, answer_text: str) -> AnswerEvaluation:
        """
        Submit answer for current question:
        1. Evaluates answer using type-specific rubric.
        2. Updates live InterviewState (topics, strengths/weaknesses, score metrics).
        3. Executes DecisionEngine to determine next adaptive strategic action.
        4. Persists state and evaluation to database.
        """
        if not self.current_question or not self.config or not self.state:
            raise ValueError("No active question or uninitialized interview state.")

        clean_text = answer_text.strip()
        answer = CandidateAnswer(
            question_id=self.current_question_db_id,
            question_number=self.current_question_number,
            answer_text=clean_text if clean_text else "(No answer provided)",
            submitted_at=datetime.now(timezone.utc).isoformat(),
        )
        self.current_answer = answer

        # 1. Evaluate Answer
        evaluation = self.evaluator.evaluate_answer(
            config=self.config,
            question=self.current_question,
            candidate_answer=answer.answer_text,
        )
        self.current_evaluation = evaluation

        # 2. Update InterviewState
        self.decision_engine.update_state(
            state=self.state,
            question=self.current_question,
            answer=answer,
            evaluation=evaluation,
            config=self.config,
        )

        # 3. Execute DecisionEngine
        decision = self.decision_engine.decide_next_action(
            state=self.state,
            config=self.config,
            latest_evaluation=evaluation,
        )
        self.state.latest_decision = decision
        self.state.difficulty = decision.target_difficulty

        # 4. Save to DB
        if self.current_question_db_id:
            try:
                with get_db() as session:
                    InterviewRepository.save_answer_and_evaluation(
                        session=session,
                        question_id=self.current_question_db_id,
                        answer=answer,
                        evaluation=evaluation,
                    )
            except Exception as e:
                logger.error(f"Database error saving answer and evaluation: {e}")

        # Append to session history
        pair = QuestionEvaluationPair(
            question=self.current_question,
            answer=answer,
            evaluation=evaluation,
        )
        self.history.append(pair)

        return evaluation

    def generate_next_question(self) -> Optional[Question]:
        """
        Advance to the next question in the adaptive interview sequence:
        1. Checks question budget limits (prevents infinite loops).
        2. Maps latest InterviewDecision to a StrategyPlan.
        3. Generates targeted question via Question Generator.
        4. Persists next question to database.
        """
        if not self.has_more_questions:
            return None

        self.current_question_number += 1
        self.current_answer = None
        self.current_evaluation = None

        # Resolve StrategyPlan from DecisionEngine
        decision = self.state.latest_decision if self.state else None
        if not decision and self.state:
            decision = self.decision_engine.decide_next_action(self.state, self.config)
            self.state.latest_decision = decision

        strategy = None
        if decision and self.state and self.config:
            strategy = self.decision_engine.map_decision_to_strategy(
                decision=decision,
                state=self.state,
                config=self.config,
                question_number=self.current_question_number,
            )

        # Generate Adaptive Question
        question = self.question_generator.generate_question(
            config=self.config,
            question_number=self.current_question_number,
            previous_questions=self.previous_questions,
            history=self.history,
            strategy=strategy,
        )

        self.current_question = question
        self.previous_questions.append(question)

        # Save to DB
        if self.interview_id:
            try:
                with get_db() as session:
                    q_model = InterviewRepository.save_question(
                        session=session,
                        interview_id=self.interview_id,
                        question=question,
                    )
                    self.current_question_db_id = q_model.id
                    question.question_id = q_model.id
            except Exception as e:
                logger.error(f"Database error saving next question: {e}")

        return question

    def finish_interview(self) -> InterviewResult:
        """
        Conclude interview session, generate overarching summary,
        update database, and return complete result payload.
        """
        self.status = InterviewStatus.COMPLETED

        if not self.config:
            raise ValueError("Cannot finish an uninitialized interview.")

        summary = self.evaluator.generate_summary(
            config=self.config,
            pairs=self.history,
        )
        self.final_summary = summary

        # Persist final state in DB
        if self.interview_id:
            try:
                with get_db() as session:
                    InterviewRepository.finalize_interview(
                        session=session,
                        interview_id=self.interview_id,
                        summary=summary,
                    )
            except Exception as e:
                logger.error(f"Database error finalizing interview: {e}")

        result = InterviewResult(
            interview_id=self.interview_id,
            config=self.config,
            pairs=self.history,
            summary=summary,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        return result

    def get_progress_percentage(self) -> float:
        """Compute interview progress ratio (0.0 to 1.0)."""
        if not self.config or self.config.num_questions == 0:
            return 0.0
        return min(1.0, len(self.history) / float(self.config.num_questions))

