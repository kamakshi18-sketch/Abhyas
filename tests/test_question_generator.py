"""
Unit and integration tests for Phase 3: Dedicated Question Generation Engine.
Tests Strategy planning, structured LLM generation, quality control validation,
anti-duplication filtering, topic/difficulty restrictions, and database persistence.
"""

import json
import pytest
from pydantic import ValidationError

from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    QuestionType,
    StrategyPlan,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    InterviewSummary,
)
from app.core.question_strategy import QuestionStrategyService
from app.services.question_generator_service import (
    QuestionGeneratorService,
    QuestionValidator,
)
from app.database.repository import InterviewRepository
from tests.conftest import MockLLMService


# =====================================================================
# 1. QUESTION MODEL & ALIAS TESTS
# =====================================================================

def test_question_model_instantiation_and_aliases():
    """Test Question model supports both Phase 3 field names and legacy alias compatibility."""
    # Instantiation with Phase 3 fields
    q1 = Question(
        id=101,
        question_number=1,
        text="Explain database index structures and B-Trees.",
        category="Databases",
        topic="SQL",
        difficulty=Difficulty.HARD,
        question_type=QuestionType.CONCEPTUAL,
        expected_concepts=["B-Tree depth", "Leaf node pointer", "Write amplification"],
        evaluation_criteria=["Technical precision", "Clear trade-off reasoning"],
        follow_up_possible=True,
        metadata={"source": "unit_test"},
    )
    assert q1.id == 101
    assert q1.question_id == 101
    assert q1.text == "Explain database index structures and B-Trees."
    assert q1.question_text == "Explain database index structures and B-Trees."
    assert q1.expected_concepts == ["B-Tree depth", "Leaf node pointer", "Write amplification"]
    assert q1.expected_points == ["B-Tree depth", "Leaf node pointer", "Write amplification"]
    assert q1.topic == "SQL"
    assert q1.question_type == QuestionType.CONCEPTUAL

    # Instantiation with legacy field names
    q2 = Question(
        question_id=202,
        question_number=2,
        question_text="How does garbage collection work in Python?",
        category="Python Internals",
        difficulty=Difficulty.MEDIUM,
        expected_points=["Reference counting", "Generational GC"],
    )
    assert q2.id == 202
    assert q2.text == "How does garbage collection work in Python?"
    assert q2.expected_concepts == ["Reference counting", "Generational GC"]
    assert q2.question_type == QuestionType.TECHNICAL
    assert q2.topic == "General"


# =====================================================================
# 2. STRATEGY ENGINE TESTS
# =====================================================================

def test_question_strategy_planning():
    """Test strategy engine generates balanced sequence plans across topics and types."""
    config = InterviewConfig(
        candidate_name="Sarah Connor",
        role="Backend Architect",
        experience_level=ExperienceLevel.FIVE_PLUS,
        interview_type=InterviewType.TECHNICAL,
        difficulty=Difficulty.HARD,
        topics=["Python", "SQL", "System Design"],
        num_questions=6,
    )

    plan = QuestionStrategyService.plan_interview_flow(config)
    assert len(plan) == 6

    # Verify cyclic topic distribution across all 3 selected topics
    assigned_topics = [step.target_topic for step in plan]
    assert assigned_topics == ["Python", "SQL", "System Design", "Python", "SQL", "System Design"]

    # Verify diverse QuestionType assignments
    assigned_types = [step.question_type for step in plan]
    assert QuestionType.CONCEPTUAL in assigned_types
    assert QuestionType.TECHNICAL in assigned_types
    assert QuestionType.PROBLEM_SOLVING in assigned_types

    # Verify experience-aligned objectives
    for step in plan:
        assert step.difficulty == Difficulty.HARD
        assert len(step.objective) > 15


