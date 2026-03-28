from pydantic import BaseModel, Field


class GeneratePaperRequest(BaseModel):
	subject: str
	topics: list[str] = Field(default_factory=list)
	cutoff_year: int
	num_questions: int = Field(gt=0, le=100)


class GeneratedQuestion(BaseModel):
	question: str
	topic: str


class GeneratePaperResponse(BaseModel):
	subject: str
	questions: list[GeneratedQuestion]


class SubjectsResponse(BaseModel):
	subjects: list[str]


class TopicsResponse(BaseModel):
	subject: str
	topics: list[str]