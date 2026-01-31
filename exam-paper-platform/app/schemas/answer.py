from typing import List

from pydantic import BaseModel, Field, field_validator

from app.schemas.exam import Question


class GenerateAnswersRequest(BaseModel):
    questions: List[Question] = Field(..., min_length=1, description="Questions requiring answers")
    namespace: str = Field(default="Electrical Engineering", description="Pinecone namespace for retrieval")

    @field_validator("namespace")
    def normalize_namespace(cls, value: str) -> str:
        return value.strip() or "Electrical Engineering"


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
