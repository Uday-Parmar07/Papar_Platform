from datetime import datetime, timezone
from typing import Any, Iterable, List

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.db.models.user import GeneratedPaper, User
from app.schemas.exam import GenerateExamResponse


def save_generated_paper(
    db: Session,
    user: User,
    result: GenerateExamResponse,
) -> GeneratedPaper:
    question_payload = [item.model_dump() for item in result.questions]

    paper = GeneratedPaper(
        user_id=user.id,
        subject=result.subject_name,
        topics=result.topics,
        questions=question_payload,
        created_at=datetime.now(timezone.utc),
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


def _to_history_item(row: GeneratedPaper) -> dict[str, Any]:
    return {
        "paper_id": row.id,
        "subject": row.subject,
        "topics": row.topics or [],
        "total_questions": len(row.questions or []),
        "created_at": row.created_at,
    }


def get_paper_history(db: Session, user: User, limit: int = 50) -> List[dict[str, Any]]:
    stmt: Select[tuple[GeneratedPaper]] = (
        select(GeneratedPaper)
        .where(GeneratedPaper.user_id == user.id)
        .order_by(desc(GeneratedPaper.created_at))
        .limit(limit)
    )
    rows: Iterable[GeneratedPaper] = db.scalars(stmt).all()
    return [_to_history_item(row) for row in rows]


def get_paper_by_id(db: Session, user: User, paper_id: int) -> GeneratedPaper | None:
    stmt: Select[tuple[GeneratedPaper]] = select(GeneratedPaper).where(
        GeneratedPaper.id == paper_id,
        GeneratedPaper.user_id == user.id,
    )
    return db.scalar(stmt)


def get_dashboard_data(db: Session, user: User) -> dict[str, Any]:
    papers_generated = db.scalar(
        select(func.count(GeneratedPaper.id)).where(GeneratedPaper.user_id == user.id)
    ) or 0

    rows = db.scalars(
        select(GeneratedPaper.questions).where(GeneratedPaper.user_id == user.id)
    ).all()
    total_questions_solved = sum(len(entry or []) for entry in rows)

    recent = get_paper_history(db, user, limit=5)

    return {
        "papers_generated": int(papers_generated),
        "total_questions_solved": int(total_questions_solved),
        "recent_papers": recent,
        "weak_topics": [],
    }
