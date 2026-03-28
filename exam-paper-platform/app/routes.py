from fastapi import APIRouter, HTTPException
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.database import get_database
from app.models import GeneratePaperRequest, GeneratePaperResponse, SubjectsResponse, TopicsResponse, GeneratedQuestion
from app.neo4j_service import Neo4jService
from app.services.exam_service import generate_exam


router = APIRouter()


def _neo4j_service() -> Neo4jService:
	return Neo4jService(get_database())


@router.get("/subjects", response_model=SubjectsResponse)
def get_subjects() -> SubjectsResponse:
	try:
		subjects = _neo4j_service().list_subjects()
		return SubjectsResponse(subjects=subjects)
	except (ServiceUnavailable, Neo4jError) as exc:
		raise HTTPException(status_code=503, detail="Neo4j is unavailable. Check NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD.") from exc


@router.get("/topics/{subject}", response_model=TopicsResponse)
def get_topics(subject: str) -> TopicsResponse:
	try:
		topics = _neo4j_service().list_topics(subject)
		if not topics:
			raise HTTPException(status_code=404, detail=f"No topics found for subject '{subject}'")
		return TopicsResponse(subject=subject, topics=topics)
	except HTTPException:
		raise
	except (ServiceUnavailable, Neo4jError) as exc:
		raise HTTPException(status_code=503, detail="Neo4j is unavailable. Check NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD.") from exc


@router.post("/generate-paper", response_model=GeneratePaperResponse)
def generate_paper_endpoint(payload: GeneratePaperRequest) -> GeneratePaperResponse:
	"""Generate exam paper using the new exam service with LangGraph."""
	try:
		# Validate topics
		topics = [topic.strip() for topic in payload.topics if topic.strip()]
		if not topics:
			raise HTTPException(status_code=400, detail="At least one topic is required")
		
		# Use the new exam service
		result = generate_exam(
			total_questions=payload.num_questions,
			cutoff_year=payload.cutoff_year,
			subject=payload.subject,
			topics=topics
		)
		
		# Convert to response format
		questions = [
			GeneratedQuestion(
				question=q.question,
				topic=q.concept  # Map concept to topic for frontend
			)
			for q in result.questions
		]
		
		return GeneratePaperResponse(
			subject=result.subject_name,
			questions=questions
		)
		
	except HTTPException:
		raise
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except (ServiceUnavailable, Neo4jError) as exc:
		raise HTTPException(status_code=503, detail="Neo4j is unavailable. Check NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD.") from exc
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to generate exam: {str(exc)}") from exc