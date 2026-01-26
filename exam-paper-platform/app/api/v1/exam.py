from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.exam import (
	GenerateExamRequest,
	GenerateExamResponse,
	SubjectListResponse,
	VerifyQuestionsRequest,
	VerifyQuestionsResponse,
	PdfRequest,
)
from app.services.exam_service import generate_exam
from app.services.pdf_service import render_questions_pdf
from app.llm.nodes.validate import validate_question
from app.graph.queries import list_subject_names


router = APIRouter()


@router.post("/generate", response_model=GenerateExamResponse)
def generate_exam_endpoint(payload: GenerateExamRequest) -> GenerateExamResponse:
	try:
		return generate_exam(
			total_questions=payload.total_questions,
			cutoff_year=payload.cutoff_year,
			subject=payload.subject,
		)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/subjects", response_model=SubjectListResponse)
def list_subjects() -> SubjectListResponse:
	subjects = list_subject_names()
	return SubjectListResponse(subjects=subjects)


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
