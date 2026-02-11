import json
import random
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

from neomodel import config, db

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
    results, _ = db.cypher_query(query, {})
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
    results, _ = db.cypher_query(query, {"subject": subject})
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

    fallback, _ = db.cypher_query(query, params)
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

    results, _ = db.cypher_query(query, params)
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

    results, _ = db.cypher_query(query, params)
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

    results, _ = db.cypher_query(query, params)
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
    results, _ = db.cypher_query(query, {"limit": limit})
    return [{"concept": r[0], "prereq_count": r[1]} for r in results]


if __name__ == "__main__":
    # Example usage
    print("High Frequency Concepts:", get_high_frequency_concepts())
    print("Never Asked Concepts:", get_never_asked_concepts())
    print("Recency Gap Concepts:", get_recency_gap_concepts(cutoff_year=2020))
    print("Prerequisite Heavy Concepts:", get_prerequisite_heavy_concepts())