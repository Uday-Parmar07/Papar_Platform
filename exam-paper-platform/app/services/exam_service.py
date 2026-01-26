from functools import lru_cache
from typing import List

from app.schemas.exam import GenerateExamResponse, Question
from app.llm.graph_flow import build_graph
from app.llm.paper_planner import build_paper_blueprint
from app.graph.queries import list_subject_names


@lru_cache()
def _compiled_graph():
	return build_graph()


def _question_from_blueprint_item(item, subject: str) -> Question:
	concept = getattr(item, "concept", "Unknown concept")
	difficulty = getattr(item, "difficulty", "Medium")
	prompt = (
		f"Describe a question on {concept} from the {subject} syllabus appropriate for {difficulty} "
		"level candidates."
	)
	return Question(concept=concept, difficulty=difficulty, question=prompt)


def generate_exam(total_questions: int, cutoff_year: int, subject: str) -> GenerateExamResponse:
	subject_name = subject.strip()
	if not subject_name:
		raise ValueError("Subject is required")

	available_subjects = list_subject_names()
	if not available_subjects:
		raise ValueError("No subjects available. Please ingest syllabus data first.")
	if subject_name not in available_subjects:
		raise ValueError(f"Unknown subject: {subject_name}")

	blueprint = build_paper_blueprint(
		total_questions=total_questions,
		cutoff_year=cutoff_year,
		subject=subject_name,
	)

	distribution = dict(blueprint.distribution)

	try:
		graph = _compiled_graph()
		result = graph.invoke({
			"total_questions": total_questions,
			"cutoff_year": cutoff_year,
			"retry_count": 0,
			"final_questions": [],
			"failed_questions": [],
			"subject": subject_name,
		})
		generated_questions = result.get("final_questions") or result.get("validated_questions") or []
	except Exception:
		generated_questions = []

	questions: List[Question] = []

	if generated_questions:
		for item in generated_questions:
			questions.append(
				Question(
					concept=item.get("concept", ""),
					difficulty=item.get("difficulty", ""),
					question=item.get("question", ""),
				)
			)

	if not questions:
		questions = [_question_from_blueprint_item(item, subject_name) for item in blueprint.questions]

	return GenerateExamResponse(
		total_questions=len(questions),
		distribution=distribution,
		questions=questions,
		subject=subject_name,
	)
