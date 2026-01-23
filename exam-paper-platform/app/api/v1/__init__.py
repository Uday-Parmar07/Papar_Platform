from fastapi import APIRouter

from app.api.v1 import exam


api_router = APIRouter()
api_router.include_router(exam.router, prefix="/exams", tags=["exams"])
