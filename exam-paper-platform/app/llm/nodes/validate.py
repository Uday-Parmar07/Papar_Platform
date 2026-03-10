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


def concept_alignment_ok(text: str, concept: str) -> bool:
    concept_tokens = [tok for tok in re.split(r"\W+", (concept or "").lower()) if len(tok) >= 4]
    if not concept_tokens:
        return True
    lowered = text.lower()
    matches = sum(1 for tok in concept_tokens if tok in lowered)
    return matches >= 1


def repetitive_opening(text: str) -> bool:
    opening = " ".join(text.lower().split()[:4])
    weak_openings = {
        "for an electrical engineering",
        "explain the fundamental principles",
        "a practical electrical engineering",
    }
    return opening in weak_openings

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

    # 6️⃣ Concept clarity check
    if not concept_alignment_ok(text, question.get("concept", "")):
        return {"valid": False, "reason": "Question does not clearly test the target concept"}

    # 7️⃣ Language monotony hint
    if repetitive_opening(text):
        return {"valid": False, "reason": "Repetitive phrasing detected"}


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
