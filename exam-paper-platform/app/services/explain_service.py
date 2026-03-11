import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from groq import Groq
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.user import ExplanationCache, User
from app.schemas.explain import ExplainQuestionRequest


PROMPT_TEMPLATE = """You are an engineering professor explaining an exam question.

Explain the following question step-by-step.

Question: {question}
Topic: {topic}
Difficulty: {difficulty}

Provide JSON with keys:
concept, formula, steps, answer, exam_tip"""


def _cache_key(payload: ExplainQuestionRequest) -> str:
    content = f"{payload.question.strip()}|{payload.topic.strip()}|{payload.difficulty.strip().lower()}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _default_explanation(payload: ExplainQuestionRequest) -> dict[str, str]:
    return {
        "concept": f"This question belongs to {payload.topic} and tests foundational engineering reasoning.",
        "formula": "Use the governing equation from the topic definition and identify all known variables before substitution.",
        "steps": "1) Parse the givens from the question. 2) Select the governing relation. 3) Substitute values carefully with units. 4) Simplify and validate dimensions.",
        "answer": "Derive the final numerical or conceptual result after applying the governing equation.",
        "exam_tip": "Write assumptions first, keep units consistent, and box the final result for faster grading.",
    }


def _generate_llm_explanation(payload: ExplainQuestionRequest) -> dict[str, str]:
    settings = get_settings()
    if not settings.groq_api_key:
        return _default_explanation(payload)

    client = Groq(api_key=settings.groq_api_key)
    completion = client.chat.completions.create(
        model=settings.explanation_model,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    question=payload.question,
                    topic=payload.topic,
                    difficulty=payload.difficulty,
                ),
            }
        ],
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content if completion.choices else "{}"

    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return _default_explanation(payload)

    response: dict[str, Any] = {
        "concept": str(data.get("concept", "")).strip(),
        "formula": str(data.get("formula", "")).strip(),
        "steps": str(data.get("steps", "")).strip(),
        "answer": str(data.get("answer", "")).strip(),
        "exam_tip": str(data.get("exam_tip", "")).strip(),
    }

    if not all(response.values()):
        return _default_explanation(payload)
    return response


def explain_question(db: Session, user: User, payload: ExplainQuestionRequest) -> dict[str, Any]:
    key = _cache_key(payload)
    existing = db.scalar(
        select(ExplanationCache).where(
            ExplanationCache.user_id == user.id,
            ExplanationCache.cache_key == key,
        )
    )
    if existing:
        return {
            "concept": existing.concept,
            "formula": existing.formula,
            "steps": existing.steps,
            "answer": existing.answer,
            "exam_tip": existing.exam_tip,
            "cached": True,
            "created_at": existing.created_at,
        }

    generated = _generate_llm_explanation(payload)
    record = ExplanationCache(
        user_id=user.id,
        cache_key=key,
        question=payload.question,
        topic=payload.topic,
        difficulty=payload.difficulty,
        concept=generated["concept"],
        formula=generated["formula"],
        steps=generated["steps"],
        answer=generated["answer"],
        exam_tip=generated["exam_tip"],
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "concept": record.concept,
        "formula": record.formula,
        "steps": record.steps,
        "answer": record.answer,
        "exam_tip": record.exam_tip,
        "cached": False,
        "created_at": record.created_at,
    }
