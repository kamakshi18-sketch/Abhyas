"""
Unit tests for Phase 5: Adaptive Interview & Decision Engine.
Deterministic testing using mocked evaluations and state snapshots.
Covers all 9 DecisionActions, State tracking, Difficulty stepping, and Infinite Loop Prevention.
"""

import pytest
from app.schemas.interview import (
    InterviewConfig,
    InterviewState,
    InterviewDecision,
    DecisionAction,
    Difficulty,
    InterviewType,
    ExperienceLevel,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    EvaluationCriterion,
    EvaluationEvidence,
    EvaluationMetrics,
    QuestionType,
    StrategyPlan,
)
from app.core.decision_engine import DecisionEngine
from app.services.decision_service import DecisionService
from app.core.interviewer import InterviewEngine


@pytest.fixture
def base_config():
    return InterviewConfig(
        candidate_name="Priya Sharma",
        role="Senior Backend Engineer",
        interview_type=InterviewType.TECHNICAL,
        experience_level=ExperienceLevel.FIVE_PLUS,
        difficulty=Difficulty.ADAPTIVE,
        num_questions=5,
        estimated_duration_minutes=30,
        topics=["Distributed Systems", "Database Indexing", "Concurrency"],
    )


@pytest.fixture
def mock_evaluation_factory():
    def _create_eval(score: float, clarity: int = 8, strengths=None, weaknesses=None):
        str_list = strengths or ["Solid domain knowledge"]
        weak_list = weaknesses or ["Omitted cache invalidation details"]
        return AnswerEvaluation(
            score=score,
            criteria_scores=[
                EvaluationCriterion(
                    name="Correctness",
                    score=score,
                    weight=0.5,
                    feedback="Assessment feedback",
                    evidence=[
                        EvaluationEvidence(
                            quote_or_reference="key logic",
                            assessment="Demonstrated accurate understanding" if score >= 6.0 else "Weak understanding",
                            is_positive=score >= 6.0,
                        )
                    ],
                ),
            ],
            evidence=[
                EvaluationEvidence(
                    quote_or_reference="key logic",
                    assessment="Demonstrated accurate understanding" if score >= 6.0 else "Weak understanding",
                    is_positive=score >= 6.0,
                )
            ],
            metrics=EvaluationMetrics(
                relevance=int(score),
                correctness=int(score),
                completeness=int(score),
                clarity=clarity,
                depth=int(score),
            ),
            strengths=str_list,
            weaknesses=weak_list,
            feedback=f"Candidate evaluated with score {score}",
            suggested_improvement="Provide specific production trade-offs.",
        )
    return _create_eval


def test_state_initialization(base_config):
    """Verify InterviewState initializes with all required tracking fields."""
    state = DecisionEngine.initialize_state(base_config)

    assert state.current_topic == "Distributed Systems"
    assert state.topics_covered == []
    assert state.topics_remaining == ["Distributed Systems", "Database Indexing", "Concurrency"]
    assert state.strengths == []
    assert state.weaknesses == []
    assert state.previous_questions == []
    assert state.previous_answers == []
    assert state.previous_evaluations == []
    assert state.difficulty == Difficulty.MEDIUM
    assert state.question_count == 0
    assert state.interview_progress == 0.0
    assert state.consecutive_high_scores == 0
    assert state.consecutive_low_scores == 0
    assert state.latest_decision is None


def test_state_update_progression(base_config, mock_evaluation_factory):
    """Verify InterviewState updates topics, strengths, weaknesses, and progress correctly."""
    state = DecisionEngine.initialize_state(base_config)
    q = Question(
        question_number=1,
        text="Explain two-phase commit in Distributed Systems.",
        category="Technical",
        topic="Distributed Systems",
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.TECHNICAL,
        expected_concepts=["Coordinator", "Prepare phase", "Commit phase"],
        evaluation_criteria=["Clarity", "Correctness"],
    )
    ans = CandidateAnswer(question_number=1, answer_text="Two phase commit coordinates distributed transactions.")
    eval_res = mock_evaluation_factory(score=8.0, strengths=["Clear protocol stages"], weaknesses=["Omitted network partition risks"])

    updated_state = DecisionEngine.update_state(state, q, ans, eval_res, base_config)

    assert updated_state.question_count == 1
    assert updated_state.interview_progress == 0.2
    assert "Distributed Systems" in updated_state.topics_covered
    assert "Distributed Systems" not in updated_state.topics_remaining
    assert "Clear protocol stages" in updated_state.strengths
    assert "Omitted network partition risks" in updated_state.weaknesses
    assert updated_state.consecutive_high_scores == 1
    assert updated_state.consecutive_low_scores == 0


