"""
Configuration Service.
Encapsulates business logic for interview setup, topic catalogs, personas,
timing estimation, and pre-flight interview summaries.
"""

from typing import List, Dict, Any, Optional
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    InterviewMode,
    InterviewerPersona,
)


class ConfigurationService:
    """Service managing interview configuration catalogs, validation, and summary generation."""

    # Extensible Topic Catalog grouped by domain
    _TOPIC_CATALOG: Dict[str, List[str]] = {
        "Programming Languages": [
            "Python",
            "Java",
            "C++",
            "JavaScript",
            "TypeScript",
            "Go",
            "Rust",
        ],
        "Core CS & Foundations": [
            "Data Structures",
            "Algorithms",
            "Databases",
            "SQL",
            "Operating Systems",
            "Networking",
        ],
        "Engineering & Architecture": [
            "Backend",
            "Frontend",
            "APIs",
            "Cloud",
            "DevOps",
            "System Design",
            "Microservices",
            "Security",
        ],
        "AI & Data Science": [
            "Machine Learning",
            "AI",
            "Data Engineering",
            "LLMs & GenAI",
        ],
        "Behavioral & Leadership": [
            "Behavioral",
            "Leadership",
            "Communication",
            "Conflict Resolution",
            "Project Management",
        ],
    }

    # Persona definitions and coaching style descriptions
    _PERSONA_DESCRIPTIONS: Dict[InterviewerPersona, str] = {
        InterviewerPersona.PROFESSIONAL: "Balanced, objective, and neutral standard hiring panel tone.",
        InterviewerPersona.EMPATHETIC: "Encouraging, supportive, providing warm feedback and guidance.",
        InterviewerPersona.STRICT: "Demanding high precision, challenging assumptions and edge cases.",
        InterviewerPersona.FAANG_LEAD: "Deep focus on scalability, optimal algorithms, and distributed systems.",
        InterviewerPersona.STARTUP_FOUNDER: "Practical, fast execution, cross-functional ownership, and agility.",
        InterviewerPersona.FAST_PACED: "Concise, rapid-fire screening evaluating quick recall and breadth.",
    }

    # Supported interview languages
    _SUPPORTED_LANGUAGES: List[str] = [
        "English",
        "Spanish",
        "French",
        "German",
        "Hindi",
        "Mandarin",
        "Japanese",
    ]

    # Mode availability status for Phase 2 vs Future Phases
    _SUPPORTED_MODES: Dict[InterviewMode, bool] = {
        InterviewMode.TEXT: True,             # Implemented in Phase 1 & 2
        InterviewMode.VOICE: False,           # Future Phase
        InterviewMode.VIDEO: False,           # Future Phase
        InterviewMode.CODING: False,          # Future Phase
        InterviewMode.SQL: False,             # Future Phase
        InterviewMode.SYSTEM_DESIGN: False,   # Future Phase
    }

    @classmethod
    def get_topic_catalog(cls) -> Dict[str, List[str]]:
        """Return categorized dictionary of all default topics."""
        return {cat: list(topics) for cat, topics in cls._TOPIC_CATALOG.items()}

    @classmethod
    def get_all_topics(cls) -> List[str]:
        """Return flat list of all default topics."""
        flat = []
        for topics in cls._TOPIC_CATALOG.values():
            flat.extend(topics)
        return list(dict.fromkeys(flat))

    @classmethod
    def get_personas(cls) -> Dict[InterviewerPersona, str]:
        """Return mapping of InterviewerPersonas to their descriptions."""
        return cls._PERSONA_DESCRIPTIONS.copy()

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Return list of supported languages."""
        return list(cls._SUPPORTED_LANGUAGES)

    @classmethod
    def get_supported_modes(cls) -> Dict[InterviewMode, bool]:
        """Return dictionary indicating which modes are currently active."""
        return cls._SUPPORTED_MODES.copy()

    @classmethod
    def calculate_recommended_duration(cls, num_questions: int, difficulty: Difficulty) -> int:
        """
        Compute recommended interview duration based on question count and difficulty.
        Easy: 4 mins/q, Medium: 5 mins/q, Hard: 7 mins/q, Adaptive: 5 mins/q.
        """
        minutes_per_q = {
            Difficulty.EASY: 4,
            Difficulty.MEDIUM: 5,
            Difficulty.HARD: 7,
            Difficulty.ADAPTIVE: 5,
        }.get(difficulty, 5)

        return max(10, num_questions * minutes_per_q)

    @classmethod
    def build_config_summary(cls, config: InterviewConfig) -> Dict[str, Any]:
        """
        Generate structured summary dictionary for pre-flight display before launching interview.
        """
        return {
            "Candidate Name": config.candidate_name,
            "Target Role": config.role or "Software Engineer",
            "Experience Level": config.experience_level.value,
            "Interview Type": config.interview_type.value,
            "Difficulty": config.difficulty.value,
            "Selected Topics": ", ".join(config.topics) if config.topics else "General / None",
            "Total Questions": config.num_questions,
            "Estimated Duration": f"{config.estimated_duration_minutes} minutes",
            "Language": config.language,
            "Interviewer Persona": config.interviewer_persona.value,
            "Interview Mode": config.mode.value,
        }

    @classmethod
    def validate_and_build(cls, data: Dict[str, Any]) -> InterviewConfig:
        """Parse raw dictionary and validate into an InterviewConfig instance."""
        return InterviewConfig.model_validate(data)


_global_config_service = ConfigurationService()


def get_config_service() -> ConfigurationService:
    """Return singleton ConfigurationService."""
    return _global_config_service
