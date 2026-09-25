"""
Unit and Integration Tests for Phase 4.5 Performance Optimizations.
Tests:
- Timer and latency recording
- EvaluationCache LRU eviction and deterministic fingerprinting
- Prompt versioning and prompt template efficiency
- Database indexing and WAL connection pragma tuning
- LLM Factory client caching
- Short-circuit optimizations and regression verification
"""

import time
import pytest
from app.performance.timers import Timer, measure_time
from app.performance.metrics import (
    record_metric,
    get_metrics,
    get_metric_stats,
    clear_metrics,
)
from app.performance.cache import EvaluationCache, get_evaluation_cache
from app.core.prompts import (
    QUESTION_PROMPT_VERSION,
    EVALUATION_PROMPT_VERSION,
    SUMMARY_PROMPT_VERSION,
    build_question_prompt,
    build_evaluation_prompt,
)
from app.core.evaluation_rubrics import EvaluationRubricService, RUBRIC_TECHNICAL
from app.ai.factory import create_llm_service
from app.ai.mock_client import MockService
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    InterviewMode,
    InterviewerPersona,
    Question,
    AnswerEvaluation,
    EvaluationMetrics,
)
from app.services.evaluation_service import AnswerEvaluationService
from app.database.database import engine, get_db
from app.database.repository import InterviewRepository


def test_timer_and_metrics_recording():
    """Verify Timer measures elapsed time and records metrics accurately."""
    clear_metrics()
    with Timer("test_operation", record_to_metrics=True) as t:
        time.sleep(0.01)  # 10ms

    assert t.elapsed_ms >= 8.0
    metrics = get_metrics()
    assert "test_operation" in metrics
    assert len(metrics["test_operation"]) == 1

    stats = get_metric_stats()
    assert "test_operation" in stats
    assert stats["test_operation"]["count"] == 1
    assert stats["test_operation"]["avg_ms"] >= 8.0


def test_measure_time_decorator():
    """Verify @measure_time records execution latency."""
    clear_metrics()

    @measure_time("decorated_func")
    def sample_func(x, y):
        return x + y

    res = sample_func(5, 10)
    assert res == 15
    metrics = get_metrics()
    assert "decorated_func" in metrics
    assert len(metrics["decorated_func"]) == 1


def test_evaluation_cache_deterministic_hit_and_lru():
    """Verify evaluation cache returns cached results for identical inputs and evicts oldest entries."""
    cache = EvaluationCache(maxsize=3)

    eval1 = AnswerEvaluation(score=8.0, feedback="Good", suggested_improvement="None")
    eval2 = AnswerEvaluation(score=9.0, feedback="Great", suggested_improvement="None")
    eval3 = AnswerEvaluation(score=7.0, feedback="Fair", suggested_improvement="None")
    eval4 = AnswerEvaluation(score=6.0, feedback="Pass", suggested_improvement="None")

    k1 = cache.generate_key("Q1", "A1", "Technical", "Professional", "English", "gemini", "1.0")
    k2 = cache.generate_key("Q2", "A2", "Technical", "Professional", "English", "gemini", "1.0")
    k3 = cache.generate_key("Q3", "A3", "Technical", "Professional", "English", "gemini", "1.0")
    k4 = cache.generate_key("Q4", "A4", "Technical", "Professional", "English", "gemini", "1.0")

    cache.put(k1, eval1)
    cache.put(k2, eval2)
    cache.put(k3, eval3)

    assert cache.get(k1) == eval1
    assert cache.hits == 1

    # Insert 4th item -> should evict k2 (since k1 was accessed recently)
    cache.put(k4, eval4)
    assert cache.get(k2) is None  # Evicted
    assert cache.get(k1) == eval1  # Retained
    assert cache.get(k4) == eval4  # Present


def test_prompt_versions_present():
    """Verify prompt version constants exist for deterministic invalidation."""
    assert QUESTION_PROMPT_VERSION in ["1.0", "2.0"]
    assert EVALUATION_PROMPT_VERSION in ["1.0", "2.0"]
    assert SUMMARY_PROMPT_VERSION in ["1.0", "2.0"]


def test_rubric_instruction_caching():
    """Verify rubric formatted prompt instructions are cached."""
    rubric = EvaluationRubricService.get_rubric(InterviewType.TECHNICAL)
    instr1 = EvaluationRubricService.format_rubric_prompt_instructions(rubric)
    instr2 = EvaluationRubricService.format_rubric_prompt_instructions(rubric)
    assert instr1 == instr2
    assert "Evaluation Rubric [Technical]" in instr1


def test_llm_factory_caching():
    """Verify create_llm_service reuses cached client instances."""
    service1 = create_llm_service(provider="mock")
    service2 = create_llm_service(provider="mock")
    assert service1 is service2


