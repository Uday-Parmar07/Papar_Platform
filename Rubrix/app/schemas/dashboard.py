from typing import List

from pydantic import BaseModel

from app.schemas.paper import PaperHistoryItem


class DashboardResponse(BaseModel):
    papers_generated: int
    total_questions_solved: int
    recent_papers: List[PaperHistoryItem]
    weak_topics: List[str]
