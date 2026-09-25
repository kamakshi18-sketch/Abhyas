"""
Persona Service (Phase 7).
Business logic layer for Interviewer Persona management, conversational styling,
greeting formatting, transition phrasing, and prompt directive construction.

Architecture Flow:
Persona -> Prompt Configuration -> LLM
Configuration-driven, zero duplicated interview logic.

Fairness Invariant:
Persona only customizes communication delivery (greeting, tone, wording, warmth, transition, explanation).
Evaluation rubrics, correctness standards, and fairness criteria remain strictly unchanged across all personas.
"""

import logging
from typing import Dict, List, Optional
from app.schemas.interview import InterviewerPersona, InterviewConfig, Question, Difficulty
from app.schemas.persona import PersonaConfig
from app.core.persona_profiles import (
    PERSONA_PROFILES,
    get_persona_profile,
    get_all_persona_profiles,
    list_persona_names,
)

logger = logging.getLogger(__name__)


class PersonaService:
    """Service providing configuration-driven persona management and prompt styling."""

    @classmethod
    def get_profile(cls, persona: InterviewerPersona) -> PersonaConfig:
        """Retrieve PersonaConfig profile for the specified persona."""
        return get_persona_profile(persona)

    @classmethod
    def get_all_profiles(cls) -> Dict[InterviewerPersona, PersonaConfig]:
        """Return all available persona configurations."""
        return get_all_persona_profiles()

    @classmethod
    def get_available_personas(cls) -> List[InterviewerPersona]:
        """Return list of all supported canonical InterviewerPersona enums."""
        return [
            InterviewerPersona.PROFESSIONAL,
            InterviewerPersona.FRIENDLY,
            InterviewerPersona.CONVERSATIONAL,
            InterviewerPersona.TECHNICAL_EXPERT,
            InterviewerPersona.STRICT,
            InterviewerPersona.STARTUP,
            InterviewerPersona.HR,
            InterviewerPersona.SENIOR_ENGINEER,
        ]

    @classmethod
    def format_persona_prompt_directive(cls, persona: InterviewerPersona) -> str:
        """
        Generate structured prompt instructions for LLM question generation,
        contextual follow-ups, and answer commentary formatting.
        """
        profile = cls.get_profile(persona)
        return (
            f"=== INTERVIEWER PERSONA: {profile.name} ===\n"
            f"- Conversational Warmth: {profile.conversational_warmth:.2f} / 1.0\n"
            f"- Greeting Style: {profile.greeting_style}\n"
            f"- Wording Style: {profile.wording_style}\n"
            f"- Explanation Style: {profile.explanation_style}\n"
            f"- Transition Style: {profile.transition_style}\n"
            f"- Feedback Delivery Tone: {profile.feedback_tone}\n"
            f"- Persona Prompt Directives:\n{profile.prompt_directive}\n"
            f"========================================"
        )

    @classmethod
    def format_evaluation_fairness_directive(cls, persona: InterviewerPersona) -> str:
        """
        Generate strict evaluation fairness prompt instructions.
        Ensures persona customizes ONLY commentary delivery style without biasing scoring or rubric standards.
        """
        profile = cls.get_profile(persona)
        return (
            f"=== EVALUATION FAIRNESS INVARIANT (Phase 7) ===\n"
            f"Interviewer Persona: {profile.name} (Warmth: {profile.conversational_warmth:.2f}/1.0)\n"
            f"CRITICAL FAIRNESS RULE:\n"
            f"1. Persona STRICTLY governs the conversational tone, wording, and delivery style of feedback and suggested improvements.\n"
            f"2. Persona MUST NEVER alter the numerical score, grading rigor, criteria weights, or correctness evaluation standards.\n"
            f"3. An identical answer MUST receive the exact same numerical score and criteria breakdown regardless of whether the persona is Strict, Friendly, Technical Expert, or Professional.\n"
            f"4. Deliver narrative feedback matching: {profile.feedback_tone}\n"
            f"==============================================="
        )

    @classmethod
    def get_session_greeting(cls, config: InterviewConfig) -> str:
        """
        Generate introductory persona-aligned session greeting for the candidate.
        """
        profile = cls.get_profile(config.interviewer_persona)
        name = config.candidate_name
        role = config.role or "Software Engineer"

        greetings = {
            InterviewerPersona.PROFESSIONAL: (
                f"Good day, {name}. Welcome to your {config.interview_type.value} interview for the {role} position. "
                f"We have structured a series of questions to assess your experience and domain proficiency. Let us begin."
            ),
            InterviewerPersona.FRIENDLY: (
                f"Hi {name}! Welcome to your mock interview for {role}. "
                f"I'm really excited to chat with you today! We'll go through some great scenarios together, so take a deep breath and feel free to think out loud. Let's get started!"
            ),
            InterviewerPersona.CONVERSATIONAL: (
                f"Hey {name}, great to meet you! Thanks for jumping into this {role} session today. "
                f"Think of this as a relaxed engineering discussion and whiteboarding chat between peers. Let's dive right in!"
            ),
            InterviewerPersona.TECHNICAL_EXPERT: (
                f"Welcome, {name}. Today's session for {role} will focus deeply on architectural principles, algorithmic mechanics, and technical trade-offs. "
                f"Please be as specific and technically rigorous as possible. Let us begin."
            ),
            InterviewerPersona.STRICT: (
                f"Hello {name}. We will be conducting a rigorous assessment for the {role} role. "
                f"We have a full agenda with strict time boundaries. Please ensure your answers are concise, accurate, and direct. Here is your first question."
            ),
            InterviewerPersona.STARTUP: (
                f"Hey {name}! Welcome to your {role} interview. In our fast-moving startup environment, we value pragmatic problem-solving, speed of iteration, and high ownership. "
                f"Let's jump straight into real problems and see how you build and deliver. Let's go!"
            ),
            InterviewerPersona.HR: (
                f"Hello {name}, it is a pleasure to meet you today! Welcome to your {role} interview. "
                f"Our goal is to understand your career journey, your collaborative style, and how you tackle team challenges. Let's begin our conversation."
            ),
            InterviewerPersona.SENIOR_ENGINEER: (
                f"Hey {name}, welcome! I'm looking forward to talking through systems, production challenges, and practical engineering trade-offs for {role}. "
                f"I love hearing about how things actually work in production when traffic hits. Let's get into our first problem."
            ),
        }
        return greetings.get(config.interviewer_persona, greetings[InterviewerPersona.PROFESSIONAL])

    @classmethod
    def get_transition_phrase(
        cls,
        persona: InterviewerPersona,
        current_q_num: int,
        total_q_num: int,
        next_topic: Optional[str] = None,
    ) -> str:
        """
        Generate contextual, persona-aligned transition statement between questions.
        """
        profile = cls.get_profile(persona)
        topic_suffix = f" regarding {next_topic}" if next_topic else ""

        transitions = {
            InterviewerPersona.PROFESSIONAL: (
                f"Thank you. Moving to Question {current_q_num} of {total_q_num}{topic_suffix}."
            ),
            InterviewerPersona.FRIENDLY: (
                f"Great job on that! Let's explore Question {current_q_num} of {total_q_num}{topic_suffix} next."
            ),
            InterviewerPersona.CONVERSATIONAL: (
                f"Awesome. Building on our discussion, let's take a look at Question {current_q_num} of {total_q_num}{topic_suffix}."
            ),
            InterviewerPersona.TECHNICAL_EXPERT: (
                f"Noted. Now let us analyze Question {current_q_num} of {total_q_num}{topic_suffix}."
            ),
            InterviewerPersona.STRICT: (
                f"Understood. Next question ({current_q_num}/{total_q_num}){topic_suffix}:"
            ),
            InterviewerPersona.STARTUP: (
                f"Got it! Let's keep moving fast—here's Question {current_q_num} of {total_q_num}{topic_suffix}:"
            ),
            InterviewerPersona.HR: (
                f"Thank you for sharing that insight. Let's move to Question {current_q_num} of {total_q_num}{topic_suffix}."
            ),
            InterviewerPersona.SENIOR_ENGINEER: (
                f"Solid. Now let's shift gears to Question {current_q_num} of {total_q_num}{topic_suffix}."
            ),
        }
        return transitions.get(persona, transitions[InterviewerPersona.PROFESSIONAL])


_global_persona_service = PersonaService()


def get_persona_service() -> PersonaService:
    """Return singleton PersonaService."""
    return _global_persona_service
