"""
MUST_RELATE Edge Migration Script — Answer Grading Pipeline
=============================================================
Migration order: Run AFTER migrate_requires_edges.py (A2), BEFORE add_concept_aliases.py (A4).

For each Question that has REQUIRES edges but whose concepts lack MUST_RELATE edges,
this script calls the LLM to define concept-to-concept relationships.

Usage:
    python -m grading.migration.migrate_must_relate_edges
"""

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=True)

from groq import Groq
from app.database import get_database


# ── LLM client (reuse project's Groq setup) ───────────────────────────
llm_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"

ALLOWED_RELATION_TYPES = [
    "causes",
    "enables",
    "requires",
    "opposes",
    "converts",
    "proportional_to",
    "inversely_proportional_to",
    "part_of",
    "measured_by",
]


def fetch_questions_with_concepts(driver) -> list[dict]:
    """
    Returns questions that have REQUIRES edges but whose concepts
    have no outgoing MUST_RELATE edges yet.
    """
    query = """
    MATCH (q:Question)-[:REQUIRES]->(c:Concept)
    WHERE NOT EXISTS((c)-[:MUST_RELATE]->())
    RETURN q.uid AS id,
           coalesce(q.text, q.question, q.content, '') AS text,
           collect(DISTINCT c.name) AS concept_names
    """
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]


def extract_relations_via_llm(
    concept_names: list[str],
    question_text: str,
    client
) -> list[dict]:
    """
    Calls LLM to define relationships between concepts.

    Returns:
        [{"from": str, "to": str, "type": str, "weight": float}]

    If fewer than 2 concepts: returns empty list.
    """
    if len(concept_names) < 2:
        return []

    concepts_str = ", ".join(concept_names)
    allowed_types_str = ", ".join(ALLOWED_RELATION_TYPES)

    prompt = f"""SYSTEM:
You are an expert Electrical Engineering domain modeler.

CONCEPTS:
{concepts_str}

QUESTION CONTEXT:
{question_text[:500]}

TASK:
Define the meaningful relationships between the given concepts in the context of
Electrical Engineering.

RULES:
- Allowed relation types: {allowed_types_str}
- Only define relations that are meaningful in EE context
- Assign weight 0.1-1.0 to each relation (1.0 = very strong relationship)
- Do not invent concepts — only use the ones listed above
- Each relation must have: from, to, type, weight

RESPONSE FORMAT: JSON array only. No preamble, no markdown fences.
Example: [{{"from": "Ohm's Law", "to": "Impedance", "type": "enables", "weight": 0.8}}]

Define relations now:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You define concept relationships. Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        relations = json.loads(raw)

        if not isinstance(relations, list):
            print(f"  [WARN] LLM returned non-list: {type(relations)}")
            return []

        concept_set = set(concept_names)
        validated = []
        for r in relations:
            if not isinstance(r, dict):
                continue
            from_c = str(r.get("from", "")).strip()
            to_c = str(r.get("to", "")).strip()
            rel_type = str(r.get("type", "")).strip()
            weight = float(r.get("weight", 0.5))

            # Validate
            if not from_c or not to_c or from_c == to_c:
                continue
            if from_c not in concept_set or to_c not in concept_set:
                continue
            if rel_type not in ALLOWED_RELATION_TYPES:
                continue
            weight = max(0.1, min(1.0, weight))

            validated.append({
                "from": from_c,
                "to": to_c,
                "type": rel_type,
                "weight": weight,
            })

        return validated

    except json.JSONDecodeError:
        print(f"  [ERROR] JSON parse failed. Raw response: {raw[:200]}")
        return []
    except Exception as e:
        print(f"  [ERROR] LLM call failed: {e}")
        return []


def store_must_relate_edges(
    driver,
    relations: list[dict]
) -> int:
    """
    For each relation, MERGE a MUST_RELATE edge between existing Concept nodes.
    Skips if either concept does not exist — does not create nodes here.

    Returns count of edges created.
    """
    if not relations:
        return 0

    edges_created = 0
    query = """
    MATCH (c1:Concept {name: $from_name})
    MATCH (c2:Concept {name: $to_name})
    MERGE (c1)-[r:MUST_RELATE]->(c2)
    ON CREATE SET r.relation_type = $rel_type,
                  r.weight = $weight,
                  r.domain = "electrical_engineering",
                  r.created_at = timestamp()
    RETURN count(r) AS cnt
    """

    try:
        with driver.session() as session:
            for rel in relations:
                result = session.run(
                    query,
                    from_name=rel["from"],
                    to_name=rel["to"],
                    rel_type=rel["type"],
                    weight=rel["weight"],
                )
                record = result.single()
                if record:
                    edges_created += record["cnt"]
    except Exception as e:
        print(f"  [ERROR] Failed storing MUST_RELATE edges: {e}")

    return edges_created


def run_must_relate_migration(
    driver,
    client,
    batch_size: int = 10,
    delay_between_batches: float = 1.0
) -> dict:
    """
    Orchestrates the full MUST_RELATE edge migration.

    Returns summary dict.
    """
    print("=" * 60)
    print("  MUST_RELATE EDGE MIGRATION")
    print("=" * 60)

    questions = fetch_questions_with_concepts(driver)
    total = len(questions)
    print(f"[INFO] Found {total} questions with concepts needing MUST_RELATE edges")

    if total == 0:
        print("[INFO] Nothing to migrate.")
        return {
            "total_processed": 0,
            "total_relations_created": 0,
            "failed_questions": [],
            "skipped_few_concepts": 0,
        }

    summary = {
        "total_processed": 0,
        "total_relations_created": 0,
        "failed_questions": [],
        "skipped_few_concepts": 0,
    }

    for i, question in enumerate(questions):
        qid = question["id"]
        text = question["text"]
        concept_names = question["concept_names"]

        if len(concept_names) < 2:
            summary["skipped_few_concepts"] += 1
            print(f"  [{i + 1}/{total}] {qid} → <2 concepts (skipped)")
            summary["total_processed"] += 1
            continue

        # Extract relations via LLM
        relations = extract_relations_via_llm(concept_names, text, client)

        if not relations:
            summary["skipped_few_concepts"] += 1
            print(f"  [{i + 1}/{total}] {qid} → 0 relations (skipped)")
            summary["total_processed"] += 1
            continue

        # Store in Neo4j
        edges = store_must_relate_edges(driver, relations)

        if edges > 0:
            summary["total_relations_created"] += edges
            print(f"  [{i + 1}/{total}] {qid} → {edges} relations stored")
        else:
            summary["failed_questions"].append(qid)
            print(f"  [{i + 1}/{total}] {qid} → FAILED")

        summary["total_processed"] += 1

        # Rate limiting
        if (i + 1) % batch_size == 0 and i + 1 < total:
            print(f"  [BATCH] Processed {i + 1}/{total}, pausing {delay_between_batches}s...")
            time.sleep(delay_between_batches)

    print()
    print("=" * 60)
    print("  MUST_RELATE MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Total processed       : {summary['total_processed']}")
    print(f"  Total relations created: {summary['total_relations_created']}")
    print(f"  Failed questions      : {len(summary['failed_questions'])}")
    print(f"  Skipped (<2 concepts) : {summary['skipped_few_concepts']}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    driver = get_database()
    try:
        run_must_relate_migration(driver, llm_client)
    finally:
        pass
