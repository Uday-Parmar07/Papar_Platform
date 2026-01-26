"""Populate Neo4j with syllabus content from JSON files."""

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

# Ensure project root is importable before importing application modules.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.neo4j import resolve_neo4j_url

from neomodel import config, db

DEFAULT_INPUT_DIR = ROOT_DIR / "json_syllabus"

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

def collect_json_files(targets: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(sorted(target.glob("*.json")))
        elif target.suffix.lower() == ".json" and target.exists():
            files.append(target)
        else:
            raise FileNotFoundError(f"JSON not found: {target}")

    unique: List[Path] = []
    seen = set()
    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)

    if not unique:
        raise FileNotFoundError("No JSON files discovered from provided inputs")

    return unique


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest syllabus JSON files into Neo4j"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[DEFAULT_INPUT_DIR],
        help="JSON file(s) or directories containing JSON syllabi. Defaults to json_syllabus."
    )
    return parser


def main():
    args = build_parser().parse_args()

    try:
        json_files = collect_json_files(args.inputs)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    for syllabus_path in json_files:
        print(f"🚀 Ingesting {syllabus_path.name}")
        with open(syllabus_path, "r", encoding="utf-8") as f:
            syllabus = json.load(f)

        ingest_syllabus(syllabus)


if __name__ == "__main__":
    main()
