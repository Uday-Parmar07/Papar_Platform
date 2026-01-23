import re
from typing import Dict, List

# -----------------------------
# Constants
# -----------------------------

MIN_LENGTH = 30      # relaxed minimum to allow concise but complete prompts
MAX_LENGTH = 320     # modest buffer for richer context

FORBIDDEN_PHRASES = [
    "solution",
    "explain",
    "explanation",
    "correct answer",
]

NON_EE_KEYWORDS = [
    "chemical",
    "civil engineering",
    "biotechnology",
    "medical",
    "organic chemistry",
]

DIFFICULTY_RULES = {
    "Easy": {
        "max_steps": 1,
        "keywords": []
    },
    "Medium": {
        "max_steps": 3,
        "keywords": []
    },
    "Hard": {
        "max_steps": 5,
        "keywords": []
    }
}

# -----------------------------
# Helper functions
# -----------------------------

def word_count(text: str) -> int:
    return len(text.split())

def contains_forbidden_phrase(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in FORBIDDEN_PHRASES)

def contains_non_ee_content(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in NON_EE_KEYWORDS)

def appears_multi_question(text: str) -> bool:
    # Detect Q1/Q2, (a)/(b), or multiple question marks
    if text.count("?") > 2:
        return True
    if re.search(r"\(\s*[a-z]\s*\)", text.lower()):
        return True
    return False

# -----------------------------
# Core validation
# -----------------------------

def validate_question(question: Dict) -> Dict:
    """
    Returns:
      {
        "valid": bool,
        "reason": str
      }
    """

    text = question["question"].strip()
    difficulty = question["difficulty"]

    # 1️⃣ Single question check
    if appears_multi_question(text):
        return {"valid": False, "reason": "Multiple questions detected"}

    # 2️⃣ Length sanity
    wc = word_count(text)
    if wc < MIN_LENGTH:
        return {"valid": False, "reason": "Question too short"}
    if wc > MAX_LENGTH:
        return {"valid": False, "reason": "Question too long"}

    # 3️⃣ Forbidden content
    if contains_forbidden_phrase(text):
        return {"valid": False, "reason": "Contains solution/explanation language"}

    # 4️⃣ Syllabus domain safety
    if contains_non_ee_content(text):
        return {"valid": False, "reason": "Out-of-domain (non-EE) content"}

    # 5️⃣ Difficulty sanity (heuristic)
    if difficulty not in DIFFICULTY_RULES:
        return {"valid": False, "reason": "Unknown difficulty level"}


    return {"valid": True, "reason": "OK"}

# -----------------------------
# Batch validator
# -----------------------------

def validate_questions(questions: List[Dict]) -> List[Dict]:
    validated = []

    for q in questions:
        result = validate_question(q)
        if result["valid"]:
            validated.append(q)
        else:
            # Attach failure reason (useful for retries later)
            q["validation_error"] = result["reason"]

    return validated