def test_question_strategy_experience_objectives():
    """Test that different experience levels receive tailored pedagogical objectives."""
    fresher_config = InterviewConfig(
        candidate_name="Junior Dev",
        experience_level=ExperienceLevel.FRESHER,
        role="Junior Developer",
        topics=["Java"],
        num_questions=1,
    )
    senior_config = InterviewConfig(
        candidate_name="Lead Dev",
        experience_level=ExperienceLevel.FIVE_PLUS,
        role="Principal Engineer",
        topics=["Java"],
        num_questions=1,
    )

    fresher_step = QuestionStrategyService.get_strategy_for_step(fresher_config, question_number=1)
    senior_step = QuestionStrategyService.get_strategy_for_step(senior_config, question_number=1)

    assert "foundational" in fresher_step.objective.lower() or "terminology" in fresher_step.objective.lower()
    assert "architectural" in senior_step.objective.lower() or "limits" in senior_step.objective.lower()


# =====================================================================
# 3. QUESTION GENERATOR & QUALITY CONTROL TESTS
# =====================================================================

def test_question_generator_with_mock_llm(mock_llm):
    """Test question generator produces fully enriched Question adhering to schema."""
    config = InterviewConfig(
        candidate_name="David Miller",
        role="Cloud Infrastructure Engineer",
        experience_level=ExperienceLevel.TWO_TO_FIVE,
        interview_type=InterviewType.TECHNICAL,
        difficulty=Difficulty.MEDIUM,
        topics=["Cloud", "DevOps"],
        num_questions=3,
    )

    generator = QuestionGeneratorService(llm_service=mock_llm)
    q1 = generator.generate_question(config=config, question_number=1)

    assert isinstance(q1, Question)
    assert q1.question_number == 1
    assert q1.text is not None and len(q1.text) > 10
    assert q1.topic == "Cloud"
    assert len(q1.expected_concepts) >= 1
    assert q1.metadata.get("strategy_objective") is not None


def test_question_validator_anti_duplication():
    """Test QuestionValidator detects duplicate and near-identical questions."""
    q1 = Question(
        question_number=1,
        text="Explain how indexing works in relational databases and how B-Trees improve query lookup.",
        category="SQL",
        topic="SQL",
        expected_concepts=["B-Trees", "Lookup complexity"],
    )
    q_exact = Question(
        question_number=2,
        text="Explain how indexing works in relational databases and how B-Trees improve query lookup.",
        category="SQL",
        topic="SQL",
        expected_concepts=["B-Trees", "Lookup complexity"],
    )
    q_similar = Question(
        question_number=2,
        text="How does database indexing function in relational databases and how do B-Trees optimize queries?",
        category="SQL",
        topic="SQL",
        expected_concepts=["B-Trees", "Indexes"],
    )
    q_different = Question(
        question_number=2,
        text="Describe horizontal pod autoscaling and memory limits in Kubernetes clusters.",
        category="Cloud",
        topic="Cloud",
        expected_concepts=["HPA", "cgroups"],
    )

    strategy = StrategyPlan(
        question_number=2,
        question_type=QuestionType.TECHNICAL,
        target_topic="SQL",
        category="SQL",
        difficulty=Difficulty.MEDIUM,
        objective="Assess indexing",
    )
    config = InterviewConfig(candidate_name="Alice", role="Engineer")

    # Exact duplicate should fail
    valid_exact, msg_exact = QuestionValidator.validate(q_exact, strategy, [q1], config)
    assert valid_exact is False
    assert "duplicate" in msg_exact.lower()

    # Similar duplicate should fail
    valid_sim, msg_sim = QuestionValidator.validate(q_similar, strategy, [q1], config)
    assert valid_sim is False
    assert "similar" in msg_sim.lower()

    # Distinct question should pass
    valid_diff, msg_diff = QuestionValidator.validate(q_different, strategy, [q1], config)
    assert valid_diff is True
    assert msg_diff is None


