"""
Centralized prompt templates for Question Generation, Answer Evaluation, and Session Summary.
Phase 2: Incorporates Topics, Personas, Multilingual, and Adaptive Difficulty directives.
"""

from typing import List, Optional
from app.schemas.interview import InterviewConfig, Question, QuestionEvaluationPair, Difficulty

# System Prompts
QUESTION_GENERATOR_SYSTEM_PROMPT = """You are Abhyas, an expert hiring manager and AI interviewer conducting a personalized, highly effective mock interview.
Your responsibility is to formulate clear, engaging, and role-appropriate interview questions.

Rules:
1. Align questions closely with the candidate's target role, experience level, and selected topics.
2. Maintain the specified Interviewer Persona and tone throughout the session.
3. If a specific language is specified, write the question in that language.
4. Ensure questions test practical knowledge, architectural reasoning, or structured behavioral methods (STAR).
5. Provide expected key concepts/points for ideal evaluation.
6. Do NOT repeat or overlap with previously asked questions in the session.
7. You MUST return your response as a valid JSON object matching the requested schema.
"""

ANSWER_EVALUATOR_SYSTEM_PROMPT = """You are Abhyas, an expert interview evaluator and career mentor conducting structured, evidence-based assessment.
Your responsibility is to evaluate the candidate's answer with constructive, specific, and actionable feedback.

Rules:
1. Evaluate candidate answers against the provided type-specific rubric criteria (e.g. Technical, Behavioral STAR, HR).
2. For each criterion:
   - Provide a score from 0.0 to 10.0 based on demonstrated mastery.
   - Extract direct quotes or textual references from the candidate's answer as GROUNDING EVIDENCE.
   - State whether the evidence demonstrates strength (is_positive: true) or an omission/flaw (is_positive: false).
3. Identify 1 to 3 concrete candidate strengths and 1 to 3 specific areas of omission or weakness.
4. Provide constructive feedback matching the requested Interviewer Persona tone.
5. Provide actionable, specific suggestions on what would make this an exceptional response.
6. Calculate an overall score from 0.0 to 10.0 reflecting the weighted criteria performance.
7. Include the standard assessment disclaimer noting that AI evaluations are subjective pedagogical coaching feedback.
8. If the interview language is non-English, provide the feedback and commentary in that language.
9. You MUST return your response as a valid JSON object matching the requested schema.
"""

SUMMARY_GENERATOR_SYSTEM_PROMPT = """You are Abhyas, a senior hiring panel lead compiling a holistic interview assessment summary.
Your task is to synthesize the candidate's overall performance across all interview questions.

Rules:
1. Aggregate the candidate's performance across all evaluated criteria and questions.
2. Compute an overall session score (0.0 to 10.0) and criteria averages.
3. Highlight top observed strengths and notable skill gaps with constructive narrative feedback.
4. List key actionable recommendations and topics for the candidate to study or practice.
5. Emphasize that this summary is a coaching assessment designed for practice and growth.
6. You MUST return your response as a valid JSON object matching the requested schema.
"""


