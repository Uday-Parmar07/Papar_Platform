from functools import lru_cache
from typing import List, Optional
import re
import unicodedata
import hashlib
import json
import random
from pathlib import Path
from difflib import SequenceMatcher

from app.schemas.exam import GenerateExamResponse, Question
from app.llm.graph_flow import build_graph
from app.llm.paper_planner import build_paper_blueprint
from app.llm.nodes.generate import generate_question
from app.graph.queries import (
	list_subjects,
	list_topics_for_subject,
	resolve_subject_label,
	get_reference_question_for_concept,
	get_reference_question_by_text_match,
	get_reference_question_pool,
)


@lru_cache()
def _compiled_graph():
	return build_graph()


HASH_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "generated_question_hashes.jsonl"


def _clean_concept(concept: str) -> str:
	text = (concept or "").strip()
	text = unicodedata.normalize("NFKC", text)
	text = text.replace("−", "-").replace("–", "-").replace("—", "-").replace("‐", "-")
	text = re.sub(r"\([^)]*$", "", text)
	text = re.sub(r"\s+", " ", text)
	text = re.sub(r"^[^A-Za-z0-9]+", "", text)
	text = re.sub(r"^(of|and|the)\s+", "", text, flags=re.IGNORECASE)
	text = re.sub(r"\b(with|and|or)\b\s*$", "", text, flags=re.IGNORECASE)
	text = text.strip(" .,:;-/")
	return text or "core topic"


def _is_specific_concept(concept: str) -> bool:
	value = _clean_concept(concept).lower()
	if not value or value == "core topic":
		return False

	generic_terms = {
		"performance",
		"characteristics",
		"analysis",
		"matrix",
		"vector",
		"connections",
		"groups",
		"system",
		"model",
		"models",
		"theory",
		"principle",
		"control",
	}

	generic_phrases = [
		"principle of operation",
		"mode of operation",
		"types of losses",
		"steady-state analysis",
	]
	if any(phrase in value for phrase in generic_phrases):
		return False

	tokens = [tok for tok in re.split(r"\W+", value) if tok]
	if len(tokens) == 1 and tokens[0] in generic_terms:
		return False

	if len(value) < 5:
		return False

	return True


def _normalize_concept(concept: str, selected_topics: Optional[List[str]] = None) -> str:
	cleaned = _clean_concept(concept)
	if _is_specific_concept(cleaned):
		return cleaned

	for topic in selected_topics or []:
		topic_clean = _clean_concept(topic)
		if _is_specific_concept(topic_clean):
			return topic_clean

	return "core topic"




def _clean_question_text(text: str) -> str:
	clean = (text or "").strip()
	if not clean:
		return ""

	# Normalize full-width/math-styled unicode to plain text where possible.
	clean = unicodedata.normalize("NFKC", clean)

	# Drop common PDF footer/header artifacts.
	clean = re.sub(r"\b[A-Z]{2,}\d?\s+Page\s+\d+\s+of\s+\d+\b", " ", clean, flags=re.IGNORECASE)
	clean = re.sub(r"\bOrganizing Institute\s*:\s*[^.\n]+", " ", clean, flags=re.IGNORECASE)

	# Replace problematic dash symbols and remove replacement-char noise.
	clean = clean.replace("−", "-").replace("–", "-").replace("—", "-")
	clean = clean.replace("…", "...")
	clean = clean.replace("�", " ")

	# Remove control characters and invisible separators.
	clean = "".join(ch if ch.isprintable() else " " for ch in clean)

	# Remove leading numbering markers.
	clean = re.sub(r"^(Q\.?\s*\d+\s*[:.)-]?|\d+\s*[:.)-])\s*", "", clean, flags=re.IGNORECASE)

	# Keep readable technical symbols while dropping random artifacts.
	clean = re.sub(r"[^A-Za-z0-9\s\.,;:!?%()\[\]{}+\-*/=<>_'\"\^]", " ", clean)

	# Collapse repeated whitespace and duplicate adjacent lines.
	parts = [part.strip() for part in re.split(r"[\n\r]+", clean) if part.strip()]
	collapsed_parts = []
	for part in parts:
		if not collapsed_parts or collapsed_parts[-1].lower() != part.lower():
			collapsed_parts.append(part)
	clean = " ".join(collapsed_parts)
	clean = re.sub(r"\s+", " ", clean).strip()

	# Prevent excessively long, noisy blobs from leaking to UI.
	if len(clean) > 320:
		clean = clean[:320].rstrip() + "..."

	return clean


