"""
Unit and integration tests for Phase 4: Dedicated Answer Evaluation Engine.
Tests strong, weak, incomplete, irrelevant, and malformed answers across
Technical, Behavioral STAR, HR, and other interview types, plus SQLite persistence.
"""

import json
import pytest
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    QuestionType,
    Difficulty,
    ExperienceLevel,
    Question,
    CandidateAnswer,
    AnswerEvaluation,
    EvaluationCriterion,
    EvaluationEvidence,
    EvaluationSummary,
)
from app.core.evaluation_rubrics import (
    EvaluationRubricService,
    RUBRIC_TECHNICAL,
    RUBRIC_BEHAVIORAL,
    RUBRIC_HR,
)
from app.services.evaluation_service import AnswerEvaluationService, EvaluationValidator
from app.database.repository import InterviewRepository
from tests.conftest import MockLLMService


# =====================================================================
# 1. EVALUATION RUBRIC SERVICE TESTS
# =====================================================================

def test_evaluation_rubric_resolution():
    """Test that different interview and question types resolve to correct specialized rubrics."""
    # Technical
    tech_rubric = EvaluationRubricService.get_rubric(InterviewType.TECHNICAL, QuestionType.TECHNICAL)
    assert tech_rubric.category_name == "Technical"
    tech_names = tech_rubric.get_criterion_names()
    assert "Correctness" in tech_names
    assert "Concepts" in tech_names
    assert "Reasoning" in tech_names
    assert "Implementation" in tech_names

    # Behavioral (STAR)
    beh_rubric = EvaluationRubricService.get_rubric(InterviewType.BEHAVIORAL, QuestionType.BEHAVIORAL)
    assert beh_rubric.category_name == "Behavioral"
    beh_names = beh_rubric.get_criterion_names()
    assert "Situation" in beh_names
    assert "Task" in beh_names
    assert "Action" in beh_names
    assert "Result" in beh_names
    assert "Ownership" in beh_names
    assert "Specificity" in beh_names

    # HR
    hr_rubric = EvaluationRubricService.get_rubric(InterviewType.HR, QuestionType.HR)
    assert hr_rubric.category_name == "HR"
    hr_names = hr_rubric.get_criterion_names()
    assert "Relevance" in hr_names
    assert "Communication" in hr_names
    assert "Clarity" in hr_names
    assert "Completeness" in hr_names


# =====================================================================
# 2. STRONG ANSWER EVALUATION TEST
# =====================================================================

def test_evaluate_strong_technical_answer():
    """Test evaluation of a comprehensive, expert answer receives high score and positive evidence."""
    class StrongAnswerLLM(MockLLMService):
        def generate_structured(self, prompt, schema, system=None, temperature=None):
            return AnswerEvaluation(
                score=9.2,
                criteria_scores=[
                    EvaluationCriterion(
                        name="Correctness",
                        score=9.5,
                        feedback="Flawless explanation of GIL internals and mutex locking.",
                        evidence=[
                            EvaluationEvidence(
                                quote_or_reference="GIL prevents multiple native threads from executing Python bytecodes at once",
                                criterion_name="Correctness",
                                assessment="Accurately defines mutex mechanism",
                                is_positive=True,
                            )
                        ],
                    ),
                    EvaluationCriterion(
                        name="Concepts",
                        score=9.0,
                        feedback="Clear distinction between CPU-bound and I/O-bound tasks.",
                    ),
                    EvaluationCriterion(
                        name="Reasoning",
                        score=9.0,
                        feedback="Solid trade-off reasoning regarding multiprocessing IPC overhead.",
                    ),
                    EvaluationCriterion(
                        name="Implementation",
                        score=9.0,
                        feedback="Practical examples of ProcessPoolExecutor.",
                    ),
                ],
                evidence=[
                    EvaluationEvidence(
                        quote_or_reference="use multiprocessing.Pool for CPU heavy tasks",
                        criterion_name="Implementation",
                        assessment="Correct API selection for parallelization",
                        is_positive=True,
                    )
                ],
                strengths=[
                    "Deep conceptual understanding of CPython memory model.",
                    "Practical knowledge of process vs thread trade-offs.",
                ],
                weaknesses=[],
                feedback="Outstanding answer demonstrating senior-level mastery.",
                suggested_improvement="Could briefly mention free-threaded Python (PEP 703).",
            )

    config = InterviewConfig(
        candidate_name="Elena",
        role="Senior Python Engineer",
        interview_type=InterviewType.TECHNICAL,
    )
    question = Question(
        question_number=1,
        text="Explain how the GIL impacts multithreading in Python and when to use multiprocessing instead.",
        topic="Python",
        expected_concepts=["GIL mutex", "CPU vs I/O bound", "ProcessPoolExecutor overhead"],
    )
    strong_answer = (
        "The GIL prevents multiple native threads from executing Python bytecodes at once in CPython. "
        "For CPU-bound tasks, multithreading is limited to a single core, so we use multiprocessing.Pool "
        "or ProcessPoolExecutor to bypass the GIL across separate memory spaces."
    )

    evaluator = AnswerEvaluationService(llm_service=StrongAnswerLLM())
    evaluation = evaluator.evaluate_answer(config, question, strong_answer)

    assert evaluation.score >= 8.5
    assert len(evaluation.criteria_scores) == 4
    assert len(evaluation.evidence) >= 1
    assert evaluation.evidence[0].is_positive is True
    assert "pedagogical assessment" in evaluation.assessment_disclaimer.lower()