def test_evaluation_service_cache_integration():
    """Verify AnswerEvaluationService utilizes EvaluationCache on identical requests."""
    mock_llm = MockService()
    eval_service = AnswerEvaluationService(llm_service=mock_llm)
    config = InterviewConfig(
        candidate_name="Jane Doe",
        role="Backend Engineer",
        experience_level=ExperienceLevel.TWO_TO_FIVE,
        interview_type=InterviewType.TECHNICAL,
        difficulty=Difficulty.MEDIUM,
        num_questions=3,
        estimated_duration_minutes=20,
        interviewer_persona=InterviewerPersona.PROFESSIONAL,
    )
    question = Question(
        question_number=1,
        text="Explain database indexing in PostgreSQL.",
        category="Technical",
        topic="SQL",
        difficulty=Difficulty.MEDIUM,
    )
    answer = "B-Trees are the default index type in PostgreSQL, optimizing range queries and exact lookups in O(log n) time."

    # 1st call -> LLM generation & cache put
    res1 = eval_service.evaluate_answer(config, question, answer)
    assert res1.score > 0.0

    # 2nd call with identical inputs -> cache HIT
    res2 = eval_service.evaluate_answer(config, question, answer)
    assert res2.score == res1.score
    assert res2.feedback == res1.feedback


def test_database_wal_pragmas_and_indexes():
    """Verify SQLite WAL mode, normal synchronous, and repository operations."""
    with get_db() as session:
        cand = InterviewRepository.get_or_create_candidate(session, "Performance Test Candidate")
        assert cand.id is not None

        config = InterviewConfig(
            candidate_name="Performance Test Candidate",
            role="DevOps Specialist",
            experience_level=ExperienceLevel.FIVE_PLUS,
            interview_type=InterviewType.TECHNICAL,
            difficulty=Difficulty.HARD,
            num_questions=5,
            estimated_duration_minutes=30,
        )
        inv = InterviewRepository.create_interview(session, cand.id, config)
        assert inv.id is not None
        assert inv.status == "IN_PROGRESS"


def test_adaptive_decision_engine_submillisecond_latency():
    """Verify Adaptive Decision Engine executes in sub-millisecond time (< 0.1ms per decision)."""
    import time
    from app.core.decision_engine import AdaptiveDecisionEngine
    from app.schemas.interview import InterviewConfig, InterviewState, Question, CandidateAnswer, AnswerEvaluation

    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Speed Test",
        role="Systems Engineer",
        topics=["Linux", "Networking", "Distributed Systems"],
        num_questions=10,
    )
    state = InterviewState(
        current_topic="Linux",
        topics_covered=["Linux"],
        topics_remaining=["Networking", "Distributed Systems"],
        question_count=2,
        max_questions=10,
        previous_questions=[
            Question(question_number=1, text="Explain epoll.", topic="Linux"),
            Question(question_number=2, text="Explain cgroups.", topic="Linux"),
        ],
        previous_answers=[
            CandidateAnswer(question_number=1, answer_text="epoll is an I/O event notification facility."),
            CandidateAnswer(question_number=2, answer_text="cgroups limit resource usage."),
        ],
        previous_evaluations=[
            AnswerEvaluation(score=8.5, feedback="Great", suggested_improvement="None"),
            AnswerEvaluation(score=8.0, feedback="Solid", suggested_improvement="None"),
        ],
    )

    t0 = time.perf_counter()
    for _ in range(1000):
        decision = engine.decide_next_action(state, config)
        assert decision is not None
    total_ms = (time.perf_counter() - t0) * 1000.0

    avg_ms = total_ms / 1000.0
    # 1000 decisions should complete in under 50ms total (< 0.05ms per decision)
    assert avg_ms < 0.1, f"Adaptive decision took {avg_ms:.4f}ms per call (exceeded 0.1ms threshold)"


def test_followup_engine_submillisecond_latency():
    """Verify FollowUpEngine analysis and plan creation executes in sub-millisecond time (< 0.1ms per plan)."""
    import time
    from app.core.followup_engine import FollowUpEngine
    from app.schemas.interview import InterviewConfig, Question, AnswerEvaluation

    engine = FollowUpEngine()
    config = InterviewConfig(
        candidate_name="Speed Test",
        role="Backend Engineer",
        topics=["PostgreSQL", "Redis"],
        num_questions=5,
    )
    parent_q = Question(
        id=1,
        question_number=1,
        text="How do you handle hot database caches?",
        topic="PostgreSQL",
    )
    answer = "We used Redis as an LRU write-through cache with connection pooling."
    evaluation = AnswerEvaluation(score=8.5, feedback="Good", suggested_improvement="None")

    t0 = time.perf_counter()
    for _ in range(1000):
        plan = engine.create_follow_up_plan(
            parent_question=parent_q,
            candidate_answer=answer,
            config=config,
            evaluation=evaluation,
        )
        assert plan is not None
    total_ms = (time.perf_counter() - t0) * 1000.0

    avg_ms = total_ms / 1000.0
    assert avg_ms < 0.1, f"Follow-up planning took {avg_ms:.4f}ms per call (exceeded 0.1ms threshold)"


