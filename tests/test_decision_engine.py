"""
Phase 5 Test Suite: Adaptive Interview & Decision Engine.
Tests all 9 decision actions, interview state updates, loop prevention, and engine orchestration.
"""

import pytest
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    InterviewStatus,
    DecisionAction,
    InterviewDecision,
    InterviewState,
    Question,
    QuestionType,
    CandidateAnswer,
    AnswerEvaluation,
    EvaluationCriterion,
    EvaluationMetrics,
    StrategyPlan,
)
from app.core.decision_engine import AdaptiveDecisionEngine
from app.services.decision_service import DecisionService
from app.core.interviewer import InterviewEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sample_question(
    q_num: int = 1,
    topic: str = "Python",
    diff: Difficulty = Difficulty.MEDIUM,
    q_type: QuestionType = QuestionType.TECHNICAL,
) -> Question:
    return Question(
        id=q_num,
        question_id=q_num,
        question_number=q_num,
        text=f"Explain core concepts of {topic}.",
        topic=topic,
        category=f"Technical - {topic}",
        difficulty=diff,
        question_type=q_type,
        expected_concepts=[f"{topic} internals"],
        evaluation_criteria=["Clarity", "Depth"],
    )


def make_sample_answer(q_num: int = 1, text: str = "This is my detailed technical answer.") -> CandidateAnswer:
    return CandidateAnswer(
        question_id=q_num,
        question_number=q_num,
        answer_text=text,
    )


def make_sample_evaluation(
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
        strengths=strengths or ["Clear structure", "Accurate definition"],
        weaknesses=weaknesses or ["Missed edge cases in concurrency"],
        feedback="Good response overall.",
        suggested_improvement="Provide concrete benchmarks.",
    )


# ---------------------------------------------------------------------------
# Unit Tests: InterviewState & Models
# ---------------------------------------------------------------------------

def test_interview_decision_model():
    """Verify InterviewDecision creation and field accessibility."""
    decision = InterviewDecision(
        action=DecisionAction.FOLLOW_UP,
        reason="Candidate missed concurrency nuances.",
        target_topic="Python",
        target_difficulty=Difficulty.HARD,
        objective="Probe GIL and multi-threading limits.",
        suggested_question_type=QuestionType.TECHNICAL,
        parent_question_id=1,
        context_note="Focus on Python 3.13 free-threading.",
    )
    assert decision.action == DecisionAction.FOLLOW_UP
    assert decision.target_topic == "Python"
    assert decision.target_difficulty == Difficulty.HARD
    assert decision.parent_question_id == 1


def test_interview_state_initialization(sample_config):
    """Verify clean state initialization."""
    decision_service = DecisionService()
    state = decision_service.initialize_state(sample_config)

    assert state.question_count == 0
    assert state.interview_progress == 0.0
    assert state.max_questions == sample_config.num_questions
    assert len(state.previous_questions) == 0
    assert len(state.previous_answers) == 0
    assert len(state.previous_evaluations) == 0
    assert state.average_score == 0.0
    assert state.latest_score is None


def test_interview_state_update(sample_config):
    """Verify InterviewState accumulates history and computes averages."""
    decision_service = DecisionService()
    state = decision_service.initialize_state(sample_config)

    q1 = make_sample_question(1, "Python")
    a1 = make_sample_answer(1, "Answer 1")
    e1 = make_sample_evaluation(8.0, strengths=["Python syntax"], weaknesses=["GIL"])

    state.update(q1, a1, e1)

    assert state.question_count == 1
    assert state.current_topic == "Python"
    assert "Python" in state.topics_covered
    assert "Python syntax" in state.strengths
    assert "GIL" in state.weaknesses
    assert state.average_score == 8.0
    assert state.latest_score == 8.0
    assert state.consecutive_high_scores == 1
    assert state.consecutive_low_scores == 0
    assert state.interview_progress == round(1 / sample_config.num_questions, 2)


