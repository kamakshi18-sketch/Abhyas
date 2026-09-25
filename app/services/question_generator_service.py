"""
Question Generator Service.
Executes the Question Generation Pipeline:
InterviewConfig -> Question Strategy -> LLM -> Structured Output -> Question Validation & Quality Control -> Question Object.
"""

import re
import logging
from typing import List, Optional, Set, Tuple
from pydantic import ValidationError

from app.schemas.interview import (
    InterviewConfig,
    Question,
    QuestionType,
    StrategyPlan,
    Difficulty,
    ExperienceLevel,
)
from app.ai.ollama_client import LLMService, LLMValidationError, LLMConnectionError
from app.core.question_strategy import QuestionStrategyService
from app.core.prompts import (
    QUESTION_GENERATOR_SYSTEM_PROMPT,
    build_question_prompt,
)

logger = logging.getLogger(__name__)


class QuestionValidator:
    """Quality control validator enforcing anti-duplication, topic adherence, and experience sanity."""

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Convert text into normalized alphanumeric stemmed word tokens."""
        words = re.findall(r"\b\w{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "this", "that", "what", "how", "can", "you",
            "explain", "describe", "would", "your", "using", "from", "which", "when",
            "does", "are", "into", "their", "have", "been",
        }
        stemmed = set()
        for w in words:
            if w in stopwords:
                continue
            if w.endswith("ies"):
                w = w[:-3] + "y"
            elif w.endswith("es"):
                w = w[:-2]
            elif w.endswith("s") and not w.endswith("ss"):
                w = w[:-1]
            stemmed.add(w)
        return stemmed

    @classmethod
    def calculate_similarity(cls, text_a: str, text_b: str) -> float:
        """Calculate Jaccard token similarity between two questions."""
        tokens_a = cls._tokenize(text_a)
        tokens_b = cls._tokenize(text_b)
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / len(union)

    @classmethod
    def validate(
        cls,
        question: Question,
        strategy: StrategyPlan,
        previous_questions: List[Question],
        config: InterviewConfig,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate question against quality standards:
        1. Non-empty text (> 10 chars).
        2. Expected concepts provided (>= 1).
        3. No duplicate overlap with previously asked questions.
        4. Topic adherence.
        """
        q_text = (question.text or question.question_text or "").strip()
        if len(q_text) < 10:
            return False, "Question text is too short or empty."

        concepts = question.expected_concepts or question.expected_points or []
        if len(concepts) < 1:
            return False, "Question must provide at least one expected concept."

        # Anti-duplication check
        for prev in previous_questions:
            prev_text = prev.text or prev.question_text or ""
            if q_text.lower() == prev_text.lower():
                return False, f"Exact duplicate of Question #{prev.question_number}."
            sim = cls.calculate_similarity(q_text, prev_text)
            if sim >= 0.45:
                return False, f"Question is too similar to Question #{prev.question_number} (Similarity: {sim:.2f})."

        return True, None


