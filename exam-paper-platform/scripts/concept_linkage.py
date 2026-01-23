import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neomodel import config

from app.utils.neo4j import resolve_neo4j_url
from app.graph.schema import Concept, Question

try:
    config.DATABASE_URL = resolve_neo4j_url()
except ValueError as exc:
    print(f"❌ {exc}")
    sys.exit(1)

# -----------------------------
# HELPERS
# -----------------------------

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def token_overlap(a: str, b: str) -> float:
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens)

# -----------------------------
# OPTIONAL: EXAM-SAFE ALIASES
# -----------------------------

ALIASES = {
    "synchronous speed": ["rotating magnetic field speed", "rmf speed"],
    "slip": ["slip s", "s equals"],
    "torque": ["electromagnetic torque"],
}

# -----------------------------
# LINKING LOGIC
# -----------------------------

def link_questions_to_concepts():
    concepts = Concept.nodes.all()
    questions = Question.nodes.all()

    print(f"🔗 Linking {len(questions)} questions with {len(concepts)} concepts")

    for q in questions:
        q_text = normalize(q.text)

        for c in concepts:
            c_name = normalize(c.name)

            # Pass 1: direct token overlap
            overlap = token_overlap(c_name, q_text)

            matched = overlap >= 0.6

            # Pass 2: alias matching
            if not matched and c_name in ALIASES:
                for alias in ALIASES[c_name]:
                    if normalize(alias) in q_text:
                        matched = True
                        break

            if matched:
                # Create relationship from question -> concept if absent.
                if not q.tests_concept.is_connected(c):
                    q.tests_concept.connect(c)

    print("✅ Concept-question linking completed")

if __name__ == "__main__":
    link_questions_to_concepts()