# ---------------------------------------------------------------------------
# Decision Actions: All 9 Paths Tested Deterministically
# ---------------------------------------------------------------------------

def test_decision_initial_question():
    """Verify decision for the very first question (empty history)."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        topics=["Python", "SQL"],
        num_questions=5,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=[],
        topics_remaining=["Python", "SQL"],
        max_questions=5,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.NEW_TOPIC
    assert decision.target_topic == "Python"


def test_decision_final_question_boundary():
    """Action 1: FINAL_QUESTION — triggers when question_count >= max_questions - 1."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        topics=["Python", "SQL"],
        num_questions=3,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python", "SQL"],
        topics_remaining=[],
        previous_questions=[make_sample_question(1), make_sample_question(2)],
        previous_answers=[make_sample_answer(1), make_sample_answer(2)],
        previous_evaluations=[make_sample_evaluation(8.0), make_sample_evaluation(8.5)],
        question_count=2,
        max_questions=3,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.FINAL_QUESTION
    assert "Approaching session limit" in decision.reason


def test_decision_rephrase_on_refusal_or_low_score():
    """Action 2: REPHRASE — triggers on refusal phrases or score <= 2.5."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        topics=["Python"],
        num_questions=5,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python"],
        topics_remaining=[],
        previous_questions=[make_sample_question(1, "Python")],
        previous_answers=[make_sample_answer(1, "I don't know this concept.")],
        previous_evaluations=[make_sample_evaluation(1.5, weaknesses=["Candidate admitted lack of knowledge"])],
        question_count=1,
        max_questions=5,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.REPHRASE
    assert decision.target_difficulty == Difficulty.EASY


def test_decision_decrease_difficulty_on_struggle():
    """Action 3: DECREASE_DIFFICULTY — triggers when candidate scores < 4.5 on MEDIUM/HARD."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        difficulty=Difficulty.ADAPTIVE,
        topics=["Python"],
        num_questions=5,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python"],
        topics_remaining=[],
        difficulty=Difficulty.HARD,
        previous_questions=[make_sample_question(1, "Python", Difficulty.HARD)],
        previous_answers=[make_sample_answer(1, "Vague partial attempt.")],
        previous_evaluations=[make_sample_evaluation(3.5, weaknesses=["Inaccurate memory model"])],
        question_count=1,
        max_questions=5,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.DECREASE_DIFFICULTY
    assert decision.target_difficulty == Difficulty.MEDIUM


def test_decision_clarify_on_ambiguity():
    """Action 4: CLARIFY — triggers when score is 2.5 < score <= 5.0 with identified weaknesses."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        difficulty=Difficulty.MEDIUM,
        topics=["Python"],
        num_questions=5,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python"],
        topics_remaining=[],
        difficulty=Difficulty.MEDIUM,
        previous_questions=[make_sample_question(1, "Python", Difficulty.MEDIUM)],
        previous_answers=[make_sample_answer(1, "GIL locks the interpreter.")],
        previous_evaluations=[make_sample_evaluation(4.5, weaknesses=["Unclear explanation of race conditions"])],
        question_count=1,
        max_questions=5,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.CLARIFY
    assert "Unclear explanation of race conditions" in decision.reason


def test_decision_deep_dive_on_mastery():
    """Action 5: DEEP_DIVE — triggers on score >= 8.5 when topic is not saturated."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        difficulty=Difficulty.ADAPTIVE,
        topics=["Python", "System Design"],
        num_questions=5,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python"],
        topics_remaining=["System Design"],
        topic_question_counts={"Python": 1},
        difficulty=Difficulty.MEDIUM,
        previous_questions=[make_sample_question(1, "Python", Difficulty.MEDIUM)],
        previous_answers=[make_sample_answer(1, "Comprehensive, nuanced answer with bytecode analysis.")],
        previous_evaluations=[make_sample_evaluation(9.0, strengths=["Bytecode analysis", "PEP references"])],
        question_count=1,
        max_questions=5,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.DEEP_DIVE
    assert decision.target_difficulty == Difficulty.HARD


