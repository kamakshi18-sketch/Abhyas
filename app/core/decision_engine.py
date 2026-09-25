"""
Decision Engine for Adaptive Interviews (Phase 5).
Evaluates candidate state, rubric feedback, and session telemetry to determine the optimal next strategic action.
Guarantees application boundaries, topic coverage, difficulty stepping, and termination safety.
"""

import logging
from typing import Optional, List
from app.schemas.interview import (
    InterviewConfig,
    InterviewState,
    InterviewDecision,
    DecisionAction,
    Difficulty,
    InterviewType,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    StrategyPlan,
    QuestionType,
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Stateful decision engine governing adaptive interview progression."""

    @staticmethod
    def initialize_state(config: InterviewConfig) -> InterviewState:
        """Initialize an empty InterviewState based on the provided configuration."""
        topics = list(config.topics) if config.topics else [config.role or "Software Engineering"]
        initial_topic = topics[0] if topics else "General"
        initial_diff = Difficulty.MEDIUM if config.difficulty == Difficulty.ADAPTIVE else config.difficulty

        state = InterviewState(
            current_topic=initial_topic,
            topics_covered=[],
            topics_remaining=list(topics),
            strengths=[],
            weaknesses=[],
            previous_questions=[],
            previous_answers=[],
            previous_evaluations=[],
            difficulty=initial_diff,
            question_count=0,
            interview_progress=0.0,
            consecutive_high_scores=0,
            consecutive_low_scores=0,
            latest_decision=None,
        )
        return state

    @staticmethod
    def update_state(
        state: InterviewState,
        question: Question,
        answer: CandidateAnswer,
        evaluation: AnswerEvaluation,
        config: InterviewConfig,
    ) -> InterviewState:
        """
        Immutably/in-place update interview state with latest Q&A pair and evaluation.
        Enforces topic tracking, strengths/weaknesses aggregation, and progress telemetry.
        """
        # Append history
        state.previous_questions.append(question)
        state.previous_answers.append(answer)
        state.previous_evaluations.append(evaluation)
        state.question_count = len(state.previous_answers)

        # Update Progress
        total_q = config.num_questions if config.num_questions > 0 else 1
        state.interview_progress = min(1.0, round(state.question_count / float(total_q), 2))

        # Update Topic tracking
        q_topic = question.topic or state.current_topic or "General"
        if q_topic not in state.topics_covered:
            state.topics_covered.append(q_topic)
        if q_topic in state.topics_remaining:
            state.topics_remaining.remove(q_topic)
        state.current_topic = q_topic

        # Aggregate Strengths & Weaknesses (deduplicated)
        for s in evaluation.strengths:
            clean_s = s.strip()
            if clean_s and clean_s not in state.strengths:
                state.strengths.append(clean_s)

        for w in evaluation.weaknesses:
            clean_w = w.strip()
            if clean_w and clean_w not in state.weaknesses:
                state.weaknesses.append(clean_w)

        # Consecutive Score Tracking
        score = evaluation.score
        if score >= 7.5:
            state.consecutive_high_scores += 1
            state.consecutive_low_scores = 0
        elif score <= 4.5:
            state.consecutive_low_scores += 1
            state.consecutive_high_scores = 0
        else:
            state.consecutive_high_scores = 0
            state.consecutive_low_scores = 0

        return state

    @classmethod
    def decide_next_action(
        cls,
        state: InterviewState,
        config: InterviewConfig,
        latest_evaluation: Optional[AnswerEvaluation] = None,
    ) -> InterviewDecision:
        """
        Core decision algorithm determining the next pedagogical action based on state and evaluation.
        Guarantees termination at num_questions and covers all 9 DecisionActions.
        """
        # 1. Check End-of-Interview Budget Guardrail
        if state.question_count >= config.num_questions - 1:
            target_topic = state.current_topic or (config.topics[0] if config.topics else config.role or "System Architecture")
            return InterviewDecision(
                action=DecisionAction.FINAL_QUESTION,
                reason="Approaching total interview question budget. Executing final synthesis and alignment round.",
                target_topic=target_topic,
                target_difficulty=state.difficulty,
                objective=f"Evaluate comprehensive role readiness, architectural synthesis, and key trade-offs on {target_topic}.",
            )

        # If no evaluations yet (e.g. at start), standard MOVE_ON or initial topic
        if not latest_evaluation:
            target_topic = state.current_topic or (config.topics[0] if config.topics else "General")
            return InterviewDecision(
                action=DecisionAction.MOVE_ON,
                reason="Initial question sequence progression.",
                target_topic=target_topic,
                target_difficulty=state.difficulty,
                objective=f"Assess core competencies on {target_topic}.",
            )

        score = latest_evaluation.score
        prev_decision = state.latest_decision
        prev_action = prev_decision.action if prev_decision else None
        prev_question = state.previous_questions[-1] if state.previous_questions else None

        # 2. Severe Struggle / Misunderstanding (Score <= 2.5) -> REPHRASE or DECREASE_DIFFICULTY
        if score <= 2.5:
            if prev_action != DecisionAction.REPHRASE:
                # First attempt at rephrase
                target_diff = Difficulty.EASY if config.difficulty == Difficulty.ADAPTIVE else state.difficulty
                return InterviewDecision(
                    action=DecisionAction.REPHRASE,
                    reason="Candidate encountered severe difficulty with previous question premise. Rephrasing from a simpler, practical perspective.",
                    target_topic=state.current_topic,
                    target_difficulty=target_diff,
                    objective=f"Rephrase core concepts of {state.current_topic} using an intuitive real-world scenario.",
                    context_reference=latest_evaluation.weaknesses[0] if latest_evaluation.weaknesses else None,
                )
            else:
                # Already rephrased; decrease difficulty or shift topic
                if config.difficulty == Difficulty.ADAPTIVE and state.difficulty != Difficulty.EASY:
                    target_diff = Difficulty.EASY
                    return InterviewDecision(
                        action=DecisionAction.DECREASE_DIFFICULTY,
                        reason="Candidate struggled after rephrasing. Lowering difficulty to establish baseline foundation.",
                        target_topic=state.current_topic,
                        target_difficulty=target_diff,
                        objective=f"Assess fundamental baseline definitions and core terminology on {state.current_topic}.",
                    )
                elif state.topics_remaining:
                    next_t = state.topics_remaining[0]
                    return InterviewDecision(
                        action=DecisionAction.NEW_TOPIC,
                        reason="Transitioning to new focus area after exploring current topic baseline.",
                        target_topic=next_t,
                        target_difficulty=state.difficulty,
                        objective=f"Assess candidate capabilities on new topic: {next_t}.",
                    )
                else:
                    return InterviewDecision(
                        action=DecisionAction.MOVE_ON,
                        reason="Progressing to next question in sequence.",
                        target_topic=state.current_topic,
                        target_difficulty=state.difficulty,
                        objective=f"Assess alternative practical application on {state.current_topic}.",
                    )

        # 3. Ambiguity / Partial Answer (2.5 < Score < 5.5 or clarity <= 4) -> CLARIFY or DECREASE_DIFFICULTY
        if (2.5 < score < 5.5) or (latest_evaluation.metrics and latest_evaluation.metrics.clarity <= 4):
            if prev_action != DecisionAction.CLARIFY:
                quote = latest_evaluation.evidence[0].quote_or_reference if latest_evaluation.evidence else None
                return InterviewDecision(
                    action=DecisionAction.CLARIFY,
                    reason="Candidate response was ambiguous, incomplete, or lacked clear assumptions. Requesting structured clarification.",
                    target_topic=state.current_topic,
                    target_difficulty=state.difficulty,
                    objective=f"Clarify specific ambiguities, runtime assumptions, and trade-offs on {state.current_topic}.",
                    context_reference=quote or (latest_evaluation.weaknesses[0] if latest_evaluation.weaknesses else None),
                )
            else:
                # Already asked for clarification, now step difficulty down if adaptive or move on
                if config.difficulty == Difficulty.ADAPTIVE and state.difficulty == Difficulty.HARD:
                    return InterviewDecision(
                        action=DecisionAction.DECREASE_DIFFICULTY,
                        reason="Candidate struggled on hard question after clarification. Stepping down to Medium.",
                        target_topic=state.current_topic,
                        target_difficulty=Difficulty.MEDIUM,
                        objective=f"Evaluate intermediate standard patterns on {state.current_topic}.",
                    )
                elif config.difficulty == Difficulty.ADAPTIVE and state.difficulty == Difficulty.MEDIUM:
                    return InterviewDecision(
                        action=DecisionAction.DECREASE_DIFFICULTY,
                        reason="Candidate struggled on medium question after clarification. Stepping down to Easy.",
                        target_topic=state.current_topic,
                        target_difficulty=Difficulty.EASY,
                        objective=f"Evaluate foundational concepts on {state.current_topic}.",
                    )
                elif state.topics_remaining:
                    next_t = state.topics_remaining[0]
                    return InterviewDecision(
                        action=DecisionAction.NEW_TOPIC,
                        reason="Clarification round concluded. Transitioning to next focus area.",
                        target_topic=next_t,
                        target_difficulty=state.difficulty,
                        objective=f"Assess competencies on {next_t}.",
                    )
                else:
                    return InterviewDecision(
                        action=DecisionAction.MOVE_ON,
                        reason="Progressing to next question in sequence.",
                        target_topic=state.current_topic,
                        target_difficulty=state.difficulty,
                        objective=f"Assess practical implementation on {state.current_topic}.",
                    )

        # 4. Good Foundation with Omitted Details (5.5 <= Score < 7.5) -> FOLLOW_UP or NEW_TOPIC
        if 5.5 <= score < 7.5:
            follow_up_ok = prev_question.follow_up_possible if prev_question else True
            if follow_up_ok and prev_action != DecisionAction.FOLLOW_UP:
                gap = latest_evaluation.weaknesses[0] if latest_evaluation.weaknesses else "edge case handling"
                return InterviewDecision(
                    action=DecisionAction.FOLLOW_UP,
                    reason=f"Candidate gave a solid foundation but omitted key nuances ({gap}). Branching with follow-up probe.",
                    target_topic=state.current_topic,
                    target_difficulty=state.difficulty,
                    objective=f"Probe deeper into {gap} and specific trade-offs on {state.current_topic}.",
                    context_reference=gap,
                )
            elif state.topics_remaining:
                next_t = state.topics_remaining[0]
                return InterviewDecision(
                    action=DecisionAction.NEW_TOPIC,
                    reason="Topic sufficiently covered. Moving to next topic in matrix.",
                    target_topic=next_t,
                    target_difficulty=state.difficulty,
                    objective=f"Assess core competencies on new topic: {next_t}.",
                )
            else:
                return InterviewDecision(
                    action=DecisionAction.MOVE_ON,
                    reason="Progressing to next interview question.",
                    target_topic=state.current_topic,
                    target_difficulty=state.difficulty,
                    objective=f"Examine application design on {state.current_topic}.",
                )

        # 5. Exceptional Performance (Score >= 7.5) -> INCREASE_DIFFICULTY, DEEP_DIVE, or NEW_TOPIC
        if score >= 7.5:
            # Check Adaptive Difficulty Increase
            if config.difficulty == Difficulty.ADAPTIVE and state.difficulty != Difficulty.HARD and state.consecutive_high_scores >= 1:
                next_diff = Difficulty.HARD if state.difficulty == Difficulty.MEDIUM else Difficulty.MEDIUM
                return InterviewDecision(
                    action=DecisionAction.INCREASE_DIFFICULTY,
                    reason=f"Candidate demonstrated high proficiency (Score: {score:.1f}). Increasing difficulty to {next_diff.value}.",
                    target_topic=state.current_topic,
                    target_difficulty=next_diff,
                    objective=f"Test advanced architectural complexity, high-scale bottlenecks, and edge cases on {state.current_topic}.",
                )
            # If already at Hard (or non-adaptive) and haven't deep-dived yet
            elif prev_action != DecisionAction.DEEP_DIVE:
                return InterviewDecision(
                    action=DecisionAction.DEEP_DIVE,
                    reason=f"Candidate demonstrated mastery on {state.current_topic}. Conducting advanced deep-dive into internal mechanisms and scalability.",
                    target_topic=state.current_topic,
                    target_difficulty=state.difficulty,
                    objective=f"Deep-dive into concurrency, performance optimization, and failure modes of {state.current_topic}.",
                )
            elif state.topics_remaining:
                next_t = state.topics_remaining[0]
                return InterviewDecision(
                    action=DecisionAction.NEW_TOPIC,
                    reason="Deep-dive complete. Transitioning to next focus area in topic matrix.",
                    target_topic=next_t,
                    target_difficulty=state.difficulty,
                    objective=f"Assess competence on new topic: {next_t}.",
                )
            else:
                return InterviewDecision(
                    action=DecisionAction.MOVE_ON,
                    reason="Progressing to next interview question.",
                    target_topic=state.current_topic,
                    target_difficulty=state.difficulty,
                    objective=f"Evaluate end-to-end system design on {state.current_topic}.",
                )

        # 6. Fallback Default
        return InterviewDecision(
            action=DecisionAction.MOVE_ON,
            reason="Standard progression to next question in sequence.",
            target_topic=state.current_topic or "General",
            target_difficulty=state.difficulty,
            objective=f"Assess candidate capabilities on {state.current_topic or 'assigned topic'}.",
        )

    @classmethod
    def map_decision_to_strategy(
        cls,
        decision: InterviewDecision,
        state: InterviewState,
        config: InterviewConfig,
        question_number: int,
    ) -> StrategyPlan:
        """
        Convert an InterviewDecision into a concrete StrategyPlan for the Question Generator.
        """
        action = decision.action
        target_topic = decision.target_topic or state.current_topic or (config.topics[0] if config.topics else "General")
        diff = decision.target_difficulty

        # Map DecisionAction to appropriate QuestionType
        if action == DecisionAction.FINAL_QUESTION:
            q_type = QuestionType.ROLE_SPECIFIC if config.interview_type == InterviewType.TECHNICAL else QuestionType.BEHAVIORAL
            category = f"Final Round - {config.role or 'Synthesis'}"
        elif action == DecisionAction.FOLLOW_UP:
            q_type = QuestionType.TECHNICAL if config.interview_type == InterviewType.TECHNICAL else QuestionType.SITUATIONAL
            category = f"Follow-Up - {target_topic}"
        elif action == DecisionAction.DEEP_DIVE:
            q_type = QuestionType.PROBLEM_SOLVING if config.interview_type == InterviewType.TECHNICAL else QuestionType.PROJECT
            category = f"Deep Dive - {target_topic}"
        elif action == DecisionAction.CLARIFY:
            q_type = QuestionType.CONCEPTUAL if config.interview_type == InterviewType.TECHNICAL else QuestionType.BEHAVIORAL
            category = f"Clarification - {target_topic}"
        elif action == DecisionAction.REPHRASE:
            q_type = QuestionType.CONCEPTUAL
            category = f"Rephrased Core - {target_topic}"
        elif action in (DecisionAction.INCREASE_DIFFICULTY, DecisionAction.DECREASE_DIFFICULTY):
            q_type = QuestionType.TECHNICAL if config.interview_type == InterviewType.TECHNICAL else QuestionType.SITUATIONAL
            category = f"Calibrated ({diff.value}) - {target_topic}"
        elif action == DecisionAction.NEW_TOPIC:
            q_type = QuestionType.CONCEPTUAL if config.interview_type == InterviewType.TECHNICAL else QuestionType.BEHAVIORAL
            category = f"{config.interview_type.value} - {target_topic}"
        else: # MOVE_ON
            q_type = QuestionType.TECHNICAL if config.interview_type == InterviewType.TECHNICAL else QuestionType.BEHAVIORAL
            category = f"{config.interview_type.value} - {target_topic}"

        return StrategyPlan(
            question_number=question_number,
            question_type=q_type,
            target_topic=target_topic,
            category=category,
            difficulty=diff,
            objective=decision.objective,
            decision=decision,
            decision_action=action,
            context_reference=decision.context_reference,
        )