# =====================================================================
# 3. WEAK ANSWER EVALUATION TEST
# =====================================================================

def test_evaluate_weak_answer():
    """Test evaluation of a superficial or incorrect answer receives low score and identified weaknesses."""
    class WeakAnswerLLM(MockLLMService):
        def generate_structured(self, prompt, schema, system=None, temperature=None):
            return AnswerEvaluation(
                score=3.5,
                criteria_scores=[
                    EvaluationCriterion(name="Correctness", score=3.0, feedback="Incorrect assertions about threads."),
                    EvaluationCriterion(name="Concepts", score=4.0, feedback="Confused processes with async."),
                    EvaluationCriterion(name="Reasoning", score=3.0, feedback="No trade-off analysis."),
                    EvaluationCriterion(name="Implementation", score=4.0, feedback="Lacks concrete code/APIs."),
                ],
                evidence=[
                    EvaluationEvidence(
                        quote_or_reference="threads are always faster than processes",
                        criterion_name="Correctness",
                        assessment="Factually incorrect regarding CPU-bound work",
                        is_positive=False,
                    )
                ],
                strengths=["Attempted to answer."],
                weaknesses=[
                    "Incorrectly stated threads are always faster than processes for CPU tasks.",
                    "Did not mention GIL or memory isolation.",
                ],
                feedback="The answer shows misconceptions about Python concurrency.",
                suggested_improvement="Review how CPython GIL restricts CPU-bound multithreading.",
            )

    config = InterviewConfig(candidate_name="Bob", role="Python Dev", interview_type=InterviewType.TECHNICAL)
    question = Question(question_number=1, text="Explain Python concurrency and the GIL.", topic="Python")
    weak_answer = "Threads are always faster than processes because they are lightweight and have no limits."

    evaluator = AnswerEvaluationService(llm_service=WeakAnswerLLM())
    evaluation = evaluator.evaluate_answer(config, question, weak_answer)

    assert evaluation.score <= 4.5
    assert len(evaluation.weaknesses) >= 1
    assert evaluation.evidence[0].is_positive is False


# =====================================================================
# 4. INCOMPLETE ANSWER EVALUATION TEST
# =====================================================================

def test_evaluate_incomplete_answer():
    """Test evaluation of a partially answered question."""
    class IncompleteAnswerLLM(MockLLMService):
        def generate_structured(self, prompt, schema, system=None, temperature=None):
            return AnswerEvaluation(
                score=5.5,
                criteria_scores=[
                    EvaluationCriterion(name="Correctness", score=7.0, feedback="GIL definition is accurate."),
                    EvaluationCriterion(name="Concepts", score=6.0, feedback="Missed multiprocessing part."),
                    EvaluationCriterion(name="Reasoning", score=5.0, feedback="Partial reasoning."),
                    EvaluationCriterion(name="Implementation", score=4.0, feedback="Did not answer second half."),
                ],
                evidence=[
                    EvaluationEvidence(
                        quote_or_reference="GIL is a global lock in Python",
                        criterion_name="Correctness",
                        assessment="Correctly identified lock",
                        is_positive=True,
                    )
                ],
                strengths=["Accurately defined GIL."],
                weaknesses=["Completely skipped when to use multiprocessing."],
                feedback="Good start defining the GIL, but missed the second requirement of the prompt.",
                suggested_improvement="Always ensure every sub-question in the prompt is addressed.",
            )

    config = InterviewConfig(candidate_name="Carol", role="Dev", interview_type=InterviewType.TECHNICAL)
    question = Question(question_number=1, text="Define GIL and explain when to use multiprocessing.", topic="Python")
    incomplete_answer = "The GIL is a global lock in Python that prevents race conditions."

    evaluator = AnswerEvaluationService(llm_service=IncompleteAnswerLLM())
    evaluation = evaluator.evaluate_answer(config, question, incomplete_answer)

    assert 5.0 <= evaluation.score <= 6.5
    assert "multiprocessing" in evaluation.weaknesses[0].lower()