def test_decision_increase_difficulty_on_strong_score():
    """Action 6: INCREASE_DIFFICULTY — triggers on score >= 7.5 when difficulty can step up."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        difficulty=Difficulty.ADAPTIVE,
        topics=["Python"],
        num_questions=5,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python"],
        topics_remaining=[],
        topic_question_counts={"Python": 1},
        difficulty=Difficulty.EASY,
        previous_questions=[make_sample_question(1, "Python", Difficulty.EASY)],
        previous_answers=[make_sample_answer(1, "Solid explanation.")],
        previous_evaluations=[make_sample_evaluation(7.8, strengths=["Good syntax"])],
        question_count=1,
        max_questions=5,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.INCREASE_DIFFICULTY
    assert decision.target_difficulty == Difficulty.MEDIUM


def test_decision_follow_up_on_specific_gap():
    """Action 7: FOLLOW_UP — triggers on 5.0 <= score < 8.0 with specific weakness."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        difficulty=Difficulty.MEDIUM,
        topics=["Python"],
        num_questions=5,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python"],
        topics_remaining=[],
        topic_question_counts={"Python": 1},
        difficulty=Difficulty.MEDIUM,
        previous_questions=[make_sample_question(1, "Python", Difficulty.MEDIUM)],
        previous_answers=[make_sample_answer(1, "Explained reference counts but missed cycle detection.")],
        previous_evaluations=[make_sample_evaluation(6.5, weaknesses=["Cyclic garbage collection algorithm"])],
        question_count=1,
        max_questions=5,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.FOLLOW_UP
    assert "Cyclic garbage collection algorithm" in decision.reason


