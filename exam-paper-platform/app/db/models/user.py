from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(120), nullable=False)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
	password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

	papers: Mapped[list["GeneratedPaper"]] = relationship(back_populates="user", cascade="all, delete-orphan")
	explanations: Mapped[list["ExplanationCache"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class GeneratedPaper(Base):
	__tablename__ = "generated_papers"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
	subject: Mapped[str] = mapped_column(String(255), nullable=False)
	topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
	questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

	user: Mapped[User] = relationship(back_populates="papers")


class ExplanationCache(Base):
	__tablename__ = "question_explanations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
	cache_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
	question: Mapped[str] = mapped_column(Text, nullable=False)
	topic: Mapped[str] = mapped_column(String(255), nullable=False)
	difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
	concept: Mapped[str] = mapped_column(Text, nullable=False)
	formula: Mapped[str] = mapped_column(Text, nullable=False)
	steps: Mapped[str] = mapped_column(Text, nullable=False)
	answer: Mapped[str] = mapped_column(Text, nullable=False)
	exam_tip: Mapped[str] = mapped_column(Text, nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

	user: Mapped[User] = relationship(back_populates="explanations")