def _is_placeholder_question(text: str) -> bool:
	value = (text or "").strip().lower()
	return "describe a question on" in value and "appropriate for" in value


def _normalized_text(value: str) -> str:
	return re.sub(r"\s+", " ", (value or "").strip().lower())


def _hash_text(value: str) -> str:
	return hashlib.sha256(_normalized_text(value).encode("utf-8")).hexdigest()


def _similarity(a: str, b: str) -> float:
	a_norm = _normalized_text(a)
	b_norm = _normalized_text(b)
	if not a_norm or not b_norm:
		return 0.0
	seq = SequenceMatcher(None, a_norm, b_norm).ratio()
	ta = set(tok for tok in re.split(r"\W+", a_norm) if len(tok) >= 3)
	tb = set(tok for tok in re.split(r"\W+", b_norm) if len(tok) >= 3)
	jac = (len(ta & tb) / len(ta | tb)) if (ta and tb) else 0.0
	return max(seq, jac)


def _load_generated_history(limit: int = 3000) -> List[dict]:
	if not HASH_STORE_PATH.exists():
		return []
	rows: List[dict] = []
	try:
		with HASH_STORE_PATH.open("r", encoding="utf-8") as handle:
			for line in handle:
				line = line.strip()
				if not line:
					continue
				try:
					rows.append(json.loads(line))
				except json.JSONDecodeError:
					continue
	except OSError:
		return []
	if len(rows) > limit:
		return rows[-limit:]
	return rows


def _append_generated_history(records: List[dict]) -> None:
	if not records:
		return
	HASH_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
	with HASH_STORE_PATH.open("a", encoding="utf-8") as handle:
		for record in records:
			handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _subject_aliases(subject_id: str, subject_label: str) -> List[str]:
	aliases: List[str] = []
	for value in [subject_id, subject_label, resolve_subject_label(subject_id)]:
		clean = (value or "").strip()
		if clean and clean not in aliases:
			aliases.append(clean)
	return aliases


def _get_reference_with_aliases(
	concept: str,
	subject_id: str,
	subject_label: str,
	cutoff_year: int,
	difficulty: str,
) -> Optional[dict]:
	for alias in _subject_aliases(subject_id, subject_label):
		reference = get_reference_question_for_concept(
			concept=concept,
			subject=alias,
			cutoff_year=cutoff_year,
			difficulty=difficulty,
		)
		if not reference:
			reference = get_reference_question_by_text_match(
				concept=concept,
				subject=alias,
				cutoff_year=cutoff_year,
				difficulty=difficulty,
			)
		if reference and reference.get("text"):
			return reference
	return None


def _get_pool_with_aliases(
	subject_id: str,
	subject_label: str,
	topics_filter: Optional[List[str]],
	cutoff_year: int,
	limit: int,
) -> List[dict]:
	for alias in _subject_aliases(subject_id, subject_label):
		pool = get_reference_question_pool(
			subject=alias,
			topics=topics_filter,
			cutoff_year=cutoff_year,
			limit=limit,
		)
		if pool:
			return pool
	return []


def _extract_signal_tokens(value: str) -> List[str]:
	tokens = [tok for tok in re.split(r"\W+", (value or "").lower()) if len(tok) >= 5]
	seen = set()
	ordered: List[str] = []
	for token in tokens:
		if token in seen:
			continue
		seen.add(token)
		ordered.append(token)
	return ordered


def _matches_selected_topics(text: str, selected_topics: Optional[List[str]]) -> bool:
	if not selected_topics:
		return True
	lower = (text or "").lower()
	topic_tokens: List[str] = []
	for topic in selected_topics:
		topic_tokens.extend(_extract_signal_tokens(topic))
	topic_tokens = [tok for tok in topic_tokens if tok not in {"engineering", "systems"}]
	if not topic_tokens:
		return True
	return any(tok in lower for tok in topic_tokens)