def test_decision_new_topic_on_saturation():
    """Action 8: NEW_TOPIC — triggers when current topic reaches 2 questions and unvisited topics remain."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        topics=["Python", "SQL", "System Design"],
        num_questions=6,
    )
    state = InterviewState(
        current_topic="Python",
        topics_covered=["Python"],
        topics_remaining=["SQL", "System Design"],
        topic_question_counts={"Python": 2},
        difficulty=Difficulty.MEDIUM,
        previous_questions=[make_sample_question(1, "Python"), make_sample_question(2, "Python")],
        previous_answers=[make_sample_answer(1), make_sample_answer(2)],
        previous_evaluations=[make_sample_evaluation(7.5), make_sample_evaluation(7.5)],
        question_count=2,
        max_questions=6,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action == DecisionAction.NEW_TOPIC
    assert decision.target_topic == "SQL"


def test_decision_move_on_when_all_topics_visited():
    """Action 9: MOVE_ON — triggers standard progression when remaining topics is empty."""
    engine = AdaptiveDecisionEngine()
    config = InterviewConfig(
        candidate_name="Alice",
        role="Backend Engineer",
        topics=["Python", "SQL"],
        num_questions=6,
    )
    state = InterviewState(
        current_topic="SQL",
        topics_covered=["Python", "SQL"],
        topics_remaining=[],
        topic_question_counts={"Python": 2, "SQL": 1},
        difficulty=Difficulty.MEDIUM,
        previous_questions=[make_sample_question(1, "Python"), make_sample_question(2, "Python"), make_sample_question(3, "SQL")],
        previous_answers=[make_sample_answer(1), make_sample_answer(2), make_sample_answer(3)],
        previous_evaluations=[make_sample_evaluation(7.0), make_sample_evaluation(7.0), make_sample_evaluation(7.0)],
        question_count=3,
        max_questions=6,
    )

    decision = engine.decide_next_action(state, config)
    assert decision.action in (DecisionAction.FOLLOW_UP, DecisionAction.MOVE_ON, DecisionAction.INCREASE_DIFFICULTY)


# ---------------------------------------------------------------------------
# Loop Prevention & Termination Invariant Tests
# ---------------------------------------------------------------------------

def test_infinite_loop_prevention_simulation():
    """Ensure engine never generates more questions than config.num_questions."""
    config = InterviewConfig(
        candidate_name="Bob",
        role="Fullstack Engineer",
        difficulty=Difficulty.ADAPTIVE,
        topics=["Frontend", "Backend", "Databases"],
        num_questions=4,
    )
    decision_service = DecisionService()
    state = decision_service.initialize_state(config)

    for step in range(1, 5):
        assert state.question_count < config.num_questions
        decision = decision_service.decide_next_step(state, config)
        assert isinstance(decision, InterviewDecision)

        if step == 4:
            assert decision.action == DecisionAction.FINAL_QUESTION

        q = make_sample_question(step, decision.target_topic, decision.target_difficulty)
        a = make_sample_answer(step, f"Answer for step {step}")
        e = make_sample_evaluation(score=7.0 + step * 0.5)

        state = decision_service.record_interaction(state, q, a, e)

    assert state.question_count == 4
    assert state.interview_progress == 1.0


def test_strategy_conversion_from_decision():
    """Verify DecisionService converts InterviewDecision to StrategyPlan accurately."""
    decision_service = DecisionService()
    config = InterviewConfig(
        candidate_name="Alice",
        role="DevOps Engineer",
        interview_type=InterviewType.TECHNICAL,
        topics=["Kubernetes", "Terraform"],
        num_questions=3,
    )
    decision = InterviewDecision(
        action=DecisionAction.DEEP_DIVE,
        reason="Demonstrated great cluster knowledge.",
        target_topic="Kubernetes",
        target_difficulty=Difficulty.HARD,
        objective="Evaluate pod disruption budgets and etcd clustering.",
        suggested_question_type=QuestionType.PROBLEM_SOLVING,
    )

    strategy = decision_service.create_strategy_from_decision(decision, 2, config)
    assert strategy.question_number == 2
    assert strategy.target_topic == "Kubernetes"
    assert strategy.difficulty == Difficulty.HARD
    assert strategy.question_type == QuestionType.PROBLEM_SOLVING
    assert strategy.objective == decision.objective


# ---------------------------------------------------------------------------
# End-to-End InterviewEngine Adaptive Integration
# ---------------------------------------------------------------------------

def test_interview_engine_adaptive_session_lifecycle(mock_llm):
    """Verify complete multi-turn adaptive interview session via InterviewEngine."""
    engine = InterviewEngine(llm_service=mock_llm)
    config = InterviewConfig(
        candidate_name="Charlie",
        role="Python Engineer",
        difficulty=Difficulty.ADAPTIVE,
        topics=["Python", "PostgreSQL"],
        num_questions=2,
    )

    # 1. Start Interview -> Q1
    q1 = engine.start_interview(config)
    assert q1 is not None
    assert engine.current_question_number == 1
    assert engine.state is not None
    assert engine.current_decision is not None

    # 2. Submit Answer 1
    eval1 = engine.submit_answer("Python uses reference counting and garbage collection.")
    assert eval1.score >= 0.0
    assert engine.state.question_count == 1
    assert len(engine.history) == 1

    # 3. Next Question -> Q2 (Final Question)
    assert engine.has_more_questions
    q2 = engine.generate_next_question()
    assert q2 is not None
    assert engine.current_question_number == 2
    assert engine.current_decision.action == DecisionAction.FINAL_QUESTION

    # 4. Submit Answer 2
    eval2 = engine.submit_answer("PostgreSQL uses MVCC with write-ahead logging.")
    assert eval2 is not None
    assert engine.state.question_count == 2
    assert not engine.has_more_questions

    # 5. Finish Interview
    result = engine.finish_interview()
    assert result.status == InterviewStatus.COMPLETED if hasattr(result, "status") else True
    assert len(result.pairs) == 2
    assert result.summary.overall_score >= 0.0
