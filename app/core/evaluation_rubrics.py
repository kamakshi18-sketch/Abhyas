"""
Evaluation Rubrics Service.
Defines specialized evaluation criteria, descriptions, and weightings
per Interview Type and Question Type.
"""

from typing import List, Dict
from dataclasses import dataclass
from app.schemas.interview import InterviewType, QuestionType


@dataclass(frozen=True)
class RubricCriterionDefinition:
    """Specification of a rubric criterion."""
    name: str
    description: str
    weight: float
    guiding_question: str


@dataclass(frozen=True)
class EvaluationRubric:
    """Complete rubric for an interview or question type."""
    category_name: str
    criteria: List[RubricCriterionDefinition]
    guidelines: str

    def get_criterion_names(self) -> List[str]:
        return [c.name for c in self.criteria]


# =====================================================================
# RUBRIC DEFINITIONS PER INTERVIEW / QUESTION TYPE
# =====================================================================

RUBRIC_TECHNICAL = EvaluationRubric(
    category_name="Technical",
    criteria=[
        RubricCriterionDefinition(
            name="Correctness",
            description="Factual, syntactic, and algorithmic accuracy of the technical assertions.",
            weight=1.5,
            guiding_question="Are the technical facts, statements, and code logic accurate and error-free?",
        ),
        RubricCriterionDefinition(
            name="Concepts",
            description="Understanding of core domain concepts, internals, execution models, and data structures.",
            weight=1.2,
            guiding_question="Did the candidate demonstrate solid grasp of fundamental architectural principles?",
        ),
        RubricCriterionDefinition(
            name="Reasoning",
            description="Logical justification of design choices, computational complexity, trade-offs, and scaling limits.",
            weight=1.2,
            guiding_question="Did the candidate explain 'why' a solution works and consider time/space trade-offs?",
        ),
        RubricCriterionDefinition(
            name="Implementation",
            description="Pragmatic consideration of implementation details, edge cases, error handling, and production readiness.",
            weight=1.1,
            guiding_question="Does the answer detail concrete implementation steps, APIs, or defensive programming patterns?",
        ),
    ],
    guidelines="Evaluate technical rigor, precision in terminology, handling of edge cases, and architectural reasoning.",
)

RUBRIC_BEHAVIORAL = EvaluationRubric(
    category_name="Behavioral",
    criteria=[
        RubricCriterionDefinition(
            name="Situation",
            description="Clear context setting outlining the background, environment, stakes, and constraints.",
            weight=1.0,
            guiding_question="Was the background circumstance and initial problem clearly articulated?",
        ),
        RubricCriterionDefinition(
            name="Task",
            description="Definition of the candidate's specific objective, challenge, or mandate.",
            weight=1.0,
            guiding_question="What was the candidate's exact role and expected deliverable in the situation?",
        ),
        RubricCriterionDefinition(
            name="Action",
            description="Detailed personal actions, initiative, technical/interpersonal decisions, and methodologies executed.",
            weight=1.5,
            guiding_question="What concrete actions did the candidate take rather than relying solely on team effort?",
        ),
        RubricCriterionDefinition(
            name="Result",
            description="Measurable business or technical outcome, qualitative impact, retrospective learnings, and metrics.",
            weight=1.3,
            guiding_question="What were the quantifiable or tangible outcomes, and what lessons were learned?",
        ),
        RubricCriterionDefinition(
            name="Ownership",
            description="Demonstration of proactive accountability, leadership, resilience, and personal responsibility.",
            weight=1.1,
            guiding_question="Did the candidate take proactive responsibility for challenges and resolutions?",
        ),
        RubricCriterionDefinition(
            name="Specificity",
            description="Avoidance of vague generalities; presence of concrete details, timeline references, and explicit examples.",
            weight=1.1,
            guiding_question="Was the story grounded in specific, believable real-world experiences?",
        ),
    ],
    guidelines="Evaluate using the STAR framework. Prioritize first-person ownership ('I' vs 'we') and quantifiable impact.",
)