def _is_usable_question(
	question_text: str,
	subject_label: str,
	concept: Optional[str] = None,
	selected_topics: Optional[List[str]] = None,
) -> bool:
	text = _clean_question_text(question_text)
	if not text:
		return False

	if _is_placeholder_question(text):
		return False

	if len(text) < 40:
		return False

	if len(re.findall(r"\b\w+\b", text)) < 7:
		return False

	lower = text.lower()
	bad_patterns = [
		r"appropriate for",
		r"based on (the )?provided context",
		r"this question (tests|assesses)",
		r"lorem ipsum",
		r"\bplaceholder\b",
		r"\bgenerate(d)?\b.*\bquestion\b",
	]
	if any(re.search(pattern, lower) for pattern in bad_patterns):
		return False

	alpha_count = len(re.findall(r"[A-Za-z]", text))
	if alpha_count / max(len(text), 1) < 0.55:
		return False

	if not _question_matches_subject(text, subject_label):
		return False

	if not _matches_selected_topics(text, selected_topics):
		return False

	return True


def _is_minimally_acceptable_question(
	question_text: str,
	subject_label: str,
	concept: Optional[str] = None,
	selected_topics: Optional[List[str]] = None,
) -> bool:
	text = _clean_question_text(question_text)
	if not text:
		return False
	if _is_placeholder_question(text):
		return False
	if len(text) < 28:
		return False
	if not _question_matches_subject(text, subject_label):
		return False
	if not _matches_selected_topics(text, selected_topics):
		return False
	return True


def _pick_from_pool(pool: List[dict], difficulty: str) -> Optional[dict]:
	if not pool:
		return None

	target = (difficulty or "").strip().lower()
	for idx, item in enumerate(pool):
		level = str(item.get("difficulty", "")).strip().lower()
		if level == target:
			return pool.pop(idx)

	return pool.pop(0)


def _pick_valid_from_pool(
	pool: List[dict],
	difficulty: str,
	subject_label: str,
	selected_topics: Optional[List[str]] = None,
) -> Optional[dict]:
	while pool:
		item = _pick_from_pool(pool, difficulty)
		if not item:
			return None
		text = _clean_question_text(item.get("text", ""))
		if not _is_usable_question(
			text,
			subject_label=subject_label,
			concept=item.get("concept"),
			selected_topics=selected_topics,
		):
			continue
		item["text"] = text
		return item
	return None


def _pick_minimal_from_pool(
	pool: List[dict],
	difficulty: str,
	subject_label: str,
	selected_topics: Optional[List[str]] = None,
) -> Optional[dict]:
	while pool:
		item = _pick_from_pool(pool, difficulty)
		if not item:
			return None
		text = _clean_question_text(item.get("text", ""))
		if not _is_minimally_acceptable_question(
			text,
			subject_label=subject_label,
			concept=item.get("concept"),
			selected_topics=selected_topics,
		):
			continue
		item["text"] = text
		return item
	return None


def _question_matches_subject(question_text: str, subject_label: str) -> bool:
	text = (question_text or "").lower()
	subject = (subject_label or "").lower()

	branch_signatures = {
		"electrical engineering": {
			"allow": ["electrical engineering", "(ee)", "(ee)", " ee ", "electrical engineering (ee)"],
			"block": [
				"civil engineering", "chemical engineering", "mechanical engineering", "metallurgical engineering", "computer science",
				"(ce)", "(ce1)", "(ce2)", " ce ", "(ch)", " ch ", "(me)", " me ", "(mt)", " mt ", "(cs)", " cs ", "(ec)", " ec ",
			],
		},
		"civil engineering": {
			"allow": ["civil engineering", "(ce)", " ce ", "civil engineering (ce)"],
			"block": ["electrical engineering", "mechanical engineering", "chemical engineering", "metallurgical engineering", "computer science", "(ee)", " ee "],
		},
		"mechanical engineering": {
			"allow": ["mechanical engineering", "(me)", " me ", "mechanical engineering (me)"],
			"block": ["electrical engineering", "civil engineering", "chemical engineering", "metallurgical engineering", "computer science", "(ee)", " ee ", "(ce)", " ce "],
		},
	}

	for key, sig in branch_signatures.items():
		if key in subject:
			if any(token in text for token in sig["block"]):
				return False
			if re.search(r"\((ee|ce|me|ch|cs|ec|mt)\d?\)", text):
				if not any(token in text for token in sig["allow"]):
					return False
			if re.search(r"\b(civil|mechanical|chemical|metallurgical|computer science|electronics and communication|electrical)\b", text):
				if not any(token in text for token in sig["allow"]):
					return False
			return True

	return True


