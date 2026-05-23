"""
REQUIRES Edge Migration Script — Answer Grading Pipeline
=========================================================
Migration order: Run AFTER audit_neo4j_schema.py (A1), BEFORE migrate_must_relate_edges.py (A3).

For each Question node missing REQUIRES edges, this script:
1. Calls the Groq LLM to extract required concepts from question text
2. MERGEs Concept nodes and REQUIRES relationships into Neo4j

Usage:
    python -m grading.migration.migrate_requires_edges
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


def fetch_questions_needing_migration(driver) -> list[dict]:
    """
    Returns list of dicts with keys: id, text, reference_answer
    Only returns questions WHERE NOT EXISTS((q)-[:REQUIRES]->(:Concept))
    Uses parameterized Cypher, no f-string interpolation inside queries.
    """
    query = """
    MATCH (q:Question)
    WHERE NOT EXISTS((q)-[:REQUIRES]->(:Concept))
    RETURN q.uid AS id,
           coalesce(q.text, q.question, q.content, '') AS text,
           coalesce(q.reference_answer, '') AS reference_answer
    """
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]


def extract_concepts_via_llm(
    question_text: str,
    reference_answer: str,
    client
) -> list[dict]:
    """
    Calls LLM to extract required concepts from a question.

    Returns:
        [{"name": str, "weight": float, "is_critical": bool}]
    If JSON parsing fails: logs raw response and returns empty list.
    """
    if not question_text or len(question_text.strip()) < 10:
        return []

    context_section = ""
    if reference_answer and reference_answer.strip():
        context_section = f"\nREFERENCE ANSWER:\n{reference_answer[:500]}\n"

    prompt = f"""SYSTEM:
You are an expert Electrical Engineering examiner analyzing GATE exam questions.

QUESTION:
{question_text[:800]}
{context_section}
TASK:
Extract the concepts a student MUST mention to receive full marks for this question.

RULES:
- For each concept provide: name, weight (0.1-1.0), is_critical (bool)
- If a concept is a formula or law, include the full common name
  e.g. "Kirchhoff's Voltage Law" not just "KVL"
- Domain: Electrical Engineering
- Return between 1 and 8 concepts
- weight: 1.0 = absolutely essential, 0.1 = minor detail
- is_critical: true if missing this concept means the answer is fundamentally wrong

RESPONSE FORMAT: JSON array only. No preamble, no markdown fences, no explanation.
Example: [{{"name": "Ohm's Law", "weight": 0.9, "is_critical": true}}]

Extract concepts now:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You extract exam concepts. Respond with JSON only."},
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

        concepts = json.loads(raw)

        if not isinstance(concepts, list):
            print(f"  [WARN] LLM returned non-list: {type(concepts)}")
            return []

        validated = []
        for c in concepts:
            if not isinstance(c, dict) or "name" not in c:
                continue
            validated.append({
                "name": str(c["name"]).strip(),
                "weight": float(c.get("weight", 0.5)),
                "is_critical": bool(c.get("is_critical", False)),
            })

        return validated

    except json.JSONDecodeError:
        print(f"  [ERROR] JSON parse failed. Raw response: {raw[:200]}")
        return []
    except Exception as e:
        print(f"  [ERROR] LLM call failed: {e}")
        return []


def store_requires_edges(
    driver,
    question_id: str,
    concepts: list[dict]
) -> int:
    """
    For each concept:
    1. MERGE the Concept node (create if not exists)
    2. MERGE the REQUIRES relationship with properties

    Returns count of edges created.
    """
    if not concepts:
        return 0

    edges_created = 0
    query = """
    MATCH (q:Question {uid: $question_id})
    MERGE (c:Concept {name: $concept_name})
    ON CREATE SET c.domain = "electrical_engineering"
    MERGE (q)-[r:REQUIRES]->(c)
    ON CREATE SET r.weight = $weight,
                  r.is_critical = $is_critical,
                  r.created_at = timestamp()
    RETURN count(r) AS cnt
    """

    try:
        with driver.session() as session:
            for concept in concepts:
                result = session.run(
                    query,
                    question_id=question_id,
                    concept_name=concept["name"],
                    weight=concept["weight"],
                    is_critical=concept["is_critical"],
                )
                record = result.single()
                if record:
                    edges_created += record["cnt"]
    except Exception as e:
        print(f"  [ERROR] Failed storing edges for question {question_id}: {e}")

    return edges_created


def run_requires_migration(
    driver,
    client,
    batch_size: int = 10,
    delay_between_batches: float = 1.0
) -> dict:
    """
    Orchestrates the full REQUIRES edge migration.

    Returns migration summary dict.
    """
    print("=" * 60)
    print("  REQUIRES EDGE MIGRATION")
    print("=" * 60)

    questions = fetch_questions_needing_migration(driver)
    total = len(questions)
    print(f"[INFO] Found {total} questions needing REQUIRES migration")

    if total == 0:
        print("[INFO] Nothing to migrate.")
        return {
            "total_processed": 0,
            "total_concepts_created": 0,
            "failed_questions": [],
            "skipped_empty": 0,
        }

    summary = {
        "total_processed": 0,
        "total_concepts_created": 0,
        "failed_questions": [],
        "skipped_empty": 0,
    }

    for i, question in enumerate(questions):
        qid = question["id"]
        text = question["text"]

        # Extract concepts via LLM
        concepts = extract_concepts_via_llm(
            question_text=text,
            reference_answer=question.get("reference_answer", ""),
            client=client,
        )

        if not concepts:
            summary["skipped_empty"] += 1
            print(f"  [{i + 1}/{total}] {qid} → 0 concepts (skipped)")
            summary["total_processed"] += 1
            continue

        # Store in Neo4j
        edges = store_requires_edges(driver, qid, concepts)

        if edges > 0:
            summary["total_concepts_created"] += edges
            print(f"  [{i + 1}/{total}] {qid} → {edges} concepts stored")
        else:
            summary["failed_questions"].append(qid)
            print(f"  [{i + 1}/{total}] {qid} → FAILED")

        summary["total_processed"] += 1

        # Rate limiting: pause between batches
        if (i + 1) % batch_size == 0 and i + 1 < total:
            print(f"  [BATCH] Processed {i + 1}/{total}, pausing {delay_between_batches}s...")
            time.sleep(delay_between_batches)

    print()
    print("=" * 60)
    print("  REQUIRES MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Total processed      : {summary['total_processed']}")
    print(f"  Total concepts created: {summary['total_concepts_created']}")
    print(f"  Failed questions     : {len(summary['failed_questions'])}")
    print(f"  Skipped (empty)      : {summary['skipped_empty']}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    driver = get_database()
    try:
        run_requires_migration(driver, llm_client)
    finally:
        pass