def test_question_generator_malformed_llm_fallback():
    """Test that when LLM produces malformed responses, fallback generator yields valid Question."""
    class MalformedLLM(MockLLMService):
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("Malformed JSON syntax in LLM stream")

    config = InterviewConfig(
        candidate_name="Elena Rostova",
        role="Distributed Systems Engineer",
        experience_level=ExperienceLevel.FIVE_PLUS,
        interview_type=InterviewType.ROLE_SPECIFIC,
        difficulty=Difficulty.HARD,
        topics=["System Design", "Distributed Systems"],
        num_questions=2,
    )

    generator = QuestionGeneratorService(llm_service=MalformedLLM(), max_retries=1)
    fallback_q = generator.generate_question(config=config, question_number=1)

    assert isinstance(fallback_q, Question)
    assert fallback_q.question_number == 1
    assert "System Design" in fallback_q.text or "System Design" in fallback_q.topic
    assert fallback_q.difficulty == Difficulty.HARD
    assert fallback_q.metadata.get("fallback") is True
    assert len(fallback_q.expected_concepts) >= 2
    assert len(fallback_q.evaluation_criteria) >= 2


# =====================================================================
# 4. DATABASE PERSISTENCE OF RICH QUESTION MODEL
# =====================================================================

def test_database_persistence_of_phase3_question(db_session):
    """Test persisting and retrieving full Phase 3 Question model with topics, type, criteria, and metadata."""
    config = InterviewConfig(
        candidate_name="Ada Lovelace",
        role="Chief Algorithm Engineer",
        experience_level=ExperienceLevel.FIVE_PLUS,
        interview_type=InterviewType.TECHNICAL,
        difficulty=Difficulty.HARD,
        topics=["Algorithms", "Data Structures"],
        num_questions=2,
    )

    candidate = InterviewRepository.get_or_create_candidate(db_session, config.candidate_name)
    interview = InterviewRepository.create_interview(db_session, candidate.id, config)

    # 1. Create rich Phase 3 Question
    rich_question = Question(
        question_number=1,
        text="Design a cache eviction policy supporting O(1) get, put, and evict under strict memory limits.",
        category="Algorithms & Data Structures",
        topic="Data Structures",
        difficulty=Difficulty.HARD,
        question_type=QuestionType.PROBLEM_SOLVING,
        expected_concepts=["Doubly linked list", "Hash map pointers", "Eviction synchronization"],
        evaluation_criteria=["Algorithmic complexity", "Concurrency safety", "Memory overhead analysis"],
        follow_up_possible=True,
        metadata={"strategy": "Problem Solving", "tier": "5+ years"},
    )

    # 2. Save Question to DB
    q_model = InterviewRepository.save_question(db_session, interview.id, rich_question)
    assert q_model.id is not None
    assert q_model.topic == "Data Structures"
    assert q_model.question_type == "Problem Solving"
    assert "Doubly linked list" in q_model.expected_concepts_json
    assert "Algorithmic complexity" in q_model.evaluation_criteria_json
    assert q_model.follow_up_possible == 1

    # 3. Save Answer and Finalize
    ans = CandidateAnswer(
        question_id=q_model.id,
        question_number=1,
        answer_text="Use an LRU Cache with a hash table mapping keys to doubly linked list nodes.",
    )
    ev = AnswerEvaluation(
        score=9.5,
        strengths=["Clear O(1) structure identification"],
        weaknesses=[],
        feedback="Masterful explanation.",
        suggested_improvement="Mention lock striping.",
    )
    InterviewRepository.save_answer_and_evaluation(db_session, q_model.id, ans, ev)

    summary = InterviewSummary(
        overall_score=9.5,
        strengths_summary=["Deep algorithms knowledge"],
        overall_feedback="Outstanding candidate.",
    )
    InterviewRepository.finalize_interview(db_session, interview.id, summary)

    # 4. Reconstruct InterviewResult
    result = InterviewRepository.get_interview_result(db_session, interview.id)
    assert result is not None
    assert len(result.pairs) == 1

    recovered_q = result.pairs[0].question
    assert recovered_q.id == q_model.id
    assert recovered_q.text == rich_question.text
    assert recovered_q.topic == "Data Structures"
    assert recovered_q.question_type == QuestionType.PROBLEM_SOLVING
    assert recovered_q.expected_concepts == ["Doubly linked list", "Hash map pointers", "Eviction synchronization"]
    assert recovered_q.evaluation_criteria == ["Algorithmic complexity", "Concurrency safety", "Memory overhead analysis"]
    assert recovered_q.follow_up_possible is True
    assert recovered_q.metadata.get("strategy") == "Problem Solving"
