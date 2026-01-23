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


@lru_cache()
def get_settings() -> Settings:
	return Settings()
