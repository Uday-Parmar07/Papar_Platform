from fastapi import APIRouter

from app.api.v1 import auth, dashboard, exam, explain, papers, platform


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(exam.router, prefix="/exams", tags=["exams"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(explain.router, prefix="/explain", tags=["explain"])
api_router.include_router(platform.router, tags=["platform"])