# =====================================================================
# 5. IRRELEVANT / REFUSAL ANSWER TESTS
# =====================================================================

def test_evaluate_refusal_answer():
    """Test explicit refusal answers (e.g. 'I don't know') get instant constructive feedback."""
    config = InterviewConfig(candidate_name="Dan", role="Dev", interview_type=InterviewType.TECHNICAL)
    question = Question(question_number=1, text="Explain distributed consensus in Raft.", topic="Distributed Systems")

    evaluator = AnswerEvaluationService(llm_service=MockLLMService())
    evaluation = evaluator.evaluate_answer(config, question, "I don't know.")

    assert evaluation.score <= 2.0
    assert len(evaluation.criteria_scores) >= 1
    assert "honesty" in evaluation.strengths[0].lower() or "boundary" in evaluation.strengths[0].lower()


def test_evaluate_empty_answer():
    """Test empty answer string produces standard 1.0 baseline evaluation."""
    config = InterviewConfig(candidate_name="Dan", role="Dev", interview_type=InterviewType.TECHNICAL)
    question = Question(question_number=1, text="Explain caching strategies.", topic="System Design")

    evaluator = AnswerEvaluationService(llm_service=MockLLMService())
    evaluation = evaluator.evaluate_answer(config, question, "   ")

    assert evaluation.score == 1.0
    assert "empty" in evaluation.feedback.lower() or "non-substantive" in evaluation.feedback.lower()


# =====================================================================
# 6. BEHAVIORAL STAR RUBRIC TEST
# =====================================================================

def test_evaluate_behavioral_star_answer():
    """Test that behavioral interview evaluates against Situation, Task, Action, Result, Ownership, Specificity."""
    class BehavioralLLM(MockLLMService):
        def generate_structured(self, prompt, schema, system=None, temperature=None):
            return AnswerEvaluation(
                score=8.8,
                criteria_scores=[
                    EvaluationCriterion(name="Situation", score=8.5, feedback="Clear outage context."),
                    EvaluationCriterion(name="Task", score=8.5, feedback="Clear lead responsibilities."),
                    EvaluationCriterion(name="Action", score=9.0, feedback="Initiated rollback and postmortem."),
                    EvaluationCriterion(name="Result", score=9.0, feedback="Reduced MTTR from 45m to 8m."),
                    EvaluationCriterion(name="Ownership", score=9.0, feedback="Took personal charge."),
                    EvaluationCriterion(name="Specificity", score=9.0, feedback="Concrete metric reference."),
                ],
                evidence=[
                    EvaluationEvidence(
                        quote_or_reference="reduced our MTTR from 45 minutes to 8 minutes",
                        criterion_name="Result",
                        assessment="Strong quantifiable metric provided",
                        is_positive=True,
                    )
                ],
                strengths=["Excellent STAR structure with quantifiable outcome."],
                weaknesses=[],
                feedback="Compelling behavioral example.",
                suggested_improvement="Highlight how you coached junior team members afterwards.",
            )

    config = InterviewConfig(
        candidate_name="Frank",
        role="Engineering Manager",
        interview_type=InterviewType.BEHAVIORAL,
    )
    question = Question(
        question_number=1,
        text="Tell me about a high-severity production outage you managed.",
        question_type=QuestionType.BEHAVIORAL,
        topic="Crisis Management",
    )
    star_answer = (
        "During Black Friday, our checkout API experienced a deadlock (Situation). As incident commander, my goal was "
        "to restore transaction flow within 15 minutes (Task). I initiated a canary rollback, enabled circuit breakers, "
        "and stabilized Redis (Action). As a result, we restored 100% uptime in 8 minutes and reduced our MTTR from 45 minutes to 8 minutes (Result)."
    )

    evaluator = AnswerEvaluationService(llm_service=BehavioralLLM())
    evaluation = evaluator.evaluate_answer(config, question, star_answer)

    criterion_names = [c.name for c in evaluation.criteria_scores]
    assert "Situation" in criterion_names
    assert "Action" in criterion_names
    assert "Result" in criterion_names
    assert evaluation.score >= 8.5


# =====================================================================
# 7. MALFORMED LLM RESPONSE & DETERMINISTIC FALLBACK TEST
# =====================================================================

