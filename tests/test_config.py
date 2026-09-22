"""
Unit and integration tests for Phase 2: Advanced Interview Configuration.
Tests schema validation, boundary values, service layer, serialization, and database persistence.
"""

import json
import pytest
from pydantic import ValidationError

from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    InterviewMode,
    InterviewerPersona,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    EvaluationMetrics,
    InterviewSummary,
)
from app.services.config_service import ConfigurationService
from app.database.repository import InterviewRepository


# =====================================================================
# 1. VALID CONFIGURATION TESTS
# =====================================================================

def test_valid_configuration_defaults():
    """Test creating an InterviewConfig with minimum required fields and verify default values."""
    config = InterviewConfig(
        candidate_name="Alex Turner",
        role="Backend Engineer",
    )
    assert config.candidate_name == "Alex Turner"
    assert config.role == "Backend Engineer"
    assert config.experience_level == ExperienceLevel.TWO_TO_FIVE
    assert config.interview_type == InterviewType.TECHNICAL
    assert config.difficulty == Difficulty.MEDIUM
    assert config.num_questions == 5
    assert config.estimated_duration_minutes == 30
    assert config.language == "English"
    assert config.interviewer_persona == InterviewerPersona.PROFESSIONAL
    assert config.mode == InterviewMode.TEXT
    assert len(config.topics) >= 1


def test_valid_configuration_custom_values():
    """Test InterviewConfig with comprehensive custom Phase 2 values."""
    config = InterviewConfig(
        candidate_name="Priya Sharma",
        role="AI Systems Architect",
        experience_level=ExperienceLevel.FIVE_PLUS,
        interview_type=InterviewType.ROLE_SPECIFIC,
        difficulty=Difficulty.ADAPTIVE,
        num_questions=8,
        estimated_duration_minutes=35,
        language="English",
        interviewer_persona=InterviewerPersona.STRICT,
        mode=InterviewMode.TEXT,
        topics=["Python", "Machine Learning", "System Design", "Cloud"],
    )
    assert config.candidate_name == "Priya Sharma"
    assert config.role == "AI Systems Architect"
    assert config.experience_level == ExperienceLevel.FIVE_PLUS
    assert config.interview_type == InterviewType.ROLE_SPECIFIC
    assert config.difficulty == Difficulty.ADAPTIVE
    assert config.num_questions == 8
    assert config.estimated_duration_minutes == 35
    assert config.interviewer_persona == InterviewerPersona.STRICT
    assert len(config.topics) == 4
    assert "Machine Learning" in config.topics


# =====================================================================
# 2. INVALID CONFIGURATION & BOUNDARY TESTS
# =====================================================================

def test_invalid_candidate_name_empty():
    """Test validation failure when candidate name is blank or whitespace."""
    with pytest.raises(ValidationError) as excinfo:
        InterviewConfig(candidate_name="", role="Developer")
    assert "candidate_name" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        InterviewConfig(candidate_name="   ", role="Developer")
    assert "candidate_name" in str(excinfo.value)


def test_role_default_when_blank():
    """Test that role gracefully falls back to default if empty string given."""
    config = InterviewConfig(candidate_name="Bob", role="   ")
    assert config.role == "Software Engineer"


@pytest.mark.parametrize("invalid_count", [0, -1, -10, 26, 100])
def test_boundary_num_questions_invalid(invalid_count):
    """Test that question count outside [1, 25] raises ValidationError."""
    with pytest.raises(ValidationError):
        InterviewConfig(
            candidate_name="Charlie",
            role="QA Engineer",
            num_questions=invalid_count,
        )


@pytest.mark.parametrize("valid_count", [1, 5, 10, 20, 25])
def test_boundary_num_questions_valid(valid_count):
    """Test that question count on exact boundaries [1, 25] succeeds."""
    config = InterviewConfig(
        candidate_name="Charlie",
        role="QA Engineer",
        num_questions=valid_count,
        estimated_duration_minutes=valid_count * 5,
    )
    assert config.num_questions == valid_count


@pytest.mark.parametrize("invalid_duration", [0, 4, -5, 181, 300])
def test_boundary_duration_invalid(invalid_duration):
    """Test that duration outside [5, 180] minutes raises ValidationError."""
    with pytest.raises(ValidationError):
        InterviewConfig(
            candidate_name="Dana",
            role="DevOps Specialist",
            estimated_duration_minutes=invalid_duration,
        )


@pytest.mark.parametrize("valid_duration", [5, 15, 60, 120, 180])
def test_boundary_duration_valid(valid_duration):
    """Test that duration on exact boundaries [5, 180] minutes succeeds."""
    config = InterviewConfig(
        candidate_name="Dana",
        role="DevOps Specialist",
        num_questions=5,
        estimated_duration_minutes=valid_duration,
    )
    assert config.estimated_duration_minutes == valid_duration


