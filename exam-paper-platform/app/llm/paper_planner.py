from dataclasses import dataclass
from typing import List, Dict

@dataclass
class BlueprintItem:
    concept: str
    difficulty: str
    reason: str   # why this concept was chosen

@dataclass
class PaperBlueprint:
    total_questions: int
    distribution: Dict[str, int]
    questions: List[BlueprintItem]
    subject: str


from app.graph.queries import (
    get_high_frequency_concepts,
    get_never_asked_concepts,
    get_recency_gap_concepts
)
import random


def build_paper_blueprint(
    total_questions: int = 65,
    cutoff_year: int = 2019,
    subject: str | None = None
):
    blueprint = []

    # -----------------------------
    # Decide counts
    # -----------------------------
    hf_count = int(total_questions * 0.5)
    rg_count = int(total_questions * 0.3)
    na_count = total_questions - hf_count - rg_count

    # -----------------------------
    # Retrieve concepts
    # -----------------------------
    high_freq = get_high_frequency_concepts(hf_count, subject=subject)
    recency_gap = get_recency_gap_concepts(cutoff_year, rg_count, subject=subject)
    never_asked = get_never_asked_concepts(na_count, subject=subject)

    # -----------------------------
    # Assign difficulty
    # -----------------------------
    def assign_difficulty():
        r = random.random()
        if r < 0.3:
            return "Easy"
        elif r < 0.8:
            return "Medium"
        return "Hard"

    # -----------------------------
    # Build blueprint items
    # -----------------------------
    for c in high_freq:
        blueprint.append(
            BlueprintItem(
                concept=c["concept"],
                difficulty=assign_difficulty(),
                reason="High frequency in PYQs"
            )
        )

    for c in recency_gap:
        blueprint.append(
            BlueprintItem(
                concept=c["concept"],
                difficulty=assign_difficulty(),
                reason="Not asked recently"
            )
        )

    for c in never_asked:
        blueprint.append(
            BlueprintItem(
                concept=c["concept"],
                difficulty=assign_difficulty(),
                reason="Never asked in PYQs"
            )
        )

    return PaperBlueprint(
        total_questions=total_questions,
        distribution={
            "high_frequency": hf_count,
            "recency_gap": rg_count,
            "never_asked": na_count
        },
        questions=blueprint,
        subject=subject or ""
    )
