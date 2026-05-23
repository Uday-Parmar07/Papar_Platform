from typing import Dict, List, Optional
from groq import Groq
import os
import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from dotenv import load_dotenv

from app.graph.queries import get_generation_context

# -----------------------------
# Groq client
# -----------------------------

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# Llama 70B generation controls.
MODEL_NAME = "llama-3.3-70b-versatile"
MODEL_TEMPERATURE = 0.72
MODEL_TOP_P = 0.95
MODEL_MAX_TOKENS = 280
MODEL_FREQUENCY_PENALTY = 0.35
MODEL_PRESENCE_PENALTY = 0.2

# -----------------------------
# Difficulty rules
# -----------------------------

DIFFICULTY_GUIDELINES = {
    "Easy": (
        "Single-step conceptual recall or simple numeric substitution. "
        "Provide one clear data point or condition so the question is answerable."
    ),
    "Medium": (
        "Incorporate 2–3 reasoning steps, blending theory with calculation or reasoning. "
        "State any required assumptions explicitly."
    ),
    "Hard": (
        "Require multi-step reasoning or analysis of interacting phenomena. "
        "Include realistic parameter values and constraints to guide problem solving."
    )
}

QUESTION_STYLES = [
    "conceptual",
    "numerical",
    "application-based",
    "analytical",
]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEBUG_LOG_PATH = PROJECT_ROOT / "data" / "llm_debug.jsonl"
HASH_STORE_PATH = PROJECT_ROOT / "data" / "generated_question_hashes.jsonl"

# -----------------------------
# Prompt builder
# -----------------------------

def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _hash_text(value: str) -> str:
    return hashlib.sha256(_normalize_text(value).encode("utf-8")).hexdigest()


def _token_set(value: str) -> set[str]:
    return set(tok for tok in re.split(r"\W+", _normalize_text(value)) if len(tok) > 2)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()
    ta = _token_set(a)
    tb = _token_set(b)
    jaccard = (len(ta & tb) / len(ta | tb)) if (ta and tb) else 0.0
    return max(ratio, jaccard)


def _load_hash_memory() -> List[dict]:
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
    return rows


def _append_hash_memory(record: dict) -> None:
    HASH_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HASH_STORE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _debug_event(event: str, payload: dict) -> None:
    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {"event": event, **payload}
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _is_duplicate_candidate(question_text: str, in_batch: List[Dict], threshold: float = 0.82) -> bool:
    q_hash = _hash_text(question_text)

    for item in _load_hash_memory():
        prior_text = item.get("question", "")
        if not prior_text:
            continue
        if item.get("hash") == q_hash:
            return True
        if _similarity(question_text, prior_text) >= threshold:
            return True

    for item in in_batch:
        prior_text = item.get("question", "")
        if not prior_text:
            continue
        if _hash_text(prior_text) == q_hash:
            return True
        if _similarity(question_text, prior_text) >= threshold:
            return True

    return False


def _language_signals(prior_questions: List[dict]) -> dict:
    stems: List[str] = []
    technical_tokens: List[str] = []

    for row in prior_questions[:6]:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        stem = " ".join(text.split()[:8])
        if stem and stem not in stems:
            stems.append(stem)

        for tok in re.split(r"\W+", text.lower()):
            if len(tok) >= 6 and tok not in technical_tokens:
                technical_tokens.append(tok)
            if len(technical_tokens) >= 18:
                break

    return {
        "sample_openings": stems[:4],
        "technical_vocabulary": technical_tokens[:18],
    }


