from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.paper import GeneratePaperRequest, GeneratePaperResponse, PaperDetail, PaperHistoryItem
from app.services.exam_service import generate_exam
from app.services.paper_service import get_paper_by_id, get_paper_history, save_generated_paper


router = APIRouter()


@router.post("/generate-paper", response_model=GeneratePaperResponse)
def generate_paper(payload: GeneratePaperRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> GeneratePaperResponse:
    try:
        result = generate_exam(
            total_questions=payload.total_questions,
            cutoff_year=payload.cutoff_year,
            subject=payload.subject,
            topics=payload.topics,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    saved = save_generated_paper(db, current_user, result)
    return GeneratePaperResponse(paper_id=saved.id, result=result)


@router.get("/history", response_model=list[PaperHistoryItem])
def papers_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[PaperHistoryItem]:
    rows = get_paper_history(db, current_user)
    return [PaperHistoryItem(**row) for row in rows]


@router.get("/{paper_id}", response_model=PaperDetail)
def paper_detail(paper_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PaperDetail:
    paper = get_paper_by_id(db, current_user, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return PaperDetail(
        paper_id=paper.id,
        subject=paper.subject,
        topics=paper.topics or [],
        questions=paper.questions or [],
        created_at=paper.created_at,
    )
