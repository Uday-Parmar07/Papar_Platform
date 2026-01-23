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

def get_high_frequency_concepts(limit=10):
    query = """
    MATCH (c:Concept)
    WHERE c.frequency > 0
    RETURN c.name AS name, c.frequency AS score
    ORDER BY score DESC
    LIMIT $limit
    """
    results, _ = db.cypher_query(query, {"limit": limit})
    return [{"concept": r[0], "score": r[1]} for r in results]


def get_never_asked_concepts(limit=10):
    query = """
    MATCH (c:Concept)
    WHERE c.frequency = 0
    RETURN c.name AS name
    LIMIT $limit
    """
    results, _ = db.cypher_query(query, {"limit": limit})
    return [{"concept": r[0]} for r in results]


def get_recency_gap_concepts(cutoff_year, limit=10):
    query = """
    MATCH (c:Concept)-[:APPEARS_IN]->(q:Question)
    WITH c, max(q.year) AS last_year
    WHERE last_year <= $cutoff
    RETURN c.name AS name, last_year
    ORDER BY last_year ASC
    LIMIT $limit
    """
    results, _ = db.cypher_query(
        query,
        {"cutoff": cutoff_year, "limit": limit}
    )
    return [{"concept": r[0], "last_asked": r[1]} for r in results]


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