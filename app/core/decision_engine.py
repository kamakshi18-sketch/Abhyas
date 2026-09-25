"""
Adaptive Decision Engine (Phase 5).
Implements the pedagogical intelligence layer for dynamic interview adaptation.
Decides the next interview action, topic steering, and difficulty scaling based on
candidate performance, demonstrated strengths, detected weaknesses, and topic coverage.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from app.schemas.interview import (
    InterviewConfig,
    InterviewState,
    InterviewDecision,
    DecisionAction,
    Difficulty,
    QuestionType,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
)
from app.ai.ollama_client import LLMService
from app.performance.timers import Timer

logger = logging.getLogger(__name__)

_REFUSAL_PHRASES: Tuple[str, ...] = (
    "i don't know",
    "i do not know",
    "no idea",
    "pass",
    "not sure",
    "skip",
    "no answer",
    "can't answer",
    "cannot answer",
    "i have not worked with this",
    "never used this",
    "no clue",
)


class AdaptiveDecisionEngine:
    """
    Intelligent, deterministic and bounded decision engine for adaptive interviews.
    
    Guarantees:
    1. Bounded termination: Strictly honors config.num_questions. Never creates infinite loops.
    2. Topic coverage: Systematically explores topics from config.topics before recycling.
    3. Calibrated difficulty: Dynamically scales difficulty (EASY <-> MEDIUM <-> HARD) based on performance.
    4. Deterministic fallback: All decision paths are fully testable and guaranteed to produce valid InterviewDecisions.
    """

    MAX_QUESTIONS_PER_TOPIC = 2

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service

    def decide_next_action(
        self,
        state: InterviewState,
        config: InterviewConfig,
    ) -> InterviewDecision:
        """
        Main decision engine entrypoint.
        Evaluates interview state, candidate performance, topic coverage, and question limits
        to produce the next pedagogical InterviewDecision.
        """
        with Timer("adaptive_decision_engine"):
            return self._decide_action_internal(state, config)

    def _decide_action_internal(
        self,
        state: InterviewState,
        config: InterviewConfig,
    ) -> InterviewDecision:
        # Guard: If no questions asked yet (First Question)
        if not state.previous_questions or state.question_count == 0:
            first_topic = config.topics[0] if config.topics else (config.role or "Software Engineering")
            init_diff = Difficulty.MEDIUM if config.difficulty == Difficulty.ADAPTIVE else config.difficulty
            return InterviewDecision(
                action=DecisionAction.NEW_TOPIC,
                reason="Starting initial interview question on primary focus topic.",
                target_topic=first_topic,
                target_difficulty=init_diff,
                objective=f"Evaluate foundational understanding and problem-solving readiness in {first_topic}.",
                suggested_question_type=QuestionType.CONCEPTUAL if config.interview_type.value == "Technical" else QuestionType.BEHAVIORAL,
            )

        # 1. HARD TERMINATION GUARD: Final Question Check
        if state.question_count >= config.num_questions - 1:
            return self._decide_final_question(state, config)

        # Retrieve latest evaluation and context
        latest_eval = state.latest_evaluation
        latest_q = state.latest_question
        latest_ans = state.latest_answer
        last_score = latest_eval.score if latest_eval else 5.0
        current_diff = state.difficulty

        # Determine effective current topic question count
        curr_topic = state.current_topic
        topic_count = state.topic_question_counts.get(curr_topic, 1)

        # 2. REPHRASE: Severe struggle, refusal, empty answer, or score <= 2.5
        if last_score <= 2.5 or (latest_ans and self._is_refusal_or_empty(latest_ans.answer_text)):
            return InterviewDecision(
                action=DecisionAction.REPHRASE,
                reason=f"Candidate struggled significantly (score: {last_score:.1f}). Rephrasing with simpler framing, accessible hints, and scaffolding.",
                target_topic=curr_topic,
                target_difficulty=Difficulty.EASY,
                objective=f"Provide scaffolded rephrasing on {curr_topic} to help candidate demonstrate fundamental understanding.",
                suggested_question_type=QuestionType.CONCEPTUAL,
                parent_question_id=latest_q.id if latest_q else None,
                context_note="Scaffold with simpler terminology or practical everyday analogies.",
            )

        # 3. DECREASE_DIFFICULTY: Poor performance (score < 4.5) when not already at EASY
        if last_score < 4.5 and current_diff in (Difficulty.HARD, Difficulty.MEDIUM) and config.difficulty == Difficulty.ADAPTIVE:
            new_diff = Difficulty.MEDIUM if current_diff == Difficulty.HARD else Difficulty.EASY
            state.difficulty = new_diff
            return InterviewDecision(
                action=DecisionAction.DECREASE_DIFFICULTY,
                reason=f"Candidate scored {last_score:.1f} on {current_diff.value} level. Calibrating difficulty down to {new_diff.value} for fair evaluation.",
                target_topic=curr_topic,
                target_difficulty=new_diff,
                objective=f"Calibrate complexity down to {new_diff.value} to test essential core principles of {curr_topic}.",
                suggested_question_type=QuestionType.CONCEPTUAL,
                parent_question_id=latest_q.id if latest_q else None,
            )

        # 4. CLARIFY: Vague, ambiguous, or incomplete response with score between 2.5 and 5.0
        if 2.5 < last_score <= 5.0 and latest_eval and latest_eval.weaknesses:
            gap = latest_eval.weaknesses[0]
            return InterviewDecision(
                action=DecisionAction.CLARIFY,
                reason=f"Answer was ambiguous or partially incomplete (score: {last_score:.1f}). Requesting clarification on: '{gap}'.",
                target_topic=curr_topic,
                target_difficulty=current_diff,
                objective=f"Request explicit clarification and elaboration regarding {gap} in {curr_topic}.",
                suggested_question_type=QuestionType.PROBLEM_SOLVING if config.interview_type.value == "Technical" else QuestionType.SITUATIONAL,
                parent_question_id=latest_q.id if latest_q else None,
                context_note=f"Clarification probe focusing on: {gap}",
            )

        # 5. DEEP_DIVE: Outstanding answer (score >= 8.5) and high mastery on current topic
        if last_score >= 8.5:
            # If topic is not saturated, deep dive into advanced nuances
            if topic_count < self.MAX_QUESTIONS_PER_TOPIC:
                deep_diff = Difficulty.HARD if config.difficulty == Difficulty.ADAPTIVE else current_diff
                state.difficulty = deep_diff
                return InterviewDecision(
                    action=DecisionAction.DEEP_DIVE,
                    reason=f"Candidate demonstrated exceptional mastery (score: {last_score:.1f}). Exploring complex architectural internals, scalability, and edge cases.",
                    target_topic=curr_topic,
                    target_difficulty=deep_diff,
                    objective=f"Deep dive into advanced distributed trade-offs, internal execution models, and edge cases in {curr_topic}.",
                    suggested_question_type=QuestionType.TECHNICAL if config.interview_type.value == "Technical" else QuestionType.PROJECT,
                    parent_question_id=latest_q.id if latest_q else None,
                    context_note="Advanced deep-dive question probing nuanced technical trade-offs.",
                )

        # 6. INCREASE_DIFFICULTY: Strong answer (score >= 7.5) and current difficulty can step up
        if last_score >= 7.5 and current_diff in (Difficulty.EASY, Difficulty.MEDIUM) and config.difficulty == Difficulty.ADAPTIVE:
            new_diff = Difficulty.HARD if current_diff == Difficulty.MEDIUM else Difficulty.MEDIUM
            state.difficulty = new_diff
            return InterviewDecision(
                action=DecisionAction.INCREASE_DIFFICULTY,
                reason=f"Candidate performed strongly (score: {last_score:.1f}) on {current_diff.value} level. Escalating difficulty to {new_diff.value}.",
                target_topic=curr_topic,
                target_difficulty=new_diff,
                objective=f"Escalate difficulty to {new_diff.value} to assess higher-order design and edge cases in {curr_topic}.",
                suggested_question_type=QuestionType.PROBLEM_SOLVING,
                parent_question_id=latest_q.id if latest_q else None,
            )

        # 7. FOLLOW_UP: Solid answer (5.0 <= score < 8.0) with specific omission or weakness to probe
        if 5.0 <= last_score < 8.0 and latest_eval and latest_eval.weaknesses and topic_count < self.MAX_QUESTIONS_PER_TOPIC:
            weakness_target = latest_eval.weaknesses[0]
            return InterviewDecision(
                action=DecisionAction.FOLLOW_UP,
                reason=f"Candidate gave a good response ({last_score:.1f}) but missed key aspects: '{weakness_target}'. Probing with a targeted follow-up.",
                target_topic=curr_topic,
                target_difficulty=current_diff,
                objective=f"Follow up on candidate's previous response to specifically evaluate understanding of {weakness_target}.",
                suggested_question_type=QuestionType.TECHNICAL if config.interview_type.value == "Technical" else QuestionType.SITUATIONAL,
                parent_question_id=latest_q.id if latest_q else None,
                context_note=f"Targeted follow-up probing: {weakness_target}",
            )

        # 8. NEW_TOPIC: Topic is saturated (>= 2 questions) or unvisited topics remain
        if (topic_count >= self.MAX_QUESTIONS_PER_TOPIC or last_score >= 7.0) and state.topics_remaining:
            next_topic = state.topics_remaining[0]
            return InterviewDecision(
                action=DecisionAction.NEW_TOPIC,
                reason=f"Topic '{curr_topic}' adequately explored ({topic_count} questions). Shifting focus to next unvisited topic: '{next_topic}'.",
                target_topic=next_topic,
                target_difficulty=state.difficulty,
                objective=f"Assess core competencies and practical experience on new topic '{next_topic}'.",
                suggested_question_type=QuestionType.CONCEPTUAL if config.interview_type.value == "Technical" else QuestionType.BEHAVIORAL,
            )

        # 9. MOVE_ON: Default progression across topics or sequence
        target_topic = self._select_next_topic(state, config)
        return InterviewDecision(
            action=DecisionAction.MOVE_ON,
            reason=f"Progressing to next phase of the interview with focus on '{target_topic}'.",
            target_topic=target_topic,
            target_difficulty=state.difficulty,
            objective=f"Evaluate comprehensive domain readiness on {target_topic} for {config.role or 'Candidate'}.",
            suggested_question_type=QuestionType.ROLE_SPECIFIC,
        )

    def _decide_final_question(
        self,
        state: InterviewState,
        config: InterviewConfig,
    ) -> InterviewDecision:
        """Formulate the final concluding question decision."""
        # Pick topic with fewest questions or remaining topic
        target_topic = self._select_next_topic(state, config)
        return InterviewDecision(
            action=DecisionAction.FINAL_QUESTION,
            reason=f"Approaching session limit (Question {state.question_count + 1} of {config.num_questions}). Concluding with holistic synthesis question.",
            target_topic=target_topic,
            target_difficulty=state.difficulty,
            objective=f"Final synthesis question evaluating overarching technical vision, end-to-end design, or career ownership in {config.role or 'Candidate'}.",
            suggested_question_type=QuestionType.PROJECT if config.interview_type.value in ("Technical", "Mixed") else QuestionType.HR,
        )

    def _select_next_topic(self, state: InterviewState, config: InterviewConfig) -> str:
        """Select the next topic ensuring even coverage and avoiding starvation."""
        if state.topics_remaining:
            return state.topics_remaining[0]
        
        all_topics = config.topics if config.topics else [config.role or "Software Engineering"]
        # Find topic with minimum question count
        min_topic = all_topics[0]
        min_count = state.topic_question_counts.get(min_topic, 0)
        for t in all_topics[1:]:
            count = state.topic_question_counts.get(t, 0)
            if count < min_count:
                min_topic = t
                min_count = count
        return min_topic

    @staticmethod
    def _is_refusal_or_empty(text: str) -> bool:
        """Detect candidate refusal, 'I don't know', or empty response."""
        normalized = text.strip().lower()
        if len(normalized) < 5:
            return True
        return any(phrase in normalized for phrase in _REFUSAL_PHRASES)
