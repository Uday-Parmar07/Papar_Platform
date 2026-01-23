"""
Syllabus Ingestion Script
-------------------------
Reads syllabus structure from JSON and populates Neo4j graph.

Expected graph hierarchy:
Subject -> Topic -> SubTopic -> Concept
Concept -> PREREQUISITE_OF -> Concept

Run:
    python scripts/ingest_syllabus.py syllabus.json
"""

import json
import sys
from pathlib import Path
from app.utils.neo4j import resolve_neo4j_url

# Ensure project root is importable when running as a script
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from neomodel import config, db

# Import graph schema
from app.graph.schema import Subject, Topic, SubTopic, Concept

# ===============================
# NEO4J CONNECTION
# ===============================

try:
    config.DATABASE_URL = resolve_neo4j_url()
except ValueError as exc:
    print(f"❌ {exc}")
    sys.exit(1)


# ===============================
# HELPERS
# ===============================

def get_or_create(node_cls, **props):
    """
    Idempotent get-or-create helper
    """
    node = node_cls.nodes.get_or_none(**props)
    if node:
        return node
    return node_cls(**props).save()


# ===============================
# INGESTION LOGIC
# ===============================

def ingest_syllabus(syllabus: dict):
    """
    Ingest syllabus JSON into Neo4j
    """

    subject_name = syllabus["subject"]
    subject = get_or_create(Subject, name=subject_name)

    for topic_data in syllabus.get("topics", []):
        topic = get_or_create(Topic, name=topic_data["name"])
        subject.has_topic.connect(topic)

        for subtopic_data in topic_data.get("subtopics", []):
            subtopic = get_or_create(SubTopic, name=subtopic_data["name"])
            topic.has_subtopic.connect(subtopic)

            for concept_data in subtopic_data.get("concepts", []):
                concept = get_or_create(
                    Concept,
                    name=concept_data["name"]
                )

                # Optional metadata
                if "weight" in concept_data:
                    concept.weight = concept_data["weight"]
                if "frequency" in concept_data:
                    concept.frequency = concept_data["frequency"]

                concept.save()
                subtopic.has_concept.connect(concept)

    # Handle prerequisites AFTER all concepts exist
    for topic_data in syllabus.get("topics", []):
        for subtopic_data in topic_data.get("subtopics", []):
            for concept_data in subtopic_data.get("concepts", []):
                if "prerequisites" not in concept_data:
                    continue

                concept = Concept.nodes.get(name=concept_data["name"])
                for prereq_name in concept_data["prerequisites"]:
                    prereq = Concept.nodes.get_or_none(name=prereq_name)
                    if prereq:
                        prereq.prerequisite_of.connect(concept)

    print("✅ Syllabus ingestion completed successfully.")


# ===============================
# MAIN
# ===============================

def main():
    if len(sys.argv) != 2:
        print("Usage: python ingest_syllabus.py syllabus.json")
        sys.exit(1)

    syllabus_path = Path(sys.argv[1])
    if not syllabus_path.exists():
        print(f"❌ File not found: {syllabus_path}")
        sys.exit(1)

    with open(syllabus_path, "r", encoding="utf-8") as f:
        syllabus = json.load(f)

    ingest_syllabus(syllabus)


if __name__ == "__main__":
    main()