def build_prompt(
    concept: str,
    difficulty: str,
    subject: str,
    style: str,
    context: dict,
    topics: Optional[List[str]] = None,
) -> str:
    subject_label = subject or "Engineering"
    if topics:
        joined = ", ".join(sorted(set(topics)))
        topics_line = f"- Focus only on topics drawn from: {joined}."
    else:
        topics_line = ""

    prior_questions = context.get("prior_questions", [])
    language_signals = _language_signals(prior_questions)
    context_blob = {
        "source": context.get("source", "fallback"),
        "concept": context.get("concept", concept),
        "topics": context.get("topics", topics or []),
        "prerequisites": context.get("prerequisites", []),
        "dependent_concepts": context.get("dependent_concepts", []),
        "similar_concepts": context.get("similar_concepts", []),
        "prior_questions": [
            {
                "year": row.get("year"),
                "difficulty": row.get("difficulty"),
                "text": (row.get("text", "")[:220] + "...") if len(row.get("text", "")) > 220 else row.get("text", ""),
            }
            for row in prior_questions
        ],
        "language_signals": language_signals,
    }

    return f"""
SYSTEM:
You generate high-quality engineering exam questions.

CONTEXT FROM NEO4J:
{json.dumps(context_blob, ensure_ascii=True)}

TOPIC:
{', '.join(topics or context.get('topics', [])) or 'General ' + subject_label}

CONCEPTS:
{concept}

TASK:
Generate ONE exam-quality GATE {subject_label} question.

CONSTRAINTS:
- Concept: {concept}
- Difficulty: {difficulty}
- Style: {style}
- {DIFFICULTY_GUIDELINES[difficulty]}
- Syllabus strictly limited to {subject_label} (GATE level)
{topics_line}
- Follow the language register of retrieved prior questions (terminology density, technical phrasing, exam tone).
- Use retrieved vocabulary naturally, but do not copy any prior question sentence.
- Keep sentence openings varied; do not reuse repetitive templates.
- Target length: 45-120 words. Provide enough context, numeric values, and conditions so the question is self-contained.
- Avoid duplicates with previously asked/generated wording; use fresh phrasing and structure.
- Do NOT include solution
- Do NOT include explanation
- Do NOT include multiple questions
- Do NOT mention marks explicitly
- Use standard GATE exam language

STRUCTURE:
- Begin with a concise scenario or set of givens before the actual interrogative.
- End with a single question sentence.
- Avoid bullet lists; write as a short paragraph.

OUTPUT:
Return ONLY the question text.

QUESTION:
""".strip()

# -----------------------------
# Question generation
# -----------------------------

def generate_question(
    concept: str,
    difficulty: str,
    subject: str,
    topics: Optional[List[str]] = None,
    existing_questions: Optional[List[Dict]] = None,
    subject_id: Optional[str] = None,
) -> Dict:
    existing_questions = existing_questions or []
    style_seed = (len(existing_questions) + len(concept)) % len(QUESTION_STYLES)

    context = get_generation_context(
        concept=concept,
        subject=subject_id or subject,
        topics=topics,
        difficulty=difficulty,
        limit=5,
    )
    _debug_event(
        "neo4j_context",
        {
            "subject": subject,
            "concept": concept,
            "difficulty": difficulty,
            "source": context.get("source"),
            "context": context,
        },
    )

    attempts = 3
    final_question = ""
    final_style = QUESTION_STYLES[style_seed]
    for attempt in range(attempts):
        style = QUESTION_STYLES[(style_seed + attempt) % len(QUESTION_STYLES)]
        prompt = build_prompt(concept, difficulty, subject, style=style, context=context, topics=topics)

        _debug_event(
            "llm_prompt",
            {
                "subject": subject,
                "concept": concept,
                "difficulty": difficulty,
                "style": style,
                "prompt": prompt,
            },
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a strict GATE {subject or 'Engineering'} examiner.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=MODEL_TEMPERATURE,
            max_tokens=MODEL_MAX_TOKENS,
            top_p=MODEL_TOP_P,
            frequency_penalty=MODEL_FREQUENCY_PENALTY,
            presence_penalty=MODEL_PRESENCE_PENALTY,
        )

        question_text = response.choices[0].message.content.strip()
        _debug_event(
            "llm_output",
            {
                "subject": subject,
                "concept": concept,
                "difficulty": difficulty,
                "style": style,
                "question": question_text,
            },
        )

        final_question = question_text
        final_style = style
        if not _is_duplicate_candidate(question_text, existing_questions):
            break

    record = {
        "hash": _hash_text(final_question),
        "question": final_question,
        "concept": concept,
        "difficulty": difficulty,
        "subject": subject,
        "style": final_style,
    }
    _append_hash_memory(record)

    return {
        "concept": concept,
        "difficulty": difficulty,
        "question": final_question,
        "style": final_style,
        "year_similarity": context.get("prior_questions", [{}])[0].get("year") if context.get("prior_questions") else None,
        "neo4j_context_source": context.get("source"),
    }
