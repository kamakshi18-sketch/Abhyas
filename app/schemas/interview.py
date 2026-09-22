"""
Pydantic schemas for the AI Interviewer domain models.
Phase 2: Advanced Interview Configuration.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class InterviewType(str, Enum):
    """Supported interview categories."""
    HR = "HR"
    TECHNICAL = "Technical"
    BEHAVIORAL = "Behavioral"
    MIXED = "Mixed"
    ROLE_SPECIFIC = "Role Specific"
    PROJECT_BASED = "Project Based"


class ExperienceLevel(str, Enum):
    """Candidate experience tiers."""
    FRESHER = "Fresher"
    ZERO_TO_TWO = "0–2 years"
    TWO_TO_FIVE = "2–5 years"
    FIVE_PLUS = "5+ years"


class Difficulty(str, Enum):
    """Interview difficulty levels."""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    ADAPTIVE = "Adaptive"


class InterviewMode(str, Enum):
    """Interview operational delivery modes."""
    TEXT = "TEXT"
    VOICE = "VOICE"
    VIDEO = "VIDEO"
    CODING = "CODING"
    SQL = "SQL"
    SYSTEM_DESIGN = "SYSTEM DESIGN"


class InterviewerPersona(str, Enum):
    """Interviewer conversational persona and coaching tone."""
    PROFESSIONAL = "Professional & Neutral"
    EMPATHETIC = "Empathetic & Supportive"
    STRICT = "Strict & Demanding"
    FAANG_LEAD = "FAANG Hiring Manager"
    STARTUP_FOUNDER = "Startup Founder"
    FAST_PACED = "Fast-Paced Screener"


class InterviewStatus(str, Enum):
    """Lifecycle status of an interview session."""
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InterviewConfig(BaseModel):
    """Comprehensive configuration payload for launching an interview."""
    candidate_name: str = Field(..., min_length=1, max_length=100, description="Full name of the candidate")
    role: Optional[str] = Field(default="Software Engineer", max_length=100, description="Target job title / role")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.TWO_TO_FIVE)
    interview_type: InterviewType = Field(default=InterviewType.TECHNICAL)
    difficulty: Difficulty = Field(default=Difficulty.MEDIUM)
    num_questions: int = Field(default=5, ge=1, le=25, description="Total number of interview questions")
    estimated_duration_minutes: int = Field(default=30, ge=5, le=180, description="Estimated interview length in minutes")
    language: str = Field(default="English", max_length=50, description="Language for conducting the interview")
    interviewer_persona: InterviewerPersona = Field(default=InterviewerPersona.PROFESSIONAL)
    topics: List[str] = Field(default_factory=list, description="Selected technical or behavioral focus topics")
    mode: InterviewMode = Field(default=InterviewMode.TEXT, description="Active delivery mode")

    @field_validator("candidate_name")
    @classmethod
    def validate_candidate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Candidate name cannot be blank or whitespace-only.")
        return stripped

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return "Software Engineer"
        return v.strip()

    @field_validator("topics")
    @classmethod
    def sanitize_topics(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip() for t in v if t and t.strip()]
        # Deduplicate while preserving order
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "InterviewConfig":
        # If technical or role-specific, ensure at least one topic is provided or default to Role
        if self.interview_type in (InterviewType.TECHNICAL, InterviewType.MIXED, InterviewType.ROLE_SPECIFIC):
            if not self.topics:
                # Default to role or general CS if none selected
                self.topics = ["General Computer Science", self.role or "Software Engineering"]

        # Validate that duration is reasonable for question count (at least 1 min per question)
        if self.estimated_duration_minutes < self.num_questions:
            raise ValueError(
                f"Estimated duration ({self.estimated_duration_minutes} mins) is too short for {self.num_questions} questions."
            )
        return self


class QuestionType(str, Enum):
    """Specific pedagogical and evaluative style of an interview question."""
    TECHNICAL = "Technical"
    BEHAVIORAL = "Behavioral"
    HR = "HR"
    SITUATIONAL = "Situational"
    CONCEPTUAL = "Conceptual"
    PROBLEM_SOLVING = "Problem Solving"
    PROJECT = "Project"
    ROLE_SPECIFIC = "Role Specific"


class StrategyPlan(BaseModel):
    """Strategic blueprint for generating a specific question in the interview sequence."""
    question_number: int = Field(..., ge=1, description="Question number in the sequence")
    question_type: QuestionType = Field(default=QuestionType.TECHNICAL)
    target_topic: str = Field(default="General", description="Specific topic to assess")
    category: str = Field(default="Technical", description="Broad category")
    difficulty: Difficulty = Field(default=Difficulty.MEDIUM)
    objective: str = Field(..., description="Assessment objective and pedagogical focus")


class Question(BaseModel):
    """Structured question model generated by the Strategy and AI Engine."""
    id: Optional[int] = Field(default=None, description="Database identifier")
    question_id: Optional[int] = Field(default=None, description="Alias for id")
    question_number: int = Field(default=1, ge=1, description="Sequential question number")
    text: str = Field(..., min_length=5, description="The interview question text")
    question_text: Optional[str] = Field(default=None, description="Alias for text")
    category: str = Field(default="Technical", description="Category or domain of the question")
    topic: str = Field(default="General", description="Specific topic focus (e.g. Python, SQL, System Design)")
    difficulty: Difficulty = Field(default=Difficulty.MEDIUM)
    question_type: QuestionType = Field(default=QuestionType.TECHNICAL)
    expected_concepts: List[str] = Field(default_factory=list, description="Key concepts expected in ideal answer")
    expected_points: Optional[List[str]] = Field(default=None, description="Alias for expected_concepts")
    evaluation_criteria: List[str] = Field(default_factory=list, description="Rubric criteria used by evaluator")
    follow_up_possible: bool = Field(default=True, description="Whether this question can be branched with follow-up")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible telemetry or strategy parameters")

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sanitize string IDs (e.g. 'py-int-001')
            for id_key in ["id", "question_id"]:
                if id_key in data and data[id_key] is not None:
                    val = data[id_key]
                    if isinstance(val, int):
                        pass
                    elif isinstance(val, str) and val.isdigit():
                        data[id_key] = int(val)
                    else:
                        data.setdefault("metadata", {})
                        if isinstance(data["metadata"], dict):
                            data["metadata"][f"raw_{id_key}"] = str(val)
                        data[id_key] = None

            # Sync id <-> question_id
            if data.get("id") is None and data.get("question_id") is not None:
                data["id"] = data["question_id"]
            elif data.get("question_id") is None and data.get("id") is not None:
                data["question_id"] = data["id"]
            
            # Flexible text aliases: question_text, question, title, prompt, problem_statement
            for text_key in ["question_text", "question", "title", "prompt", "problem_statement"]:
                if "text" not in data and text_key in data and data[text_key]:
                    data["text"] = str(data[text_key])
                    break
            if "question_text" not in data and "text" in data:
                data["question_text"] = data["text"]
            
            # Sync expected_concepts <-> expected_points / key_points / concepts
            for points_key in ["expected_points", "key_points", "concepts", "expected_answers"]:
                if "expected_concepts" not in data and points_key in data and data[points_key]:
                    data["expected_concepts"] = data[points_key]
                    break
            if "expected_points" not in data and "expected_concepts" in data:
                data["expected_points"] = data["expected_concepts"]

            # Normalize difficulty
            if "difficulty" in data and isinstance(data["difficulty"], str):
                diff_str = data["difficulty"].strip().title()
                diff_map = {
                    "Easy": "Easy", "Beginner": "Easy", "Junior": "Easy", "Entry": "Easy",
                    "Medium": "Medium", "Intermediate": "Medium", "Mid": "Medium", "Mid-Level": "Medium",
                    "Hard": "Hard", "Senior": "Hard", "Advanced": "Hard", "Expert": "Hard", "Lead": "Hard", "Staff": "Hard",
                    "Adaptive": "Adaptive"
                }
                data["difficulty"] = diff_map.get(diff_str, "Medium")

            # Normalize question_type
            if "question_type" in data and isinstance(data["question_type"], str):
                qt_str = data["question_type"].strip().lower()
                qt_map = {
                    "technical": "Technical", "coding": "Technical",
                    "behavioral": "Behavioral", "hr": "HR", "situational": "Situational",
                    "conceptual": "Conceptual", "theory": "Conceptual",
                    "problem solving": "Problem Solving", "problem_solving": "Problem Solving",
                    "project": "Project", "role specific": "Role Specific", "role_specific": "Role Specific"
                }
                data["question_type"] = qt_map.get(qt_str, data["question_type"])
        return data

    @model_validator(mode="after")
    def populate_reciprocal_aliases(self) -> "Question":
        if self.question_id is None and self.id is not None:
            self.question_id = self.id
        if self.id is None and self.question_id is not None:
            self.id = self.question_id
        if self.question_text is None and self.text:
            self.question_text = self.text
        if self.expected_points is None and self.expected_concepts:
            self.expected_points = self.expected_concepts
        return self


class CandidateAnswer(BaseModel):
    """Candidate's response submission."""
    question_id: Optional[int] = Field(default=None)
    question_number: int = Field(default=1, ge=1)
    answer_text: str = Field(..., min_length=1, description="Raw text of the candidate's answer")
    submitted_at: Optional[str] = Field(default=None)

    @field_validator("answer_text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Answer cannot be empty.")
        return stripped


