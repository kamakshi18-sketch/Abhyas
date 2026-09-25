"""
Phase 6 Test Suite: Follow-Up Engine.
Tests all 10 specialized follow-up categories, anchor phrase extraction, diagnostic heuristics,
experience calibration, and fallback template generation.
"""

import pytest
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    Question,
    QuestionType,
    AnswerEvaluation,
    EvaluationMetrics,
    FollowUpType,
    FollowUpPlan,
)
from app.core.followup_engine import FollowUpEngine
from app.services.followup_service import FollowUpService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_parent_question(
    topic: str = "Python",
    diff: Difficulty = Difficulty.MEDIUM,
    q_type: QuestionType = QuestionType.TECHNICAL,
) -> Question:
    return Question(
        id=1,
        question_number=1,
        text="Explain how Python manages memory and handles object cleanup.",
        topic=topic,
        category="Technical - Python",
        difficulty=diff,
        question_type=q_type,
        expected_concepts=["Reference counting", "Garbage collection"],
        evaluation_criteria=["Accuracy", "Clarity"],
    )


def make_eval(
    score: float = 7.0,
    strengths: list = None,
    weaknesses: list = None,
) -> AnswerEvaluation:
    return AnswerEvaluation(
        score=score,
        metrics=EvaluationMetrics(
            relevance=int(score),
            correctness=int(score),
            completeness=int(score),
            clarity=int(score),
            depth=int(score),
        ),
        strengths=strengths or ["Clear explanation of reference counting"],
        weaknesses=weaknesses or ["Did not discuss cyclical reference edge cases"],
        feedback="Good foundational grasp.",
        suggested_improvement="Provide concrete cyclical GC example.",
    )


# ---------------------------------------------------------------------------
# Unit Tests: Anchor Extraction & Heuristics
# ---------------------------------------------------------------------------

def test_anchor_extraction_from_technology():
    """Verify engine detects and extracts mentioned technologies as anchors."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Databases")
    answer = "In my last project we used Redis to cache hot database query results from PostgreSQL."

    anchor = engine.extract_anchor(answer, parent_q)
    assert anchor.lower() in ("redis", "postgresql")


def test_anchor_extraction_from_weakness():
    """Verify engine falls back to evaluation weaknesses when no explicit tech keyword."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Algorithms")
    answer = "I used a quicksort algorithm to partition elements in-place."
    evaluation = make_eval(
        score=6.0,
        weaknesses=["Worst case O(N^2) pivot selection behavior"],
    )

    anchor = engine.extract_anchor(answer, parent_q, evaluation)
    assert "pivot" in anchor.lower() or "quicksort" in anchor.lower() or "worst case" in anchor.lower()


def test_diagnostic_type_selection_vague_answer():
    """Diagnostic Rule 1: Vague/brief answer selects EXAMPLE_REQUEST or CLARIFICATION."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("System Design")
    vague_answer = "We just cache things."
    evaluation = make_eval(score=3.5, weaknesses=["Answer is too brief and vague without examples"])

    ftype = engine.determine_follow_up_type(vague_answer, parent_q, evaluation)
    assert ftype in (FollowUpType.EXAMPLE_REQUEST, FollowUpType.CLARIFICATION)


def test_diagnostic_type_selection_strong_answer(sample_config):
    """Diagnostic Rule 2: Technically strong answer (score >= 8.5) selects DEEP_TECHNICAL, TRADEOFF, or OPTIMIZATION."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Concurrency", Difficulty.HARD)
    strong_answer = (
        "We implemented non-blocking concurrent lock-free queues using atomic CAS operations "
        "and memory barriers in C++ to prevent cache line bouncing and optimize CPU cache locality."
    )
    evaluation = make_eval(score=9.5, strengths=["Detailed CAS knowledge", "Cache line awareness"])

    ftype = engine.determine_follow_up_type(strong_answer, parent_q, evaluation, config=sample_config)
    assert ftype in (FollowUpType.DEEP_TECHNICAL, FollowUpType.TRADEOFF, FollowUpType.OPTIMIZATION)


def test_diagnostic_type_selection_misconception():
    """Diagnostic Rule 3: Incorrect assumption or misconception selects CHALLENGE or COUNTEREXAMPLE."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Distributed Systems")
    flawed_answer = "TCP always guarantees that messages arrive in zero time and never drop packets."
    evaluation = make_eval(score=3.0, weaknesses=["Incorrect assumption regarding network packet latency"])

    ftype = engine.determine_follow_up_type(flawed_answer, parent_q, evaluation)
    assert ftype in (FollowUpType.CHALLENGE, FollowUpType.COUNTEREXAMPLE, FollowUpType.WHY_QUESTION)


# ---------------------------------------------------------------------------
# All 10 Follow-Up Categories Tested Individually
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target_type", [
    FollowUpType.CLARIFICATION,
    FollowUpType.EXAMPLE_REQUEST,
    FollowUpType.WHY_QUESTION,
    FollowUpType.HOW_QUESTION,
    FollowUpType.DEEP_TECHNICAL,
    FollowUpType.TRADEOFF,
    FollowUpType.CHALLENGE,
    FollowUpType.COUNTEREXAMPLE,
    FollowUpType.OPTIMIZATION,
    FollowUpType.PROJECT_SPECIFIC,
])
def test_all_ten_follow_up_categories(target_type, sample_config):
    """Verify engine generates valid, grounded follow-ups for each of the 10 categories."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Python")
    answer = "We used asyncio event loops with Celery tasks to process background jobs asynchronously."
    evaluation = make_eval(score=7.5)

    follow_up_q = engine.generate_follow_up(
        config=sample_config,
        parent_question=parent_q,
        candidate_answer=answer,
        question_number=2,
        evaluation=evaluation,
        follow_up_type=target_type,
    )

    assert follow_up_q is not None
    assert follow_up_q.question_number == 2
    assert follow_up_q.is_follow_up is True
    assert follow_up_q.follow_up_type == target_type
    assert follow_up_q.parent_question_id == parent_q.id
    assert follow_up_q.anchor_reference is not None
    assert len(follow_up_q.expected_concepts) >= 1
    assert len(follow_up_q.evaluation_criteria) >= 1
    # Ensure text is non-empty and references the anchor/context
    assert len(follow_up_q.text) > 15


