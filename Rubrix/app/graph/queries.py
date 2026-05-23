import json
import logging
import random
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

from neomodel import config, db
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable

try:
    from app.utils.neo4j import resolve_neo4j_url
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from app.utils.neo4j import resolve_neo4j_url

try:
    config.DATABASE_URL = resolve_neo4j_url()
except ValueError as exc:
    raise RuntimeError(f"Neo4j configuration error: {exc}") from exc


SUBJECT_LABELS = {
    "CE 2026": "Civil Engineering",
    "CH 2026": "Chemical Engineering",
    "CS 2026": "Computer Science Engineering",
    "EC 2026": "Electronics and Communication Engineering",
    "EE 2026": "Electrical Engineering",
    "Electrical Engineering": "Electrical Engineering",
    "ME 2026": "Mechanical Engineering",
    "MT 2026": "Metallurgical Engineering",
}

SUBJECT_PRIORITY = {
    "CE 2026": 0,
    "CH 2026": 0,
    "CS 2026": 0,
    "EC 2026": 0,
    "EE 2026": 0,
    "ME 2026": 0,
    "MT 2026": 0,
    "Electrical Engineering": 1,
}

logger = logging.getLogger(__name__)


SUBJECT_MARKERS = {
    "EE 2026": {
        "allow": ["(ee)", "electrical engineering (ee)", " ee)"],
        "block": ["(ce)", "(ce1)", "(ce2)", "(me)", "(ch)", "(mt)", "(cs)", "(ec)", "civil engineering", "mechanical engineering", "chemical engineering", "metallurgical engineering"],
    },
    "CE 2026": {
        "allow": ["(ce)", "(ce1)", "(ce2)", "civil engineering (ce)"],
        "block": ["(ee)", "(me)", "(ch)", "(mt)", "(cs)", "(ec)", "electrical engineering", "mechanical engineering", "chemical engineering", "metallurgical engineering"],
    },
    "ME 2026": {
        "allow": ["(me)", "mechanical engineering (me)"],
        "block": ["(ee)", "(ce)", "(ch)", "(mt)", "(cs)", "(ec)", "electrical engineering", "civil engineering", "chemical engineering", "metallurgical engineering"],
    },
    "CH 2026": {
        "allow": ["(ch)", "chemical engineering (ch)"],
        "block": ["(ee)", "(ce)", "(me)", "(mt)", "(cs)", "(ec)", "electrical engineering", "civil engineering", "mechanical engineering", "metallurgical engineering"],
    },
    "MT 2026": {
        "allow": ["(mt)", "metallurgical engineering (mt)"],
        "block": ["(ee)", "(ce)", "(me)", "(ch)", "(cs)", "(ec)", "electrical engineering", "civil engineering", "mechanical engineering", "chemical engineering"],
    },
    "CS 2026": {
        "allow": ["(cs)", "computer science"],
        "block": ["(ee)", "(ce)", "(me)", "(ch)", "(mt)", "(ec)", "electrical engineering", "civil engineering", "mechanical engineering", "chemical engineering", "metallurgical engineering"],
    },
    "EC 2026": {
        "allow": ["(ec)", "electronics and communication"],
        "block": ["(ee)", "(ce)", "(me)", "(ch)", "(mt)", "(cs)", "civil engineering", "mechanical engineering", "chemical engineering", "metallurgical engineering"],
    },
}


def _subject_marker_filters(subject: str) -> tuple[list[str], list[str]]:
    marker = SUBJECT_MARKERS.get(subject)
    if not marker:
        return [], []
    return marker["allow"], marker["block"]


def _safe_cypher_query(query: str, params: dict):
    try:
        logger.debug("Executing Cypher query", extra={"params": params, "query": query.strip()[:500]})
        results, meta = db.cypher_query(query, params)
        logger.debug("Cypher query completed", extra={"row_count": len(results)})
        return results, meta
    except (ServiceUnavailable, AuthError, Neo4jError, OSError) as exc:
        logger.warning("Neo4j unavailable; using fallback data. Error: %s", exc)
        return [], None


def resolve_subject_label(subject_id: str) -> str:
    return SUBJECT_LABELS.get(subject_id, subject_id)