def test_decision_final_question(base_config, mock_evaluation_factory):
    """Verify FINAL_QUESTION is strictly selected when question count reaches budget limit."""
    state = DecisionEngine.initialize_state(base_config)
    state.question_count = 4  # Total is 5, so Q5 is the final question (4 >= 5 - 1)
    state.current_topic = "Concurrency"

    decision = DecisionEngine.decide_next_action(state, base_config)
    assert decision.action == DecisionAction.FINAL_QUESTION
    assert decision.target_topic == "Concurrency"
    assert "final" in decision.reason.lower()


def test_decision_rephrase_on_severe_struggle(base_config, mock_evaluation_factory):
    """Verify REPHRASE is selected when candidate has severe difficulty (score <= 2.5)."""
    state = DecisionEngine.initialize_state(base_config)
    eval_res = mock_evaluation_factory(score=2.0, weaknesses=["Complete confusion on consensus algorithms"])

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.REPHRASE
    assert decision.target_topic == "Distributed Systems"
    assert decision.context_reference == "Complete confusion on consensus algorithms"


def test_decision_clarify_on_ambiguous_answer(base_config, mock_evaluation_factory):
    """Verify CLARIFY is triggered on partial or low-clarity answers (clarity <= 4 or 2.5 < score < 5.5)."""
    state = DecisionEngine.initialize_state(base_config)
    eval_res = mock_evaluation_factory(score=4.0, clarity=3, weaknesses=["Vague statement on write locks"])

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.CLARIFY
    assert "ambiguous" in decision.reason.lower() or "clarification" in decision.reason.lower()


def test_decision_follow_up_on_solid_with_omissions(base_config, mock_evaluation_factory):
    """Verify FOLLOW_UP is chosen when answer is good (5.5 <= score < 7.5) with follow_up_possible."""
    state = DecisionEngine.initialize_state(base_config)
    q = Question(
        question_number=1,
        text="Explain Raft consensus.",
        category="Technical",
        topic="Distributed Systems",
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.TECHNICAL,
        expected_concepts=["Leader election"],
        evaluation_criteria=["Correctness"],
        follow_up_possible=True,
    )
    state.previous_questions.append(q)
    eval_res = mock_evaluation_factory(score=6.5, weaknesses=["Omitted split-brain handling"])

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.FOLLOW_UP
    assert decision.context_reference == "Omitted split-brain handling"


def test_decision_increase_difficulty_adaptive(base_config, mock_evaluation_factory):
    """Verify INCREASE_DIFFICULTY in ADAPTIVE mode after high performance (Score >= 7.5)."""
    state = DecisionEngine.initialize_state(base_config)
    state.difficulty = Difficulty.MEDIUM
    state.consecutive_high_scores = 1
    eval_res = mock_evaluation_factory(score=9.0)

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.INCREASE_DIFFICULTY
    assert decision.target_difficulty == Difficulty.HARD


def test_decision_deep_dive_when_already_hard(base_config, mock_evaluation_factory):
    """Verify DEEP_DIVE is selected when already at HARD difficulty and showing mastery."""
    state = DecisionEngine.initialize_state(base_config)
    state.difficulty = Difficulty.HARD
    eval_res = mock_evaluation_factory(score=8.5)

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.DEEP_DIVE
    assert "deep-dive" in decision.reason.lower() or "mastery" in decision.reason.lower()


def test_decision_decrease_difficulty_after_rephrase(base_config, mock_evaluation_factory):
    """Verify DECREASE_DIFFICULTY when candidate continues struggling after a rephrase."""
    state = DecisionEngine.initialize_state(base_config)
    state.difficulty = Difficulty.MEDIUM
    state.latest_decision = InterviewDecision(
        action=DecisionAction.REPHRASE,
        reason="Initial rephrase",
        target_topic="Distributed Systems",
        target_difficulty=Difficulty.MEDIUM,
        objective="Rephrase core concepts",
    )
    eval_res = mock_evaluation_factory(score=2.0)

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.DECREASE_DIFFICULTY
    assert decision.target_difficulty == Difficulty.EASY


