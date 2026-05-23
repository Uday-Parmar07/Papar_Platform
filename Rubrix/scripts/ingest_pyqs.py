import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List

# Ensure project root is importable before importing application modules.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from neomodel import config, db

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

QUESTION_SPLIT_REGEX = re.compile(r"\nQ\.\s*\d+|\n\d+\.")
DEFAULT_INPUT_DIR = PROJECT_ROOT / "raw_pyqs"

SUBJECT_CODE_MAP = {
    "CE": "CE 2026",
    "CH": "CH 2026",
    "CS": "CS 2026",
    "EC": "EC 2026",
    "EE": "EE 2026",
    "ME": "ME 2026",
    "MT": "MT 2026",
}

_SUBJECT_CONCEPTS_CACHE: dict[str, list[str]] = {}

# -----------------------------
# HELPERS
# -----------------------------

def extract_text(pdf_path):
    doc = fitz.open(str(pdf_path))
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

def split_questions(text):
    parts = QUESTION_SPLIT_REGEX.split(text)
    return [p.strip() for p in parts if len(p.strip()) > 50]

def _infer_subject_from_path(pdf_path: Path) -> str:
    parts = [part.upper() for part in pdf_path.parts]
    for idx, part in enumerate(parts):
        if part == "RAW_PYQS" and idx + 1 < len(parts):
            code = parts[idx + 1]
            subject = SUBJECT_CODE_MAP.get(code)
            if subject:
                return subject
    raise ValueError(f"Cannot infer subject code from path: {pdf_path}")


def _subject_concept_names(subject_id: str) -> list[str]:
    if subject_id in _SUBJECT_CONCEPTS_CACHE:
        return _SUBJECT_CONCEPTS_CACHE[subject_id]

    query = """
    MATCH (s:Subject {name: $subject})-[:HAS_TOPIC]->(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)-[:HAS_CONCEPT]->(c:Concept)
    RETURN DISTINCT c.name AS name
    """
    rows, _ = db.cypher_query(query, {"subject": subject_id})
    names = [row[0] for row in rows if row and row[0]]
    _SUBJECT_CONCEPTS_CACHE[subject_id] = names
    return names


def link_concepts(question_text, question_node, subject_id: str):
    concept_names = _subject_concept_names(subject_id)
    lower_text = question_text.lower()

    for name in concept_names:
        if name.lower() in lower_text:
            concept = Concept.nodes.get_or_none(name=name)
            if concept is None:
                continue
            concept.appears_in.connect(question_node)

# -----------------------------
# INGESTION
# -----------------------------

def infer_year_from_name(pdf_path: Path) -> int:
    match = re.search(r"(20\d{2})", pdf_path.stem)
    if not match:
        raise ValueError(f"Cannot infer year from file name: {pdf_path.name}")
    return int(match.group(1))


def ingest_pdf(pdf_path: Path, marks: int, difficulty: str):
    try:
        year = infer_year_from_name(pdf_path)
    except ValueError as exc:
        print(f"⚠️  Skipping {pdf_path.name}: {exc}")
        return

    text = extract_text(pdf_path)
    questions = split_questions(text)
    try:
        subject_id = _infer_subject_from_path(pdf_path)
    except ValueError as exc:
        print(f"⚠️  Skipping {pdf_path.name}: {exc}")
        return

    if not questions:
        print(f"⚠️  No questions detected in {pdf_path.name}")
        return

    print(f"📄 {pdf_path.name}: ingesting {len(questions)} questions for {year}")

    for q_text in questions:
        question = Question(
            text=q_text,
            subject_id=subject_id,
            year=year,
            marks=marks,
            difficulty=difficulty,
            is_pyq=True
        ).save()

        link_concepts(q_text, question, subject_id)


def collect_pdfs(targets: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(sorted(target.rglob("*.pdf")))
        elif target.suffix.lower() == ".pdf" and target.exists():
            files.append(target)
        else:
            raise FileNotFoundError(f"PDF not found: {target}")

    unique: List[Path] = []
    seen = set()
    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)

    if not unique:
        raise FileNotFoundError("No PDF files discovered from provided inputs")

    return unique


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest previous year question PDFs into Neo4j"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[DEFAULT_INPUT_DIR],
        help="PDF file(s) or directories to ingest. Defaults to raw_pyqs."
    )
    parser.add_argument(
        "--marks",
        type=int,
        default=1,
        help="Marks assigned to each ingested question. Defaults to 1."
    )
    parser.add_argument(
        "--difficulty",
        type=str,
        default="medium",
        help="Difficulty label applied to ingested questions. Defaults to 'medium'."
    )
    return parser

if __name__ == "__main__":
    args = build_parser().parse_args()

    try:
        pdf_files = collect_pdfs(args.inputs)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    for pdf_file in pdf_files:
        ingest_pdf(pdf_file, marks=args.marks, difficulty=args.difficulty)

    print("✅ Completed ingestion for provided exam papers")
