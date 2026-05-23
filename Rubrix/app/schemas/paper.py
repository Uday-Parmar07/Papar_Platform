from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field

from app.schemas.exam import GenerateExamRequest, GenerateExamResponse


class GeneratePaperRequest(GenerateExamRequest):
    pass


class GeneratePaperResponse(BaseModel):
    paper_id: int
    result: GenerateExamResponse


class PaperHistoryItem(BaseModel):
    paper_id: int
    subject: str
    topics: List[str]
    total_questions: int
    created_at: datetime


class PaperDetail(BaseModel):
    paper_id: int
    subject: str
    topics: List[str]
    questions: List[Any] = Field(default_factory=list)
    created_at: datetime
