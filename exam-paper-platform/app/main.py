from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import close_database
from app.routes import router


def create_app() -> FastAPI:
	app = FastAPI(title="AI Exam Paper Generator")

	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	app.include_router(router)

	@app.get("/health")
	def health() -> dict[str, str]:
		return {"status": "ok"}

	@app.on_event("shutdown")
	def shutdown_event() -> None:
		close_database()

	return app


app = create_app()
