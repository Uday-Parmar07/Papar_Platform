#!/usr/bin/env python3
"""Generate answers for exam questions using Pinecone RAG and Groq LLM."""

import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.answer import AnswerItem
from app.schemas.exam import Question
from app.services.answer_service import generate_answers

DEFAULT_NAMESPACE = os.getenv("PINECONE_DEFAULT_NAMESPACE", "Electrical Engineering")


def _ensure_question(payload: dict) -> Question:
	return Question(
		concept=payload.get("concept", "Unknown Concept"),
		difficulty=payload.get("difficulty", "Medium"),
		question=payload.get("question", ""),
	)


def _serialize_answers(items: Iterable[AnswerItem]) -> List[dict]:
	serialized: List[dict] = []
	for item in items:
		if hasattr(item, "model_dump"):
			serialized.append(item.model_dump())
			continue
		serialized.append(
			{
				"concept": item.concept,
				"difficulty": item.difficulty,
				"question": item.question,
				"answer": item.answer,
				"context_retrieved": item.context_retrieved,
			}
		)
	return serialized


def _load_questions_from_file(path: Path) -> List[Question]:
	if not path.exists():
		raise FileNotFoundError(f"Input file not found: {path}")
	with path.open("r", encoding="utf-8") as handle:
		payload = json.load(handle)
	if isinstance(payload, dict):
		items = payload.get("questions", [])
	else:
		items = payload
	return [_ensure_question(item) for item in items if item]


def _write_answers(path: Path, namespace: str, answers: List[AnswerItem]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open("w", encoding="utf-8") as handle:
		json.dump(
			{
				"total_questions": len(answers),
				"namespace": namespace,
				"answers": _serialize_answers(answers),
			},
			handle,
			indent=2,
		)


def generate_answers_from_file(input_file: Path, output_file: Path, namespace: str) -> None:
	questions = _load_questions_from_file(input_file)
	if not questions:
		print("No questions found in input file")
		return

	print(f"Generating answers for {len(questions)} questions...")
	answers = generate_answers(questions, namespace=namespace)
	_write_answers(output_file, namespace, answers)
	print(f"\nAnswers saved to: {output_file}")


def generate_sample_answers(total: int, output_file: Path) -> None:
	sample_questions = [
		Question(
			question="A 3-phase synchronous motor is running at no-load. If the excitation is increased suddenly, what will happen to the armature current and power factor?",
			concept="Synchronous Motor Operation",
			difficulty="Medium",
		),
		Question(
			question="Calculate the equivalent resistance of a delta-connected circuit where each phase has a resistance of 30 ohms, if it is converted to a star connection.",
			concept="Delta-Y Transformation",
			difficulty="Easy",
		),
		Question(
			question="A transmission line has a resistance of 10 ohms per km, inductance of 1 mH per km, and capacitance of 0.01 uF per km. Find the characteristic impedance at 50 Hz.",
			concept="Transmission Line Parameters",
			difficulty="Hard",
		),
		Question(
			question="In a BJT, if the base current is increased, explain the effect on the collector current and the operating point of the transistor.",
			concept="BJT Biasing",
			difficulty="Medium",
		),
		Question(
			question="A synchronous generator has a synchronous reactance of 0.5 pu and is connected to an infinite bus. If the load angle is 30 deg, find the maximum power that can be transferred.",
			concept="Power Transfer in Synchronous Machines",
			difficulty="Hard",
		),
	]

	selection = sample_questions[: max(1, min(total, len(sample_questions)))]

	print(f"Generating {len(selection)} sample answers for Electrical Engineering...")
	answers = generate_answers(selection, namespace=DEFAULT_NAMESPACE)
	_write_answers(output_file, DEFAULT_NAMESPACE, answers)
	print(f"\nSample answers saved to: {output_file}")


def main() -> None:
	import argparse

	parser = argparse.ArgumentParser(
		description="Generate answers for exam questions using Pinecone RAG and Groq LLM",
	)
	parser.add_argument(
		"--input",
		type=Path,
		help="Input JSON file with questions (must have 'question', 'concept', 'difficulty' fields)",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=Path("answers.json"),
		help="Output JSON file for answers (default: answers.json)",
	)
	parser.add_argument(
		"--namespace",
		default=DEFAULT_NAMESPACE,
		help="Pinecone namespace to retrieve from (default: Electrical Engineering)",
	)
	parser.add_argument(
		"--sample",
		type=int,
		help="Generate sample answers (provide number of questions, max 5)",
	)

	args = parser.parse_args()

	try:
		load_dotenv()
		if args.sample:
			generate_sample_answers(args.sample, args.output)
		elif args.input:
			generate_answers_from_file(args.input, args.output, args.namespace)
		else:
			parser.print_help()
			print("\nExample usage:")
			print("  # Generate sample answers:")
			print("  python scripts/generate_answers.py --sample 3")
			print("\n  # Generate from questions file:")
			print("  python scripts/generate_answers.py --input questions.json --output answers.json")
	except Exception as exc:
		print(f"Error: {exc}")
		sys.exit(1)


if __name__ == "__main__":
	main()
