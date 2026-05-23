"""
Neo4j Schema Audit Script — Answer Grading Pipeline
====================================================
Audits the current Neo4j graph to determine migration readiness
for the Stage 2 grading pipeline.

Checks for:
- Existing node labels and relationship types
- REQUIRES edges (Question → Concept)
- MUST_RELATE edges (Concept → Concept)
- Concept alias properties

This script is READ-ONLY. It does NOT modify any data.

Usage:
    python -m grading.migration.audit_neo4j_schema
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import app.utils.neo4j
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neomodel import config, db
from app.utils.neo4j import resolve_neo4j_url

# ── Connect to Neo4j using existing project configuration ──────────────
config.DATABASE_URL = resolve_neo4j_url()


def _run_query(description: str, query: str):
    """Run a Cypher query and return results. Print errors but don't crash."""
    try:
        results, meta = db.cypher_query(query)
        return results
    except Exception as e:
        print(f"  [ERROR] {description}: {e}")
        return []


def audit():
    """Run all audit queries and print the migration readiness report."""

    print("=" * 60)
    print("  NEO4J SCHEMA AUDIT — Answer Grading Pipeline")
    print("=" * 60)
    print()

    # ── Query 1: All node labels ───────────────────────────────────────
    print("[1/8] Fetching node labels...")
    results = _run_query("node labels", "CALL db.labels()")
    node_labels = [row[0] for row in results]
    print(f"  Labels: {node_labels}")
    print()

    # ── Query 2: All relationship types ────────────────────────────────
    print("[2/8] Fetching relationship types...")
    results = _run_query("relationship types", "CALL db.relationshipTypes()")
    rel_types = [row[0] for row in results]
    print(f"  Relationship types: {rel_types}")
    print()

    # ── Query 3: Sample Question nodes ─────────────────────────────────
    print("[3/8] Sampling Question nodes (limit 5)...")
    results = _run_query(
        "sample questions",
        "MATCH (q:Question) RETURN q LIMIT 5",
    )
    for i, row in enumerate(results):
        node = row[0]
        props = dict(node) if hasattr(node, '__iter__') else node
        print(f"  Q{i + 1}: {props}")
    if not results:
        print("  No Question nodes found.")
    print()

    # ── Query 4: REQUIRES edge count ──────────────────────────────────
    print("[4/8] Checking REQUIRES edges...")
    results = _run_query(
        "REQUIRES count",
        "MATCH ()-[r:REQUIRES]->() RETURN count(r) AS requires_count",
    )
    requires_count = results[0][0] if results else 0
    print(f"  REQUIRES edges: {requires_count}")
    print()

    # ── Query 5: MUST_RELATE edge count ────────────────────────────────
    print("[5/8] Checking MUST_RELATE edges...")
    results = _run_query(
        "MUST_RELATE count",
        "MATCH ()-[r:MUST_RELATE]->() RETURN count(r) AS must_relate_count",
    )
    must_relate_count = results[0][0] if results else 0
    print(f"  MUST_RELATE edges: {must_relate_count}")
    print()

    # ── Query 6: Questions missing REQUIRES edges ──────────────────────
    print("[6/8] Counting Questions missing REQUIRES edges...")
    results = _run_query(
        "questions needing migration",
        """
        MATCH (q:Question)
        WHERE NOT EXISTS((q)-[:REQUIRES]->(:Concept))
        RETURN count(q) AS questions_needing_migration
        """,
    )
    questions_needing_migration = results[0][0] if results else 0
    print(f"  Questions needing REQUIRES migration: {questions_needing_migration}")
    print()

    # ── Query 7: Sample Concept nodes ──────────────────────────────────
    print("[7/8] Sampling Concept nodes (limit 20)...")
    results = _run_query(
        "sample concepts",
        "MATCH (c:Concept) RETURN c LIMIT 20",
    )
    for i, row in enumerate(results):
        node = row[0]
        props = dict(node) if hasattr(node, '__iter__') else node
        print(f"  C{i + 1}: {props}")
    if not results:
        print("  No Concept nodes found.")
    print()

    # ── Query 8: Concepts missing aliases ──────────────────────────────
    print("[8/8] Counting Concepts missing aliases property...")
    results = _run_query(
        "concepts missing aliases",
        """
        MATCH (c:Concept)
        WHERE c.aliases IS NULL
        RETURN count(c) AS concepts_missing_aliases
        """,
    )
    concepts_missing_aliases = results[0][0] if results else 0
    print(f"  Concepts missing aliases: {concepts_missing_aliases}")
    print()

    # ── Total counts for report ────────────────────────────────────────
    results = _run_query("total questions", "MATCH (q:Question) RETURN count(q)")
    total_questions = results[0][0] if results else 0

    results = _run_query("total concepts", "MATCH (c:Concept) RETURN count(c)")
    total_concepts = results[0][0] if results else 0

    # ── Migration Readiness Report ─────────────────────────────────────
    print()
    print("=" * 60)
    print("  NEO4J MIGRATION READINESS REPORT")
    print("=" * 60)
    print(f"  Node labels found        : {node_labels}")
    print(f"  Relationship types found : {rel_types}")
    print(f"  Questions total          : {total_questions}")
    print(f"  Questions needing REQUIRES migration: {questions_needing_migration}")
    print(f"  Concepts total           : {total_concepts}")
    print(f"  Concepts missing aliases : {concepts_missing_aliases}")
    print(f"  REQUIRES edges exist     : {'YES' if requires_count > 0 else 'NO'}")
    print(f"  MUST_RELATE edges exist  : {'YES' if must_relate_count > 0 else 'NO'}")
    print("=" * 60)

    # ── Summary action items ───────────────────────────────────────────
    print()
    print("ACTION ITEMS:")
    if requires_count == 0:
        print("  [!] REQUIRES edges need to be created (Question → Concept)")
    else:
        print(f"  [✓] REQUIRES edges already exist ({requires_count} found)")

    if must_relate_count == 0:
        print("  [!] MUST_RELATE edges need to be created (Concept → Concept)")
    else:
        print(f"  [✓] MUST_RELATE edges already exist ({must_relate_count} found)")

    if concepts_missing_aliases > 0:
        print(f"  [!] {concepts_missing_aliases} Concepts need aliases property")
    else:
        print("  [✓] All Concepts have aliases")

    if questions_needing_migration > 0:
        print(f"  [!] {questions_needing_migration} Questions need REQUIRES edges")
    else:
        print("  [✓] All Questions have REQUIRES edges")

    print()


if __name__ == "__main__":
    audit()