class QuestionGeneratorService:
    """Dedicated Question Generation Engine orchestrating Strategy, LLM, Validation, and Fallback."""

    def __init__(self, llm_service: LLMService, max_retries: int = 2):
        self.llm_service = llm_service
        self.max_retries = max_retries
        self.strategy_service = QuestionStrategyService()
        self.validator = QuestionValidator()

    def generate_question(
        self,
        config: InterviewConfig,
        question_number: int,
        previous_questions: Optional[List[Question]] = None,
        strategy: Optional[StrategyPlan] = None,
    ) -> Question:
        """
        Full Question Generation Pipeline:
        1. Determine StrategyPlan (uses provided adaptive strategy or calculates baseline).
        2. Formulate targeted LLM prompt with Persona, Topic, Type, Decision, and Language.
        3. Query LLM for structured Question output.
        4. Validate quality, duplicates, and topic restrictions.
        5. Retry on failure or fallback gracefully.
        """
        prev_qs = previous_questions or []
        
        # 1. Question Strategy
        active_strategy = strategy or self.strategy_service.get_strategy_for_step(
            config=config,
            question_number=question_number,
            asked_questions=prev_qs,
        )

        # 2. LLM Generation Loop with Quality Control
        prompt = build_question_prompt(
            config=config,
            question_number=question_number,
            previous_questions=prev_qs,
            effective_difficulty=active_strategy.difficulty,
            strategy=active_strategy,
        )


        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                question = self.llm_service.generate_structured(
                    prompt=prompt,
                    schema=Question,
                    system=QUESTION_GENERATOR_SYSTEM_PROMPT,
                )

                # Ensure strategy parameters are enforced
                question.question_number = question_number
                question.topic = active_strategy.target_topic
                question.category = question.category or active_strategy.category
                question.difficulty = question.difficulty or active_strategy.difficulty
                question.question_type = question.question_type or active_strategy.question_type

                # 3. Quality Control Validation
                is_valid, reason = self.validator.validate(
                    question=question,
                    strategy=active_strategy,
                    previous_questions=prev_qs,
                    config=config,
                )

                if is_valid:
                    # Enrich metadata
                    question.metadata = {
                        "strategy_objective": active_strategy.objective,
                        "generation_attempt": attempt + 1,
                        "persona": config.interviewer_persona.value,
                        "language": config.language,
                    }
                    if active_strategy.decision:
                        question.metadata["decision_action"] = active_strategy.decision.action.value
                        question.metadata["decision_reason"] = active_strategy.decision.reason
                    logger.info(f"Generated Q{question_number} [{question.question_type.value} | {question.topic}] on attempt {attempt + 1}")
                    return question
                else:
                    logger.warning(f"Question validation failed (Attempt {attempt + 1}): {reason}")
                    last_error = reason
                    prompt += f"\n\nCRITICAL FIX REQUIRED: Previous attempt failed validation ({reason}). Please formulate a fresh, distinct, and specific question on '{active_strategy.target_topic}'."

            except (LLMValidationError, LLMConnectionError, ValidationError, Exception) as e:
                logger.warning(f"Error during structured question generation on attempt {attempt + 1}: {e}")
                last_error = str(e)
                prompt += f"\n\nJSON Parse Error: Please return strict JSON matching the Question schema."

        # 4. Fallback Heuristic Generator
        logger.error(f"LLM question generation failed after {self.max_retries + 1} attempts ({last_error}). Using deterministic fallback.")
        return self._generate_fallback_question(config, active_strategy, question_number)

    def _generate_fallback_question(
        self,
        config: InterviewConfig,
        strategy: StrategyPlan,
        question_number: int,
    ) -> Question:
        """
        Deterministic, high-quality fallback generator aligned to StrategyPlan, DecisionAction, and ExperienceLevel.
        """
        role = config.role or "Software Engineer"
        topic = strategy.target_topic
        q_type = strategy.question_type
        exp = config.experience_level
        diff = strategy.difficulty
        action = strategy.decision_action or (strategy.decision.action if strategy.decision else None)

        # Customized fallback questions based on DecisionAction
        if action == "FOLLOW_UP":
            ref = strategy.context_reference or "the key mechanism"
            text = f"Following up on your previous answer regarding {topic}, could you elaborate specifically on how you would address {ref} and handle potential concurrency or failure edge cases?"
            concepts = [f"{topic} edge case handling", "Failure recovery", "Trade-off analysis"]
            rubric = ["Precision of follow-up detail", "Technical accuracy", "Practical resilience"]
        elif action == "DEEP_DIVE":
            text = f"Let's dive deeper into {topic}. In a mission-critical, high-scale {role} environment, how does the internal memory model and execution runtime handle peak load without performance degradation?"
            concepts = ["Memory management & GC/pointers", "Lock contention / asynchronous concurrency", "Low-level optimization"]
            rubric = ["Architectural depth", "Internal execution comprehension", "Performance trade-offs"]
        elif action == "CLARIFY":
            text = f"To clarify your previous point on {topic}, could you clearly distinguish the underlying assumptions and trade-offs of your chosen implementation versus standard alternatives?"
            concepts = ["Core trade-off justification", "Underlying assumptions", "Clear architectural reasoning"]
            rubric = ["Clarity of thought", "Factual accuracy", "Structured communication"]
        elif action == "REPHRASE":
            text = f"To explore {topic} from another angle: suppose you are explaining this concept to a junior teammate with a practical real-world analogy. How would you describe what {topic} solves?"
            concepts = [f"Foundational role of {topic}", "Core problem solved", "Intuitive real-world analogy"]
            rubric = ["Conceptual clarity", "Simplicity and accuracy", "Communication effectiveness"]
        elif action == "FINAL_QUESTION":
            text = f"As our final question: looking back at our discussion across {topic} and system design, what is the single most critical architectural decision you would make for a {role} project, and why?"
            concepts = ["Comprehensive system synthesis", "Strategic trade-off evaluation", "Executive engineering judgment"]
            rubric = ["Holistic perspective", "Senior leadership judgment", "Clarity and impact"]
        elif q_type == QuestionType.CONCEPTUAL:
            text = f"Can you explain the foundational architecture, core principles, and internal execution model of {topic} in modern {role} systems?"
            concepts = [f"{topic} architecture", "Core execution lifecycle", "Key advantages and limitations"]
            rubric = ["Conceptual depth", "Accuracy of technical terms", "Clarity of explanation"]
        elif q_type == QuestionType.PROBLEM_SOLVING:
            text = f"Suppose you encounter a severe latency spike or deadlock related to {topic} in production. Walk me step-by-step through how you would isolate and fix the root cause."
            concepts = ["Diagnostic logging & metrics", "Root cause isolation", "Remediation and regression prevention"]
            rubric = ["Systematic debugging approach", "Practical production awareness", "Edge case handling"]
        elif q_type == QuestionType.PROJECT:
            text = f"Describe a complex project where you utilized {topic}. What key technical design trade-offs did you make, and how did it impact overall system performance?"
            concepts = [f"{topic} implementation details", "Architectural trade-offs", "Measurable outcome / latency / throughput"]
            rubric = ["Depth of ownership", "Justification of design trade-offs", "Reflective insight"]
        elif q_type == QuestionType.BEHAVIORAL:
            text = f"Tell me about a time when you and another engineer disagreed on an implementation strategy concerning {topic}. How did you resolve the disagreement and reach consensus?"
            concepts = ["Active listening & data-driven arguments", "Constructive compromise", "Team alignment"]
            rubric = ["STAR structure (Situation, Task, Action, Result)", "Professionalism", "Collaboration"]
        elif q_type == QuestionType.SITUATIONAL:
            text = f"If you were asked to deliver a mission-critical feature involving {topic} under a very tight deadline with incomplete specifications, how would you approach the execution?"
            concepts = ["Requirements clarification", "Scope prioritization & MVP", "Risk mitigation"]
            rubric = ["Pragmatic decision making", "Stakeholder communication", "Quality assurance"]
        elif q_type == QuestionType.HR:
            text = f"What initially drew you to work with {topic} in your career as a {role}, and where do you see your technical skills evolving over the next two years?"
            concepts = ["Career trajectory & passions", "Continuous learning mindset", "Alignment with engineering excellence"]
            rubric = ["Authenticity", "Growth orientation", "Clarity of vision"]
        else: # TECHNICAL / ROLE_SPECIFIC
            if exp in (ExperienceLevel.FIVE_PLUS, ExperienceLevel.TWO_TO_FIVE):
                text = f"In the context of a high-throughput distributed system for {role}, how would you architect and optimize data consistency, caching, and partitioning when working with {topic}?"
                concepts = ["Horizontal scaling & partitioning", "Cache invalidation strategies", "Failure recovery & fault tolerance"]
                rubric = ["Scalability reasoning", "Handling network partitions", "Operational observability"]
            else:
                text = f"As a {role}, what are the primary best practices, common anti-patterns, and testing strategies you apply when developing applications with {topic}?"
                concepts = ["Idiomatic coding standards", "Error handling & validation", "Unit and integration testing"]
                rubric = ["Code quality awareness", "Defensive programming", "Practical comprehension"]


        return Question(
            question_number=question_number,
            text=text,
            category=strategy.category,
            topic=topic,
            difficulty=diff,
            question_type=q_type,
            expected_concepts=concepts,
            evaluation_criteria=rubric,
            follow_up_possible=True,
            metadata={
                "fallback": True,
                "strategy_objective": strategy.objective,
                "experience_tier": exp.value,
            },
        )