def _question_from_blueprint_item(
	item,
	subject_id: str,
	subject_label: str,
	cutoff_year: int,
	selected_topics: Optional[List[str]] = None,
) -> Optional[Question]:
	concept = _normalize_concept(getattr(item, "concept", "Unknown concept"), selected_topics)
	difficulty = getattr(item, "difficulty", "Medium")

	reference = get_reference_question_for_concept(
		concept=concept,
		subject=subject_id,
		cutoff_year=cutoff_year,
		difficulty=difficulty,
	)
	if not reference:
		reference = _get_reference_with_aliases(concept, subject_id, subject_label, cutoff_year, difficulty)
	if reference and reference.get("text"):
		prompt = _clean_question_text(reference["text"])
		if _is_minimally_acceptable_question(prompt, subject_label=subject_label, concept=concept):
			return Question(concept=concept, difficulty=difficulty, question=prompt)

	return None


def _llm_question_from_blueprint_item(
	item,
	subject_id: str,
	subject_label: str,
	selected_topics: Optional[List[str]],
	existing_questions: Optional[List[Question]] = None,
) -> Optional[Question]:
	concept = _normalize_concept(getattr(item, "concept", "Unknown concept"), selected_topics)
	difficulty = (getattr(item, "difficulty", "Medium") or "Medium").title()
	batch = [{"question": q.question} for q in (existing_questions or [])]
	try:
		generated = generate_question(
			concept=concept,
			difficulty=difficulty,
			subject=subject_label,
			topics=selected_topics,
			existing_questions=batch,
			subject_id=subject_id,
		)
	except Exception:
		return None

	question_text = _clean_question_text(generated.get("question", ""))
	if not _is_minimally_acceptable_question(question_text, subject_label, concept, selected_topics):
		return None

	return Question(concept=concept, difficulty=difficulty, question=question_text)


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
	question_pool = _get_pool_with_aliases(
		subject_id=subject_id,
		subject_label=subject_label,
		topics_filter=topics_filter,
		cutoff_year=cutoff_year,
		limit=max(total_questions * 4, 40),
	)
	if question_pool:
		random.shuffle(question_pool)
	raw_question_pool = list(question_pool)

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
			concept = _normalize_concept(item.get("concept", ""), selected_topics)
			difficulty = (item.get("difficulty", "") or "Medium").strip().title()
			question_text = _clean_question_text((item.get("question", "") or "").strip())

			reference = _get_reference_with_aliases(concept, subject_id, subject_label, cutoff_year, difficulty)
			if reference and reference.get("text"):
				candidate_ref = _clean_question_text(reference["text"])
				if _is_usable_question(candidate_ref, subject_label, concept, selected_topics):
					question_text = candidate_ref

			if not _is_usable_question(question_text, subject_label, concept, selected_topics):
				pool_item = _pick_valid_from_pool(question_pool, difficulty, subject_label, selected_topics)
				if pool_item and pool_item.get("text"):
					question_text = pool_item["text"]

			if not _is_usable_question(question_text, subject_label, concept, selected_topics):
				continue

			questions.append(
				Question(
					concept=concept,
					difficulty=difficulty,
					question=question_text,
				)
			)

	if not questions:
		for item in blueprint.questions:
			difficulty = getattr(item, "difficulty", "Medium")
			pool_item = _pick_minimal_from_pool(question_pool, difficulty, subject_label, selected_topics)
			if pool_item and pool_item.get("text"):
				questions.append(
					Question(
						concept=_normalize_concept(pool_item.get("concept") or getattr(item, "concept", ""), selected_topics),
						difficulty=(pool_item.get("difficulty") or difficulty).title(),
						question=pool_item["text"],
					)
				)
			else:
				candidate = _question_from_blueprint_item(item, subject_id, subject_label, cutoff_year, selected_topics)
				if not candidate:
					candidate = _llm_question_from_blueprint_item(item, subject_id, subject_label, selected_topics, questions)
				if candidate:
					questions.append(candidate)

	# Remove near-duplicate questions so repeated text does not appear in output.
	all_candidates = list(questions)
	unique_questions: List[Question] = []
	seen_signatures = set()
	history = _load_generated_history()
	history_texts = [entry.get("question", "") for entry in history if entry.get("question")]
	for question in questions:
		cleaned = _clean_question_text(question.question)
		if not _is_usable_question(cleaned, subject_label, question.concept, selected_topics):
			continue
		question.question = cleaned
		signature = re.sub(r"\s+", " ", question.question.lower()).strip()
		if signature in seen_signatures:
			continue
		if any(_similarity(question.question, prior) >= 0.86 for prior in history_texts):
			continue
		seen_signatures.add(signature)
		unique_questions.append(question)

	questions = unique_questions

	if not questions and all_candidates:
		# If history pruning is too aggressive, keep unique in-run candidates instead of returning empty output.
		seen_signatures = set()
		for question in all_candidates:
			cleaned = _clean_question_text(question.question)
			if not _is_minimally_acceptable_question(cleaned, subject_label, question.concept, selected_topics):
				continue
			question.question = cleaned
			signature = re.sub(r"\s+", " ", question.question.lower()).strip()
			if signature in seen_signatures:
				continue
			seen_signatures.add(signature)
			questions.append(question)

	if len(questions) < total_questions:
		for item in blueprint.questions:
			if len(questions) >= total_questions:
				break
			difficulty = getattr(item, "difficulty", "Medium")
			pool_item = _pick_minimal_from_pool(question_pool, difficulty, subject_label, selected_topics)
			if pool_item and pool_item.get("text"):
				candidate = Question(
					concept=_normalize_concept(pool_item.get("concept") or getattr(item, "concept", ""), selected_topics),
					difficulty=(pool_item.get("difficulty") or difficulty).title(),
					question=_clean_question_text(pool_item["text"]),
				)
			else:
				candidate = _question_from_blueprint_item(item, subject_id, subject_label, cutoff_year, selected_topics)
				if not candidate:
					candidate = _llm_question_from_blueprint_item(item, subject_id, subject_label, selected_topics, questions)
				if not candidate:
					continue

			if not _is_usable_question(candidate.question, subject_label, candidate.concept, selected_topics):
				continue
			signature = re.sub(r"\s+", " ", candidate.question.lower()).strip()
			if signature in seen_signatures:
				continue
			if any(_similarity(candidate.question, prior) >= 0.86 for prior in history_texts):
				continue
			seen_signatures.add(signature)
			questions.append(candidate)

	if len(questions) < total_questions and selected_topics:
		difficulty_cycle = ["Easy", "Medium", "Hard"]
		for idx in range(total_questions * 3):
			if len(questions) >= total_questions:
				break
			topic = selected_topics[idx % len(selected_topics)]
			difficulty = difficulty_cycle[idx % len(difficulty_cycle)]
			try:
				gen = generate_question(
					concept=_normalize_concept(topic, selected_topics),
					difficulty=difficulty,
					subject=subject_label,
					topics=selected_topics,
					existing_questions=[{"question": q.question} for q in questions],
					subject_id=subject_id,
				)
			except Exception:
				continue

			candidate = Question(
				concept=_normalize_concept(gen.get("concept", topic), selected_topics),
				difficulty=(gen.get("difficulty") or difficulty).title(),
				question=_clean_question_text(gen.get("question", "")),
			)
			if not _is_minimally_acceptable_question(candidate.question, subject_label, candidate.concept, selected_topics):
				continue
			signature = re.sub(r"\s+", " ", candidate.question.lower()).strip()
			if signature in seen_signatures:
				continue
			if any(_similarity(candidate.question, prior) >= 0.90 for prior in history_texts):
				continue
			seen_signatures.add(signature)
			questions.append(candidate)

	if not questions and raw_question_pool:
		random.shuffle(raw_question_pool)
		seen = set()
		for item in raw_question_pool:
			if len(questions) >= total_questions:
				break
			text = _clean_question_text(item.get("text", ""))
			if not text or _is_placeholder_question(text):
				continue
			if not _matches_selected_topics(text, selected_topics):
				continue
			if not _question_matches_subject(text, subject_label):
				continue
			if any(_similarity(text, prior) >= 0.92 for prior in history_texts):
				continue
			sig = re.sub(r"\s+", " ", text.lower()).strip()
			if sig in seen:
				continue
			seen.add(sig)
			questions.append(
				Question(
					concept=_normalize_concept(item.get("concept", ""), selected_topics),
					difficulty=(item.get("difficulty") or "Medium").title(),
					question=text,
				)
			)

	if len(questions) < total_questions:
		while question_pool and len(questions) < total_questions:
			pool_item = _pick_minimal_from_pool(question_pool, "Medium", subject_label, selected_topics)
			if not pool_item or not pool_item.get("text"):
				break
			candidate = Question(
				concept=_normalize_concept(pool_item.get("concept", ""), selected_topics),
				difficulty=(pool_item.get("difficulty") or "Medium").title(),
				question=_clean_question_text(pool_item["text"]),
			)
			signature = re.sub(r"\s+", " ", candidate.question.lower()).strip()
			if signature in seen_signatures:
				continue
			if any(_similarity(candidate.question, prior) >= 0.86 for prior in history_texts):
				continue
			seen_signatures.add(signature)
			questions.append(candidate)

	if len(questions) < total_questions:
		for item in blueprint.questions:
			if len(questions) >= total_questions:
				break
			candidate = _llm_question_from_blueprint_item(item, subject_id, subject_label, selected_topics, questions)
			if not candidate:
				continue
			signature = re.sub(r"\s+", " ", candidate.question.lower()).strip()
			if signature in seen_signatures:
				continue
			if any(_similarity(candidate.question, prior) >= 0.90 for prior in history_texts):
				continue
			seen_signatures.add(signature)
			questions.append(candidate)

	# Last non-template safety net: allow minimally acceptable LLM/pool phrasing if strict validator is too restrictive.
	if len(questions) < total_questions:
		for item in generated_questions:
			if len(questions) >= total_questions:
				break
			candidate = Question(
				concept=_normalize_concept(item.get("concept", ""), selected_topics),
				difficulty=(item.get("difficulty") or "Medium").title(),
				question=_clean_question_text(item.get("question", "")),
			)
			if not _is_minimally_acceptable_question(candidate.question, subject_label, candidate.concept, selected_topics):
				continue
			signature = re.sub(r"\s+", " ", candidate.question.lower()).strip()
			if signature in seen_signatures:
				continue
			if any(_similarity(candidate.question, prior) >= 0.90 for prior in history_texts):
				continue
			seen_signatures.add(signature)
			questions.append(candidate)

	# Final hard fallback: ensure the API never returns an empty paper.
	if not questions:
		fallback_topics = selected_topics or [subject_label]
		for idx in range(total_questions):
			topic = fallback_topics[idx % len(fallback_topics)]
			questions.append(
				Question(
					concept=_normalize_concept(topic, selected_topics),
					difficulty="Medium",
					question=(
						f"For {subject_label}, explain the core principles of {topic}, derive the governing relation, "
						"and solve one representative exam-level problem with clear assumptions and final result."
					),
				)
			)

	_append_generated_history(
		[
			{
				"hash": _hash_text(q.question),
				"question": q.question,
				"concept": q.concept,
				"difficulty": q.difficulty,
				"subject": subject_id,
			}
			for q in questions
		]
	)

	return GenerateExamResponse(
		total_questions=len(questions),
		distribution=distribution,
		questions=questions,
		subject_id=subject_id,
		subject_name=subject_label,
		topics=selected_topics,
	)
