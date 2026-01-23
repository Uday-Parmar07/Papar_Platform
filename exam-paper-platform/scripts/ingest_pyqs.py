import re
import sys
from pathlib import Path

# Ensure project root is importable before importing application modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from neomodel import config

from app.utils.neo4j import resolve_neo4j_url
from app.graph.schema import Question, Concept

# -----------------------------
# CONFIG
# -----------------------------

try:
    config.DATABASE_URL = resolve_neo4j_url()
except ValueError as exc:
    print(f"❌ {exc}")
    sys.exit(1)

PDF_PATH = "exam-paper-platform/raw_pyqs/EE/EE2025.pdf"
YEAR = 2025

QUESTION_SPLIT_REGEX = re.compile(r"\nQ\.\s*\d+|\n\d+\.")

# -----------------------------
# HELPERS
# -----------------------------

def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

def split_questions(text):
    parts = QUESTION_SPLIT_REGEX.split(text)
    return [p.strip() for p in parts if len(p.strip()) > 50]

def link_concepts(question_text, question_node):
    concepts = Concept.nodes.all()
    lower_text = question_text.lower()

    for concept in concepts:
        if concept.name.lower() in lower_text:
            concept.appears_in.connect(question_node)

# -----------------------------
# INGESTION
# -----------------------------

def ingest_pyq_pdf():
    text = extract_text(PDF_PATH)
    questions = split_questions(text)

    print(f"📄 Found {len(questions)} questions")

    for q_text in questions:
        question = Question(
            text=q_text,
            year=YEAR,
            marks=1,             # can refine later
            difficulty="medium",  # align with schema choices
            is_pyq=True
        ).save()

        link_concepts(q_text, question)

    print("✅ PYQ ingestion completed")

if __name__ == "__main__":
    ingest_pyq_pdf()
