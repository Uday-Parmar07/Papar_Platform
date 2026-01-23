from functools import lru_cache
from typing import List

from app.schemas.exam import GenerateExamResponse, Question
from app.llm.graph_flow import build_graph
from app.llm.paper_planner import build_paper_blueprint


@lru_cache()
def _compiled_graph():
	return build_graph()


def _question_from_blueprint_item(item) -> Question:
	concept = getattr(item, "concept", "Unknown concept")
	difficulty = getattr(item, "difficulty", "Medium")
	prompt = f"Describe a question on {concept} appropriate for {difficulty} level candidates."
	return Question(concept=concept, difficulty=difficulty, question=prompt)


def generate_exam(total_questions: int, cutoff_year: int) -> GenerateExamResponse:
	blueprint = build_paper_blueprint(total_questions=total_questions, cutoff_year=cutoff_year)

	distribution = dict(blueprint.distribution)

	try:
		graph = _compiled_graph()
		result = graph.invoke({
			"total_questions": total_questions,
			"cutoff_year": cutoff_year,
			"retry_count": 0,
			"final_questions": [],
			"failed_questions": [],
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
		questions = [_question_from_blueprint_item(item) for item in blueprint.questions]

	return GenerateExamResponse(
		total_questions=len(questions),
		distribution=distribution,
		questions=questions,
	)
