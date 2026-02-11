#!/usr/bin/env python3
"""
Integration script: Generate exam questions and answers together.

This script demonstrates the complete workflow:
1. Generate exam questions using the exam service (supports all subjects)
2. Generate answers using the RAG system (currently EE only)
3. Combine them into a complete exam paper with solutions
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.exam_service import generate_exam
from app.services.answer_service import generate_answers, ANSWER_ENABLED_SUBJECTS, SUBJECT_NAMESPACE_MAP
from app.schemas.exam import Question
from scripts.generate_answers import generate_answer


def generate_complete_exam(
    total_questions: int = 5,
    cutoff_year: int = 2023,
    subject: str = "EE 2026",
    topics: List[str] | None = None,
    output_dir: Path = Path("exam_output"),
    skip_answers: bool = False
) -> Dict:
    """
    Generate a complete exam paper with questions and optionally answers.
    
    Args:
        total_questions: Number of questions to generate
        cutoff_year: Don't include questions asked after this year
        subject: Subject ID (e.g., "EE 2026", "CS 2026")
        topics: Optional list of specific topics
        output_dir: Directory to save output files
        skip_answers: Skip answer generation (questions only)
        
    Returns:
        Dictionary with exam details and results
    """
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("GENERATING EXAM QUESTIONS" + (" WITH ANSWERS" if not skip_answers else ""))
    print("=" * 70)
    
    # Step 1: Generate questions
    print(f"\n[STEP 1] Generating {total_questions} exam questions for {subject}...")
    try:
        exam_result = generate_exam(
            total_questions=total_questions,
            cutoff_year=cutoff_year,
            subject=subject,
            topics=topics
        )
        print(f"✓ Generated {exam_result.total_questions} questions")
        print(f"  Subject: {exam_result.subject_name}")
        print(f"  Topics: {', '.join(exam_result.topics)}")
    except Exception as e:
        print(f"✗ Failed to generate questions: {e}")
        return {"status": "failed", "error": str(e)}
    
    # Check if answers can be generated
    can_generate_answers = exam_result.subject_id in ANSWER_ENABLED_SUBJECTS
    if not skip_answers and not can_generate_answers:
        print(f"\n⚠ NOTE: Answer generation is currently only supported for Electrical Engineering.")
        print(f"  Subject '{exam_result.subject_name}' does not have RAG embeddings available yet.")
        print(f"  Proceeding with question generation only.")
        skip_answers = True
    
    # Step 2: Save questions
    print(f"\n[STEP 2] Saving questions...")
    questions_list = [
        {
            "question": q.question,
            "concept": q.concept,
            "difficulty": q.difficulty
        }
        for q in exam_result.questions
    ]
    questions_file = output_dir / "questions.json"
    with open(questions_file, 'w') as f:
        json.dump({
            "subject": exam_result.subject_name,
            "subject_id": exam_result.subject_id,
            "total_questions": exam_result.total_questions,
            "topics": exam_result.topics,
            "questions": questions_list
        }, f, indent=2)
    print(f"✓ Questions saved to: {questions_file}")
    
    # Step 3: Generate answers (if enabled)
    if skip_answers:
        print(f"\n⚠ Skipping answer generation.")
        print(f"\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Subject: {exam_result.subject_name}")
        print(f"Total Questions Generated: {exam_result.total_questions}")
        print(f"Output Directory: {output_dir.resolve()}")
        print(f"\nGenerated Files:")
        print(f"  - questions.json (questions only)")
        print("=" * 70)
        
        return {
            "status": "success",
            "subject": exam_result.subject_name,
            "total_questions": exam_result.total_questions,
            "answers_generated": False,
            "output_dir": str(output_dir.resolve()),
            "files": {
                "questions": str(questions_file)
            }
        }
    
    print(f"\n[STEP 3] Generating answers for {total_questions} questions...")
    answers_list = []
    failed_count = 0
    
    # Convert to Question objects for the service
    question_objs = [Question(**q) for q in questions_list]
    
    try:
        answers = generate_answers(
            question_objs,
            subject=exam_result.subject_id
        )
        for i, (question, answer) in enumerate(zip(exam_result.questions, answers), 1):
            print(f"  [{i}/{total_questions}] {question.concept}... ✓")
            answers_list.append({
                "question": question.question,
                "concept": question.concept,
                "difficulty": question.difficulty,
                "answer": answer.answer,
                "context_retrieved": answer.context_retrieved
            })
    except Exception as e:
        print(f"✗ Failed to generate answers: {e}")
        return {
            "status": "partially_failed",
            "subject": exam_result.subject_name,
            "total_questions": exam_result.total_questions,
            "error": str(e),
            "files": {
                "questions": str(questions_file)
            }
        }
    
    
    # Step 4: Save answers
    print(f"\n[STEP 4] Saving answers...")
    answers_file = output_dir / "answers.json"
    with open(answers_file, 'w') as f:
        json.dump({
            "subject": exam_result.subject_name,
            "total_questions": len(answers_list),
            "successfully_answered": len(answers_list) - failed_count,
            "failed": failed_count,
            "answers": answers_list
        }, f, indent=2)
    print(f"✓ Answers saved to: {answers_file}")
    
    # Step 5: Combine into complete exam
    print(f"\n[STEP 5] Creating combined Q&A document...")
    combined_exam = {
        "metadata": {
            "subject": exam_result.subject_name,
            "subject_id": exam_result.subject_id,
            "total_questions": exam_result.total_questions,
            "topics": exam_result.topics,
            "cutoff_year": cutoff_year,
            "distribution": exam_result.distribution
        },
        "questions_and_answers": [
            {
                "question_number": i + 1,
                "question": q.question,
                "concept": q.concept,
                "difficulty": q.difficulty,
                "answer": a.get("answer", "N/A"),
                "context_retrieved": a.get("context_retrieved", False)
            }
            for i, (q, a) in enumerate(zip(exam_result.questions, answers_list))
        ]
    }
    
    combined_file = output_dir / "exam_with_solutions.json"
    with open(combined_file, 'w') as f:
        json.dump(combined_exam, f, indent=2)
    print(f"✓ Combined exam saved to: {combined_file}")
    
    # Step 6: Summary
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Subject: {exam_result.subject_name}")
    print(f"Total Questions: {exam_result.total_questions}")
    print(f"Successfully Answered: {len(answers_list) - failed_count}")
    print(f"Failed: {failed_count}")
    print(f"Output Directory: {output_dir.resolve()}")
    print(f"\nGenerated Files:")
    print(f"  - questions.json (questions only)")
    print(f"  - answers.json (answers only)")
    print(f"  - exam_with_solutions.json (complete exam)")
    print("=" * 70)
    
    return {
        "status": "success",
        "subject": exam_result.subject_name,
        "total_questions": exam_result.total_questions,
        "successfully_answered": len(answers_list) - failed_count,
        "failed": failed_count,
        "answers_generated": True,
        "output_dir": str(output_dir.resolve()),
        "files": {
            "questions": str(questions_file),
            "answers": str(answers_file),
            "combined": str(combined_file)
        }
    }


def generate_from_file(
    input_file: Path,
    output_dir: Path = Path("exam_output")
) -> Dict:
    """
    Generate answers for questions from an existing file.
    
    Args:
        input_file: Path to questions.json file
        output_dir: Directory to save output files
        
    Returns:
        Dictionary with results
    """
    
    if not input_file.exists():
        return {"status": "failed", "error": f"Input file not found: {input_file}"}
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("GENERATING ANSWERS FROM EXISTING QUESTIONS")
    print("=" * 70)
    
    # Load questions
    print(f"\n[STEP 1] Loading questions from {input_file}...")
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            questions = data.get("questions", [])
            subject = data.get("subject", "Unknown")
        else:
            questions = data
            subject = "Unknown"
        
        print(f"✓ Loaded {len(questions)} questions")
        print(f"  Subject: {subject}")
    except Exception as e:
        return {"status": "failed", "error": f"Failed to load questions: {str(e)}"}
    
    # Generate answers
    print(f"\n[STEP 2] Generating answers...")
    answers_list = []
    failed_count = 0
    
    for i, question in enumerate(questions, 1):
        try:
            print(f"  [{i}/{len(questions)}] {question.get('concept', 'Unknown')}...", end=" ", flush=True)
            answer_result = generate_answer(
                question=question.get("question", ""),
                concept=question.get("concept", "Unknown"),
                difficulty=question.get("difficulty", "Medium"),
                namespace=subject
            )
            answers_list.append(answer_result)
            print("✓")
        except Exception as e:
            print(f"✗")
            answers_list.append({
                "question": question.get("question", ""),
                "concept": question.get("concept", "Unknown"),
                "difficulty": question.get("difficulty", "Medium"),
                "answer": f"Error: {str(e)}",
                "context_retrieved": False
            })
            failed_count += 1
    
    # Save answers
    print(f"\n[STEP 3] Saving results...")
    answers_file = output_dir / "answers.json"
    with open(answers_file, 'w') as f:
        json.dump({
            "subject": subject,
            "total_questions": len(answers_list),
            "successfully_answered": len(answers_list) - failed_count,
            "failed": failed_count,
            "answers": answers_list
        }, f, indent=2)
    print(f"✓ Answers saved to: {answers_file}")
    
    # Combine
    print(f"\n[STEP 4] Creating combined Q&A document...")
    combined_exam = {
        "metadata": {
            "subject": subject,
            "total_questions": len(questions)
        },
        "questions_and_answers": [
            {
                "question_number": i + 1,
                "question": q.get("question", ""),
                "concept": q.get("concept", ""),
                "difficulty": q.get("difficulty", ""),
                "answer": a.get("answer", "N/A"),
                "context_retrieved": a.get("context_retrieved", False)
            }
            for i, (q, a) in enumerate(zip(questions, answers_list))
        ]
    }
    
    combined_file = output_dir / "exam_with_solutions.json"
    with open(combined_file, 'w') as f:
        json.dump(combined_exam, f, indent=2)
    print(f"✓ Combined exam saved to: {combined_file}")
    
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Questions: {len(questions)}")
    print(f"Successfully Answered: {len(answers_list) - failed_count}")
    print(f"Failed: {failed_count}")
    print(f"Output Directory: {output_dir.resolve()}")
    print("=" * 70)
    
    return {
        "status": "success",
        "total_questions": len(questions),
        "successfully_answered": len(answers_list) - failed_count,
        "failed": failed_count,
        "output_files": {
            "answers": str(answers_file),
            "combined": str(combined_file)
        }
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate exam questions (all subjects) with optional answers (EE only)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Generate new exam
    gen_parser = subparsers.add_parser("generate", help="Generate new exam with questions and optionally answers")
    gen_parser.add_argument("--total", type=int, default=5, help="Total questions to generate")
    gen_parser.add_argument("--cutoff-year", type=int, default=2023, help="Cutoff year for questions")
    gen_parser.add_argument(
        "--subject", 
        default="EE 2026", 
        help="Subject ID (e.g., 'EE 2026', 'CS 2026', 'CE 2026', 'EC 2026', 'ME 2026', 'CH 2026', 'MT 2026')"
    )
    gen_parser.add_argument("--topics", nargs="+", help="Specific topics to focus on")
    gen_parser.add_argument("--output", type=Path, default=Path("exam_output"), help="Output directory")
    gen_parser.add_argument(
        "--skip-answers",
        action="store_true",
        help="Skip answer generation (questions only). Automatically enabled for non-EE subjects."
    )
    
    # Generate from file
    file_parser = subparsers.add_parser("from-file", help="Generate answers for existing questions")
    file_parser.add_argument("input", type=Path, help="Input questions.json file")
    file_parser.add_argument("--output", type=Path, default=Path("exam_output"), help="Output directory")
    
    args = parser.parse_args()
    
    try:
        if args.command == "generate":
            result = generate_complete_exam(
                total_questions=args.total,
                cutoff_year=args.cutoff_year,
                subject=args.subject,
                topics=args.topics,
                output_dir=args.output,
                skip_answers=args.skip_answers
            )
        elif args.command == "from-file":
            result = generate_from_file(
                input_file=args.input,
                output_dir=args.output
            )
        else:
            parser.print_help()
            print("\nExample usage:")
            print("  # Generate questions for Electrical Engineering with answers:")
            print("  python scripts/generate_exam_with_answers.py generate --total 5 --subject 'EE 2026'")
            print("\n  # Generate questions for Computer Science (questions only):")
            print("  python scripts/generate_exam_with_answers.py generate --total 5 --subject 'CS 2026' --skip-answers")
            print("\n  # Generate answers for existing questions:")
            print("  python scripts/generate_exam_with_answers.py from-file questions.json")
            print("\n  Available subjects: EE 2026, CS 2026, CE 2026, EC 2026, ME 2026, CH 2026, MT 2026")
            print("  Note: Answer generation currently only supported for EE 2026")
            sys.exit(0)
        
        print("\n✓ Operation completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
