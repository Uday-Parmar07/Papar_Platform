from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.exam import Question


class GenerateAnswersRequest(BaseModel):
    questions: List[Question] = Field(..., min_length=1, description="Questions requiring answers")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace for retrieval (auto-detected from subject if not provided)")
    subject: Optional[str] = Field(default=None, description="Subject ID (e.g., 'EE 2026') for validation and namespace mapping")

    @field_validator("namespace")
    def normalize_namespace(cls, value: str | None) -> str | None:
        if value:
            return value.strip() or None
        return None


class AnswerItem(BaseModel):
    concept: str
    difficulty: str
    question: str
    answer: str
    context_retrieved: bool


class GenerateAnswersResponse(BaseModel):
    total: int
    namespace: str
    answers: List[AnswerItem]
