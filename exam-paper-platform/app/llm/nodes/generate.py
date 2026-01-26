from typing import Dict
from groq import Groq
import os
from dotenv import load_dotenv

# -----------------------------
# Groq client
# -----------------------------

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# -----------------------------
# Difficulty rules
# -----------------------------

DIFFICULTY_GUIDELINES = {
    "Easy": (
        "Single-step conceptual recall or simple numeric substitution. "
        "Provide one clear data point or condition so the question is answerable."
    ),
    "Medium": (
        "Incorporate 2–3 reasoning steps, blending theory with calculation or reasoning. "
        "State any required assumptions explicitly."
    ),
    "Hard": (
        "Require multi-step reasoning or analysis of interacting phenomena. "
        "Include realistic parameter values and constraints to guide problem solving."
    )
}

# -----------------------------
# Prompt builder
# -----------------------------

def build_prompt(concept: str, difficulty: str, subject: str) -> str:
    subject_label = subject or "Engineering"
    return f"""
You are an expert GATE {subject_label} question setter.

TASK:
Generate ONE exam-quality GATE {subject_label} question.

CONSTRAINTS:
- Concept: {concept}
- Difficulty: {difficulty}
- {DIFFICULTY_GUIDELINES[difficulty]}
- Syllabus strictly limited to {subject_label} (GATE level)
- Target length: 45-120 words. Provide enough context, numeric values, and conditions so the question is self-contained.
- Do NOT include solution
- Do NOT include explanation
- Do NOT include multiple questions
- Do NOT mention marks explicitly
- Use standard GATE exam language

STRUCTURE:
- Begin with a concise scenario or set of givens before the actual interrogative.
- End with a single question sentence.
- Avoid bullet lists; write as a short paragraph.

OUTPUT:
Return ONLY the question text.

QUESTION:
""".strip()

# -----------------------------
# Question generation
# -----------------------------

def generate_question(concept: str, difficulty: str, subject: str) -> Dict:
    prompt = build_prompt(concept, difficulty, subject)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Groq LLaMA 70B (use if available)
        # If your account shows llama-17b explicitly, use:
        # model="llama-17b"
        messages=[
            {
                "role": "system",
                "content": "You are a strict GATE Electrical Engineering examiner."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.35,   # exam-safe
        max_tokens=220,
        top_p=0.9
    )

    question_text = response.choices[0].message.content.strip()

    return {
        "concept": concept,
        "difficulty": difficulty,
        "question": question_text
    }
