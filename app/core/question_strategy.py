"""
Question Strategy Engine.
Determines interview pacing, sequence blueprint, topic coverage,
question types, and assessment objectives. Decouples pedagogical strategy
from LLM creative phrasing.
"""

import logging
from typing import List, Dict, Any, Optional
from app.schemas.interview import (
    InterviewConfig,
    InterviewType,
    ExperienceLevel,
    Difficulty,
    QuestionType,
    StrategyPlan,
    Question,
)

logger = logging.getLogger(__name__)


class QuestionStrategyService:
    """Service that precomputes and governs strategic objectives for interview questions."""

    # Default question type distribution recipes by InterviewType
    _TYPE_DISTRIBUTIONS: Dict[InterviewType, List[QuestionType]] = {
        InterviewType.TECHNICAL: [
            QuestionType.CONCEPTUAL,
            QuestionType.TECHNICAL,
            QuestionType.PROBLEM_SOLVING,
            QuestionType.ROLE_SPECIFIC,
            QuestionType.TECHNICAL,
        ],
        InterviewType.BEHAVIORAL: [
            QuestionType.BEHAVIORAL,
            QuestionType.SITUATIONAL,
            QuestionType.PROJECT,
            QuestionType.BEHAVIORAL,
            QuestionType.SITUATIONAL,
        ],
        InterviewType.HR: [
            QuestionType.HR,
            QuestionType.BEHAVIORAL,
            QuestionType.SITUATIONAL,
            QuestionType.HR,
            QuestionType.BEHAVIORAL,
        ],
        InterviewType.MIXED: [
            QuestionType.CONCEPTUAL,
            QuestionType.TECHNICAL,
            QuestionType.BEHAVIORAL,
            QuestionType.PROBLEM_SOLVING,
            QuestionType.SITUATIONAL,
        ],
        InterviewType.ROLE_SPECIFIC: [
            QuestionType.ROLE_SPECIFIC,
            QuestionType.TECHNICAL,
            QuestionType.PROJECT,
            QuestionType.PROBLEM_SOLVING,
            QuestionType.ROLE_SPECIFIC,
        ],
        InterviewType.PROJECT_BASED: [
            QuestionType.PROJECT,
            QuestionType.TECHNICAL,
            QuestionType.PROBLEM_SOLVING,
            QuestionType.SITUATIONAL,
            QuestionType.PROJECT,
        ],
    }

    # Objective templates based on QuestionType and ExperienceLevel
    _OBJECTIVE_MAP: Dict[QuestionType, Dict[ExperienceLevel, str]] = {
        QuestionType.CONCEPTUAL: {
            ExperienceLevel.FRESHER: "Evaluate core foundational terminology, syntax understanding, and basic theoretical knowledge.",
            ExperienceLevel.ZERO_TO_TWO: "Assess practical understanding of core principles, runtime behaviors, and basic standard idioms.",
            ExperienceLevel.TWO_TO_FIVE: "Examine deep internal mechanisms, performance trade-offs, and memory/concurrency models.",
            ExperienceLevel.FIVE_PLUS: "Scrutinize advanced architectural fundamentals, system limits, and comparative paradigm trade-offs.",
        },
        QuestionType.TECHNICAL: {
            ExperienceLevel.FRESHER: "Assess ability to explain fundamental algorithms, data structures, and implementation logic.",
            ExperienceLevel.ZERO_TO_TWO: "Evaluate practical API usage, framework best practices, and clean code construction.",
            ExperienceLevel.TWO_TO_FIVE: "Test design patterns, distributed caching, database indexing, and API security optimization.",
            ExperienceLevel.FIVE_PLUS: "Evaluate resilient distributed system design, high availability, database partitioning, and throughput bottlenecks.",
        },
        QuestionType.PROBLEM_SOLVING: {
            ExperienceLevel.FRESHER: "Assess structured thinking on array/string manipulation, edge case handling, and step-by-step logic.",
            ExperienceLevel.ZERO_TO_TWO: "Evaluate troubleshooting approach to runtime exceptions, data validation bugs, and integration errors.",
            ExperienceLevel.TWO_TO_FIVE: "Test root-cause analysis of performance degradation, race conditions, and deadlocks in production.",
            ExperienceLevel.FIVE_PLUS: "Evaluate crisis triage of cascade system failures, network partitions, and catastrophic data corruption.",
        },
        QuestionType.ROLE_SPECIFIC: {
            ExperienceLevel.FRESHER: "Evaluate readiness for day-to-day junior tasks within the specified role.",
            ExperienceLevel.ZERO_TO_TWO: "Assess competence with modern toolchains, libraries, and workflows specific to the target role.",
            ExperienceLevel.TWO_TO_FIVE: "Evaluate production ownership, CI/CD pipeline optimization, and cross-service domain modeling.",
            ExperienceLevel.FIVE_PLUS: "Examine domain leadership, architectural standards, technical roadmapping, and scalability strategy for the role.",
        },
        QuestionType.PROJECT: {
            ExperienceLevel.FRESHER: "Assess academic or personal project architecture, key learnings, and technologies used.",
            ExperienceLevel.ZERO_TO_TWO: "Evaluate candidate's specific code contributions, bug fixes, and feature releases on past teams.",
            ExperienceLevel.TWO_TO_FIVE: "Scrutinize architectural decisions made, tech stack selection rationale, and refactoring trade-offs.",
            ExperienceLevel.FIVE_PLUS: "Evaluate end-to-end multi-team system delivery, business impact, tech debt management, and post-mortems.",
        },
        QuestionType.BEHAVIORAL: {
            ExperienceLevel.FRESHER: "Assess enthusiasm for learning, receiving feedback, and adapting to new team environments.",
            ExperienceLevel.ZERO_TO_TWO: "Evaluate time management, task estimation, asking for help, and team communication under deadlines.",
            ExperienceLevel.TWO_TO_FIVE: "Assess handling technical disagreements, managing scope changes, and collaborating across disciplines.",
            ExperienceLevel.FIVE_PLUS: "Evaluate leadership in ambiguous situations, driving engineering consensus, mentorship, and culture building.",
        },
        QuestionType.SITUATIONAL: {
            ExperienceLevel.FRESHER: "Assess response when facing an unfamiliar error or ambiguous task assignment.",
            ExperienceLevel.ZERO_TO_TWO: "Evaluate handling a tight production deadline or sudden requirement modification from stakeholders.",
            ExperienceLevel.TWO_TO_FIVE: "Assess response to a severe production outage or conflicting stakeholder technical demands.",
            ExperienceLevel.FIVE_PLUS: "Assess strategic crisis management, executive trade-off negotiation, and organizational pivot execution.",
        },
        QuestionType.HR: {
            ExperienceLevel.FRESHER: "Evaluate career motivations, learning aspirations, and cultural alignment.",
            ExperienceLevel.ZERO_TO_TWO: "Assess teamwork preferences, professional growth goals, and company alignment.",
            ExperienceLevel.TWO_TO_FIVE: "Evaluate career trajectory, ownership mindset, and long-term retention potential.",
            ExperienceLevel.FIVE_PLUS: "Assess executive presence, organizational vision, leadership philosophy, and alignment with company mission.",
        },
    }

    @classmethod
    def plan_interview_flow(cls, config: InterviewConfig) -> List[StrategyPlan]:
        """
        Generate a complete strategic roadmap for all questions in the interview sequence.
        Distributes selected topics and question types evenly across the question budget.
        """
        num_questions = config.num_questions
        topics = config.topics if config.topics else ["General Computer Science"]
        interview_type = config.interview_type
        experience = config.experience_level
        difficulty = config.difficulty

        # If difficulty is ADAPTIVE in config, baseline strategy starts at MEDIUM
        effective_diff = Difficulty.MEDIUM if difficulty == Difficulty.ADAPTIVE else difficulty

        # Base pattern recipe
        recipe = cls._TYPE_DISTRIBUTIONS.get(interview_type, cls._TYPE_DISTRIBUTIONS[InterviewType.TECHNICAL])
        
        plan: List[StrategyPlan] = []
        for i in range(1, num_questions + 1):
            # Select QuestionType in cyclic pattern from recipe
            q_type = recipe[(i - 1) % len(recipe)]
            
            # Select topic in cyclic pattern from user-selected topics
            topic = topics[(i - 1) % len(topics)]
            
            # Category name
            category = f"{interview_type.value} - {topic}" if topic != "General" else interview_type.value

            # Objective lookup
            type_map = cls._OBJECTIVE_MAP.get(q_type, cls._OBJECTIVE_MAP[QuestionType.TECHNICAL])
            objective = type_map.get(experience, "Assess candidate competency and depth on assigned topic.")

            plan.append(
                StrategyPlan(
                    question_number=i,
                    question_type=q_type,
                    target_topic=topic,
                    category=category,
                    difficulty=effective_diff,
                    objective=objective,
                )
            )

        logger.info(f"Planned interview strategy for {num_questions} questions across topics: {topics}")
        return plan

    @classmethod
    def get_strategy_for_step(
        cls,
        config: InterviewConfig,
        question_number: int,
        asked_questions: Optional[List[Question]] = None,
    ) -> StrategyPlan:
        """
        Retrieve or dynamically generate the StrategyPlan for a specific question index.
        """
        full_plan = cls.plan_interview_flow(config)
        if 1 <= question_number <= len(full_plan):
            return full_plan[question_number - 1]

        # Fallback for extra/extended questions
        topics = config.topics if config.topics else ["General"]
        topic = topics[(question_number - 1) % len(topics)]
        return StrategyPlan(
            question_number=question_number,
            question_type=QuestionType.TECHNICAL,
            target_topic=topic,
            category=f"Technical - {topic}",
            difficulty=config.difficulty if config.difficulty != Difficulty.ADAPTIVE else Difficulty.MEDIUM,
            objective=f"Deep-dive assessment on {topic} for {config.role or 'Candidate'}.",
        )