RUBRIC_HR = EvaluationRubric(
    category_name="HR",
    criteria=[
        RubricCriterionDefinition(
            name="Relevance",
            description="Direct alignment with the question prompt, career trajectory, and organizational expectations.",
            weight=1.2,
            guiding_question="Did the response directly address the question without wandering off-topic?",
        ),
        RubricCriterionDefinition(
            name="Communication",
            description="Tone, empathy, professional articulation, pacing, and executive presentation.",
            weight=1.3,
            guiding_question="Was the delivery professional, respectful, structured, and pleasant to follow?",
        ),
        RubricCriterionDefinition(
            name="Clarity",
            description="Structure, conciseness, coherence, and absence of confusing jargon or ambiguous phrasing.",
            weight=1.2,
            guiding_question="Was the message easy to understand and well organized?",
        ),
        RubricCriterionDefinition(
            name="Completeness",
            description="Thorough coverage of all aspects of the query, including motivations and future vision.",
            weight=1.1,
            guiding_question="Did the candidate address every aspect of the question thoroughly?",
        ),
    ],
    guidelines="Assess cultural addition, professional enthusiasm, career alignment, self-awareness, and clear communication.",
)

RUBRIC_CONCEPTUAL = EvaluationRubric(
    category_name="Conceptual",
    criteria=[
        RubricCriterionDefinition(
            name="Conceptual Understanding",
            description="Grasp of theoretical foundations, abstractions, mental models, and terminology.",
            weight=1.4,
            guiding_question="Does the candidate demonstrate deep foundational knowledge of the concept?",
        ),
        RubricCriterionDefinition(
            name="Technical Accuracy",
            description="Precision in definitions, execution mechanics, and state changes.",
            weight=1.4,
            guiding_question="Are the explanations factually exact without misconceptions?",
        ),
        RubricCriterionDefinition(
            name="Clarity",
            description="Ability to explain intricate concepts in a clean, intuitive, and accessible manner.",
            weight=1.1,
            guiding_question="Is the explanation structured and straightforward to comprehend?",
        ),
        RubricCriterionDefinition(
            name="Depth",
            description="Exploration of subtle nuances, internal lifecycle, and performance implications.",
            weight=1.1,
            guiding_question="Does the explanation go beyond superficial definitions into internal workings?",
        ),
    ],
    guidelines="Focus on pedagogical clarity, conceptual fidelity, and deep comprehension of principles.",
)

RUBRIC_PROBLEM_SOLVING = EvaluationRubric(
    category_name="Problem Solving",
    criteria=[
        RubricCriterionDefinition(
            name="Problem Decomposition",
            description="Breaking complex problems down into modular, manageable sub-problems.",
            weight=1.2,
            guiding_question="Did the candidate dissect the problem systematically before jumping into solutions?",
        ),
        RubricCriterionDefinition(
            name="Algorithm & Logic Correctness",
            description="Soundness of the algorithmic approach, data structure choices, and logic flow.",
            weight=1.5,
            guiding_question="Is the proposed solution logically sound and optimal?",
        ),
        RubricCriterionDefinition(
            name="Edge Cases",
            description="Identification of boundary conditions, concurrency hazards, scale ceilings, and failure modes.",
            weight=1.1,
            guiding_question="Were corner cases, null inputs, and unexpected failure modes addressed?",
        ),
        RubricCriterionDefinition(
            name="Trade-Offs",
            description="Evaluating time vs space complexity, latency vs throughput, and consistency vs availability.",
            weight=1.2,
            guiding_question="Did the candidate explicitly evaluate the compromises of their design?",
        ),
    ],
    guidelines="Reward structured analytical thinking, systematic debugging, and conscious trade-off evaluation.",
)

