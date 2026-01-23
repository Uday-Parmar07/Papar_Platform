import json
import sys
from pathlib import Path

# -------------------------------
# Validation Helpers
# -------------------------------

def fail(msg: str):
    print(f"❌ VALIDATION FAILED: {msg}")
    sys.exit(1)

def warn(msg: str):
    print(f"⚠️ WARNING: {msg}")

# -------------------------------
# Core Validation
# -------------------------------

def validate_syllabus(data: dict):
    # ---- Top level ----
    if not isinstance(data, dict):
        fail("Top-level JSON must be an object")

    if "subject" not in data or not isinstance(data["subject"], str):
        fail("Missing or invalid 'subject'")

    if "topics" not in data or not isinstance(data["topics"], list):
        fail("Missing or invalid 'topics' list")

    if not data["topics"]:
        fail("Topics list is empty")

    # ---- Topics ----
    for t_idx, topic in enumerate(data["topics"]):
        if "name" not in topic or not isinstance(topic["name"], str):
            fail(f"Topic {t_idx} missing valid 'name'")

        if "subtopics" not in topic or not isinstance(topic["subtopics"], list):
            fail(f"Topic '{topic['name']}' missing 'subtopics' list")

        if not topic["subtopics"]:
            warn(f"Topic '{topic['name']}' has no subtopics")

        # ---- Subtopics ----
        for s_idx, sub in enumerate(topic["subtopics"]):
            if "name" not in sub or not isinstance(sub["name"], str):
                fail(
                    f"Subtopic {s_idx} in topic '{topic['name']}' missing valid 'name'"
                )

            if "concepts" not in sub or not isinstance(sub["concepts"], list):
                fail(
                    f"Subtopic '{sub['name']}' missing 'concepts' list"
                )

            if not sub["concepts"]:
                warn(
                    f"Subtopic '{sub['name']}' has no concepts"
                )

            # ---- Concepts ----
            for c_idx, concept in enumerate(sub["concepts"]):
                if not isinstance(concept, dict):
                    fail(
                        f"Concept {c_idx} in subtopic '{sub['name']}' is not an object"
                    )

                if "name" not in concept or not isinstance(concept["name"], str):
                    fail(
                        f"Concept {c_idx} in subtopic '{sub['name']}' missing valid 'name'"
                    )

                if len(concept["name"].strip()) < 2:
                    warn(
                        f"Suspiciously short concept name: '{concept['name']}'"
                    )

                if len(concept["name"]) > 200:
                    warn(
                        f"Very long concept name (possible PDF noise): '{concept['name']}'"
                    )

    print("✅ JSON structure is VALID and ready for ingestion")

# -------------------------------
# Entry Point
# -------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_syllabus_json.py <syllabus.json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])

    if not json_path.exists():
        fail(f"File not found: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON format: {e}")

    validate_syllabus(data)
