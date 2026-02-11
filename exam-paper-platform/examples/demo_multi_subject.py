#!/usr/bin/env python3
"""
Demo script showing multi-subject question generation with EE-only answer generation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.exam_service import generate_exam
from app.services.answer_service import generate_answers, ANSWER_ENABLED_SUBJECTS
from app.schemas.exam import Question


def demo_all_subjects():
    """Demonstrate question generation for all subjects."""
    print("=" * 80)
    print("MULTI-SUBJECT QUESTION GENERATION DEMO")
    print("=" * 80)
    
    subjects = [
        ("EE 2026", "Electrical Engineering"),
        ("CS 2026", "Computer Science Engineering"),
        ("CE 2026", "Civil Engineering"),
        ("EC 2026", "Electronics and Communication Engineering"),
        ("ME 2026", "Mechanical Engineering"),
        ("CH 2026", "Chemical Engineering"),
        ("MT 2026", "Metallurgical Engineering"),
    ]
    
    for subject_id, subject_name in subjects:
        print(f"\n{'='*80}")
        print(f"Subject: {subject_name} ({subject_id})")
        print(f"{'='*80}")
        
        try:
            # Generate questions
            print(f"\n[1/2] Generating 3 questions...")
            exam = generate_exam(
                total_questions=3,
                cutoff_year=2023,
                subject=subject_id,
                topics=None
            )
            
            print(f"✅ Successfully generated {exam.total_questions} questions")
            print(f"    Topics covered: {', '.join(exam.topics[:3])}{'...' if len(exam.topics) > 3 else ''}")
            
            # Display sample question
            if exam.questions:
                q = exam.questions[0]
                print(f"\n📝 Sample Question:")
                print(f"    Concept: {q.concept}")
                print(f"    Difficulty: {q.difficulty}")
                print(f"    Question: {q.question[:100]}...")
            
            # Check if answer generation is supported
            can_generate_answers = subject_id in ANSWER_ENABLED_SUBJECTS
            print(f"\n[2/2] Answer generation: ", end="")
            
            if can_generate_answers:
                print(f"✅ SUPPORTED")
                try:
                    # Generate answer for first question
                    print(f"    Generating sample answer...")
                    answers = generate_answers(
                        [exam.questions[0]],
                        subject=subject_id
                    )
                    print(f"    ✅ Answer generated successfully!")
                    print(f"    Context retrieved: {answers[0].context_retrieved}")
                except Exception as e:
                    print(f"    ❌ Error: {str(e)}")
            else:
                print(f"❌ NOT SUPPORTED")
                print(f"    Reason: RAG embeddings not available for {subject_name}")
                print(f"    To enable: Embed books for this subject into Pinecone")
                
                # Demonstrate error message
                try:
                    generate_answers(
                        [exam.questions[0]],
                        subject=subject_id
                    )
                except ValueError as e:
                    print(f"    Expected error: {str(e)[:100]}...")
        
        except Exception as e:
            print(f"❌ Error generating questions: {str(e)}")
            import traceback
            traceback.print_exc()


def demo_ee_complete_workflow():
    """Demonstrate complete workflow for EE (questions + answers)."""
    print(f"\n{'='*80}")
    print("COMPLETE WORKFLOW DEMO: ELECTRICAL ENGINEERING")
    print(f"{'='*80}")
    
    try:
        # Generate questions
        print("\n[Step 1] Generating 5 EE questions...")
        exam = generate_exam(
            total_questions=5,
            cutoff_year=2023,
            subject="EE 2026",
            topics=None
        )
        print(f"✅ Generated {exam.total_questions} questions")
        
        # Generate answers
        print(f"\n[Step 2] Generating answers for all questions...")
        answers = generate_answers(
            exam.questions,
            subject="EE 2026"
        )
        print(f"✅ Generated {len(answers)} answers")
        
        # Display results
        print(f"\n{'='*80}")
        print("COMPLETE EXAM PAPER WITH SOLUTIONS")
        print(f"{'='*80}")
        
        for i, (q, a) in enumerate(zip(exam.questions, answers), 1):
            print(f"\n{'='*80}")
            print(f"Question {i}/{exam.total_questions}")
            print(f"{'='*80}")
            print(f"Concept: {q.concept}")
            print(f"Difficulty: {q.difficulty}")
            print(f"\nQuestion:")
            print(f"{q.question}\n")
            print(f"Answer:")
            print(f"{a.answer[:200]}...")
            print(f"\nContext Retrieved: {'✅' if a.context_retrieved else '❌'}")
        
        print(f"\n{'='*80}")
        print("✅ Complete workflow successful for Electrical Engineering!")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EXAM PAPER PLATFORM - MULTI-SUBJECT SUPPORT DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows:")
    print("  1. Question generation for ALL 7 subjects (CE, CH, CS, EC, EE, ME, MT)")
    print("  2. Answer generation ONLY for Electrical Engineering (EE)")
    print("  3. Proper validation and error messages for unsupported subjects")
    print("\n" + "="*80)
    
    try:
        # Demo 1: All subjects question generation
        demo_all_subjects()
        
        # Demo 2: Complete workflow for EE
        demo_ee_complete_workflow()
        
        print("\n" + "="*80)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nKey Takeaways:")
        print("  ✅ Questions can be generated for ALL subjects")
        print("  ⚡ Answers currently only for Electrical Engineering")
        print("  🚀 Easy to extend to other subjects by embedding books")
        print("  🛡️ Proper validation prevents incorrect usage")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n❌ Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