RUBRIC_SITUATIONAL = EvaluationRubric(
    category_name="Situational",
    criteria=[
        RubricCriterionDefinition(
            name="Scenario Comprehension",
            description="Accurate diagnosis of the presented scenario, constraints, and stakeholder stakes.",
            weight=1.1,
            guiding_question="Did the candidate understand the core dilemma and urgency?",
        ),
        RubricCriterionDefinition(
            name="Pragmatism",
            description="Practical, achievable solutions balancing short-term stability with long-term quality.",
            weight=1.3,
            guiding_question="Is the proposed course of action realistic and grounded in real-world constraints?",
        ),
        RubricCriterionDefinition(
            name="Decision Reasoning",
            description="Structured decision-making criteria and risk management under uncertainty.",
            weight=1.3,
            guiding_question="Was the rationale for the chosen path articulated logically?",
        ),
        RubricCriterionDefinition(
            name="Stakeholder Communication",
            description="Proactive communication with team members, leadership, and cross-functional partners.",
            weight=1.1,
            guiding_question="Did the candidate detail how they would align with stakeholders?",
        ),
    ],
    guidelines="Evaluate crisis management, engineering pragmatism, and cross-functional alignment.",
)

RUBRIC_PROJECT = EvaluationRubric(
    category_name="Project",
    criteria=[
        RubricCriterionDefinition(
            name="Scope & Ownership",
            description="Clarity of personal contribution, project architecture, and system boundaries.",
            weight=1.2,
            guiding_question="Was the candidate's personal impact and technical ownership clearly distinct?",
        ),
        RubricCriterionDefinition(
            name="Architectural Reasoning",
            description="Justification of technology stack, frameworks, scaling mechanisms, and protocols.",
            weight=1.4,
            guiding_question="Why were specific technologies and patterns chosen over alternatives?",
        ),
        RubricCriterionDefinition(
            name="Technical Implementation",
            description="Execution rigor, maintainability, testing strategies, and monitoring/observability.",
            weight=1.2,
            guiding_question="Were implementation, deployment, and testing workflows sound?",
        ),
        RubricCriterionDefinition(
            name="Business & Performance Impact",
            description="Measurable results, latency reduction, reliability gains, or business velocity improvements.",
            weight=1.2,
            guiding_question="What concrete value or efficiency gain was achieved?",
        ),
    ],
    guidelines="Focus on authentic technical ownership, architectural maturity, and deliverable impact.",
)


class EvaluationRubricService:
    """Resolves and formats appropriate evaluation rubrics for interview questions."""

    _RUBRIC_REGISTRY: Dict[str, EvaluationRubric] = {
        "technical": RUBRIC_TECHNICAL,
        "behavioral": RUBRIC_BEHAVIORAL,
        "hr": RUBRIC_HR,
        "conceptual": RUBRIC_CONCEPTUAL,
        "problem solving": RUBRIC_PROBLEM_SOLVING,
        "problem_solving": RUBRIC_PROBLEM_SOLVING,
        "situational": RUBRIC_SITUATIONAL,
        "project": RUBRIC_PROJECT,
        "role specific": RUBRIC_TECHNICAL,
        "role_specific": RUBRIC_TECHNICAL,
    }

    @classmethod
    def get_rubric(
        cls,
        interview_type: InterviewType,
        question_type: QuestionType = QuestionType.TECHNICAL,
    ) -> EvaluationRubric:
        """
        Resolve the most appropriate evaluation rubric.
        Prioritizes question_type, falling back to interview_type or Technical.
        """
        # 1. Match on QuestionType
        qt_key = question_type.value.lower()
        if qt_key in cls._RUBRIC_REGISTRY:
            return cls._RUBRIC_REGISTRY[qt_key]

        # 2. Match on InterviewType
        it_key = interview_type.value.lower()
        if it_key in cls._RUBRIC_REGISTRY:
            return cls._RUBRIC_REGISTRY[it_key]

        # 3. Default fallback
        return RUBRIC_TECHNICAL

    @classmethod
    def format_rubric_prompt_instructions(cls, rubric: EvaluationRubric) -> str:
        """Generate formatted prompt text detailing criteria and guidelines for the LLM."""
        lines = [
            f"Evaluation Rubric [{rubric.category_name}]:",
            f"General Directive: {rubric.guidelines}",
            "",
            "Specific Evaluation Criteria (Score each on a 0.0 - 10.0 scale with evidence):",
        ]
        for c in rubric.criteria:
            lines.append(f"- **{c.name}** (Weight: {c.weight}): {c.description} (Guideline: {c.guiding_question})")
        return "\n".join(lines)
