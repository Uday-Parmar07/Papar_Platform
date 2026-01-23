import json
import re
from pathlib import Path
import fitz

BASE_DIR = Path(__file__).resolve().parents[1]

PDF_PATH = BASE_DIR / "raw_syllabus" / "EE_2026_Syllabus.pdf"
OUTPUT_JSON = BASE_DIR / "json_syllabus" / "EE_2026_Syllabus.json"

SECTION_RE = re.compile(r"Section\s+\d+:\s+(.*)")

def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

def parse_syllabus(text):
    syllabus = {
        "subject": "Electrical Engineering",
        "topics": []
    }

    current_topic = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            current_topic = {
                "name": section_match.group(1),
                "subtopics": []
            }
            syllabus["topics"].append(current_topic)
            continue

        if not current_topic:
            continue

        # Subtopic : concepts
        if ":" in line:
            subtopic_name, concepts_part = line.split(":", 1)

            subtopic = {
                "name": subtopic_name.strip(),
                "concepts": []
            }
            current_topic["subtopics"].append(subtopic)

            concepts = re.split(r"[;,]", concepts_part)
            for c in concepts:
                c = c.strip().rstrip(".")
                if c:
                    subtopic["concepts"].append({"name": c})
            continue

        # Concepts only → auto subtopic
        if "," in line:
            existing = next(
                (s for s in current_topic["subtopics"]
                 if s["name"] == current_topic["name"]),
                None
            )

            if not existing:
                existing = {
                    "name": current_topic["name"],
                    "concepts": []
                }
                current_topic["subtopics"].append(existing)

            concepts = re.split(r"[;,]", line)
            for c in concepts:
                c = c.strip().rstrip(".")
                if c:
                    existing["concepts"].append({"name": c})

    return syllabus

if __name__ == "__main__":
    print("🚀 Starting syllabus PDF → JSON conversion")

    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    text = extract_text(PDF_PATH)
    print(f"📄 Extracted {len(text)} characters from PDF")

    syllabus = parse_syllabus(text)
    print(f"📊 Topics parsed: {len(syllabus['topics'])}")

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(syllabus, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON written to: {OUTPUT_JSON}")
