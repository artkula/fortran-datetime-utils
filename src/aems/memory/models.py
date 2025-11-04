"""
Memory Models

Data structures for storing learnings and feedback at different levels.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MemoryLevel(str, Enum):
    """Level at which memory is stored."""
    COURSE = "course"
    EXAM = "exam"
    QUESTION = "question"
    USER = "user"


class FeedbackType(str, Enum):
    """Type of feedback provided."""
    GRADE_OVERRIDE = "grade_override"
    IMPROVE_CHECKING = "improve_checking"
    EQUIVALENCE = "equivalence"
    CLARIFICATION = "clarification"
    COMMON_ERROR = "common_error"


class Memory(BaseModel):
    """
    A single memory entry representing a learning or feedback.

    Memories are stored at different levels and used to improve
    future grading decisions.
    """
    id: str = Field(..., description="Unique identifier for this memory")
    level: MemoryLevel

    # Context identifiers
    course_id: Optional[str] = None
    exam_id: Optional[str] = None
    question_id: Optional[str] = None
    check_id: Optional[str] = None
    user_id: Optional[str] = None

    # Memory content
    feedback_type: FeedbackType
    title: str = Field(..., description="Short title of the learning")
    description: str = Field(..., description="Detailed description")

    # Original grading context
    original_verdict: Optional[str] = None
    override_verdict: Optional[str] = None
    original_points: Optional[float] = None
    override_points: Optional[float] = None

    # Additional context
    student_work_excerpt: Optional[str] = Field(
        None,
        description="Relevant excerpt from student work"
    )
    rationale: Optional[str] = Field(
        None,
        description="Reasoning for the feedback/override"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0, le=1.0)
    applied_count: int = Field(
        default=0,
        description="Number of times this memory has been applied"
    )

    # Tags for retrieval
    tags: List[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class EquivalenceRule(BaseModel):
    """
    Represents an equivalence between different formulations.

    E.g., "F=ma" is equivalent to "Force equals mass times acceleration"
    """
    canonical_form: str = Field(..., description="The canonical/preferred form")
    equivalent_forms: List[str] = Field(
        default_factory=list,
        description="Alternative equivalent forms"
    )
    context: Optional[str] = Field(
        None,
        description="When this equivalence applies"
    )
    confidence: float = Field(default=1.0, ge=0, le=1.0)


class GradingPolicy(BaseModel):
    """
    High-level grading policy or guideline.

    Stored at course or exam level.
    """
    name: str
    description: str
    applies_to: Optional[str] = Field(
        None,
        description="What this policy applies to (e.g., 'all numeric answers')"
    )
    examples: List[str] = Field(default_factory=list)


class CommonError(BaseModel):
    """
    Documentation of a common student error pattern.
    """
    error_pattern: str = Field(..., description="Description of the error")
    typical_work: str = Field(..., description="What the work typically looks like")
    partial_credit: Optional[float] = Field(
        None,
        description="Suggested partial credit for this error"
    )
    feedback_suggestion: Optional[str] = Field(
        None,
        description="Suggested feedback to student"
    )


class MemoryQuery(BaseModel):
    """Query for retrieving relevant memories."""
    level: Optional[MemoryLevel] = None
    course_id: Optional[str] = None
    exam_id: Optional[str] = None
    question_id: Optional[str] = None
    check_id: Optional[str] = None
    user_id: Optional[str] = None
    feedback_type: Optional[FeedbackType] = None
    tags: Optional[List[str]] = None
    min_confidence: float = Field(default=0.5, ge=0, le=1.0)
    limit: Optional[int] = Field(default=10, gt=0)
