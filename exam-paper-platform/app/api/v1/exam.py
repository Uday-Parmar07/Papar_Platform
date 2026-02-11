from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.answer import GenerateAnswersRequest, GenerateAnswersResponse
from app.schemas.exam import (
	GenerateExamRequest,
	GenerateExamResponse,
	SubjectListResponse,
	TopicListResponse,
	VerifyQuestionsRequest,
	VerifyQuestionsResponse,
	PdfRequest,
)
from app.services.exam_service import generate_exam
from app.services.pdf_service import render_questions_pdf
from app.services.answer_service import generate_answers as generate_answers_batch
from app.llm.nodes.validate import validate_question
from app.graph.queries import list_subjects as graph_list_subjects
from app.graph.queries import list_topics_for_subject, resolve_subject_label


router = APIRouter()


@router.post("/generate", response_model=GenerateExamResponse)
def generate_exam_endpoint(payload: GenerateExamRequest) -> GenerateExamResponse:
	try:
		return generate_exam(
			total_questions=payload.total_questions,
			cutoff_year=payload.cutoff_year,
			subject=payload.subject,
			topics=payload.topics,
		)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/subjects", response_model=SubjectListResponse)
def list_subjects() -> SubjectListResponse:
	subjects = graph_list_subjects()
	return SubjectListResponse(subjects=subjects)


@router.get("/subjects/{subject_id}/topics", response_model=TopicListResponse)
def list_topics(subject_id: str) -> TopicListResponse:
	topics = list_topics_for_subject(subject_id)
	if not topics:
		subject_exists = any(subject["id"] == subject_id for subject in graph_list_subjects())
		if not subject_exists:
			raise HTTPException(status_code=404, detail=f"Subject '{resolve_subject_label(subject_id)}' not found")
	return TopicListResponse(topics=topics)


@router.post("/verify", response_model=VerifyQuestionsResponse)
def verify_questions(payload: VerifyQuestionsRequest) -> VerifyQuestionsResponse:
	validation_results = []

	for question in payload.questions:
		result = validate_question(question.dict())
		validation_results.append(
			{
				"concept": question.concept,
				"difficulty": question.difficulty,
				"question": question.question,
				"valid": result["valid"],
				"reason": result.get("reason", "OK"),
			}
		)

	valid_questions = [item for item in validation_results if item["valid"]]

	return VerifyQuestionsResponse(
		total=len(validation_results),
		valid=len(valid_questions),
		invalid=len(validation_results) - len(valid_questions),
		results=validation_results,
	)


@router.post("/answers", response_model=GenerateAnswersResponse)
def generate_answers(payload: GenerateAnswersRequest) -> GenerateAnswersResponse:
	try:
		answers = generate_answers_batch(
			payload.questions, 
			namespace=payload.namespace,
			subject=payload.subject
		)
		# Determine the actual namespace used
		if payload.namespace:
			used_namespace = payload.namespace
		elif payload.subject:
			# Import here to avoid circular dependency
			from app.services.answer_service import SUBJECT_NAMESPACE_MAP
			used_namespace = SUBJECT_NAMESPACE_MAP.get(payload.subject, "Electrical Engineering")
		else:
			used_namespace = "Electrical Engineering"
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except RuntimeError as exc:
		raise HTTPException(status_code=500, detail=str(exc)) from exc

	return GenerateAnswersResponse(
		total=len(answers),
		namespace=used_namespace,
		answers=answers,
	)


@router.post("/pdf")
def download_pdf(payload: PdfRequest):
	if not payload.questions:
		raise HTTPException(status_code=400, detail="No questions supplied")

	pdf_bytes = render_questions_pdf(
		title=payload.metadata.title,
		questions=[question.dict() for question in payload.questions],
	)

	return StreamingResponse(
		pdf_bytes,
		media_type="application/pdf",
		headers={
			"Content-Disposition": f"attachment; filename=exam-paper.pdf",
		},
	)