def _unique_ordered(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


@lru_cache()
def _syllabus_index() -> dict[str, dict]:
    syllabus_dir = Path(__file__).resolve().parents[2] / "json_syllabus"
    index: dict[str, dict] = {}
    if not syllabus_dir.exists():
        return index

    for path in syllabus_dir.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            continue

        subject_id = payload.get("subject")
        if subject_id:
            index[subject_id] = payload

    return index


def _resolve_candidate_subjects(subject: str) -> List[str]:
    candidates = [subject]
    for subject_id, label in SUBJECT_LABELS.items():
        if subject_id == subject or label == subject:
            candidates.append(subject_id)
    return _unique_ordered(candidates)


def _topics_from_syllabus(subject: str) -> List[str]:
    syllabus = _syllabus_index().get(subject)
    if not syllabus:
        return []

    topics = [
        item.get("name")
        for item in syllabus.get("topics", [])
        if isinstance(item, dict) and item.get("name")
    ]
    return _unique_ordered(topics)


def _concepts_from_syllabus(subject: str, topics: Optional[List[str]] = None) -> List[str]:
    syllabus = _syllabus_index().get(subject)
    if not syllabus:
        return []

    normalized_topics = set(topics or [])
    concepts: List[str] = []

    for topic in syllabus.get("topics", []):
        if not isinstance(topic, dict):
            continue
        topic_name = topic.get("name")
        if normalized_topics and topic_name not in normalized_topics:
            continue

        for subtopic in topic.get("subtopics", []):
            if not isinstance(subtopic, dict):
                continue
            for concept in subtopic.get("concepts", []):
                if isinstance(concept, dict):
                    name = concept.get("name")
                else:
                    name = concept
                if name:
                    concepts.append(name)

    return _unique_ordered(concepts)


def list_subjects() -> List[dict]:
    query = """
    MATCH (s:Subject)
    RETURN s.name AS name
    ORDER BY name
    """
    results, _ = _safe_cypher_query(query, {})
    raw_names = [row[0] for row in results]
    unique = _unique_ordered(raw_names)

    preferred: dict[str, tuple[str, int]] = {}
    for name in unique:
        display = resolve_subject_label(name)
        priority = SUBJECT_PRIORITY.get(name, 100)
        current = preferred.get(display)
        if current is None or priority < current[1]:
            preferred[display] = (name, priority)

    subjects = [
        {"id": subject_id, "name": display}
        for display, (subject_id, _) in preferred.items()
    ]

    existing_ids = {item["id"] for item in subjects}
    for subject_id, label in SUBJECT_LABELS.items():
        if subject_id not in existing_ids:
            subjects.append({"id": subject_id, "name": label})
            existing_ids.add(subject_id)

    for subject_id in _syllabus_index().keys():
        if subject_id not in existing_ids:
            subjects.append({"id": subject_id, "name": resolve_subject_label(subject_id)})
            existing_ids.add(subject_id)

    subjects.sort(key=lambda item: item["name"].lower())
    return subjects


def list_topics_for_subject(subject: str) -> List[str]:
    query = """
    MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)
    RETURN DISTINCT t.name AS name
    ORDER BY name
    """
    results, _ = _safe_cypher_query(query, {"subject": subject})
    topics = [row[0] for row in results]
    if topics:
        return topics

    for candidate in _resolve_candidate_subjects(subject):
        fallback_topics = _topics_from_syllabus(candidate)
        if fallback_topics:
            return fallback_topics

    return []


def _apply_topic_condition(topics: Optional[List[str]]) -> str:
    if topics:
        return "WHERE t.name IN $topics\n"
    return ""


def _concept_fallback(subject: str | None, topics: Optional[List[str]], limit: int):
    if subject:
        base = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)
        {topic_condition}MATCH (t)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        RETURN DISTINCT c.name AS name
        ORDER BY rand()
        LIMIT $limit
        """
        query = base.replace("{topic_condition}", _apply_topic_condition(topics))
        params = {"subject": subject, "limit": limit}
        if topics:
            params["topics"] = topics
    else:
        query = """
        MATCH (c:Concept)
        RETURN c.name AS name
        ORDER BY rand()
        LIMIT $limit
        """
        params = {"limit": limit}

    fallback, _ = _safe_cypher_query(query, params)
    candidates = [row[0] for row in fallback]
    if candidates:
        return candidates

    syllabus_subjects: List[str]
    if subject:
        syllabus_subjects = _resolve_candidate_subjects(subject)
    else:
        syllabus_subjects = list(_syllabus_index().keys())

    for candidate in syllabus_subjects:
        concepts = _concepts_from_syllabus(candidate, topics)
        if concepts:
            if limit and len(concepts) > limit:
                concepts = random.sample(concepts, k=limit)
            return concepts

    return []

# -----------------------------
# GRAPH RAG RETRIEVAL QUERIES
# -----------------------------


def get_high_frequency_concepts(limit=10, subject: str | None = None, topics: Optional[List[str]] = None):
    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)
        {topic_condition}MATCH (t)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WITH DISTINCT c
        OPTIONAL MATCH (q:Question)-[:APPEARS_IN]->(c)
        WITH c, count(q) AS score
        WHERE score > 0
        RETURN c.name AS name, score
        ORDER BY score DESC
        LIMIT $limit
        """
        query = query.replace("{topic_condition}", _apply_topic_condition(topics))
        params = {"subject": subject, "limit": limit}
        if topics:
            params["topics"] = topics
    else:
        query = """
        MATCH (q:Question)-[:APPEARS_IN]->(c:Concept)
        RETURN c.name AS name, count(q) AS score
        ORDER BY score DESC
        LIMIT $limit
        """
        params = {"limit": limit}

    results, _ = _safe_cypher_query(query, params)
    concepts = [{"concept": row[0], "score": row[1]} for row in results]

    if concepts:
        return concepts

    fallback = _concept_fallback(subject, topics, limit)
    return [{"concept": name, "score": 0} for name in fallback]


