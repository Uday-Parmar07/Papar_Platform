from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExplainQuestionRequest(BaseModel):
    question: str = Field(min_length=10)
    topic: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "exam"]


class ExplainQuestionResponse(BaseModel):
    concept: str
    formula: str
    steps: str
    answer: str
    exam_tip: str
    cached: bool = False
    created_at: datetime | None = None