def build_question_prompt(
    config: InterviewConfig,
    question_number: int,
    previous_questions: List[Question],
    effective_difficulty: Optional[Difficulty] = None,
    strategy: Optional["StrategyPlan"] = None,
) -> str:
    """Build user prompt for generating the next interview question adhering to the strategy plan and adaptive decision."""
    prev_q_texts = (
        "\n".join([f"- Q{q.question_number} [{q.question_type.value if hasattr(q, 'question_type') else 'Technical'} | {q.topic}]: {q.text or q.question_text}" for q in previous_questions])
        if previous_questions
        else "None (This is the first question)."
    )

    diff = effective_difficulty or (strategy.difficulty if strategy else (config.difficulty if config.difficulty != Difficulty.ADAPTIVE else Difficulty.MEDIUM))
    target_topic = strategy.target_topic if strategy else (config.topics[0] if config.topics else config.role or "Software Engineering")
    q_type_str = strategy.question_type.value if strategy else "Technical"
    objective_str = strategy.objective if strategy else f"Assess candidate competency on {target_topic}."

    # Adaptive Directive Section
    decision_section = ""
    if strategy and strategy.decision:
        dec = strategy.decision
        decision_section = f"""
ADAPTIVE DECISION DIRECTIVE: [{dec.action.value}]
Decision Justification: {dec.reason}
Assessment Focus: {dec.objective}
"""
        if dec.context_reference:
            decision_section += f"Previous Response Context / Target Gap: \"{dec.context_reference}\"\n"

    return f"""Target Role: {config.role}
Experience Level: {config.experience_level.value}
Interview Category: {config.interview_type.value}
Target Topic: {target_topic}
Question Type: {q_type_str}
Strategic Objective: {objective_str}
Difficulty Level: {diff.value}
Interviewer Persona: {config.interviewer_persona.value}
Interview Language: {config.language}
Question Number: {question_number} of {config.num_questions}
{decision_section}
Previously asked questions in this session:
{prev_q_texts}

STRICT QUALITY RULES:
1. The question MUST specifically assess '{target_topic}'. Do not divert into unrelated subjects.
2. The style of the question MUST be '{q_type_str}'.
3. Do NOT repeat or paraphrase any previously asked question.
4. Pitch the complexity precisely to the '{diff.value}' difficulty tier for a '{config.experience_level.value}' candidate.
5. If an Adaptive Directive is provided (e.g. FOLLOW_UP, DEEP_DIVE, CLARIFY, REPHRASE), formulate the question to directly fulfill that directive.

Expected JSON format:
{{
  "question_number": {question_number},
  "text": "The exact interview question text",
  "category": "{config.interview_type.value}",
  "topic": "{target_topic}",
  "difficulty": "{diff.value}",
  "question_type": "{q_type_str}",
  "expected_concepts": [
    "Key concept or technical element 1",
    "Key concept or technical element 2",
    "Key concept or technical element 3"
  ],
  "evaluation_criteria": [
    "Evaluation rubric point 1",
    "Evaluation rubric point 2"
  ],
  "follow_up_possible": true
}}
"""



def build_evaluation_prompt(
    config: InterviewConfig,
    question: Question,
    candidate_answer: str,
    rubric_instructions: Optional[str] = None,
) -> str:
    """Build user prompt for evaluating a candidate's answer with type-specific rubric and evidence extraction."""
    expected_pts = question.expected_concepts or question.expected_points or []
    expected_pts_str = (
        "\n".join([f"- {pt}" for pt in expected_pts])
        if expected_pts
        else "General industry best practices, clear reasoning, and pragmatic implementation."
    )

    rubric_section = rubric_instructions or (
        "Evaluation Criteria:\n"
        "- Correctness: Factual and algorithmic accuracy\n"
        "- Concepts: Core foundational principles\n"
        "- Reasoning: Logical justification and trade-offs\n"
        "- Implementation: Code/system practical details"
    )

    q_type_val = question.question_type.value if hasattr(question.question_type, "value") else str(question.question_type or "Technical")

    return f"""Interview Context:
- Target Role: {config.role}
- Experience Level: {config.experience_level.value}
- Question Category: {question.category}
- Question Topic: {question.topic}
- Question Type: {q_type_val}
- Difficulty: {question.difficulty.value if hasattr(question.difficulty, 'value') else str(question.difficulty)}
- Interviewer Persona: {config.interviewer_persona.value}
- Language: {config.language}

Target Interview Question:
\"\"\"{question.text or question.question_text}\"\"\"

Expected Key Concepts / Rubric Benchmark:
{expected_pts_str}

Candidate's Submitted Answer:
\"\"\"{candidate_answer}\"\"\"

{rubric_section}

STRICT EVALUATION INSTRUCTIONS:
1. Score each criterion in the rubric from 0.0 to 10.0 based on the candidate's actual text.
2. Under each criterion or in the evidence array, quote specific phrases from the candidate's answer as grounding evidence.
3. If an answer is weak or incomplete, specify exactly what was omitted in weaknesses.
4. Calculate an overall weighted score between 0.0 and 10.0.
5. Provide actionable feedback aligning with the {config.interviewer_persona.value} persona.

Expected JSON format:
{{
  "score": 7.5,
  "criteria_scores": [
    {{
      "name": "Criterion Name",
      "score": 8.0,
      "weight": 1.2,
      "feedback": "Specific assessment of this criterion",
      "evidence": [
        {{
          "quote_or_reference": "exact excerpt or phrase from answer",
          "criterion_name": "Criterion Name",
          "assessment": "Demonstrates clear understanding of X",
          "is_positive": true
        }}
      ]
    }}
  ],
  "evidence": [
    {{
      "quote_or_reference": "exact excerpt or phrase from answer",
      "criterion_name": "Criterion Name",
      "assessment": "Shows understanding of Y",
      "is_positive": true
    }}
  ],
  "strengths": [
    "Highlighted key concept accurately",
    "Clear structure in the answer"
  ],
  "weaknesses": [
    "Did not address edge cases or limitations",
    "Could provide concrete real-world examples"
  ],
  "feedback": "A concise, constructive evaluation paragraph explaining the score rationale.",
  "suggested_improvement": "Concrete advice on what would elevate this to a top-tier answer.",
  "assessment_disclaimer": "This evaluation is an AI-assisted pedagogical assessment designed for coaching and practice feedback. It does not represent an absolute or objective measurement."
}}
"""