def get_never_asked_concepts(limit=10, subject: str | None = None, topics: Optional[List[str]] = None):
    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)
        {topic_condition}MATCH (t)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WITH DISTINCT c
        OPTIONAL MATCH (q:Question)-[:APPEARS_IN]->(c)
        WITH c, count(q) AS appearances
        WHERE appearances = 0
        RETURN c.name AS name
        ORDER BY rand()
        LIMIT $limit
        """
        query = query.replace("{topic_condition}", _apply_topic_condition(topics))
        params = {"subject": subject, "limit": limit}
        if topics:
            params["topics"] = topics
    else:
        query = """
        MATCH (c:Concept)
        WHERE NOT EXISTS { MATCH (:Question)-[:APPEARS_IN]->(c) }
        RETURN c.name AS name
        ORDER BY rand()
        LIMIT $limit
        """
        params = {"limit": limit}

    results, _ = _safe_cypher_query(query, params)
    concepts = [{"concept": row[0]} for row in results]

    if concepts:
        return concepts

    fallback = _concept_fallback(subject, topics, limit)
    return [{"concept": name} for name in fallback]


def get_recency_gap_concepts(cutoff_year, limit=10, subject: str | None = None, topics: Optional[List[str]] = None):
    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)
        {topic_condition}MATCH (t)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WITH DISTINCT c
        MATCH (q:Question)-[:APPEARS_IN]->(c)
        WITH c, max(q.year) AS last_year
        WHERE last_year <= $cutoff
        RETURN c.name AS name, last_year
        ORDER BY last_year ASC
        LIMIT $limit
        """
        query = query.replace("{topic_condition}", _apply_topic_condition(topics))
        params = {"subject": subject, "cutoff": cutoff_year, "limit": limit}
        if topics:
            params["topics"] = topics
    else:
        query = """
        MATCH (q:Question)-[:APPEARS_IN]->(c:Concept)
        WITH c, max(q.year) AS last_year
        WHERE last_year <= $cutoff
        RETURN c.name AS name, last_year
        ORDER BY last_year ASC
        LIMIT $limit
        """
        params = {"cutoff": cutoff_year, "limit": limit}

    results, _ = _safe_cypher_query(query, params)
    concepts = [{"concept": row[0], "last_asked": row[1]} for row in results]

    if concepts:
        return concepts

    fallback = _concept_fallback(subject, topics, limit)
    return [{"concept": name, "last_asked": None} for name in fallback]



def get_prerequisite_heavy_concepts(limit=10):
    query = """
    MATCH (c:Concept)<-[:PREREQUISITE_OF]-(p:Concept)
    RETURN c.name AS name, count(p) AS prereq_count
    ORDER BY prereq_count DESC
    LIMIT $limit
    """
    results, _ = _safe_cypher_query(query, {"limit": limit})
    return [{"concept": r[0], "prereq_count": r[1]} for r in results]


