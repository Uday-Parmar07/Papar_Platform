from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	api_v1_prefix: str = "/api/v1"
	project_name: str = "Exam Paper Platform"
	allow_origins: List[AnyHttpUrl] = []
	database_url: str = "sqlite:///./exam_platform.db"
	enable_local_db_fallback: bool = True
	local_fallback_database_url: str = "sqlite:///./exam_platform.db"
	jwt_secret_key: str = "change-this-in-production"
	jwt_algorithm: str = "HS256"
	access_token_expire_minutes: int = 60 * 24
	groq_api_key: str | None = None
	explanation_model: str = "llama-3.3-70b-versatile"


@lru_cache()
def get_settings() -> Settings:
	return Settings()
