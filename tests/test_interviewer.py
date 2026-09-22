"""
Unit tests for InterviewEngine lifecycle, state transitions, and validation.
"""

import pytest
from pydantic import ValidationError
from app.core.interviewer import InterviewEngine
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    InterviewStatus,
)


def test_invalid_interview_config():
    """Test validation errors for invalid configuration values."""
    with pytest.raises(ValidationError):
        InterviewConfig(
            candidate_name="",  # blank name
            role="Engineer",
        )

    with pytest.raises(ValidationError):
        InterviewConfig(
            candidate_name="Alex",
            role="Engineer",
            num_questions=0,  # ge=1 violated
        )


def test_interview_engine_lifecycle(mock_llm, sample_config):
    """Test complete end-to-end interview flow in InterviewEngine."""
    engine = InterviewEngine(llm_service=mock_llm)

    assert engine.status == InterviewStatus.CREATED
    assert engine.current_question_number == 0

    # 1. Start Interview
    first_q = engine.start_interview(sample_config)
    assert engine.status == InterviewStatus.IN_PROGRESS
    assert engine.current_question_number == 1
    assert first_q is not None
    assert engine.current_question == first_q
    assert engine.has_more_questions is True
    assert engine.get_progress_percentage() == 0.0

    # 2. Submit First Answer
    eval_1 = engine.submit_answer("Memory management uses reference counting.")
    assert eval_1 is not None
    assert eval_1.score == 8.5
    assert len(engine.history) == 1
    assert round(engine.get_progress_percentage(), 2) == 0.33

    # 3. Next Question (Q2)
    next_q = engine.generate_next_question()
    assert next_q is not None
    assert engine.current_question_number == 2
    assert engine.has_more_questions is True

    # 4. Submit Second Answer
    eval_2 = engine.submit_answer("GIL prevents multiple native threads from executing Python bytecodes simultaneously.")
    assert eval_2 is not None
    assert len(engine.history) == 2
    assert round(engine.get_progress_percentage(), 2) == 0.67

    # 5. Next Question (Q3 - Final configured question)
    q3 = engine.generate_next_question()
    assert q3 is not None
    assert engine.current_question_number == 3
    assert engine.has_more_questions is False  # Reached max configured (3)

    # 6. Submit Third Answer
    eval_3 = engine.submit_answer("Cyclic garbage collector identifies unreachable reference loops.")
    assert eval_3 is not None
    assert len(engine.history) == 3
    assert engine.get_progress_percentage() == 1.0

    # 7. Finish Interview
    result = engine.finish_interview()
    assert engine.status == InterviewStatus.COMPLETED
    assert result.summary.overall_score == 8.2
    assert len(result.pairs) == 3
    assert engine.is_finished is True


def test_submit_without_start_raises_error(mock_llm):
    """Test that submitting an answer before starting throws ValueError."""
    engine = InterviewEngine(llm_service=mock_llm)
    with pytest.raises(ValueError):
        engine.submit_answer("My answer")