def test_malformed_llm_fallback_evaluation():
    """Test that when LLM throws exceptions, deterministic fallback generates rubric-aligned evaluation."""
    class BrokenLLM(MockLLMService):
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("JSON Syntax Corrupt Stream")

    config = InterviewConfig(
        candidate_name="Grace",
        role="Backend Engineer",
        interview_type=InterviewType.HR,
    )
    question = Question(
        question_number=1,
        text="Why do you want to join our engineering team?",
        question_type=QuestionType.HR,
        topic="Career Goals",
    )
    answer = "I have admired your open source contributions and distributed systems architecture for years, and I want to contribute to high-scale infrastructure."

    evaluator = AnswerEvaluationService(llm_service=BrokenLLM(), max_retries=1)
    evaluation = evaluator.evaluate_answer(config, question, answer)

    assert isinstance(evaluation, AnswerEvaluation)
    assert evaluation.score >= 4.0
    assert len(evaluation.criteria_scores) >= 1
    assert len(evaluation.strengths) >= 1
    assert "pedagogical assessment" in evaluation.assessment_disclaimer.lower()


# =====================================================================
# 8. DATABASE PERSISTENCE OF PHASE 4 EVALUATION
# =====================================================================

def test_database_persistence_of_rich_evaluation(db_session):
    """Test persisting and recovering full AnswerEvaluation with criteria_scores and evidence."""
    config = InterviewConfig(
        candidate_name="Alan Turing",
        role="Lead Cryptographer",
        interview_type=InterviewType.TECHNICAL,
    )

    candidate = InterviewRepository.get_or_create_candidate(db_session, config.candidate_name)
    interview = InterviewRepository.create_interview(db_session, candidate.id, config)

    question = Question(
        question_number=1,
        text="Explain public-key cryptography and RSA key generation.",
        topic="Cryptography",
    )
    q_model = InterviewRepository.save_question(db_session, interview.id, question)

    answer = CandidateAnswer(
        question_id=q_model.id,
        question_number=1,
        answer_text="RSA uses two large primes p and q, calculates modulus n = p*q, and Euler totient phi(n).",
    )

    evaluation = AnswerEvaluation(
        score=9.0,
        criteria_scores=[
            EvaluationCriterion(
                name="Correctness",
                score=9.5,
                weight=1.5,
                feedback="Precise mathematical definition of RSA.",
                evidence=[
                    EvaluationEvidence(
                        quote_or_reference="RSA uses two large primes p and q",
                        criterion_name="Correctness",
                        assessment="Correct key foundation",
                        is_positive=True,
                    )
                ],
            ),
            EvaluationCriterion(name="Concepts", score=9.0, weight=1.2, feedback="Accurate Euler totient grasp."),
        ],
        evidence=[
            EvaluationEvidence(
                quote_or_reference="calculates modulus n = p*q",
                criterion_name="Correctness",
                assessment="Accurate modulus formulation",
                is_positive=True,
            )
        ],
        strengths=["Exact algebraic formulation."],
        weaknesses=[],
        feedback="Masterful explanation of asymmetric cryptography.",
        suggested_improvement="Mention prime generation algorithms like Miller-Rabin.",
    )

    # 1. Save Answer and Evaluation
    ans_model, eval_model = InterviewRepository.save_answer_and_evaluation(
        session=db_session,
        question_id=q_model.id,
        answer=answer,
        evaluation=evaluation,
    )

    assert eval_model.id is not None
    assert eval_model.criteria_scores_json is not None
    assert eval_model.evidence_json is not None
    assert "RSA uses two large primes" in eval_model.evidence_json

    # 2. Finalize Interview
    summary = EvaluationSummary(
        overall_score=9.0,
        criteria_averages={"Correctness": 9.5, "Concepts": 9.0},
        strengths_summary=["Deep mathematical foundation"],
        weaknesses_summary=[],
        overall_feedback="Outstanding cryptography performance.",
    )
    InterviewRepository.finalize_interview(db_session, interview.id, summary)

    # 3. Load full result and verify recovery
    result = InterviewRepository.get_interview_result(db_session, interview.id)
    assert result is not None
    assert len(result.pairs) == 1

    recovered_eval = result.pairs[0].evaluation
    assert recovered_eval.score == 9.0
    assert len(recovered_eval.criteria_scores) == 2
    assert recovered_eval.criteria_scores[0].name == "Correctness"
    assert len(recovered_eval.evidence) >= 1
    evidence_quotes = [e.quote_or_reference for e in recovered_eval.evidence]
    assert any("RSA uses two large primes" in q for q in evidence_quotes)
