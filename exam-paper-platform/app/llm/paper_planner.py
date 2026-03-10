from dataclasses import dataclass
from typing import Dict, List, Optional

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
    subject_label: str
    topics: List[str]


from app.graph.queries import (
    get_high_frequency_concepts,
    get_never_asked_concepts,
    get_recency_gap_concepts,
)
import random


def build_paper_blueprint(
    total_questions: int = 65,
    cutoff_year: int = 2019,
    subject: str | None = None,
    subject_label: Optional[str] = None,
    topics: Optional[List[str]] = None,
    topics_selected: Optional[List[str]] = None,
):
    blueprint = []
    seen_concepts = set()
    def append_item(concept_name: str, reason: str):
        normalized = " ".join((concept_name or "").lower().split())
        if not normalized or normalized in seen_concepts:
            return
        seen_concepts.add(normalized)
        blueprint.append(
            BlueprintItem(
                concept=concept_name,
                difficulty=assign_difficulty(),
                reason=reason,
            )
        )


    # -----------------------------
    # Decide counts
    # -----------------------------
    hf_count = int(total_questions * 0.5)
    rg_count = int(total_questions * 0.3)
    na_count = total_questions - hf_count - rg_count

    # -----------------------------
    # Retrieve concepts
    # -----------------------------
    high_freq = get_high_frequency_concepts(hf_count, subject=subject, topics=topics)
    recency_gap = get_recency_gap_concepts(cutoff_year, rg_count, subject=subject, topics=topics)
    never_asked = get_never_asked_concepts(na_count, subject=subject, topics=topics)

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
        append_item(c["concept"], "High frequency in PYQs")

    for c in recency_gap:
        append_item(c["concept"], "Not asked recently")

    for c in never_asked:
        append_item(c["concept"], "Never asked in PYQs")

    # Ensure requested count even after dedupe by allowing controlled repeats at the end.
    if len(blueprint) < total_questions:
        combined = high_freq + recency_gap + never_asked
        for c in combined:
            if len(blueprint) >= total_questions:
                break
            concept_name = c.get("concept")
            if not concept_name:
                continue
            blueprint.append(
                BlueprintItem(
                    concept=concept_name,
                    difficulty=assign_difficulty(),
                    reason="Supplemental concept to match requested count",
                )
            )

    blueprint = blueprint[:total_questions]

    return PaperBlueprint(
        total_questions=total_questions,
        distribution={
            "high_frequency": hf_count,
            "recency_gap": rg_count,
            "never_asked": na_count
        },
        questions=blueprint,
        subject=subject or "",
        subject_label=subject_label or (subject or ""),
        topics=topics_selected or (topics or []),
    )