class EvaluationMetrics(BaseModel):
    """Fine-grained numerical breakdown (1–10 scale) of answer quality (legacy & aggregate)."""
    relevance: int = Field(default=5, ge=1, le=10, description="Directness in addressing the question")
    correctness: int = Field(default=5, ge=1, le=10, description="Factual and conceptual accuracy")
    completeness: int = Field(default=5, ge=1, le=10, description="Coverage of necessary points")
    clarity: int = Field(default=5, ge=1, le=10, description="Communication structure and readability")
    depth: int = Field(default=5, ge=1, le=10, description="Demonstration of technical nuance")


class EvaluationEvidence(BaseModel):
    """Textual evidence or quote extracted from the candidate's answer supporting the score."""
    quote_or_reference: str = Field(..., description="Direct quote or textual reference from candidate answer")
    criterion_name: str = Field(default="General", description="Associated evaluation criterion")
    assessment: str = Field(..., description="Explanation of why this evidence supports or detracts from score")
    is_positive: bool = Field(default=True, description="True if evidence of strength; False if flaw/omission")


class EvaluationCriterion(BaseModel):
    """Specific rubric criterion evaluated with score, weight, and evidence."""
    name: str = Field(..., description="Name of the criterion (e.g. Correctness, STAR-Action, Reasoning)")
    score: float = Field(default=5.0, ge=0.0, le=10.0, description="Criterion rating (0-10)")
    weight: float = Field(default=1.0, ge=0.1, le=5.0, description="Relative weight in overall evaluation")
    feedback: str = Field(default="", description="Specific criterion-level feedback")
    evidence: List[EvaluationEvidence] = Field(default_factory=list, description="Grounding evidence points")


