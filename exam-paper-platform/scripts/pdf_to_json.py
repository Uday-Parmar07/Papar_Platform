import argparse
import json
import re
from pathlib import Path
from typing import Iterable, List

import fitz

BASE_DIR = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_DIR = BASE_DIR / "raw_syllabus"
DEFAULT_OUTPUT_DIR = BASE_DIR / "json_syllabus"

SECTION_RE = re.compile(r"Section\s+\d+:\s+(.*)")

def extract_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text

def parse_syllabus(text: str, subject: str) -> dict:
    syllabus = {
        "subject": subject,
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


def collect_pdfs(targets: Iterable[Path]) -> List[Path]:
    pdfs: List[Path] = []

    for target in targets:
        if target.is_dir():
            pdfs.extend(sorted(target.glob("*.pdf")))
        elif target.suffix.lower() == ".pdf" and target.exists():
            pdfs.append(target)
        else:
            raise FileNotFoundError(f"No PDF found at {target}")

    unique_pdfs = []
    seen = set()
    for pdf in pdfs:
        resolved = pdf.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_pdfs.append(resolved)

    if not unique_pdfs:
        raise FileNotFoundError("No PDF files discovered from provided inputs")

    return unique_pdfs


def normalize_subject_name(stem: str) -> str:
    name = stem.replace("_", " ").strip()
    if not name:
        return "Syllabus"

    suffixes = [" syllabus", "_syllabus"]
    lower_name = name.lower()
    for suffix in suffixes:
        if lower_name.endswith(suffix):
            name = name[: -len(suffix)]
            break

    cleaned_parts = []
    for part in re.split(r"\s+", name.strip()):
        if not part:
            continue
        if part.isupper() or part.isdigit():
            cleaned_parts.append(part)
        else:
            cleaned_parts.append(part.capitalize())

    return " ".join(cleaned_parts) if cleaned_parts else "Syllabus"


def convert_pdf(pdf_path: Path, output_dir: Path, subject_override: str | None = None) -> Path:
    print(f"🚀 Converting {pdf_path.name}")
    text = extract_text(pdf_path)
    print(f"📄 Extracted {len(text)} characters from {pdf_path.name}")

    subject = subject_override or normalize_subject_name(pdf_path.stem)
    syllabus = parse_syllabus(text, subject)
    print(f"📊 Parsed {len(syllabus['topics'])} topics from {pdf_path.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{pdf_path.stem}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(syllabus, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON written to: {output_path}")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert syllabus PDFs into JSON structures"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[DEFAULT_INPUT_DIR],
        help="PDF files or directories containing PDFs. Defaults to raw_syllabus."
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where JSON files will be written. Defaults to json_syllabus."
    )
    parser.add_argument(
        "-s",
        "--subject",
        type=str,
        help="Override subject name used in generated JSON."
    )
    return parser

if __name__ == "__main__":
    args = build_parser().parse_args()

    try:
        pdfs = collect_pdfs(args.inputs)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc))

    for pdf in pdfs:
        convert_pdf(pdf, args.output_dir, args.subject)

    print("🎉 Conversion complete for all PDFs")