def build_summary_prompt(
    config: InterviewConfig,
    pairs: List[QuestionEvaluationPair],
) -> str:
    """Build prompt for generating overall interview summary."""
    transcript_blocks = []
    for idx, pair in enumerate(pairs, 1):
        q_type_str = pair.question.question_type.value if hasattr(pair.question.question_type, 'value') else "Technical"
        transcript_blocks.append(
            f"--- Question {idx} [{q_type_str} | {pair.question.topic}] ---\n"
            f"Question: {pair.question.text or pair.question.question_text}\n"
            f"Answer: {pair.answer.answer_text}\n"
            f"Score: {pair.evaluation.score}/10\n"
            f"Strengths: {', '.join(pair.evaluation.strengths)}\n"
            f"Weaknesses: {', '.join(pair.evaluation.weaknesses)}\n"
        )
    transcript_text = "\n\n".join(transcript_blocks)

    return f"""Interview Session Overview:
- Candidate Name: {config.candidate_name}
- Target Role: {config.role}
- Experience Level: {config.experience_level.value}
- Interview Type: {config.interview_type.value}
- Focus Topics: {', '.join(config.topics) if config.topics else 'General'}
- Interviewer Persona: {config.interviewer_persona.value}
- Language: {config.language}
- Total Questions Answered: {len(pairs)}

Session Transcript and Individual Evaluations:
{transcript_text}

Generate a comprehensive final interview assessment.

Expected JSON format:
{{
  "overall_score": 7.5,
  "criteria_averages": {{
    "Correctness": 8.0,
    "Concepts": 7.5,
    "Reasoning": 7.0
  }},
  "strengths_summary": [
    "Consistent demonstration of foundational concepts",
    "Clear communication and structure"
  ],
  "weaknesses_summary": [
    "Gap in advanced concurrency details",
    "Could explore deeper architectural trade-offs"
  ],
  "overall_feedback": "A holistic 2-3 paragraph assessment of candidate performance, readiness, and communication style.",
  "areas_to_improve": [
    "Review concurrency primitives and memory synchronization",
    "Practice structured STAR communication framework"
  ],
  "disclaimer": "This summary is an AI-assisted pedagogical assessment designed for coaching and practice feedback."
}}
"""
