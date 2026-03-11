from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.dashboard import DashboardResponse
from app.schemas.explain import ExplainQuestionRequest, ExplainQuestionResponse
from app.schemas.paper import GeneratePaperRequest, GeneratePaperResponse
from app.services.exam_service import generate_exam
from app.services.explain_service import explain_question
from app.services.paper_service import get_dashboard_data, save_generated_paper


router = APIRouter()


@router.post('/generate-paper', response_model=GeneratePaperResponse)
def generate_paper_alias(
    payload: GeneratePaperRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GeneratePaperResponse:
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


@router.get('/dashboard', response_model=DashboardResponse)
def dashboard_alias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    return DashboardResponse(**get_dashboard_data(db, current_user))


@router.post('/explain-question', response_model=ExplainQuestionResponse)
def explain_question_alias(
    payload: ExplainQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExplainQuestionResponse:
    return ExplainQuestionResponse(**explain_question(db, current_user, payload))