def test_topics_sanitization_and_cleaning():
    """Test that topic list cleans whitespace and falls back gracefully."""
    config = InterviewConfig(
        candidate_name="Eve",
        role="Full Stack",
        topics=["  Python  ", " SQL ", "", "   "],
    )
    assert config.topics == ["Python", "SQL"]

    # When all empty strings provided in technical interview, should fallback to default domain topics
    config_empty = InterviewConfig(
        candidate_name="Eve",
        role="Full Stack",
        topics=["", "  "],
    )
    assert len(config_empty.topics) >= 1
    assert "General Computer Science" in config_empty.topics or "Full Stack" in config_empty.topics


# =====================================================================
# 3. SERIALIZATION & DESERIALIZATION TESTS
# =====================================================================

def test_configuration_json_roundtrip():
    """Test that InterviewConfig serializes to JSON and recovers losslessly."""
    original = InterviewConfig(
        candidate_name="Grace Hopper",
        role="Compiler Architect",
        experience_level=ExperienceLevel.FIVE_PLUS,
        interview_type=InterviewType.PROJECT_BASED,
        difficulty=Difficulty.HARD,
        num_questions=12,
        estimated_duration_minutes=45,
        language="English",
        interviewer_persona=InterviewerPersona.FAANG_LEAD,
        mode=InterviewMode.TEXT,
        topics=["Data Structures", "Algorithms", "C++"],
    )

    json_str = original.model_dump_json()
    assert isinstance(json_str, str)
    
    # Parse back
    recovered = InterviewConfig.model_validate_json(json_str)
    assert recovered == original
    assert recovered.candidate_name == "Grace Hopper"
    assert recovered.interviewer_persona == InterviewerPersona.FAANG_LEAD
    assert recovered.topics == ["Data Structures", "Algorithms", "C++"]


# =====================================================================
# 4. CONFIGURATION SERVICE TESTS
# =====================================================================

def test_config_service_topic_catalog():
    """Test topic catalog integrity across all primary categories."""
    catalog = ConfigurationService.get_topic_catalog()
    assert isinstance(catalog, dict)
    
    required_categories = [
        "Programming Languages",
        "Core CS & Foundations",
        "Engineering & Architecture",
        "AI & Data Science",
        "Behavioral & Leadership",
    ]
    for cat in required_categories:
        assert cat in catalog, f"Category '{cat}' missing from topic catalog"

    flat_topics = ConfigurationService.get_all_topics()
    
    # Verify required topics from Phase 2 spec are all present
    required_topics = [
        "Python", "Java", "C++", "JavaScript",
        "Data Structures", "Algorithms",
        "Databases", "SQL", "APIs", "Backend", "Frontend",
        "Cloud", "DevOps", "System Design",
        "Machine Learning", "AI",
        "Behavioral", "Leadership", "Communication",
    ]
    for req in required_topics:
        assert req in flat_topics, f"Required topic '{req}' missing from flat topics catalog"


def test_config_service_persona_catalog():
    """Test persona definitions have valid descriptions."""
    personas = ConfigurationService.get_personas()
    assert len(personas) >= 5
    for p in InterviewerPersona:
        assert p in personas
        assert isinstance(personas[p], str)
        assert len(personas[p]) > 5


def test_config_service_duration_estimation():
    """Test dynamic duration calculation across difficulties."""
    dur_easy = ConfigurationService.calculate_recommended_duration(10, Difficulty.EASY)
    dur_medium = ConfigurationService.calculate_recommended_duration(10, Difficulty.MEDIUM)
    dur_hard = ConfigurationService.calculate_recommended_duration(10, Difficulty.HARD)
    dur_adaptive = ConfigurationService.calculate_recommended_duration(10, Difficulty.ADAPTIVE)

    assert dur_easy == 40       # 10 * 4 = 40
    assert dur_medium == 50     # 10 * 5 = 50
    assert dur_hard == 70       # 10 * 7 = 70
    assert dur_adaptive == 50   # 10 * 5 = 50


