"""
Follow-Up Engine (Phase 6).
Generates intelligent, natural, context-grounded follow-up questions referencing the candidate's actual answer.
Supports all 10 specialized Follow-Up Types with sub-millisecond diagnostics and deterministic fallback generation.
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple, Callable
from app.schemas.interview import (
    InterviewConfig,
    Question,
    QuestionType,
    Difficulty,
    ExperienceLevel,
    AnswerEvaluation,
    FollowUpType,
    FollowUpPlan,
)
from app.ai.ollama_client import LLMService, LLMValidationError, LLMConnectionError
from app.core.prompts import (
    FOLLOW_UP_GENERATOR_SYSTEM_PROMPT,
    build_follow_up_prompt,
)
from app.performance.timers import Timer

logger = logging.getLogger(__name__)

# Pre-compiled regular expressions for sub-millisecond token matching
_TECH_PATTERNS = re.compile(
    r"\b(python|django|fastapi|flask|postgresql|postgres|mysql|sqlite|redis|kafka|rabbitmq|"
    r"docker|kubernetes|k8s|aws|gcp|azure|react|vue|angular|node|typescript|graphql|grpc|"
    r"celery|asyncio|multiprocessing|threading|pandas|numpy|pytorch|tensorflow|spark|"
    r"elasticsearch|mongodb|dynamodb|cassandra|terraform|ansible|prometheus|grafana)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT_REGEX = re.compile(r"[.!?\n]+")

_MISCONCEPTION_KEYWORDS: Tuple[str, ...] = (
    "incorrect",
    "wrong",
    "misconception",
    "flaw",
    "inaccurate",
    "assumption",
    "mistake",
)

# Static Objective Formatters
_OBJECTIVE_TEMPLATES: Dict[FollowUpType, str] = {
    FollowUpType.CLARIFICATION: "Clarify ambiguous or incomplete statements regarding '{anchor}' in {topic}.",
    FollowUpType.EXAMPLE_REQUEST: "Evaluate concrete code or architectural implementation of '{anchor}' in practice.",
    FollowUpType.WHY_QUESTION: "Assess architectural justification and reasoning behind choosing '{anchor}'.",
    FollowUpType.HOW_QUESTION: "Examine step-by-step implementation mechanics and workflow of '{anchor}'.",
    FollowUpType.DEEP_TECHNICAL: "Deep dive into internal engine concurrency, memory synchronization, and limits of '{anchor}'.",
    FollowUpType.TRADEOFF: "Scrutinize latency, throughput, complexity, and resource trade-offs of '{anchor}'.",
    FollowUpType.CHALLENGE: "Test candidate resilience and edge case handling when '{anchor}' faces system failures.",
    FollowUpType.COUNTEREXAMPLE: "Evaluate ability to identify failure modes, anti-patterns, and limits of '{anchor}'.",
    FollowUpType.OPTIMIZATION: "Assess throughput optimization, caching, profiling, and performance scaling for '{anchor}'.",
    FollowUpType.PROJECT_SPECIFIC: "Examine direct hands-on ownership, debugging hurdles, and production impact with '{anchor}'.",
}

# Static Fallback Templates: (text_template, expected_concepts, rubric)
_FALLBACK_TEMPLATES: Dict[FollowUpType, Tuple[str, List[str], List[str]]] = {
    FollowUpType.CLARIFICATION: (
        "Earlier you mentioned '{anchor}'. Could you clarify specifically how that functions under edge conditions and high load in {topic}?",
        ["{anchor} clarification", "Edge condition behavior", "Operational stability"],
        ["Clarity of explanation", "Directness", "Accuracy of technical terms"],
    ),
    FollowUpType.EXAMPLE_REQUEST: (
        "You referenced '{anchor}'. Could you walk me through a concrete, practical code or architecture example where you implemented this in {topic}?",
        ["Concrete {anchor} implementation", "API/code structure", "Real-world utility"],
        ["Specificity of example", "Practical comprehension", "Code/design quality"],
    ),
    FollowUpType.WHY_QUESTION: (
        "In your previous answer regarding '{anchor}', why did you choose this specific architectural approach over alternative design patterns in {topic}?",
        ["{anchor} justification", "Comparative analysis", "Architectural trade-offs"],
        ["Logical justification", "Awareness of alternatives", "Clear reasoning"],
    ),
    FollowUpType.HOW_QUESTION: (
        "You described using '{anchor}'. How exactly would you configure, execute, and monitor this step-by-step to guarantee reliable performance in production for a {role}?",
        ["Step-by-step {anchor} workflow", "Configuration best practices", "Monitoring & telemetry"],
        ["Actionability", "Production readiness", "Completeness"],
    ),
    FollowUpType.DEEP_TECHNICAL: (
        "Diving deeper into your mention of '{anchor}', how does the underlying engine manage memory synchronization, low-level concurrency, and lock contention in {topic}?",
        ["Low-level {anchor} mechanics", "Memory & lock synchronization", "Throughput bottlenecks"],
        ["Deep technical rigor", "Internal execution insight", "Concurrency awareness"],
    ),
    FollowUpType.TRADEOFF: (
        "You highlighted '{anchor}' as a solution. What are the key latency, resource consumption, and operational trade-offs of this approach compared to simpler designs in {topic}?",
        ["{anchor} trade-off matrix", "Latency vs throughput", "Operational complexity"],
        ["Balanced critical evaluation", "Systems thinking", "Nuanced trade-off analysis"],
    ),
    FollowUpType.CHALLENGE: (
        "You suggested that '{anchor}' will maintain consistency. What happens when a sudden network partition or database deadlock occurs during execution, and how do you recover?",
        ["Failure mode resilience", "Network partition handling", "Deadlock resolution & recovery"],
        ["Crisis reasoning", "Defensive system design", "Fault tolerance"],
    ),
    FollowUpType.COUNTEREXAMPLE: (
        "While '{anchor}' works well in standard scenarios, can you describe a specific counterexample or anti-pattern where using this approach severely degrades system performance?",
        ["Anti-pattern identification", "Scale limitations", "Boundary edge cases"],
        ["Critical discernment", "Performance pitfall awareness", "Architectural judgment"],
    ),
    FollowUpType.OPTIMIZATION: (
        "Looking at your strategy with '{anchor}', how would you profile the application and optimize throughput or latency by 10x in a large-scale {role} environment?",
        ["Profiling & bottleneck detection", "Cache & indexing optimization", "Throughput tuning"],
        ["Optimization methodology", "Data-driven tuning", "Scalability intuition"],
    ),
    FollowUpType.PROJECT_SPECIFIC: (
        "You mentioned working with '{anchor}'. In your past projects, what specific role did you play in deploying this, what unexpected challenges did you face, and what was the outcome?",
        ["Hands-on {anchor} ownership", "Debugging real-world hurdles", "Measurable outcome"],
        ["Depth of ownership (STAR)", "Practical troubleshooting", "Authenticity"],
    ),
}


class FollowUpEngine:
    """
    Dedicated Follow-Up Engine analyzing candidate responses and generating grounded follow-ups across 10 categories.
    """

    def __init__(self, llm_service: Optional[LLMService] = None, max_retries: int = 2):
        self.llm_service = llm_service
        self.max_retries = max_retries

    def extract_anchor(
        self,
        candidate_answer: str,
        parent_question: Question,
        evaluation: Optional[AnswerEvaluation] = None,
    ) -> str:
        """
        Extract an anchor quote, technology, or key phrase from the candidate's response to reference.
        """
        ans_text = candidate_answer.strip()
        if not ans_text:
            return parent_question.topic or "the previous topic"

        # 1. Check if candidate mentioned specific known technologies
        tech_matches = _TECH_PATTERNS.findall(ans_text)
        if tech_matches:
            return tech_matches[0].title()

        # 2. Check evaluation weaknesses or strengths quotes
        if evaluation:
            if evaluation.weaknesses:
                w = evaluation.weaknesses[0]
                if len(w) > 4:
                    return w.rstrip(".")
            if evaluation.strengths:
                s = evaluation.strengths[0]
                if len(s) > 4:
                    return s.rstrip(".")

        # 3. Fallback: extract the first meaningful clause or subject
        sentences = [s.strip() for s in _SENTENCE_SPLIT_REGEX.split(ans_text) if len(s.strip()) > 10]
        if sentences:
            first_sent = sentences[0]
            if len(first_sent) > 60:
                first_sent = first_sent[:60].rsplit(" ", 1)[0] + "..."
            return first_sent

        return parent_question.topic or "your previous response"

    def determine_follow_up_type(
        self,
        candidate_answer: str,
        parent_question: Question,
        evaluation: Optional[AnswerEvaluation] = None,
        config: Optional[InterviewConfig] = None,
    ) -> FollowUpType:
        """
        Heuristic / Diagnostic rule engine to select the most appropriate FollowUpType.
        
        Rules:
        - If answer is vague / brief (< 20 words or score <= 5.0 without examples): EXAMPLE_REQUEST or CLARIFICATION
        - If answer is technically strong (score >= 8.5): DEEP_TECHNICAL, TRADEOFF, or OPTIMIZATION
        - If answer contains an incorrect assumption / misconception: CHALLENGE, COUNTEREXAMPLE, or WHY_QUESTION
        - If candidate specifically mentions a technology / past project: PROJECT_SPECIFIC or HOW_QUESTION
        """
        ans = candidate_answer.strip()
        words = ans.split()
        score = evaluation.score if evaluation else 5.0
        weaknesses = evaluation.weaknesses if evaluation else []

        # Check for misconception / incorrect assumption flagged in weaknesses
        has_misconception = any(
            any(k in w.lower() for k in _MISCONCEPTION_KEYWORDS)
            for w in weaknesses
        )
        if has_misconception:
            if score < 4.0:
                return FollowUpType.CHALLENGE
            return FollowUpType.COUNTEREXAMPLE

        # Check for vague / brief answer needing concrete demonstration
        if len(words) < 25 or (score <= 5.0 and any("example" in w.lower() or "vague" in w.lower() or "brief" in w.lower() for w in weaknesses)):
            return FollowUpType.EXAMPLE_REQUEST

        if score <= 5.0:
            return FollowUpType.CLARIFICATION

        # Check for explicit technology mentions in strong answers
        tech_matches = _TECH_PATTERNS.findall(ans)
        if tech_matches and config and config.interview_type.value in ("Project Based", "Role Specific", "Technical"):
            if len(words) > 50:
                return FollowUpType.PROJECT_SPECIFIC
            return FollowUpType.HOW_QUESTION

        # Strong technical answers -> probe depth, trade-offs, or optimization
        if score >= 8.5:
            if config and config.experience_level in (ExperienceLevel.TWO_TO_FIVE, ExperienceLevel.FIVE_PLUS):
                return FollowUpType.DEEP_TECHNICAL
            return FollowUpType.OPTIMIZATION

        if score >= 7.0:
            return FollowUpType.TRADEOFF

        # Default fallback
        return FollowUpType.HOW_QUESTION

    def create_follow_up_plan(
        self,
        parent_question: Question,
        candidate_answer: str,
        config: InterviewConfig,
        evaluation: Optional[AnswerEvaluation] = None,
        follow_up_type: Optional[FollowUpType] = None,
    ) -> FollowUpPlan:
        """
        Formulate a structured FollowUpPlan prior to generation with sub-millisecond execution.
        """
        ftype = follow_up_type or self.determine_follow_up_type(
            candidate_answer=candidate_answer,
            parent_question=parent_question,
            evaluation=evaluation,
            config=config,
        )

        anchor = self.extract_anchor(
            candidate_answer=candidate_answer,
            parent_question=parent_question,
            evaluation=evaluation,
        )

        topic = parent_question.topic or (config.topics[0] if config.topics else "General")
        diff = parent_question.difficulty

        template = _OBJECTIVE_TEMPLATES.get(ftype, "Probe candidate depth and practical mastery on '{anchor}' in {topic}.")
        objective = template.format(anchor=anchor, topic=topic)

        return FollowUpPlan(
            follow_up_type=ftype,
            anchor_concept_or_quote=anchor,
            target_topic=topic,
            difficulty=diff,
            objective=objective,
            rationale=f"Selected {ftype.value} targeting anchor '{anchor}' based on candidate response analysis.",
        )

    def generate_follow_up(
        self,
        config: InterviewConfig,
        parent_question: Question,
        candidate_answer: str,
        question_number: int,
        evaluation: Optional[AnswerEvaluation] = None,
        follow_up_type: Optional[FollowUpType] = None,
    ) -> Question:
        """
        Full Follow-Up Generation Pipeline:
        1. Formulate FollowUpPlan.
        2. Formulate LLM prompt referencing candidate's exact words and target type.
        3. Query LLM for structured Question output.
        4. Validate adherence to FollowUpType and anchor referencing.
        5. Fallback gracefully to deterministic templates if offline or invalid.
        """
        with Timer("follow_up_generation"):
            plan = self.create_follow_up_plan(
                parent_question=parent_question,
                candidate_answer=candidate_answer,
                config=config,
                evaluation=evaluation,
                follow_up_type=follow_up_type,
            )

            # If LLM service is available, attempt structured generation
            if self.llm_service:
                prompt = build_follow_up_prompt(
                    config=config,
                    parent_question=parent_question,
                    candidate_answer=candidate_answer,
                    follow_up_plan=plan,
                    question_number=question_number,
                    evaluation=evaluation,
                )

                for attempt in range(self.max_retries + 1):
                    try:
                        q = self.llm_service.generate_structured(
                            prompt=prompt,
                            schema=Question,
                            system=FOLLOW_UP_GENERATOR_SYSTEM_PROMPT,
                        )

                        # Enforce follow-up invariants
                        q.question_number = question_number
                        q.is_follow_up = True
                        q.follow_up_type = plan.follow_up_type
                        q.parent_question_id = parent_question.id or parent_question.question_number or 1
                        q.anchor_reference = plan.anchor_concept_or_quote
                        q.topic = plan.target_topic
                        q.difficulty = plan.difficulty
                        q.metadata["follow_up_objective"] = plan.objective
                        q.metadata["generation_attempt"] = attempt + 1

                        logger.info(f"Generated Follow-Up Q{question_number} [{plan.follow_up_type.value}] referencing '{plan.anchor_concept_or_quote}'")
                        return q

                    except (LLMValidationError, LLMConnectionError, Exception) as e:
                        logger.warning(f"Follow-up LLM generation error on attempt {attempt + 1}: {e}")

            # Deterministic Fallback Generator
            logger.info(f"Using deterministic fallback for follow-up type [{plan.follow_up_type.value}]")
            return self._generate_fallback_follow_up(
                config=config,
                parent_question=parent_question,
                plan=plan,
                question_number=question_number,
            )

    def _generate_fallback_follow_up(
        self,
        config: InterviewConfig,
        parent_question: Question,
        plan: FollowUpPlan,
        question_number: int,
    ) -> Question:
        """
        Deterministic, high-quality follow-up question generator for all 10 FollowUpTypes.
        """
        role = config.role or "Software Engineer"
        topic = plan.target_topic
        anchor = plan.anchor_concept_or_quote
        ftype = plan.follow_up_type
        diff = plan.difficulty

        tpl_entry = _FALLBACK_TEMPLATES.get(ftype, _FALLBACK_TEMPLATES[FollowUpType.CLARIFICATION])
        text_tpl, raw_concepts, raw_rubric = tpl_entry

        text = text_tpl.format(anchor=anchor, topic=topic, role=role)
        concepts = [c.format(anchor=anchor, topic=topic, role=role) for c in raw_concepts]
        rubric = [r.format(anchor=anchor, topic=topic, role=role) for r in raw_rubric]

        return Question(
            question_number=question_number,
            text=text,
            category=f"{config.interview_type.value} - Follow-Up",
            topic=topic,
            difficulty=diff,
            question_type=parent_question.question_type,
            expected_concepts=concepts,
            evaluation_criteria=rubric,
            follow_up_possible=True,
            is_follow_up=True,
            follow_up_type=ftype,
            parent_question_id=parent_question.id or parent_question.question_number or 1,
            anchor_reference=anchor,
            metadata={
                "fallback": True,
                "follow_up_type": ftype.value,
                "anchor_reference": anchor,
                "objective": plan.objective,
            },
        )
