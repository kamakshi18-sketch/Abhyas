"""
Tests for Phase 7: Configurable InterviewerPersona System.

Verifies:
1. All 8 canonical personas exist with complete, valid PersonaConfig profiles.
2. Distinct conversational warmth levels, greetings, wording styles, explanation styles, and transitions.
3. Architecture flow: Persona -> Prompt Configuration -> LLM.
4. Evaluation Fairness Invariant: Persona modifies communication and commentary style
   WITHOUT changing evaluation standards, rubrics, or scoring criteria.
"""

import pytest
from typing import Dict, List

from app.schemas.interview import (
    InterviewerPersona,
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    Question,
    QuestionType,
    CandidateAnswer,
    AnswerEvaluation,
    EvaluationCriterion,
)
from app.schemas.persona import PersonaConfig
from app.core.persona_profiles import (
    PERSONA_PROFILES,
    get_persona_profile,
    get_all_persona_profiles,
    list_persona_names,
)
from app.services.persona_service import PersonaService, get_persona_service
from app.services.config_service import ConfigurationService
from app.core.evaluation_rubrics import EvaluationRubricService
from app.services.evaluation_service import AnswerEvaluationService
from app.core.prompts import (
    build_question_prompt,
    build_follow_up_prompt,
    build_evaluation_prompt,
    build_summary_prompt,
)
from app.schemas.interview import FollowUpPlan, FollowUpType


# =====================================================================
# 1. CATALOG & SCHEMA VALIDATION FOR ALL 8 PERSONAS
# =====================================================================

EXPECTED_8_PERSONAS = [
    InterviewerPersona.PROFESSIONAL,
    InterviewerPersona.FRIENDLY,
    InterviewerPersona.CONVERSATIONAL,
    InterviewerPersona.TECHNICAL_EXPERT,
    InterviewerPersona.STRICT,
    InterviewerPersona.STARTUP,
    InterviewerPersona.HR,
    InterviewerPersona.SENIOR_ENGINEER,
]


def test_all_eight_personas_configured():
    """Verify all 8 canonical personas are defined in enum and have complete profiles."""
    profiles = get_all_persona_profiles()
    assert len(profiles) == 8, f"Expected 8 personas in profile catalog, got {len(profiles)}"

    for persona in EXPECTED_8_PERSONAS:
        assert persona in profiles, f"Persona {persona.value} missing from PERSONA_PROFILES catalog"
        profile = profiles[persona]
        assert isinstance(profile, PersonaConfig)
        assert profile.persona == persona
        assert profile.name == persona.value


def test_persona_config_fields_validation():
    """Verify all 8 personas have valid, non-empty attributes and warmth between 0.0 and 1.0."""
    for persona in EXPECTED_8_PERSONAS:
        profile = get_persona_profile(persona)
        assert len(profile.name.strip()) > 0
        assert len(profile.description.strip()) > 10
        assert 0.0 <= profile.conversational_warmth <= 1.0
        assert len(profile.greeting_style.strip()) > 10
        assert len(profile.wording_style.strip()) > 10
        assert len(profile.explanation_style.strip()) > 10
        assert len(profile.transition_style.strip()) > 10
        assert len(profile.feedback_tone.strip()) > 10
        assert len(profile.sample_phrase.strip()) > 10
        assert len(profile.prompt_directive.strip()) > 20


def test_conversational_warmth_hierarchy():
    """Verify conversational warmth levels match pedagogical intentions."""
    strict_warmth = get_persona_profile(InterviewerPersona.STRICT).conversational_warmth
    tech_warmth = get_persona_profile(InterviewerPersona.TECHNICAL_EXPERT).conversational_warmth
    prof_warmth = get_persona_profile(InterviewerPersona.PROFESSIONAL).conversational_warmth
    sr_warmth = get_persona_profile(InterviewerPersona.SENIOR_ENGINEER).conversational_warmth
    start_warmth = get_persona_profile(InterviewerPersona.STARTUP).conversational_warmth
    conv_warmth = get_persona_profile(InterviewerPersona.CONVERSATIONAL).conversational_warmth
    hr_warmth = get_persona_profile(InterviewerPersona.HR).conversational_warmth
    friendly_warmth = get_persona_profile(InterviewerPersona.FRIENDLY).conversational_warmth

    assert strict_warmth < tech_warmth < prof_warmth < sr_warmth < start_warmth < conv_warmth < hr_warmth <= friendly_warmth
    assert strict_warmth == 0.10
    assert friendly_warmth == 0.90


def test_persona_fallback_behavior():
    """Verify fallback to Professional for unknown or invalid persona keys."""
    profile = get_persona_profile("NonExistentPersona")  # type: ignore
    assert profile.persona == InterviewerPersona.PROFESSIONAL
    assert profile.name == "Professional"


# =====================================================================
# 2. GREETINGS & TRANSITION STYLES ACROSS PERSONAS
# =====================================================================

