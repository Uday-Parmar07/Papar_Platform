#!/usr/bin/env python3
"""
Example: Using the generate_answers script with exam questions.

This example shows how to:
1. Generate exam questions
2. Generate answers for those questions
3. Combine them into a complete Q&A dataset
"""

import json
from pathlib import Path

# Example 1: Using pre-defined sample questions
if __name__ == "__main__":
    print("=" * 70)
    print("EXAMPLE 1: Generate Sample Answers")
    print("=" * 70)
    print("""
This will generate answers for 3 pre-defined electrical engineering questions.

Run with:
    python scripts/generate_answers.py --sample 3

The output will be saved to 'answers.json' with format:
    {
        "total_questions": 3,
        "namespace": "Electrical Engineering",
        "answers": [
            {
                "question": "...",
                "concept": "...",
                "difficulty": "Easy|Medium|Hard",
                "answer": "Generated answer...",
                "context_retrieved": true
            }
        ]
    }
""")

    print("\n" + "=" * 70)
    print("EXAMPLE 2: Generate Answers from Custom Questions File")
    print("=" * 70)
    print("""
Create a file 'my_questions.json':
    {
        "questions": [
            {
                "question": "What is the efficiency of a transformer with 95% at full load?",
                "concept": "Transformer Efficiency",
                "difficulty": "Easy"
            },
            {
                "question": "Derive the torque equation for a 3-phase induction motor.",
                "concept": "Induction Motor Torque",
                "difficulty": "Hard"
            }
        ]
    }

Run with:
    python scripts/generate_answers.py --input my_questions.json --output my_answers.json
""")

    print("\n" + "=" * 70)
    print("EXAMPLE 3: Integration with Question Generation")
    print("=" * 70)
    print("""
from services.exam_service import generate_exam
import json

# Step 1: Generate exam questions
exam_result = generate_exam(
    total_questions=5,
    cutoff_year=2023,
    subject="EE",
    topics=["Power Systems", "Control Systems"]
)

# Step 2: Save questions to file
questions_data = {
    "questions": [
        {
            "question": q.question,
            "concept": q.concept,
            "difficulty": q.difficulty
        }
        for q in exam_result.questions
    ]
}

with open("generated_questions.json", "w") as f:
    json.dump(questions_data, f, indent=2)

# Step 3: Generate answers
# Run: python scripts/generate_answers.py --input generated_questions.json --output generated_answers.json

# Step 4: Combine questions and answers
with open("generated_questions.json") as f1, open("generated_answers.json") as f2:
    questions = json.load(f1)["questions"]
    answers = json.load(f2)["answers"]
    
    combined = {
        "subject": exam_result.subject_name,
        "topics": exam_result.topics,
        "total_questions": exam_result.total_questions,
        "q_and_a": [
            {
                "question": q["question"],
                "concept": q["concept"],
                "difficulty": q["difficulty"],
                "answer": a["answer"]
            }
            for q, a in zip(questions, answers)
        ]
    }
    
    with open("exam_with_answers.json", "w") as f:
        json.dump(combined, f, indent=2)
""")

    print("\n" + "=" * 70)
    print("EXAMPLE 4: Python API Usage")
    print("=" * 70)
    print("""
from scripts.generate_answers import generate_answer

# Generate answer for a single question
result = generate_answer(
    question="Calculate the apparent power in a 3-phase circuit with voltage 440V, current 10A.",
    concept="Power Calculation",
    difficulty="Easy",
    namespace="Electrical Engineering"
)

print(f"Question: {result['question']}")
print(f"Answer: {result['answer']}")
print(f"Context Retrieved: {result['context_retrieved']}")
""")

    print("\n" + "=" * 70)
    print("Key Points")
    print("=" * 70)
    print("""
1. SETUP:
   - Set GROQ_API_KEY and PINECONE_API_KEY in .env
   - Ensure electrical engineering books are embedded in Pinecone

2. INPUT FORMAT:
   - Questions must have: question, concept, difficulty
   - Difficulty levels: Easy, Medium, Hard

3. PERFORMANCE:
   - ~10-15 seconds per question (depends on model)
   - Batch of 5 questions: ~1-2 minutes

4. OUTPUT:
   - JSON file with question-answer pairs
   - Includes context retrieval status
   - Easy to integrate with PDF generation or storage

5. ADVANCED:
   - Customize RETRIEVAL_TOP_K for more/less context
   - Change Groq model for different performance/quality tradeoffs
   - Implement caching for repeated questions
""")
