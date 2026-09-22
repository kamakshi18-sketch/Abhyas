"""
Unit tests for AnswerEvaluator and QuestionGenerator engines.
"""

import pytest
from app.core.evaluator import AnswerEvaluator
from app.core.question_generator import QuestionGenerator
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    QuestionEvaluationPair,
    EvaluationMetrics,
)
from tests.conftest import MockLLMService


def test_question_generator_with_mock_llm(mock_llm, sample_config):
    """Test standard question generation with Mock LLM."""
    q_gen = QuestionGenerator(llm_service=mock_llm)
    q = q_gen.generate_question(sample_config, question_number=1)

    assert isinstance(q, Question)
    assert q.question_number == 1
    assert q.question_text == "Explain Python memory management and the GIL."
    assert q.category == "Python Internals"
    assert len(q.expected_points) == 3


def test_question_generator_fallback(sample_config):
    """Test question generator fallback when LLM fails."""
    class FailingLLM(MockLLMService):
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("LLM connection timed out")

    q_gen = QuestionGenerator(llm_service=FailingLLM())
    q = q_gen.generate_question(sample_config, question_number=2)

    assert isinstance(q, Question)
    assert q.question_number == 2
    assert "Senior Backend Engineer" in q.question_text
    assert q.difficulty == sample_config.difficulty


def test_evaluate_valid_answer(mock_llm, sample_config):
    """Test evaluation of a valid answer using LLM."""
    evaluator = AnswerEvaluator(llm_service=mock_llm)
    question = Question(
        question_number=1,
        question_text="Explain Python memory management.",
        category="Python Internals",
        difficulty=Difficulty.MEDIUM,
    )
    answer = "Python uses reference counting and a cyclic garbage collector."

    evaluation = evaluator.evaluate_answer(
        config=sample_config,
        question=question,
        candidate_answer=answer,
    )

    assert isinstance(evaluation, AnswerEvaluation)
    assert evaluation.score == 8.5
    assert evaluation.metrics.relevance == 9
    assert evaluation.metrics.correctness == 8
    assert len(evaluation.strengths) > 0
    assert len(evaluation.weaknesses) > 0


def test_evaluate_empty_answer(mock_llm, sample_config):
    """Test evaluation when candidate submits an empty or whitespace answer."""
    evaluator = AnswerEvaluator(llm_service=mock_llm)
    question = Question(
        question_number=1,
        question_text="Explain Python memory management.",
        category="Python Internals",
        difficulty=Difficulty.MEDIUM,
    )

    evaluation = evaluator.evaluate_answer(
        config=sample_config,
        question=question,
        candidate_answer="   ",
    )

    assert evaluation.score == 1.0
    assert evaluation.metrics.relevance == 1
    assert "empty" in evaluation.feedback.lower()


def test_evaluator_fallback_when_llm_fails(sample_config):
    """Test heuristic fallback evaluation when LLM encounters an error."""
    class FailingLLM(MockLLMService):
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("Ollama service down")

    evaluator = AnswerEvaluator(llm_service=FailingLLM())
    question = Question(
        question_number=1,
        question_text="Describe system design tradeoffs.",
        category="Architecture",
        difficulty=Difficulty.HARD,
    )
    answer = "We choose between consistency and availability depending on the partition tolerance requirements of the system."

    evaluation = evaluator.evaluate_answer(
        config=sample_config,
        question=question,
        candidate_answer=answer,
    )

    assert isinstance(evaluation, AnswerEvaluation)
    assert 0.0 <= evaluation.score <= 10.0
    assert evaluation.metrics.relevance >= 1
    assert len(evaluation.strengths) > 0


def test_summary_generation_and_fallback(mock_llm, sample_config):
    """Test interview summary generation with LLM and fallback."""
    evaluator = AnswerEvaluator(llm_service=mock_llm)

    q = Question(question_number=1, question_text="What is the GIL?", category="Python", difficulty=Difficulty.MEDIUM)
    a = CandidateAnswer(question_number=1, answer_text="Global Interpreter Lock.")
    e = AnswerEvaluation(
        score=8.0,
        metrics=EvaluationMetrics(),
        strengths=["Direct answer"],
        weaknesses=["Brief"],
        feedback="Good start.",
        suggested_improvement="Elaborate.",
    )
    pair = QuestionEvaluationPair(question=q, answer=a, evaluation=e)

    summary = evaluator.generate_summary(sample_config, [pair])
    assert summary.overall_score == 8.2
    assert len(summary.strengths_summary) > 0

    # Test empty pairs summary
    empty_summary = evaluator.generate_summary(sample_config, [])
    assert empty_summary.overall_score == 0.0
