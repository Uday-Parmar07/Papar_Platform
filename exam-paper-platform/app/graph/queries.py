import sys
from pathlib import Path

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

# -----------------------------
# GRAPH RAG RETRIEVAL QUERIES
# -----------------------------

def _concept_fallback(subject: str | None, limit: int):
    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WITH DISTINCT c
        RETURN c.name AS name
        ORDER BY rand()
        LIMIT $limit
        """
        params = {"subject": subject, "limit": limit}
    else:
        query = """
        MATCH (c:Concept)
        RETURN c.name AS name
        ORDER BY rand()
        LIMIT $limit
        """
        params = {"limit": limit}

    fallback, _ = db.cypher_query(query, params)
    return [row[0] for row in fallback]


def get_high_frequency_concepts(limit=10, subject: str | None = None):
    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WITH DISTINCT c
        OPTIONAL MATCH (q:Question)-[:APPEARS_IN]->(c)
        WITH c, count(q) AS score
        WHERE score > 0
        RETURN c.name AS name, score
        ORDER BY score DESC
        LIMIT $limit
        """
        params = {"subject": subject, "limit": limit}
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

    fallback = _concept_fallback(subject, limit)
    return [{"concept": name, "score": 0} for name in fallback]


def get_never_asked_concepts(limit=10, subject: str | None = None):
    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WITH DISTINCT c
        OPTIONAL MATCH (q:Question)-[:APPEARS_IN]->(c)
        WITH c, count(q) AS appearances
        WHERE appearances = 0
        RETURN c.name AS name
        ORDER BY rand()
        LIMIT $limit
        """
        params = {"subject": subject, "limit": limit}
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

    fallback = _concept_fallback(subject, limit)
    return [{"concept": name} for name in fallback]


def get_recency_gap_concepts(cutoff_year, limit=10, subject: str | None = None):
    if subject:
        query = """
        MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
        WITH DISTINCT c
        MATCH (q:Question)-[:APPEARS_IN]->(c)
        WITH c, max(q.year) AS last_year
        WHERE last_year <= $cutoff
        RETURN c.name AS name, last_year
        ORDER BY last_year ASC
        LIMIT $limit
        """
        params = {"subject": subject, "cutoff": cutoff_year, "limit": limit}
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

    fallback = _concept_fallback(subject, limit)
    return [{"concept": name, "last_asked": None} for name in fallback]


def list_subject_names() -> list[str]:
    query = """
    MATCH (s:Subject)
    RETURN s.name AS name
    ORDER BY name
    """
    results, _ = db.cypher_query(query, {})
    return [row[0] for row in results]


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