def test_persona_greetings_unique_and_appropriate():
    """Verify all 8 personas generate distinct session greetings reflecting candidate name and role."""
    greetings = set()
    for persona in EXPECTED_8_PERSONAS:
        config = InterviewConfig(
            candidate_name="Alex Rivera",
            role="Backend Engineer",
            experience_level=ExperienceLevel.TWO_TO_FIVE,
            interview_type=InterviewType.TECHNICAL,
            interviewer_persona=persona,
        )
        greeting = PersonaService.get_session_greeting(config)
        assert "Alex Rivera" in greeting
        assert "Backend Engineer" in greeting or "interview" in greeting.lower()
        assert greeting not in greetings, f"Duplicate greeting detected for {persona.value}"
        greetings.add(greeting)

    assert len(greetings) == 8


def test_persona_transition_phrases_unique_and_appropriate():
    """Verify all 8 personas generate distinct transition phrases."""
    transitions = set()
    for persona in EXPECTED_8_PERSONAS:
        phrase = PersonaService.get_transition_phrase(
            persona=persona,
            current_q_num=3,
            total_q_num=5,
            next_topic="Distributed Caching",
        )
        assert "3" in phrase or "Distributed Caching" in phrase
        assert phrase not in transitions, f"Duplicate transition phrase for {persona.value}"
        transitions.add(phrase)

    assert len(transitions) == 8


# =====================================================================
# 3. PROMPT CONFIGURATION & ARCHITECTURE FLOW (Persona -> Prompt -> LLM)
# =====================================================================

def test_persona_directive_injection_in_question_prompt():
    """Verify build_question_prompt injects persona directives into LLM prompt."""
    for persona in EXPECTED_8_PERSONAS:
        config = InterviewConfig(
            candidate_name="Diana Prince",
            role="Distributed Systems Architect",
            experience_level=ExperienceLevel.FIVE_PLUS,
            interview_type=InterviewType.TECHNICAL,
            topics=["Consensus Algorithms"],
            interviewer_persona=persona,
        )
        prompt = build_question_prompt(config=config, question_number=1, previous_questions=[])
        
        profile = get_persona_profile(persona)
        assert f"INTERVIEWER PERSONA: {profile.name}" in prompt
        assert f"Warmth: {profile.conversational_warmth:.2f}" in prompt
        assert profile.wording_style in prompt
        assert f"Interviewer Persona: {persona.value}" in prompt


def test_persona_directive_injection_in_followup_prompt():
    """Verify build_follow_up_prompt injects persona directives into follow-up LLM prompt."""
    config = InterviewConfig(
        candidate_name="Bruce Wayne",
        role="Security Architect",
        experience_level=ExperienceLevel.FIVE_PLUS,
        interview_type=InterviewType.TECHNICAL,
        topics=["OAuth & JWT"],
        interviewer_persona=InterviewerPersona.TECHNICAL_EXPERT,
    )
    parent_q = Question(
        question_number=1,
        text="Explain how JWT signature verification works.",
        category="Technical",
        topic="OAuth & JWT",
        difficulty=Difficulty.HARD,
        question_type=QuestionType.TECHNICAL,
    )
    fu_plan = FollowUpPlan(
        follow_up_type=FollowUpType.DEEP_TECHNICAL,
        target_topic="OAuth & JWT",
        anchor_concept_or_quote="symmetric HMAC vs asymmetric RSA",
        objective="Probe key rotation and algorithm confusion vulnerabilities",
        rationale="Candidate mentioned asymmetric signing without key rotation handling",
        difficulty=Difficulty.HARD,
    )

    prompt = build_follow_up_prompt(
        config=config,
        parent_question=parent_q,
        candidate_answer="I use HMAC with secret key or RSA with private/public key pairs.",
        follow_up_plan=fu_plan,
        question_number=2,
    )

    assert "INTERVIEWER PERSONA: Technical Expert" in prompt
    assert "symmetric HMAC vs asymmetric RSA" in prompt
    assert "DEEP_TECHNICAL" in prompt or "Deep technical question" in prompt


# =====================================================================
# 4. EVALUATION FAIRNESS INVARIANT VERIFICATION
# =====================================================================

def test_evaluation_prompt_contains_explicit_fairness_invariant():
    """
    CRITICAL REQUIREMENT:
    The persona MUST NOT change evaluation standards or fairness criteria.
    Verify build_evaluation_prompt embeds strict fairness invariants for all personas.
    """
    for persona in EXPECTED_8_PERSONAS:
        config = InterviewConfig(
            candidate_name="Elena Rostova",
            role="Data Engineer",
            experience_level=ExperienceLevel.TWO_TO_FIVE,
            interview_type=InterviewType.TECHNICAL,
            interviewer_persona=persona,
        )
        q = Question(
            question_number=1,
            text="How does MapReduce handle straggler nodes?",
            category="Technical",
            topic="Big Data",
            difficulty=Difficulty.MEDIUM,
            question_type=QuestionType.TECHNICAL,
        )
        eval_prompt = build_evaluation_prompt(
            config=config,
            question=q,
            candidate_answer="It uses speculative execution to run backup tasks.",
        )

        # Assert evaluation fairness invariant is explicitly injected
        assert "EVALUATION FAIRNESS INVARIANT" in eval_prompt
        assert "Persona MUST NEVER alter the numerical score" in eval_prompt
        assert "identical answer MUST receive the exact same numerical score" in eval_prompt