DEFAULT_ASSESSMENT_DISCLAIMER = (
    "This evaluation is an AI-assisted pedagogical assessment designed for coaching and practice feedback. "
    "It does not represent an absolute or objective measurement."
)


class AnswerEvaluation(BaseModel):
    """Structured evaluation generated for a single question response."""
    score: float = Field(default=5.0, ge=0.0, le=10.0, description="Overall score out of 10 for this answer")
    criteria_scores: List[EvaluationCriterion] = Field(
        default_factory=list,
        description="Type-specific rubric criteria evaluations with evidence"
    )
    evidence: List[EvaluationEvidence] = Field(
        default_factory=list,
        description="Grounding evidence quotes extracted from candidate answer"
    )
    metrics: EvaluationMetrics = Field(
        default_factory=EvaluationMetrics,
        description="Aggregate 5-dimension metrics for backward compatibility"
    )
    strengths: List[str] = Field(default_factory=list, description="Specific things candidate answered well")
    weaknesses: List[str] = Field(default_factory=list, description="Missing elements or mistakes")
    feedback: str = Field(..., description="Constructive feedback explaining the score")
    suggested_improvement: str = Field(..., description="Actionable advice or ideal response hints")
    assessment_disclaimer: str = Field(
        default=DEFAULT_ASSESSMENT_DISCLAIMER,
        description="Subjectivity disclaimer for AI scoring"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_evaluation_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Clamp score if out of bounds
            if "score" in data and isinstance(data["score"], (int, float)):
                data["score"] = max(0.0, min(10.0, round(float(data["score"]), 1)))

            # Sync criteria_scores from criteria if present
            if "criteria" in data and "criteria_scores" not in data:
                data["criteria_scores"] = data["criteria"]

            # Flatten evidence if criteria have evidence but top-level is empty
            if "evidence" not in data and "criteria_scores" in data and isinstance(data["criteria_scores"], list):
                ev_list = []
                for c in data["criteria_scores"]:
                    if isinstance(c, dict) and "evidence" in c and isinstance(c["evidence"], list):
                        ev_list.extend(c["evidence"])
                if ev_list:
                    data["evidence"] = ev_list

            # Populate metrics for backward compatibility if empty
            if "metrics" not in data or not data["metrics"]:
                base_score = int(max(1, min(10, round(float(data.get("score", 5.0))))))
                data["metrics"] = {
                    "relevance": base_score,
                    "correctness": base_score,
                    "completeness": base_score,
                    "clarity": base_score,
                    "depth": base_score,
                }
        return data

    @model_validator(mode="after")
    def sync_criteria_and_evidence(self) -> "AnswerEvaluation":
        # Collect all unique evidence items across top-level and criteria
        all_ev = list(self.evidence)
        existing_quotes = {e.quote_or_reference for e in all_ev}
        if self.criteria_scores:
            for c in self.criteria_scores:
                for ev in c.evidence:
                    if ev.quote_or_reference not in existing_quotes:
                        all_ev.append(ev)
                        existing_quotes.add(ev.quote_or_reference)
        self.evidence = all_ev
        return self


class QuestionEvaluationPair(BaseModel):
    """Pairing of a question, its submitted answer, and evaluation."""
    question: Question
    answer: CandidateAnswer
    evaluation: AnswerEvaluation


class EvaluationSummary(BaseModel):
    """Holistic summary of the entire interview session."""
    overall_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Aggregated overall score (0-10)")
    criteria_averages: Dict[str, float] = Field(default_factory=dict, description="Average scores across evaluated criteria")
    strengths_summary: List[str] = Field(default_factory=list, description="Top observed candidate strengths")
    weaknesses_summary: List[str] = Field(default_factory=list, description="Key areas needing improvement")
    overall_feedback: str = Field(default="", description="Comprehensive performance narrative")
    areas_to_improve: List[str] = Field(default_factory=list, description="Actionable topics to study or practice")
    disclaimer: str = Field(default=DEFAULT_ASSESSMENT_DISCLAIMER, description="Subjectivity disclaimer")


# Alias for backward compatibility
InterviewSummary = EvaluationSummary


class InterviewResult(BaseModel):
    """Complete interview payload after conclusion."""
    interview_id: Optional[int] = Field(default=None)
    config: InterviewConfig
    pairs: List[QuestionEvaluationPair] = Field(default_factory=list)
    summary: InterviewSummary
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
