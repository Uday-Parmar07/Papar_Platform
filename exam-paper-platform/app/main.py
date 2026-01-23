from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
	settings = get_settings()

	app = FastAPI(title=settings.project_name)

	app.add_middleware(
		CORSMiddleware,
		allow_origins=settings.allow_origins or ["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	app.include_router(api_router, prefix=settings.api_v1_prefix)

	return app


app = create_app()