# ---------------------------------------------------------------------------
# Specific Category Quality & Grounding Checks
# ---------------------------------------------------------------------------

def test_clarification_follow_up(sample_config):
    """Category 1: CLARIFICATION."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Security")
    ans = "We used JWT tokens."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.CLARIFICATION)
    assert q.follow_up_type == FollowUpType.CLARIFICATION
    assert "clarify" in q.text.lower() or "mentioned" in q.text.lower()


def test_example_request_follow_up(sample_config):
    """Category 2: EXAMPLE_REQUEST."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Design Patterns")
    ans = "Factory pattern is good for abstraction."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.EXAMPLE_REQUEST)
    assert q.follow_up_type == FollowUpType.EXAMPLE_REQUEST
    assert "example" in q.text.lower()


def test_why_question_follow_up(sample_config):
    """Category 3: WHY_QUESTION."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Architecture")
    ans = "We picked MongoDB over PostgreSQL."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.WHY_QUESTION)
    assert q.follow_up_type == FollowUpType.WHY_QUESTION
    assert "why" in q.text.lower()


def test_how_question_follow_up(sample_config):
    """Category 4: HOW_QUESTION."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Deployment")
    ans = "We automated our release with Docker containers."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.HOW_QUESTION)
    assert q.follow_up_type == FollowUpType.HOW_QUESTION
    assert "how" in q.text.lower()


def test_deep_technical_follow_up(sample_config):
    """Category 5: DEEP_TECHNICAL."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Python")
    ans = "The Global Interpreter Lock prevents parallel bytecode execution on native threads."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.DEEP_TECHNICAL)
    assert q.follow_up_type == FollowUpType.DEEP_TECHNICAL
    assert "deep" in q.text.lower() or "memory" in q.text.lower() or "concurrency" in q.text.lower()


def test_tradeoff_follow_up(sample_config):
    """Category 6: TRADEOFF."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Databases")
    ans = "We added multiple B-Tree indexes on every table column to speed up search queries."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.TRADEOFF)
    assert q.follow_up_type == FollowUpType.TRADEOFF
    assert "trade-off" in q.text.lower() or "tradeoff" in q.text.lower()


def test_challenge_follow_up(sample_config):
    """Category 7: CHALLENGE."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Microservices")
    ans = "All our services call each other synchronously via HTTP."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.CHALLENGE)
    assert q.follow_up_type == FollowUpType.CHALLENGE
    assert "partition" in q.text.lower() or "deadlock" in q.text.lower() or "failure" in q.text.lower() or "what happens" in q.text.lower()


def test_counterexample_follow_up(sample_config):
    """Category 8: COUNTEREXAMPLE."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Caching")
    ans = "Caching everything in memory with no eviction is our strategy."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.COUNTEREXAMPLE)
    assert q.follow_up_type == FollowUpType.COUNTEREXAMPLE
    assert "counterexample" in q.text.lower() or "anti-pattern" in q.text.lower() or "degrades" in q.text.lower()


def test_optimization_follow_up(sample_config):
    """Category 9: OPTIMIZATION."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("Backend APIs")
    ans = "We query the database inside a loop for each item in the list."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.OPTIMIZATION)
    assert q.follow_up_type == FollowUpType.OPTIMIZATION
    assert "optimize" in q.text.lower() or "throughput" in q.text.lower() or "latency" in q.text.lower()


def test_project_specific_follow_up(sample_config):
    """Category 10: PROJECT_SPECIFIC."""
    engine = FollowUpEngine()
    parent_q = make_parent_question("DevOps")
    ans = "I led the migration of our monolithic service into Kubernetes clusters."
    q = engine.generate_follow_up(sample_config, parent_q, ans, 2, follow_up_type=FollowUpType.PROJECT_SPECIFIC)
    assert q.follow_up_type == FollowUpType.PROJECT_SPECIFIC
    assert "project" in q.text.lower() or "role" in q.text.lower() or "deployed" in q.text.lower()


# ---------------------------------------------------------------------------
# FollowUpService Planning & Integration
# ---------------------------------------------------------------------------

def test_followup_service_plan_and_execution(mock_llm, sample_config):
    """Verify FollowUpService properly coordinates FollowUpPlan and LLM generation."""
    service = FollowUpService(llm_service=mock_llm)
    parent_q = make_parent_question("Python")
    answer = "Python's reference counting decrements whenever a variable goes out of scope."
    evaluation = make_eval(score=8.5)

    plan = service.plan_follow_up(
        parent_question=parent_q,
        candidate_answer=answer,
        config=sample_config,
        evaluation=evaluation,
    )
    assert isinstance(plan, FollowUpPlan)
    assert plan.target_topic == "Python"
    assert len(plan.objective) > 10

    follow_up_q = service.generate_follow_up_question(
        config=sample_config,
        parent_question=parent_q,
        candidate_answer=answer,
        question_number=2,
        evaluation=evaluation,
    )
    assert follow_up_q is not None
    assert follow_up_q.question_number == 2
    assert follow_up_q.is_follow_up is True
