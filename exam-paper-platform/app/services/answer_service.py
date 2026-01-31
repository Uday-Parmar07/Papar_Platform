import os
from functools import lru_cache
from typing import Iterable, List

from groq import Groq

from app.rag.embeddings import embed_texts
from app.rag.vector_store import PineconeVectorStore
from app.schemas.answer import AnswerItem
from app.schemas.exam import Question

DEFAULT_NAMESPACE = os.getenv("PINECONE_DEFAULT_NAMESPACE", "Electrical Engineering")
DEFAULT_TOP_K = int(os.getenv("ANSWER_TOP_K", "5"))
MAX_CONTEXT_CHARS = int(os.getenv("ANSWER_MAX_CONTEXT_CHARS", "4000"))
DEFAULT_MODEL = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")


@lru_cache()
def _groq_client() -> Groq:
	api_key = os.getenv("GROQ_API_KEY")
	if not api_key:
		raise RuntimeError("GROQ_API_KEY environment variable not set")
	return Groq(api_key=api_key)


@lru_cache()
def _vector_store() -> PineconeVectorStore:
	index_name = os.getenv("PINECONE_INDEX_NAME", "exam-books")
	return PineconeVectorStore(index_name=index_name)


def _format_context(matches: Iterable[dict]) -> str:
	sections: List[str] = []
	total_chars = 0

	for idx, match in enumerate(matches, start=1):
		if isinstance(match, dict):
			metadata = match.get("metadata", {})
			score = match.get("score")
		else:
			metadata = getattr(match, "metadata", {}) or {}
			score = getattr(match, "score", None)
		text = metadata.get("text", "")
		if not text:
			continue

		remaining = MAX_CONTEXT_CHARS - total_chars
		if remaining <= 0:
			break

		chunk = text[:remaining]
		source = metadata.get("source", "Unknown")
		topic = metadata.get("topic", "")
		label = f"[Source {idx}: {source} | Topic: {topic}]"
		if score is not None:
			label += f" (score={score:.4f})"
		sections.append(f"{label}\n{chunk}")
		total_chars += len(chunk)

	if not sections:
		return ""

	return "RETRIEVED CONTEXT:\n\n" + "\n\n".join(sections)


def _retrieve_context(question_text: str, namespace: str, top_k: int) -> str:
	try:
		embeddings = embed_texts([question_text])
		if not embeddings:
			return ""
		store = _vector_store()
		results = store.query(
			vector=embeddings[0],
			top_k=top_k,
			namespace=namespace or DEFAULT_NAMESPACE,
			include_metadata=True,
		)
		if isinstance(results, dict):
			matches = results.get("matches", [])
		else:
			matches = getattr(results, "matches", [])
		return _format_context(matches)
	except Exception as exc:
		print(f"Error retrieving context: {exc}")
		return ""


def _build_prompt(question: Question, context: str) -> str:
	difficulty_guidance = {
		"Easy": "Provide a clear, concise answer with basic explanation.",
		"Medium": "Provide a detailed answer with step-by-step working if applicable.",
		"Hard": "Provide a comprehensive answer with deep analysis and multiple approaches if applicable.",
	}

	guidance = difficulty_guidance.get(question.difficulty, difficulty_guidance["Medium"])

	context_block = context if context else "NOTE: No context available from knowledge base."

	return (
		"You are an expert Electrical Engineering tutor preparing answers for GATE exam questions.\n\n"
		f"QUESTION:\n{question.question}\n\n"
		f"CONCEPT: {question.concept}\n"
		f"DIFFICULTY LEVEL: {question.difficulty}\n\n"
		"INSTRUCTIONS:\n"
		f"1. {guidance}\n"
		"2. Use the retrieved context below to support your answer.\n"
		"3. Show all calculations and reasoning.\n"
		"4. If numerical, include units and final boxed answer.\n"
		"5. Keep answer focused and exam-appropriate.\n\n"
		f"{context_block}\n\n"
		"ANSWER:"
	)


def _generate_answer(question: Question, namespace: str, model: str) -> AnswerItem:
	context = _retrieve_context(question.question, namespace, DEFAULT_TOP_K)
	prompt = _build_prompt(question, context)

	client = _groq_client()

	try:
		completion = client.chat.completions.create(
			model=model,
			max_tokens=2000,
			messages=[{"role": "user", "content": prompt}],
		)
		snippet = ""
		choices = getattr(completion, "choices", [])
		if choices:
			message = getattr(choices[0], "message", None)
			if message:
				snippet = getattr(message, "content", "")
		answer_text = snippet or "Unable to generate answer."
	except Exception as exc:
		print(f"Error generating answer: {exc}")
		answer_text = f"Error generating answer: {exc}"

	return AnswerItem(
		concept=question.concept,
		difficulty=question.difficulty,
		question=question.question,
		answer=answer_text,
		context_retrieved=bool(context),
	)


def generate_answers(questions: List[Question], namespace: str | None = None, model: str | None = None) -> List[AnswerItem]:
	if not questions:
		return []

	target_namespace = namespace.strip() if isinstance(namespace, str) else None
	if not target_namespace:
		target_namespace = DEFAULT_NAMESPACE

	target_model = (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL

	results: List[AnswerItem] = []
	for question in questions:
		results.append(_generate_answer(question, target_namespace, target_model))
	return results