def get_reference_question_for_concept(
    concept: str,
    subject: Optional[str] = None,
    cutoff_year: Optional[int] = None,
    difficulty: Optional[str] = None,
) -> Optional[dict]:
    allow_markers, block_markers = _subject_marker_filters(subject or "")
    params = {
        "concept": concept,
        "cutoff": cutoff_year,
        "difficulty": difficulty.lower() if difficulty else None,
        "allow_markers": allow_markers,
        "block_markers": block_markers,
    }

    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WHERE toLower(c.name) = toLower($concept)
        MATCH (q:Question)-[:APPEARS_IN]->(c)
                WHERE ($cutoff IS NULL OR q.year <= $cutoff)
                    AND (
                        q.subject_id = $subject
                        OR (
                            q.subject_id IS NULL
                            AND size($allow_markers) > 0
                            AND any(m IN $allow_markers WHERE toLower(q.text) CONTAINS m)
                            AND none(m IN $block_markers WHERE toLower(q.text) CONTAINS m)
                        )
                    )
          AND ($difficulty IS NULL OR toLower(q.difficulty) = $difficulty)
        RETURN q.text AS text, q.year AS year, q.marks AS marks, q.difficulty AS difficulty
        ORDER BY q.year DESC
        LIMIT 1
        """
        params["subject"] = subject
    else:
        query = """
        MATCH (c:Concept)
        WHERE toLower(c.name) = toLower($concept)
        MATCH (q:Question)-[:APPEARS_IN]->(c)
        WHERE ($cutoff IS NULL OR q.year <= $cutoff)
          AND ($difficulty IS NULL OR toLower(q.difficulty) = $difficulty)
        RETURN q.text AS text, q.year AS year, q.marks AS marks, q.difficulty AS difficulty
        ORDER BY q.year DESC
        LIMIT 1
        """

    results, _ = _safe_cypher_query(query, params)
    if not results:
        return None

    row = results[0]
    return {
        "text": row[0],
        "year": row[1],
        "marks": row[2],
        "difficulty": row[3],
    }


def get_reference_question_by_text_match(
    concept: str,
    subject: Optional[str] = None,
    cutoff_year: Optional[int] = None,
    difficulty: Optional[str] = None,
) -> Optional[dict]:
    allow_markers, block_markers = _subject_marker_filters(subject or "")
    params = {
        "concept": concept,
        "subject": subject,
        "cutoff": cutoff_year,
        "difficulty": difficulty.lower() if difficulty else None,
        "allow_markers": allow_markers,
        "block_markers": block_markers,
    }

    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        MATCH (q:Question)-[:APPEARS_IN]->(c)
        WHERE toLower(q.text) CONTAINS toLower($concept)
                    AND (
                        q.subject_id = $subject
                        OR (
                            q.subject_id IS NULL
                            AND size($allow_markers) > 0
                            AND any(m IN $allow_markers WHERE toLower(q.text) CONTAINS m)
                            AND none(m IN $block_markers WHERE toLower(q.text) CONTAINS m)
                        )
                    )
          AND ($cutoff IS NULL OR q.year <= $cutoff)
          AND ($difficulty IS NULL OR toLower(q.difficulty) = $difficulty)
        RETURN q.text AS text, q.year AS year, q.marks AS marks, q.difficulty AS difficulty
        ORDER BY q.year DESC
        LIMIT 1
        """
    else:
        query = """
        MATCH (q:Question)
        WHERE toLower(q.text) CONTAINS toLower($concept)
          AND ($cutoff IS NULL OR q.year <= $cutoff)
          AND ($difficulty IS NULL OR toLower(q.difficulty) = $difficulty)
        RETURN q.text AS text, q.year AS year, q.marks AS marks, q.difficulty AS difficulty
        ORDER BY q.year DESC
        LIMIT 1
        """

    results, _ = _safe_cypher_query(query, params)
    if not results:
        return None

    row = results[0]
    return {
        "text": row[0],
        "year": row[1],
        "marks": row[2],
        "difficulty": row[3],
    }


def get_reference_question_pool(
    subject: str,
    topics: Optional[List[str]] = None,
    cutoff_year: Optional[int] = None,
    limit: int = 50,
) -> List[dict]:
    allow_markers, block_markers = _subject_marker_filters(subject)
    query = """
    MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
    MATCH (q:Question)-[:APPEARS_IN]->(c)
    WHERE ($cutoff IS NULL OR q.year <= $cutoff)
            AND (
                q.subject_id = $subject
                OR (
                    q.subject_id IS NULL
                    AND size($allow_markers) > 0
                    AND any(m IN $allow_markers WHERE toLower(q.text) CONTAINS m)
                    AND none(m IN $block_markers WHERE toLower(q.text) CONTAINS m)
                )
            )
      AND ($topics IS NULL OR t.name IN $topics)
    RETURN DISTINCT q.text AS text, q.year AS year, q.marks AS marks, q.difficulty AS difficulty, c.name AS concept
    ORDER BY q.year DESC
    LIMIT $limit
    """

    params = {
        "subject": subject,
        "topics": topics if topics else None,
        "cutoff": cutoff_year,
        "limit": limit,
        "allow_markers": allow_markers,
        "block_markers": block_markers,
    }

    results, _ = _safe_cypher_query(query, params)
    pool = []
    for row in results:
        pool.append(
            {
                "text": row[0],
                "year": row[1],
                "marks": row[2],
                "difficulty": row[3],
                "concept": row[4],
            }
        )
    return pool


