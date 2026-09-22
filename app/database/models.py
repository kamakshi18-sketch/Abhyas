"""
SQLAlchemy ORM models for Candidate, Interview, Question, Answer, and Evaluation.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database.database import Base


def utc_now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)



class Candidate(Base):
    """Candidate entity."""
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    interviews = relationship(
        "Interview",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(Interview.created_at)",
    )


class Interview(Base):
    """Interview session entity."""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    role = Column(String(100), nullable=False)
    experience_level = Column(String(50), nullable=False)
    interview_type = Column(String(50), nullable=False)
    difficulty = Column(String(50), nullable=False)
    num_questions = Column(Integer, nullable=False, default=5)
    estimated_duration_minutes = Column(Integer, nullable=False, default=30)
    language = Column(String(50), nullable=False, default="English")
    interviewer_persona = Column(String(100), nullable=True)
    mode = Column(String(50), nullable=False, default="TEXT")
    topics_json = Column(Text, nullable=True)         # JSON-encoded list of topics
    config_json = Column(Text, nullable=True)         # Full serialized InterviewConfig
    status = Column(String(50), default="CREATED", nullable=False)
    overall_score = Column(Float, nullable=True)
    overall_feedback = Column(Text, nullable=True)
    strengths_summary = Column(Text, nullable=True)  # JSON-encoded list
    weaknesses_summary = Column(Text, nullable=True)  # JSON-encoded list
    areas_to_improve = Column(Text, nullable=True)    # JSON-encoded list
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)


    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")
    questions = relationship(
        "QuestionModel",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="QuestionModel.question_number",
    )


class QuestionModel(Base):
    """Question entity generated during an interview."""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    topic = Column(String(100), nullable=True, default="General")
    difficulty = Column(String(50), nullable=False)
    question_type = Column(String(50), nullable=True, default="Technical")
    expected_points = Column(Text, nullable=True)             # JSON-encoded list of expected points
    expected_concepts_json = Column(Text, nullable=True)      # JSON-encoded list of concepts
    evaluation_criteria_json = Column(Text, nullable=True)    # JSON-encoded list of rubric criteria
    follow_up_possible = Column(Integer, default=1)           # 1 for True, 0 for False
    metadata_json = Column(Text, nullable=True)               # JSON-encoded metadata dictionary
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    interview = relationship("Interview", back_populates="questions")
    answers = relationship(
        "AnswerModel",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class AnswerModel(Base):
    """Candidate's response entity for a specific question."""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    submitted_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    question = relationship("QuestionModel", back_populates="answers")
    evaluation = relationship(
        "EvaluationModel",
        back_populates="answer",
        uselist=False,
        cascade="all, delete-orphan",
    )


class EvaluationModel(Base):
    """Evaluation score and constructive feedback for an answer."""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False, unique=True)
    score = Column(Float, nullable=False)
    relevance = Column(Integer, nullable=False, default=5)
    correctness = Column(Integer, nullable=False, default=5)
    completeness = Column(Integer, nullable=False, default=5)
    clarity = Column(Integer, nullable=False, default=5)
    depth = Column(Integer, nullable=False, default=5)
    criteria_scores_json = Column(Text, nullable=True)    # JSON-encoded list of EvaluationCriterion
    evidence_json = Column(Text, nullable=True)           # JSON-encoded list of EvaluationEvidence
    strengths = Column(Text, nullable=True)               # JSON-encoded list of strengths
    weaknesses = Column(Text, nullable=True)              # JSON-encoded list of weaknesses
    feedback = Column(Text, nullable=False)
    suggested_improvement = Column(Text, nullable=False)
    assessment_disclaimer = Column(Text, nullable=True)   # Subjectivity coaching disclaimer
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    answer = relationship("AnswerModel", back_populates="evaluation")