def test_config_service_summary_generation():
    """Test pre-flight summary generation conforms to required structure."""
    config = InterviewConfig(
        candidate_name="Leo Vance",
        role="Python Developer",
        experience_level=ExperienceLevel.FRESHER,
        interview_type=InterviewType.TECHNICAL,
        difficulty=Difficulty.ADAPTIVE,
        topics=["Python", "Data Structures", "SQL"],
        num_questions=10,
        estimated_duration_minutes=40,
        language="English",
        interviewer_persona=InterviewerPersona.EMPATHETIC,
    )
    summary = ConfigurationService.build_config_summary(config)
    
    assert summary["Candidate Name"] == "Leo Vance"
    assert summary["Target Role"] == "Python Developer"
    assert summary["Experience Level"] == "Fresher"
    assert summary["Interview Type"] == "Technical"
    assert summary["Difficulty"] == "Adaptive"
    assert summary["Selected Topics"] == "Python, Data Structures, SQL"
    assert summary["Total Questions"] == 10
    assert summary["Interview Mode"] == "TEXT"
    assert summary["Interviewer Persona"] == "Empathetic & Supportive"


def test_config_service_mode_statuses():
    """Test that TEXT mode is active and future modes are cleanly defined as unavailable."""
    modes = ConfigurationService.get_supported_modes()
    
    assert modes[InterviewMode.TEXT] is True
    assert modes[InterviewMode.VOICE] is False
    assert modes[InterviewMode.VIDEO] is False
    assert modes[InterviewMode.CODING] is False
    assert modes[InterviewMode.SQL] is False
    assert modes[InterviewMode.SYSTEM_DESIGN] is False


# =====================================================================
# 5. DATABASE PERSISTENCE & RETRIEVAL OF ADVANCED CONFIGURATION
# =====================================================================

def test_database_persistence_of_phase2_fields(db_session):
    """Test that all Phase 2 config attributes are stored in SQLite and recovered."""
    config = InterviewConfig(
        candidate_name="Marcus Aurelius",
        role="Chief Architect",
        experience_level=ExperienceLevel.FIVE_PLUS,
        interview_type=InterviewType.ROLE_SPECIFIC,
        difficulty=Difficulty.ADAPTIVE,
        num_questions=6,
        estimated_duration_minutes=30,
        language="English",
        interviewer_persona=InterviewerPersona.STARTUP_FOUNDER,
        mode=InterviewMode.TEXT,
        topics=["System Design", "Cloud", "Leadership"],
    )

    candidate = InterviewRepository.get_or_create_candidate(db_session, config.candidate_name)
    interview = InterviewRepository.create_interview(db_session, candidate.id, config)

    # Check direct model columns
    assert interview.id is not None
    assert interview.mode == "TEXT"
    assert interview.language == "English"
    assert interview.interviewer_persona == "Startup Founder"
    assert interview.estimated_duration_minutes == 30
    assert "System Design" in interview.topics_json
    assert interview.config_json is not None

    # Verify config_json can be parsed back to InterviewConfig
    parsed_dict = json.loads(interview.config_json)
    assert parsed_dict["candidate_name"] == "Marcus Aurelius"
    assert parsed_dict["difficulty"] == "Adaptive"
    assert parsed_dict["topics"] == ["System Design", "Cloud", "Leadership"]

    # Save question, answer, evaluation, summary
    q_schema = Question(
        question_number=1,
        question_text="How would you design a distributed rate limiter?",
        category="System Design",
        difficulty=Difficulty.HARD,
        expected_points=["Sliding window", "Redis token bucket", "Race conditions"],
    )
    q_model = InterviewRepository.save_question(db_session, interview.id, q_schema)

    ans_schema = CandidateAnswer(
        question_id=q_model.id,
        question_number=1,
        answer_text="I would use Redis with a sliding window log or token bucket using Lua scripts for atomicity.",
    )
    eval_schema = AnswerEvaluation(
        score=9.2,
        metrics=EvaluationMetrics(relevance=10, correctness=9, completeness=9, clarity=9, depth=9),
        strengths=["Mentioned Redis Lua scripts for concurrency"],
        weaknesses=[],
        feedback="Superb answer.",
        suggested_improvement="Could discuss distributed clock skew.",
    )
    InterviewRepository.save_answer_and_evaluation(db_session, q_model.id, ans_schema, eval_schema)

    summary_schema = InterviewSummary(
        overall_score=9.2,
        strengths_summary=["Deep architectural knowledge"],
        weaknesses_summary=[],
        overall_feedback="Outstanding session.",
        areas_to_improve=[],
    )
    InterviewRepository.finalize_interview(db_session, interview.id, summary_schema)

    # Retrieve full result
    result = InterviewRepository.get_interview_result(db_session, interview.id)
    assert result is not None
    assert result.config.candidate_name == "Marcus Aurelius"
    assert result.config.difficulty == Difficulty.ADAPTIVE
    assert result.config.interviewer_persona == InterviewerPersona.STARTUP_FOUNDER
    assert result.config.topics == ["System Design", "Cloud", "Leadership"]
    assert result.config.estimated_duration_minutes == 30
