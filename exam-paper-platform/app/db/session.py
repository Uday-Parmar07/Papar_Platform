from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()


def _create_engine_with_fallback():
	primary_url = settings.database_url
	primary_engine = create_engine(
		primary_url,
		connect_args={"check_same_thread": False} if primary_url.startswith("sqlite") else {},
	)

	if primary_url.startswith("sqlite"):
		return primary_engine

	if not settings.enable_local_db_fallback:
		return primary_engine

	try:
		with primary_engine.connect():
			pass
		return primary_engine
	except OperationalError:
		fallback_url = settings.local_fallback_database_url
		fallback_engine = create_engine(
			fallback_url,
			connect_args={"check_same_thread": False} if fallback_url.startswith("sqlite") else {},
		)
		return fallback_engine


engine = _create_engine_with_fallback()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
