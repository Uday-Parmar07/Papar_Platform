import random

from app.models import GeneratePaperRequest, GeneratePaperResponse, GeneratedQuestion
from app.neo4j_service import Neo4jService


class PaperGenerator:
	def __init__(self, neo4j_service: Neo4jService):
		self.neo4j_service = neo4j_service

	def generate(self, payload: GeneratePaperRequest) -> GeneratePaperResponse:
		topics = [topic.strip() for topic in payload.topics if topic.strip()]
		if not topics:
			raise ValueError("At least one topic is required")

		rows = self.neo4j_service.get_questions(
			subject=payload.subject,
			topics=topics,
			cutoff_year=payload.cutoff_year,
		)

		clean_rows = [
			row
			for row in rows
			if isinstance(row.get("question"), str) and str(row.get("question")).strip()
		]

		random.shuffle(clean_rows)
		selected = clean_rows[: payload.num_questions]

		questions = [
			GeneratedQuestion(
				question=str(row["question"]).strip(),
				topic=str(row.get("topic") or "Unknown Topic"),
			)
			for row in selected
		]

		return GeneratePaperResponse(subject=payload.subject, questions=questions)