"""
Repository layer for database CRUD operations.
Encapsulates all SQLAlchemy transactions and entity mapping.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from app.database.database import get_db
from app.database.models import (
    Candidate,
    Interview,
    QuestionModel,
    AnswerModel,
    EvaluationModel,
)
from app.schemas.interview import (
    InterviewConfig,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    EvaluationCriterion,
    EvaluationEvidence,
    EvaluationMetrics,
    QuestionEvaluationPair,
    InterviewSummary,
    InterviewResult,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    QuestionType,
    DEFAULT_ASSESSMENT_DISCLAIMER,
)

from app.performance.timers import measure_time

logger = logging.getLogger(__name__)


class InterviewRepository:
    """Repository handling persistence for interview sessions."""

    @staticmethod
    @measure_time("db_candidate_get_or_create")
    def get_or_create_candidate(session: Session, name: str) -> Candidate:
        """Find existing candidate by name or create a new candidate record."""
        clean_name = name.strip()
        candidate = session.query(Candidate).filter(Candidate.name == clean_name).first()
        if not candidate:
            candidate = Candidate(name=clean_name)
            session.add(candidate)
            session.flush()
            logger.info(f"Created new candidate: id={candidate.id}, name='{candidate.name}'")
        return candidate

    @staticmethod
    @measure_time("db_create_interview")
    def create_interview(session: Session, candidate_id: int, config: InterviewConfig) -> Interview:
        """Create a new interview record initialized in IN_PROGRESS status."""
        interview = Interview(
            candidate_id=candidate_id,
            role=config.role or "Software Engineer",
            experience_level=config.experience_level.value,
            interview_type=config.interview_type.value,
            difficulty=config.difficulty.value,
            num_questions=config.num_questions,
            estimated_duration_minutes=config.estimated_duration_minutes,
            language=config.language,
            interviewer_persona=config.interviewer_persona.value,
            mode=config.mode.value,
            topics_json=json.dumps(config.topics),
            config_json=config.model_dump_json(),
            status="IN_PROGRESS",
            created_at=datetime.now(timezone.utc),
        )
        session.add(interview)
        session.flush()
        logger.info(f"Created interview session: id={interview.id} for candidate_id={candidate_id}")
        return interview


    @staticmethod
    @measure_time("db_save_question")
    def save_question(session: Session, interview_id: int, question: Question) -> QuestionModel:
        """Persist an AI-generated question for an interview."""
        concepts = question.expected_concepts or question.expected_points or []
        criteria = question.evaluation_criteria or []
        meta = question.metadata or {}

        question_model = QuestionModel(
            interview_id=interview_id,
            question_number=question.question_number,
            question_text=question.text or question.question_text,
            category=question.category,
            topic=question.topic or "General",
            difficulty=question.difficulty.value if isinstance(question.difficulty, Difficulty) else str(question.difficulty),
            question_type=question.question_type.value if hasattr(question.question_type, "value") else str(question.question_type),
            expected_points=json.dumps(concepts),
            expected_concepts_json=json.dumps(concepts),
            evaluation_criteria_json=json.dumps(criteria),
            follow_up_possible=1 if question.follow_up_possible else 0,
            metadata_json=json.dumps(meta),
            created_at=datetime.now(timezone.utc),
        )
        session.add(question_model)
        session.flush()
        return question_model

    @staticmethod
    @measure_time("db_save_answer_and_evaluation")
    def save_answer_and_evaluation(
        session: Session,
        question_id: int,
        answer: CandidateAnswer,
        evaluation: AnswerEvaluation,
    ) -> Tuple[AnswerModel, EvaluationModel]:
        """Save candidate answer and AI evaluation."""
        answer_model = AnswerModel(
            question_id=question_id,
            answer_text=answer.answer_text,
            submitted_at=datetime.now(timezone.utc),
        )
        session.add(answer_model)
        session.flush()

        criteria_json = json.dumps([c.model_dump() for c in evaluation.criteria_scores]) if evaluation.criteria_scores else None
        evidence_json = json.dumps([e.model_dump() for e in evaluation.evidence]) if evaluation.evidence else None

        eval_model = EvaluationModel(
            answer_id=answer_model.id,
            score=float(evaluation.score),
            relevance=evaluation.metrics.relevance,
            correctness=evaluation.metrics.correctness,
            completeness=evaluation.metrics.completeness,
            clarity=evaluation.metrics.clarity,
            depth=evaluation.metrics.depth,
            criteria_scores_json=criteria_json,
            evidence_json=evidence_json,
            strengths=json.dumps(evaluation.strengths),
            weaknesses=json.dumps(evaluation.weaknesses),
            feedback=evaluation.feedback,
            suggested_improvement=evaluation.suggested_improvement,
            assessment_disclaimer=evaluation.assessment_disclaimer,
            created_at=datetime.now(timezone.utc),
        )
        session.add(eval_model)
        session.flush()

        return answer_model, eval_model

    @staticmethod
    @measure_time("db_finalize_interview")
    def finalize_interview(
        session: Session,
        interview_id: int,
        summary: InterviewSummary,
    ) -> Optional[Interview]:
        """Mark interview as COMPLETED and persist overall summary/score."""
        interview = session.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            logger.warning(f"Cannot finalize interview: id={interview_id} not found.")
            return None

        interview.status = "COMPLETED"
        interview.overall_score = float(summary.overall_score)
        interview.overall_feedback = summary.overall_feedback
        interview.strengths_summary = json.dumps(summary.strengths_summary)
        interview.weaknesses_summary = json.dumps(summary.weaknesses_summary)
        interview.areas_to_improve = json.dumps(summary.areas_to_improve)
        interview.completed_at = datetime.now(timezone.utc)
        session.flush()
        logger.info(f"Finalized interview id={interview.id} with score={interview.overall_score}")
        return interview

    @staticmethod
    def get_interview(session: Session, interview_id: int) -> Optional[Interview]:
        """Load interview with full relations."""
        return (
            session.query(Interview)
            .options(
                joinedload(Interview.candidate),
                joinedload(Interview.questions)
                .joinedload(QuestionModel.answers)
                .joinedload(AnswerModel.evaluation),
            )
            .filter(Interview.id == interview_id)
            .first()
        )

    @staticmethod
    @measure_time("db_get_interview_result")
    def get_interview_result(session: Session, interview_id: int) -> Optional[InterviewResult]:
        """Convert persisted interview data into structured InterviewResult schema."""
        interview = InterviewRepository.get_interview(session, interview_id)
        if not interview:
            return None

        if interview.config_json:
            try:
                config = InterviewConfig.model_validate_json(interview.config_json)
            except Exception:
                config = InterviewConfig(
                    candidate_name=interview.candidate.name if interview.candidate else "Unknown",
                    role=interview.role,
                    experience_level=ExperienceLevel(interview.experience_level),
                    interview_type=InterviewType(interview.interview_type),
                    difficulty=Difficulty(interview.difficulty),
                    num_questions=interview.num_questions,
                    estimated_duration_minutes=interview.estimated_duration_minutes or 30,
                    language=interview.language or "English",
                    topics=json.loads(interview.topics_json) if interview.topics_json else [],
                )
        else:
            config = InterviewConfig(
                candidate_name=interview.candidate.name if interview.candidate else "Unknown",
                role=interview.role,
                experience_level=ExperienceLevel(interview.experience_level),
                interview_type=InterviewType(interview.interview_type),
                difficulty=Difficulty(interview.difficulty),
                num_questions=interview.num_questions,
                estimated_duration_minutes=interview.estimated_duration_minutes or 30,
                language=interview.language or "English",
                topics=json.loads(interview.topics_json) if interview.topics_json else [],
            )

        pairs: List[QuestionEvaluationPair] = []
        for q in interview.questions:
            expected_pts = json.loads(q.expected_concepts_json or q.expected_points or "[]")
            eval_criteria = json.loads(q.evaluation_criteria_json or "[]")
            metadata = json.loads(q.metadata_json or "{}")
            q_schema = Question(
                id=q.id,
                question_id=q.id,
                question_number=q.question_number,
                text=q.question_text,
                question_text=q.question_text,
                category=q.category,
                topic=q.topic or "General",
                difficulty=Difficulty(q.difficulty),
                question_type=QuestionType(q.question_type) if q.question_type and q.question_type in QuestionType._value2member_map_ else QuestionType.TECHNICAL,
                expected_concepts=expected_pts,
                expected_points=expected_pts,
                evaluation_criteria=eval_criteria,
                follow_up_possible=bool(q.follow_up_possible if q.follow_up_possible is not None else True),
                metadata=metadata,
            )

            for ans in q.answers:
                ans_schema = CandidateAnswer(
                    question_id=q.id,
                    question_number=q.question_number,
                    answer_text=ans.answer_text,
                    submitted_at=ans.submitted_at.isoformat() if ans.submitted_at else None,
                )

                if ans.evaluation:
                    ev = ans.evaluation
                    raw_criteria = json.loads(ev.criteria_scores_json) if ev.criteria_scores_json else []
                    raw_evidence = json.loads(ev.evidence_json) if ev.evidence_json else []

                    ev_schema = AnswerEvaluation(
                        score=ev.score,
                        criteria_scores=[EvaluationCriterion.model_validate(c) for c in raw_criteria] if raw_criteria else [],
                        evidence=[EvaluationEvidence.model_validate(e) for e in raw_evidence] if raw_evidence else [],
                        metrics=EvaluationMetrics(
                            relevance=ev.relevance,
                            correctness=ev.correctness,
                            completeness=ev.completeness,
                            clarity=ev.clarity,
                            depth=ev.depth,
                        ),
                        strengths=json.loads(ev.strengths) if ev.strengths else [],
                        weaknesses=json.loads(ev.weaknesses) if ev.weaknesses else [],
                        feedback=ev.feedback,
                        suggested_improvement=ev.suggested_improvement,
                        assessment_disclaimer=ev.assessment_disclaimer or DEFAULT_ASSESSMENT_DISCLAIMER,
                    )
                else:
                    ev_schema = AnswerEvaluation(
                        score=0.0,
                        feedback="Evaluation pending",
                        suggested_improvement="",
                    )

                pairs.append(
                    QuestionEvaluationPair(
                        question=q_schema,
                        answer=ans_schema,
                        evaluation=ev_schema,
                    )
                )

        summary = InterviewSummary(
            overall_score=interview.overall_score or 0.0,
            strengths_summary=json.loads(interview.strengths_summary) if interview.strengths_summary else [],
            weaknesses_summary=json.loads(interview.weaknesses_summary) if interview.weaknesses_summary else [],
            overall_feedback=interview.overall_feedback or "",
            areas_to_improve=json.loads(interview.areas_to_improve) if interview.areas_to_improve else [],
        )

        return InterviewResult(
            interview_id=interview.id,
            config=config,
            pairs=pairs,
            summary=summary,
            created_at=interview.created_at.isoformat() if interview.created_at else None,
            completed_at=interview.completed_at.isoformat() if interview.completed_at else None,
        )
