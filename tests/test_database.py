"""
Unit tests for Database layer, models, and InterviewRepository.
"""

import pytest
from app.database.models import Candidate, Interview, QuestionModel, AnswerModel, EvaluationModel
from app.database.repository import InterviewRepository
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    EvaluationMetrics,
    InterviewSummary,
)


def test_candidate_creation_and_reuse(db_session):
    """Test creating and retrieving candidate records without duplicate records."""
    cand1 = InterviewRepository.get_or_create_candidate(db_session, "Alice Smith")
    assert cand1.id is not None
    assert cand1.name == "Alice Smith"

    # Re-requesting same candidate returns existing entity
    cand2 = InterviewRepository.get_or_create_candidate(db_session, "Alice Smith ")
    assert cand2.id == cand1.id


def test_interview_lifecycle_in_database(db_session, sample_config):
    """Test full interview creation, question persistence, answering, and evaluation."""
    candidate = InterviewRepository.get_or_create_candidate(db_session, sample_config.candidate_name)
    interview = InterviewRepository.create_interview(db_session, candidate.id, sample_config)

    assert interview.id is not None
    assert interview.status == "IN_PROGRESS"
    assert interview.role == "Senior Backend Engineer"

    # Save a Question
    q_schema = Question(
        question_number=1,
        question_text="How do database indexes improve query performance?",
        category="Databases",
        difficulty=Difficulty.HARD,
        expected_points=["B-Trees", "Lookup complexity", "Write overhead"],
    )
    q_model = InterviewRepository.save_question(db_session, interview.id, q_schema)
    assert q_model.id is not None
    assert q_model.interview_id == interview.id

    # Save Answer and Evaluation
    ans_schema = CandidateAnswer(
        question_id=q_model.id,
        question_number=1,
        answer_text="Indexes use B-trees to provide logarithmic lookup time.",
    )
    eval_schema = AnswerEvaluation(
        score=9.0,
        metrics=EvaluationMetrics(relevance=9, correctness=9, completeness=8, clarity=9, depth=9),
        strengths=["Clear B-tree mention"],
        weaknesses=["Could mention write penalties"],
        feedback="Great answer.",
        suggested_improvement="Mention impact on INSERT/UPDATE operations.",
    )

    ans_model, eval_model = InterviewRepository.save_answer_and_evaluation(
        db_session, q_model.id, ans_schema, eval_schema
    )
    assert ans_model.id is not None
    assert eval_model.id is not None
    assert eval_model.score == 9.0
    assert eval_model.answer_id == ans_model.id

    # Finalize Interview
    summary = InterviewSummary(
        overall_score=9.0,
        strengths_summary=["Database internals"],
        weaknesses_summary=["Minor edge cases"],
        overall_feedback="Excellent interview overall.",
        areas_to_improve=["Distributed systems tuning"],
    )
    finalized = InterviewRepository.finalize_interview(db_session, interview.id, summary)
    assert finalized.status == "COMPLETED"
    assert finalized.overall_score == 9.0
    assert finalized.completed_at is not None

    # Retrieve full InterviewResult
    result = InterviewRepository.get_interview_result(db_session, interview.id)
    assert result is not None
    assert result.interview_id == interview.id
    assert len(result.pairs) == 1
    assert result.pairs[0].question.question_text == q_schema.question_text
    assert result.pairs[0].answer.answer_text == ans_schema.answer_text
    assert result.pairs[0].evaluation.score == 9.0
    assert result.summary.overall_score == 9.0
