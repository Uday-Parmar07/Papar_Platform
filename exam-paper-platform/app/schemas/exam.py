from typing import List, Dict

from pydantic import BaseModel, Field, field_validator


class GenerateExamRequest(BaseModel):
	subject: str = Field(min_length=1, description="Subject name to generate questions for")
	total_questions: int = Field(ge=1, le=120, description="Number of questions to generate")
	cutoff_year: int = Field(ge=2000, description="Do not include questions asked after this year")


class Question(BaseModel):
	concept: str
	difficulty: str
	question: str


class GenerateExamResponse(BaseModel):
	total_questions: int
	distribution: Dict[str, int]
	questions: List[Question]
	subject: str


class VerifyQuestionsRequest(BaseModel):
	questions: List[Question]


class QuestionVerification(BaseModel):
	concept: str
	difficulty: str
	question: str
	valid: bool
	reason: str


class VerifyQuestionsResponse(BaseModel):
	total: int
	valid: int
	invalid: int
	results: List[QuestionVerification]


class PdfMetadata(BaseModel):
	title: str = "Generated Exam Paper"


class PdfRequest(BaseModel):
	questions: List[Question]
	metadata: PdfMetadata = PdfMetadata()

	@field_validator("questions")
	def ensure_questions(cls, value: List[Question]):
		if not value:
			raise ValueError("At least one question is required")
		return value


class SubjectListResponse(BaseModel):
	subjects: List[str]
