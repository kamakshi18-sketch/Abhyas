"""
Persona Schemas (Phase 7).
Defines strongly-typed Pydantic model for InterviewerPersona behavioral configurations.
"""

from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.interview import InterviewerPersona


class PersonaConfig(BaseModel):
    """Configuration-driven behavioral, tonal, and communication profile for an Interviewer Persona (Phase 7)."""
    persona: InterviewerPersona = Field(..., description="Target Interviewer Persona enum")
    name: str = Field(..., description="Display title for persona")
    description: str = Field(..., description="Summary of conversational demeanor and coaching style")
    conversational_warmth: float = Field(default=0.5, ge=0.0, le=1.0, description="Warmth level on 0.0 to 1.0 scale")
    greeting_style: str = Field(..., description="How the persona opens questions or sessions")
    wording_style: str = Field(..., description="Vocabulary, phrasing, and sentence structure")
    explanation_style: str = Field(..., description="Approach to elaborating questions or context")
    transition_style: str = Field(..., description="How the persona pivots between questions or topics")
    feedback_tone: str = Field(..., description="Tone for delivering constructive evaluation feedback")
    sample_phrase: str = Field(..., description="Representative quote showing the persona in action")
    prompt_directive: str = Field(..., description="Strict prompt instructions injected into LLM context")