def test_decision_new_topic_progression(base_config, mock_evaluation_factory):
    """Verify NEW_TOPIC is selected when topic is covered and more topics remain."""
    state = DecisionEngine.initialize_state(base_config)
    state.topics_covered = ["Distributed Systems"]
    state.topics_remaining = ["Database Indexing", "Concurrency"]
    state.latest_decision = InterviewDecision(
        action=DecisionAction.DEEP_DIVE,
        reason="Finished deep dive",
        target_topic="Distributed Systems",
        target_difficulty=Difficulty.HARD,
        objective="Deep dive",
    )
    eval_res = mock_evaluation_factory(score=8.0)

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.NEW_TOPIC
    assert decision.target_topic == "Database Indexing"


def test_decision_move_on_fallback(base_config, mock_evaluation_factory):
    """Verify MOVE_ON is selected when topics are exhausted and standard progression continues."""
    state = DecisionEngine.initialize_state(base_config)
    state.topics_remaining = []
    state.latest_decision = InterviewDecision(
        action=DecisionAction.FOLLOW_UP,
        reason="Completed follow-up",
        target_topic="Concurrency",
        target_difficulty=Difficulty.MEDIUM,
        objective="Test follow up",
    )
    eval_res = mock_evaluation_factory(score=6.0)

    decision = DecisionEngine.decide_next_action(state, base_config, eval_res)
    assert decision.action == DecisionAction.MOVE_ON


def test_strategy_mapping_all_actions(base_config):
    """Verify map_decision_to_strategy generates valid StrategyPlans across all actions."""
    state = DecisionEngine.initialize_state(base_config)
    actions = [
        DecisionAction.FOLLOW_UP,
        DecisionAction.DEEP_DIVE,
        DecisionAction.CLARIFY,
        DecisionAction.NEW_TOPIC,
        DecisionAction.INCREASE_DIFFICULTY,
        DecisionAction.DECREASE_DIFFICULTY,
        DecisionAction.REPHRASE,
        DecisionAction.MOVE_ON,
        DecisionAction.FINAL_QUESTION,
    ]

    for action in actions:
        dec = InterviewDecision(
            action=action,
            reason=f"Testing {action.value}",
            target_topic="Distributed Systems",
            target_difficulty=Difficulty.HARD,
            objective=f"Objective for {action.value}",
            context_reference="context snippet",
        )
        plan = DecisionEngine.map_decision_to_strategy(dec, state, base_config, question_number=2)
        assert isinstance(plan, StrategyPlan)
        assert plan.question_number == 2
        assert plan.target_topic == "Distributed Systems"
        assert plan.difficulty == Difficulty.HARD
        assert plan.decision_action == action
        assert plan.context_reference == "context snippet"
        assert plan.objective == f"Objective for {action.value}"


def test_infinite_loop_prevention_guarantee(mock_llm):
    """
    Verify the application strictly halts when num_questions is reached,
    preventing any infinite loops even if adaptive branching decisions continue.
    """
    config = InterviewConfig(
        candidate_name="Test Candidate",
        role="Backend Engineer",
        num_questions=3,
        estimated_duration_minutes=15,
        difficulty=Difficulty.ADAPTIVE,
        topics=["Python", "SQL", "Docker"],
    )
    engine = InterviewEngine(llm_service=mock_llm)
    engine.start_interview(config)

    # Q1
    assert engine.has_more_questions is True
    engine.submit_answer("Answer to Q1")

    # Q2
    q2 = engine.generate_next_question()
    assert q2 is not None
    assert engine.has_more_questions is True
    engine.submit_answer("Answer to Q2")

    # Q3
    q3 = engine.generate_next_question()
    assert q3 is not None
    assert engine.has_more_questions is False  # Reached max configured budget (3)
    engine.submit_answer("Answer to Q3")

    # Attempting Q4 must strictly return None
    q4 = engine.generate_next_question()
    assert q4 is None
    assert engine.has_more_questions is False

    # Complete interview
    result = engine.finish_interview()
    assert result is not None
    assert engine.is_finished is True
    assert len(result.pairs) == 3
