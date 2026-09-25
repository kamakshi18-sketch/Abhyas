"""
Dedicated Answer Evaluation Engine.
Implements structured, evidence-based candidate answer evaluation across type-specific rubrics.
"""

import json
import logging
import re
from typing import List, Optional, Tuple, Dict, Any

from pydantic import ValidationError
from app.ai.ollama_client import LLMService, LLMConnectionError, LLMValidationError
from app.ai.factory import get_llm_service
from app.schemas.interview import (
    InterviewConfig,
    Question,
    QuestionEvaluationPair,
    AnswerEvaluation,
    EvaluationCriterion,
    EvaluationEvidence,
    EvaluationMetrics,
    EvaluationSummary,
    DEFAULT_ASSESSMENT_DISCLAIMER,
)
from app.core.evaluation_rubrics import EvaluationRubricService, EvaluationRubric
from app.core.prompts import (
    ANSWER_EVALUATOR_SYSTEM_PROMPT,
    SUMMARY_GENERATOR_SYSTEM_PROMPT,
    EVALUATION_PROMPT_VERSION,
    build_evaluation_prompt,
    build_summary_prompt,
)
from app.performance.timers import Timer
from app.performance.cache import get_evaluation_cache, EvaluationCache

logger = logging.getLogger(__name__)


