import sys
from pathlib import Path

from neomodel import config, db

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.neo4j import resolve_neo4j_url

try:
    config.DATABASE_URL = resolve_neo4j_url()
except ValueError as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)


def run_backfill() -> None:
    query_unique_subject = """
    MATCH (q:Question)-[:APPEARS_IN]->(c:Concept)
    MATCH (s:Subject)-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c)
    WITH q, collect(DISTINCT s.name) AS subjects
    WHERE size(subjects) = 1
    SET q.subject_id = subjects[0]
    RETURN count(q) AS updated
    """

    marker_updates = [
        ("EE 2026", ["(ee)", "electrical engineering (ee)"]),
        ("CE 2026", ["(ce)", "(ce1)", "(ce2)", "civil engineering (ce)"]),
        ("ME 2026", ["(me)", "mechanical engineering (me)"]),
        ("CH 2026", ["(ch)", "chemical engineering (ch)"]),
        ("MT 2026", ["(mt)", "metallurgical engineering (mt)"]),
        ("CS 2026", ["(cs)", "computer science"]),
        ("EC 2026", ["(ec)", "electronics and communication"]),
    ]

    query_counts = """
    MATCH (q:Question)
    RETURN count(q) AS total,
           count(q.subject_id) AS tagged,
           count(CASE WHEN q.subject_id IS NULL THEN 1 END) AS untagged
    """

    rows, _ = db.cypher_query(query_unique_subject, {})
    updated_unique = rows[0][0] if rows else 0

    updated_marker = 0
    for subject, markers in marker_updates:
        query = """
        MATCH (q:Question)
        WHERE q.subject_id IS NULL
          AND any(m IN $markers WHERE toLower(q.text) CONTAINS m)
        SET q.subject_id = $subject
        RETURN count(q) AS updated
        """
        rows, _ = db.cypher_query(query, {"subject": subject, "markers": markers})
        count = rows[0][0] if rows else 0
        updated_marker += count
        if count:
            print(f"Marker tagged {subject}: {count}")

    rows, _ = db.cypher_query(query_counts, {})
    total, tagged, untagged = rows[0] if rows else (0, 0, 0)

    print(f"Updated via unique-subject relation: {updated_unique}")
    print(f"Updated via branch marker fallback: {updated_marker}")
    print(f"Question nodes total: {total}")
    print(f"Question nodes tagged: {tagged}")
    print(f"Question nodes untagged: {untagged}")


if __name__ == "__main__":
    run_backfill()
