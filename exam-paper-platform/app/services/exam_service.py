from functools import lru_cache
from typing import List, Optional

from app.schemas.exam import GenerateExamResponse, Question
from app.llm.graph_flow import build_graph
from app.llm.paper_planner import build_paper_blueprint
from app.graph.queries import list_subjects, list_topics_for_subject, resolve_subject_label


@lru_cache()
def _compiled_graph():
	return build_graph()


def _question_from_blueprint_item(item, subject_label: str) -> Question:
	concept = getattr(item, "concept", "Unknown concept")
	difficulty = getattr(item, "difficulty", "Medium")
	prompt = (
		f"Describe a question on {concept} from the {subject_label} syllabus appropriate for {difficulty} "
		"level candidates."
	)
	return Question(concept=concept, difficulty=difficulty, question=prompt)


def generate_exam(
	total_questions: int,
	cutoff_year: int,
	subject: str,
	topics: Optional[List[str]] = None,
) -> GenerateExamResponse:
	subject_id = subject.strip()
	if not subject_id:
		raise ValueError("Subject is required")

	available_subjects = list_subjects()
	if not available_subjects:
		raise ValueError("No subjects available. Please ingest syllabus data first.")

	subject_lookup = {item["id"]: item["name"] for item in available_subjects}
	if subject_id not in subject_lookup:
		raise ValueError(f"Unknown subject: {resolve_subject_label(subject_id)}")

	subject_label = subject_lookup[subject_id]
	available_topics = list_topics_for_subject(subject_id)
	if not available_topics:
		raise ValueError(
			f"No topics found for {subject_label}. Please ingest syllabus data before generating questions."
		)

	topics = topics or []
	requested_topics = [topic.strip() for topic in topics if topic and topic.strip()]
	if requested_topics:
		invalid = sorted({topic for topic in requested_topics if topic not in available_topics})
		if invalid:
			raise ValueError(
				f"Unknown topic(s) for {subject_label}: {', '.join(invalid)}"
			)
		selected_topics = requested_topics
	else:
		selected_topics = available_topics

	topics_filter = (
		selected_topics
		if set(selected_topics) != set(available_topics)
		else None
	)

	blueprint = build_paper_blueprint(
		total_questions=total_questions,
		cutoff_year=cutoff_year,
		subject=subject_id,
		subject_label=subject_label,
		topics=topics_filter,
		topics_selected=selected_topics,
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
			"subject": subject_id,
			"subject_label": subject_label,
			"topics": topics_filter,
			"topics_selected": selected_topics,
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
		questions = [_question_from_blueprint_item(item, subject_label) for item in blueprint.questions]

	return GenerateExamResponse(
		total_questions=len(questions),
		distribution=distribution,
		questions=questions,
		subject_id=subject_id,
		subject_name=subject_label,
		topics=selected_topics,
	)