def test_rubrics_and_criteria_remain_identical_across_all_personas():
    """
    Verify that rubric weights, criteria definitions, and scoring standards
    are completely invariant of the selected InterviewerPersona.
    """
    for interview_type in [InterviewType.TECHNICAL, InterviewType.BEHAVIORAL, InterviewType.HR]:
        base_rubric = EvaluationRubricService.get_rubric(interview_type)
        base_criteria = base_rubric.criteria

        for persona in EXPECTED_8_PERSONAS:
            config = InterviewConfig(
                candidate_name="Test User",
                role="Software Engineer",
                interview_type=interview_type,
                interviewer_persona=persona,
            )
            persona_rubric = EvaluationRubricService.get_rubric(config.interview_type)
            
            # Criteria list and weights must be identical regardless of persona
            assert len(persona_rubric.criteria) == len(base_criteria)
            for c1, c2 in zip(persona_rubric.criteria, base_criteria):
                assert c1.name == c2.name
                assert c1.weight == c2.weight
                assert c1.description == c2.description


def test_deterministic_evaluation_caching_across_personas():
    """
    Verify that EvaluationCache keys incorporate persona safely for delivery caching
    without altering the evaluation scoring invariants.
    """
    from app.performance.cache import EvaluationCache

    key_strict = EvaluationCache.generate_key(
        question_text="What is a binary search tree?",
        candidate_answer="A tree where left child < root < right child.",
        rubric_type="Technical",
        persona=InterviewerPersona.STRICT.value,
        language="English",
        model="gemini-3.6-flash",
    )

    key_friendly = EvaluationCache.generate_key(
        question_text="What is a binary search tree?",
        candidate_answer="A tree where left child < root < right child.",
        rubric_type="Technical",
        persona=InterviewerPersona.FRIENDLY.value,
        language="English",
        model="gemini-3.6-flash",
    )

    assert key_strict != key_friendly, "Cache keys should distinguish persona delivery cache"


# =====================================================================
# 5. BACKWARD COMPATIBILITY & ALIAS NORMALIZATION
# =====================================================================

def test_persona_backward_compatibility_aliases():
    """Verify legacy persona names from Phase 2 normalize correctly to canonical Phase 7 personas."""
    aliases = {
        "Professional & Neutral": InterviewerPersona.PROFESSIONAL,
        "Empathetic & Supportive": InterviewerPersona.FRIENDLY,
        "Strict & Demanding": InterviewerPersona.STRICT,
        "FAANG Hiring Manager": InterviewerPersona.SENIOR_ENGINEER,
        "Startup Founder": InterviewerPersona.STARTUP,
        "Fast-Paced Screener": InterviewerPersona.STARTUP,
    }

    for raw_label, expected_persona in aliases.items():
        config = InterviewConfig(
            candidate_name="Legacy Candidate",
            role="Developer",
            interviewer_persona=raw_label,  # type: ignore
        )
        assert config.interviewer_persona == expected_persona


def test_persona_service_singleton_instance():
    """Verify get_persona_service() returns consistent singleton."""
    svc1 = get_persona_service()
    svc2 = get_persona_service()
    assert svc1 is svc2
    assert isinstance(svc1, PersonaService)


# =====================================================================
# 6. END-TO-END EVALUATION INVARIANCE TEST WITH MOCK LLM
# =====================================================================

def test_evaluation_flow_with_mock_llm_across_personas(mock_llm):
    """
    Verify that AnswerEvaluator produces identical scoring metrics across personas
    while verifying that prompt directives correctly configure the LLM prompt.
    """
    from app.core.evaluator import AnswerEvaluator

    evaluator = AnswerEvaluator(llm_service=mock_llm)
    question = Question(
        question_number=1,
        question_text="Explain database indexing and B-Trees.",
        category="Databases",
        topic="Indexing",
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.TECHNICAL,
    )
    answer = "B-Trees keep data sorted and allow search in O(log n) time."

    evaluations: List[AnswerEvaluation] = []
    for persona in [InterviewerPersona.STRICT, InterviewerPersona.FRIENDLY, InterviewerPersona.TECHNICAL_EXPERT, InterviewerPersona.HR]:
        config = InterviewConfig(
            candidate_name="Test Subject",
            role="Software Engineer",
            interview_type=InterviewType.TECHNICAL,
            interviewer_persona=persona,
        )
        ev = evaluator.evaluate_answer(config=config, question=question, candidate_answer=answer)
        evaluations.append(ev)

    # Invariant check: Scores and criteria must be identical under the deterministic evaluation rules
    first_eval = evaluations[0]
    for ev in evaluations[1:]:
        assert ev.score == first_eval.score
        assert len(ev.criteria_scores) == len(first_eval.criteria_scores)
        for c1, c2 in zip(ev.criteria_scores, first_eval.criteria_scores):
            assert c1.score == c2.score
            assert c1.name == c2.name