def get_generation_context(
    concept: str,
    subject: str,
    topics: Optional[List[str]] = None,
    cutoff_year: Optional[int] = None,
    difficulty: Optional[str] = None,
    limit: int = 5,
) -> dict:
    """Fetch context graph around a concept for LLM prompting and debugging.

    Includes related concepts, dependencies, and prior similar question traces.
    """
    allow_markers, block_markers = _subject_marker_filters(subject)
    query = """
    MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(t:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
    WHERE toLower(c.name) CONTAINS toLower($concept)
      AND ($topics IS NULL OR t.name IN $topics)

    OPTIONAL MATCH (c)-[:PREREQUISITE_OF]->(after:Concept)
    OPTIONAL MATCH (before:Concept)-[:PREREQUISITE_OF]->(c)
    OPTIONAL MATCH (c)-[:SIMILAR_TO]-(sim:Concept)
    OPTIONAL MATCH (c)-[:APPEARED_IN_YEAR]->(y)
    OPTIONAL MATCH (q:Question)-[:APPEARS_IN]->(c)
    WHERE ($cutoff IS NULL OR q.year <= $cutoff)
            AND (
                q.subject_id = $subject
                OR (
                    q.subject_id IS NULL
                    AND size($allow_markers) > 0
                    AND any(m IN $allow_markers WHERE toLower(q.text) CONTAINS m)
                    AND none(m IN $block_markers WHERE toLower(q.text) CONTAINS m)
                )
            )
      AND ($difficulty IS NULL OR toLower(q.difficulty) = toLower($difficulty))

    RETURN c.name AS concept,
           collect(DISTINCT t.name)[0..$limit] AS topics,
           collect(DISTINCT before.name)[0..$limit] AS prerequisites,
           collect(DISTINCT after.name)[0..$limit] AS dependent_concepts,
           collect(DISTINCT sim.name)[0..$limit] AS similar_concepts,
           collect(DISTINCT y.year)[0..$limit] AS appeared_in_years,
           collect(DISTINCT {text: q.text, year: q.year, difficulty: q.difficulty})[0..$limit] AS prior_questions
    LIMIT 1
    """

    params = {
        "concept": concept,
        "subject": subject,
        "topics": topics if topics else None,
        "cutoff": cutoff_year,
        "difficulty": difficulty,
        "limit": limit,
        "allow_markers": allow_markers,
        "block_markers": block_markers,
    }
    rows, _ = _safe_cypher_query(query, params)
    if rows:
        row = rows[0]
        context = {
            "concept": row[0] or concept,
            "topics": row[1] or [],
            "prerequisites": row[2] or [],
            "dependent_concepts": row[3] or [],
            "similar_concepts": row[4] or [],
            "appeared_in_years": [year for year in (row[5] or []) if year],
            "prior_questions": [q for q in (row[6] or []) if q and q.get("text")],
            "source": "neo4j",
        }
        logger.info(
            "Neo4j context retrieved",
            extra={
                "subject": subject,
                "concept": context["concept"],
                "topics_count": len(context["topics"]),
                "prior_questions_count": len(context["prior_questions"]),
            },
        )
        return context

    fallback_question = get_reference_question_by_text_match(
        concept=concept,
        subject=subject,
        cutoff_year=cutoff_year,
        difficulty=difficulty,
    )
    fallback_context = {
        "concept": concept,
        "topics": topics or [],
        "prerequisites": [],
        "dependent_concepts": [],
        "similar_concepts": [],
        "prior_questions": [fallback_question] if fallback_question and fallback_question.get("text") else [],
        "source": "fallback",
    }
    logger.warning(
        "Neo4j context empty; using fallback context",
        extra={"subject": subject, "concept": concept, "fallback_prior_count": len(fallback_context["prior_questions"])}
    )
    return fallback_context


if __name__ == "__main__":
    # Example usage
    print("High Frequency Concepts:", get_high_frequency_concepts())
    print("Never Asked Concepts:", get_never_asked_concepts())
    print("Recency Gap Concepts:", get_recency_gap_concepts(cutoff_year=2020))
    print("Prerequisite Heavy Concepts:", get_prerequisite_heavy_concepts())