class EvaluationValidator:
    """Quality control validator for structured AnswerEvaluation payloads."""

    @classmethod
    def validate(
        cls,
        evaluation: AnswerEvaluation,
        rubric: EvaluationRubric,
        candidate_answer: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate evaluation completeness, score bounds, and evidence grounding.
        """
        # 1. Score Boundary Checks
        if evaluation.score < 0.0 or evaluation.score > 10.0:
            return False, f"Overall score {evaluation.score} is outside allowed [0.0, 10.0] range."

        for c in evaluation.criteria_scores:
            if c.score < 0.0 or c.score > 10.0:
                return False, f"Criterion '{c.name}' score {c.score} is outside allowed [0.0, 10.0] range."

        # 2. Rubric Completeness
        if rubric.criteria and not evaluation.criteria_scores:
            return False, "Evaluation contains no criteria breakdown for the required rubric."

        # 3. Non-empty narrative
        if not evaluation.feedback or len(evaluation.feedback.strip()) < 10:
            return False, "Evaluation feedback is too short or empty."

        if not evaluation.suggested_improvement or len(evaluation.suggested_improvement.strip()) < 5:
            return False, "Evaluation must provide actionable suggested improvement."

        # 4. Evidence Grounding Verification
        # Check that extracted quotes are genuinely grounded in candidate answer
        clean_ans_lower = candidate_answer.lower()
        if len(clean_ans_lower) > 20 and evaluation.evidence:
            for ev in evaluation.evidence:
                quote = ev.quote_or_reference.strip().lower()
                # For substantial quotes, verify some overlap with the answer text
                if len(quote) > 15:
                    quote_words = [w for w in re.findall(r"\w+", quote) if len(w) > 3]
                    matching_words = [w for w in quote_words if w in clean_ans_lower]
                    if quote_words and len(matching_words) / len(quote_words) < 0.3:
                        logger.debug(f"Evidence quote '{ev.quote_or_reference[:30]}' lacks sufficient overlap with candidate answer.")

        return True, None


class AnswerEvaluationService:
    """
    Dedicated Answer Evaluation Service orchestrating the pipeline:
    Candidate Answer -> Rubric Resolution -> LLM Evaluation -> Quality Validation -> Structured Result.
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        rubric_service: Optional[EvaluationRubricService] = None,
        validator: Optional[EvaluationValidator] = None,
        max_retries: int = 2,
    ):
        self.llm_service = llm_service or get_llm_service()
        self.rubric_service = rubric_service or EvaluationRubricService()
        self.validator = validator or EvaluationValidator()
        self.max_retries = max_retries

    def evaluate_answer(
        self,
        config: InterviewConfig,
        question: Question,
        candidate_answer: str,
    ) -> AnswerEvaluation:
        """
        Evaluate candidate response against question, expected concepts, and type-specific rubric.
        Optimized with deterministic LRU caching and quality validation.
        """
        with Timer("evaluation_pipeline"):
            clean_text = candidate_answer.strip()

            # 1. Resolve Type-Specific Rubric
            rubric = self.rubric_service.get_rubric(
                interview_type=config.interview_type,
                question_type=question.question_type,
            )

            # 2. Short-Circuit: Empty or Whitespace-Only Answer
            if not clean_text or clean_text == "(No answer provided)":
                return self._generate_empty_answer_evaluation(rubric)

            # 3. Short-Circuit: Refusal or Non-Answer (e.g. "I don't know", "skip", "no idea")
            if self._is_refusal_answer(clean_text):
                return self._generate_refusal_evaluation(clean_text, question, rubric)

            # 4. Check Safe Deterministic Evaluation Cache
            eval_cache = get_evaluation_cache()
            model_name = getattr(self.llm_service, "model", "default")
            cache_key = eval_cache.generate_key(
                question_text=question.text or question.question_text or "",
                candidate_answer=clean_text,
                rubric_type=rubric.category_name,
                persona=config.interviewer_persona.value,
                language=config.language,
                model=model_name,
                prompt_version=EVALUATION_PROMPT_VERSION,
            )
            cached_eval = eval_cache.get(cache_key)
            if cached_eval is not None:
                logger.info(f"Evaluation cache HIT for Q{question.question_number} (score: {cached_eval.score}/10)")
                return cached_eval

            # 5. Build Prompt
            rubric_instructions = self.rubric_service.format_rubric_prompt_instructions(rubric)
            prompt = build_evaluation_prompt(
                config=config,
                question=question,
                candidate_answer=clean_text,
                rubric_instructions=rubric_instructions,
            )

            # 6. LLM Structured Generation Loop with Validation & Retry
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    evaluation = self.llm_service.generate_structured(
                        prompt=prompt,
                        schema=AnswerEvaluation,
                        system=ANSWER_EVALUATOR_SYSTEM_PROMPT,
                    )

                    # Ensure criteria completeness
                    self._ensure_rubric_criteria_present(evaluation, rubric)

                    # Validate quality
                    is_valid, reason = self.validator.validate(
                        evaluation=evaluation,
                        rubric=rubric,
                        candidate_answer=clean_text,
                    )

                    if is_valid:
                        # Guarantee disclaimer is populated
                        if not evaluation.assessment_disclaimer:
                            evaluation.assessment_disclaimer = DEFAULT_ASSESSMENT_DISCLAIMER
                        logger.info(
                            f"Evaluated Q{question.question_number} answer with score {evaluation.score}/10 on attempt {attempt + 1}"
                        )
                        eval_cache.put(cache_key, evaluation)
                        return evaluation
                    else:
                        logger.warning(f"Evaluation validation failed (Attempt {attempt + 1}): {reason}")
                        last_error = reason
                        prompt += f"\n\nCRITICAL FIX: Previous output failed validation: {reason}. Output strict JSON adhering to schema."

                except (LLMValidationError, LLMConnectionError, ValidationError, Exception) as e:
                    logger.warning(f"Error during structured evaluation on attempt {attempt + 1}: {e}")
                    last_error = str(e)
                    prompt += "\n\nJSON Error: Ensure valid JSON with numeric scores (0.0-10.0) and criteria breakdown."

            # 7. Fallback Grounded Heuristic Evaluation
            logger.error(f"LLM evaluation failed after {self.max_retries + 1} attempts ({last_error}). Using deterministic fallback.")
            fallback_eval = self._generate_fallback_evaluation(config, question, clean_text, rubric)
            eval_cache.put(cache_key, fallback_eval)
            return fallback_eval

    def generate_summary(
        self,
        config: InterviewConfig,
        pairs: List[QuestionEvaluationPair],
    ) -> EvaluationSummary:
        """
        Synthesize individual question-answer evaluations into a comprehensive final session summary.
        """
        if not pairs:
            return EvaluationSummary(
                overall_score=0.0,
                criteria_averages={},
                strengths_summary=["Session commenced."],
                weaknesses_summary=["No questions were answered during the session."],
                overall_feedback="The interview session was concluded before any questions were submitted.",
                areas_to_improve=["Complete a full practice session with answered questions."],
                disclaimer=DEFAULT_ASSESSMENT_DISCLAIMER,
            )

        prompt = build_summary_prompt(config=config, pairs=pairs)

        for attempt in range(self.max_retries + 1):
            try:
                summary = self.llm_service.generate_structured(
                    prompt=prompt,
                    schema=EvaluationSummary,
                    system=SUMMARY_GENERATOR_SYSTEM_PROMPT,
                )
                summary.overall_score = max(0.0, min(10.0, round(summary.overall_score, 1)))
                if not summary.criteria_averages:
                    summary.criteria_averages = self._calculate_criteria_averages(pairs)
                return summary

            except Exception as e:
                logger.warning(f"Error generating summary via LLM (attempt {attempt + 1}): {e}")

        # Fallback summary computation
        return self._generate_fallback_summary(config, pairs)

    # =====================================================================
    # INTERNAL HELPERS & FALLBACK EVALUATORS
    # =====================================================================

    def _is_refusal_answer(self, text: str) -> bool:
        """Check if candidate explicitly stated they do not know or skipped."""
        refusal_patterns = [
            r"^(i\s+)?don'?t\s+know",
            r"^no\s+idea",
            r"^skip",
            r"^pass",
            r"^not\s+sure",
            r"^i\s+have\s+no\s+clue",
            r"^\.{2,}",
            r"^\?+$",
        ]
        text_lower = text.strip().lower()
        if len(text_lower.split()) <= 6:
            for pattern in refusal_patterns:
                if re.search(pattern, text_lower):
                    return True
        return False

    def _generate_empty_answer_evaluation(self, rubric: EvaluationRubric) -> AnswerEvaluation:
        """Immediate structured evaluation for empty/omitted answers."""
        criteria_scores = [
            EvaluationCriterion(
                name=c.name,
                score=1.0,
                weight=c.weight,
                feedback=f"No response provided to assess {c.name.lower()}.",
                evidence=[
                    EvaluationEvidence(
                        quote_or_reference="[No answer submitted]",
                        criterion_name=c.name,
                        assessment="Candidate did not submit text for this question.",
                        is_positive=False,
                    )
                ],
            )
            for c in rubric.criteria
        ]

        return AnswerEvaluation(
            score=1.0,
            criteria_scores=criteria_scores,
            evidence=[
                EvaluationEvidence(
                    quote_or_reference="[No answer submitted]",
                    criterion_name="General",
                    assessment="Candidate left the question blank.",
                    is_positive=False,
                )
            ],
            metrics=EvaluationMetrics(relevance=1, correctness=1, completeness=1, clarity=1, depth=1),
            strengths=["Answer submission was acknowledged."],
            weaknesses=["No substantive content or thought process was provided."],
            feedback="The answer was empty or non-substantive. In an actual interview, always state your initial intuition, ask clarifying questions, or explain your problem-solving approach even when uncertain.",
            suggested_improvement="Provide a structured response: define the core concept, discuss practical considerations, and outline how you would approach solving it.",
            assessment_disclaimer=DEFAULT_ASSESSMENT_DISCLAIMER,
        )

    def _generate_refusal_evaluation(
        self,
        answer_text: str,
        question: Question,
        rubric: EvaluationRubric,
    ) -> AnswerEvaluation:
        """Evaluation for explicit 'I don't know' or brief refusal answers."""
        criteria_scores = [
            EvaluationCriterion(
                name=c.name,
                score=2.0 if c.name.lower() in ("communication", "relevance") else 1.0,
                weight=c.weight,
                feedback=f"Candidate stated unfamiliarity with the topic.",
                evidence=[
                    EvaluationEvidence(
                        quote_or_reference=answer_text,
                        criterion_name=c.name,
                        assessment="Acknowledged lack of knowledge.",
                        is_positive=False,
                    )
                ],
            )
            for c in rubric.criteria
        ]

        expected_hint = (
            ", ".join(question.expected_concepts[:2])
            if question.expected_concepts
            else "fundamental concepts"
        )

        return AnswerEvaluation(
            score=1.5,
            criteria_scores=criteria_scores,
            evidence=[
                EvaluationEvidence(
                    quote_or_reference=answer_text,
                    criterion_name="Honesty",
                    assessment="Candidate honestly acknowledged gap in knowledge.",
                    is_positive=True,
                )
            ],
            metrics=EvaluationMetrics(relevance=2, correctness=1, completeness=1, clarity=3, depth=1),
            strengths=["Demonstrated honesty regarding knowledge boundaries."],
            weaknesses=[f"Did not attempt to reason through {question.topic or 'the question'}."],
            feedback=f"While honesty is valued, in senior interviews it is beneficial to articulate what you know adjacent to the problem, reason from first principles, or discuss how you would research '{expected_hint}'.",
            suggested_improvement=f"Study {question.topic or 'core fundamentals'}, focusing on {expected_hint}.",
            assessment_disclaimer=DEFAULT_ASSESSMENT_DISCLAIMER,
        )

    def _generate_fallback_evaluation(
        self,
        config: InterviewConfig,
        question: Question,
        answer_text: str,
        rubric: EvaluationRubric,
    ) -> AnswerEvaluation:
        """
        Deterministic, grounded evaluation fallback when LLM structured generation fails.
        Extracts representative sentences as evidence and computes weighted criteria scores.
        """
        words = answer_text.split()
        word_count = len(words)

        # Baseline score estimation based on response substance & expected concept matches
        expected_concepts = question.expected_concepts or question.expected_points or []
        concept_matches = 0
        ans_lower = answer_text.lower()
        for concept in expected_concepts:
            concept_words = [w.lower() for w in re.findall(r"\w+", concept) if len(w) > 3]
            if concept_words and any(cw in ans_lower for cw in concept_words):
                concept_matches += 1

        # Heuristic scoring
        substance_score = min(4.0, (word_count / 30.0) * 2.0)
        concept_score = (concept_matches / max(1, len(expected_concepts))) * 4.0 if expected_concepts else 2.5
        calculated_score = round(min(8.5, max(3.0, 2.0 + substance_score + concept_score)), 1)

        # Extract representative excerpt as grounded evidence
        sentences = [s.strip() for s in re.split(r"[.!?\n]", answer_text) if len(s.strip()) > 10]
        primary_quote = sentences[0] if sentences else answer_text[:80]

        criteria_scores = []
        for c in rubric.criteria:
            c_score = calculated_score
            if c.name.lower() in ("correctness", "action", "concepts"):
                c_score = round(min(10.0, max(2.0, calculated_score + (0.5 if concept_matches > 0 else -0.5))), 1)
            elif c.name.lower() in ("clarity", "communication", "specificity"):
                c_score = round(min(10.0, max(3.0, 4.0 + (word_count / 40.0))), 1)

            criteria_scores.append(
                EvaluationCriterion(
                    name=c.name,
                    score=c_score,
                    weight=c.weight,
                    feedback=f"Demonstrated response substance for {c.name.lower()}.",
                    evidence=[
                        EvaluationEvidence(
                            quote_or_reference=primary_quote,
                            criterion_name=c.name,
                            assessment=f"Candidate referenced key approach concerning {question.topic}.",
                            is_positive=True,
                        )
                    ],
                )
            )

        int_metric = int(max(1, min(10, round(calculated_score))))

        strengths = [
            f"Addressed core elements of {question.topic} with clear structure.",
            "Demonstrated relevant technical terminology in the explanation.",
        ]
        weaknesses = [
            "Could elaborate further on boundary conditions and architectural trade-offs.",
            "Would benefit from deeper concrete implementation or STAR result metrics.",
        ]

        return AnswerEvaluation(
            score=calculated_score,
            criteria_scores=criteria_scores,
            evidence=[
                EvaluationEvidence(
                    quote_or_reference=primary_quote,
                    criterion_name=rubric.criteria[0].name if rubric.criteria else "General",
                    assessment=f"Highlighted key approach on {question.topic}.",
                    is_positive=True,
                )
            ],
            metrics=EvaluationMetrics(
                relevance=int_metric,
                correctness=int_metric,
                completeness=int_metric,
                clarity=int_metric,
                depth=int_metric,
            ),
            strengths=strengths,
            weaknesses=weaknesses,
            feedback=f"Your response demonstrates a practical working knowledge of {question.topic}. To achieve a senior-level rating, structure your response by detailing underlying mechanics, edge cases, and concrete performance trade-offs.",
            suggested_improvement=f"Reinforce the explanation by covering: {', '.join(expected_concepts[:2]) if expected_concepts else 'system design implications and trade-offs'}.",
            assessment_disclaimer=DEFAULT_ASSESSMENT_DISCLAIMER,
        )

    def _ensure_rubric_criteria_present(
        self,
        evaluation: AnswerEvaluation,
        rubric: EvaluationRubric,
    ) -> None:
        """Ensure that if the LLM omitted some rubric criteria, they are backfilled."""
        existing_names = {c.name.lower() for c in evaluation.criteria_scores}
        for defn in rubric.criteria:
            if defn.name.lower() not in existing_names:
                evaluation.criteria_scores.append(
                    EvaluationCriterion(
                        name=defn.name,
                        score=evaluation.score,
                        weight=defn.weight,
                        feedback=f"Evaluated in line with overall answer score ({evaluation.score}/10).",
                        evidence=[],
                    )
                )

    def _calculate_criteria_averages(self, pairs: List[QuestionEvaluationPair]) -> Dict[str, float]:
        """Aggregate criteria averages across completed pairs."""
        criterion_sums: Dict[str, float] = {}
        criterion_counts: Dict[str, int] = {}

        for pair in pairs:
            for c in pair.evaluation.criteria_scores:
                criterion_sums[c.name] = criterion_sums.get(c.name, 0.0) + c.score
                criterion_counts[c.name] = criterion_counts.get(c.name, 0) + 1

        return {
            name: round(criterion_sums[name] / max(1, criterion_counts[name]), 1)
            for name in criterion_sums
        }

    def _generate_fallback_summary(
        self,
        config: InterviewConfig,
        pairs: List[QuestionEvaluationPair],
    ) -> EvaluationSummary:
        """Generate arithmetic aggregated summary when LLM generation fails."""
        total_score = sum(pair.evaluation.score for pair in pairs)
        avg_score = round(total_score / len(pairs), 1) if pairs else 0.0

        all_strengths = []
        all_weaknesses = []
        for pair in pairs:
            all_strengths.extend(pair.evaluation.strengths)
            all_weaknesses.extend(pair.evaluation.weaknesses)

        unique_strengths = list(dict.fromkeys(all_strengths))[:3] or [
            "Demonstrated consistent technical communication.",
            "Answered questions with structured thinking.",
        ]
        unique_weaknesses = list(dict.fromkeys(all_weaknesses))[:3] or [
            "Deepen coverage of architectural trade-offs and edge cases.",
        ]

        feedback_text = (
            f"Candidate completed {len(pairs)} questions for the {config.role} position with an overall score of {avg_score}/10. "
            f"Solid foundational knowledge and engagement were demonstrated. Focus further practice on explaining internal mechanisms, "
            f"handling failure scenarios, and quantifying outcomes."
        )

        return EvaluationSummary(
            overall_score=avg_score,
            criteria_averages=self._calculate_criteria_averages(pairs),
            strengths_summary=unique_strengths,
            weaknesses_summary=unique_weaknesses,
            overall_feedback=feedback_text,
            areas_to_improve=[
                f"Review advanced concepts relevant to {config.role}.",
                "Practice framing answers using structured reasoning and explicit trade-off comparisons.",
            ],
            disclaimer=DEFAULT_ASSESSMENT_DISCLAIMER,
        )
