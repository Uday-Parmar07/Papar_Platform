from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.explain import ExplainQuestionRequest, ExplainQuestionResponse
from app.services.explain_service import explain_question


router = APIRouter()


@router.post("/question", response_model=ExplainQuestionResponse)
def explain_question_endpoint(payload: ExplainQuestionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ExplainQuestionResponse:
    result = explain_question(db, current_user, payload)
    return ExplainQuestionResponse(**result)
