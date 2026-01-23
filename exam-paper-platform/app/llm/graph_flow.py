from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from app.llm.paper_planner import build_paper_blueprint
from app.graph.queries import (
    get_high_frequency_concepts,
    get_never_asked_concepts,
    get_recency_gap_concepts
)

# -----------------------------
# STATE DEFINITION
# -----------------------------

class PaperState(TypedDict):
    total_questions: int
    cutoff_year: int

    blueprint: dict
    questions: List[dict]
    validated_questions: List[dict]
    final_questions: List[dict]
    failed_questions: List[dict]
    retry_count: int

# -----------------------------
# NODE 1: GRAPH RAG RETRIEVAL
# -----------------------------

def retrieve_concepts(state: PaperState):
    return {
        "high_frequency": get_high_frequency_concepts(
            limit=int(state["total_questions"] * 0.5)
        ),
        "recency_gap": get_recency_gap_concepts(
            cutoff_year=state["cutoff_year"],
            limit=int(state["total_questions"] * 0.3)
        ),
        "never_asked": get_never_asked_concepts(
            limit=int(state["total_questions"] * 0.2)
        )
    }

# -----------------------------
# NODE 2: BUILD BLUEPRINT
# -----------------------------

def build_blueprint_node(state: PaperState):
    blueprint = build_paper_blueprint(
        total_questions=state["total_questions"],
        cutoff_year=state["cutoff_year"]
    )
    return {"blueprint": blueprint}

# -----------------------------
# NODE 3: GENERATE QUESTIONS
# (stub for now)
# -----------------------------
# 
# 
from app.llm.nodes.generate import generate_question

def generate_questions_node(state: PaperState):
    questions = []

    for item in state["blueprint"].questions:
        q = generate_question(
            concept=item.concept,
            difficulty=item.difficulty
        )
        questions.append(q)

    return {"questions": questions}


# -----------------------------
# NODE 4: VALIDATE QUESTIONS
# -----------------------------

from app.llm.nodes.validate import validate_question

def validate_questions_node(state: PaperState):
    valid = []
    failed = []

    for q in state["questions"]:
        result = validate_question(q)
        if result["valid"]:
            valid.append(q)
        else:
            q["validation_error"] = result["reason"]
            failed.append(q)

    existing = state.get("final_questions")
    if isinstance(existing, list):
        accumulated = list(existing)
    else:
        accumulated = []
    accumulated.extend(valid)

    # keep both keys so callers can use either naming
    return {
        "validated_questions": accumulated,
        "final_questions": accumulated,
        "failed_questions": failed
    }

MAX_RETRIES = 2

def regenerate_failed_questions(state: PaperState):
    retry = state.get("retry_count", 0)

    if retry >= MAX_RETRIES or not state["failed_questions"]:
        return {}

    regenerated = []

    for q in state["failed_questions"]:
        new_q = generate_question(
            concept=q["concept"],
            difficulty=q["difficulty"]
        )
        regenerated.append(new_q)

    return {
        "questions": regenerated,
        "retry_count": retry + 1
    }

def should_retry(state: PaperState):
    if state.get("failed_questions") and state.get("retry_count", 0) < MAX_RETRIES:
        return "regenerate_failed_questions"
    return "finalize_paper"

def finalize_paper(state: PaperState):
    return {
        "final_questions": state.get("final_questions", [])
    }

# -----------------------------
# BUILD GRAPH
# -----------------------------

def build_graph():
    graph = StateGraph(PaperState)

    graph.add_node("retrieve_concepts", retrieve_concepts)
    graph.add_node("build_blueprint", build_blueprint_node)
    graph.add_node("generate_questions", generate_questions_node)
    graph.add_node("validate_questions", validate_questions_node)
    graph.add_node("regenerate_failed_questions", regenerate_failed_questions)
    graph.add_node("finalize_paper", finalize_paper)

    graph.set_entry_point("retrieve_concepts")

    graph.add_edge("retrieve_concepts", "build_blueprint")
    graph.add_edge("build_blueprint", "generate_questions")
    graph.add_edge("generate_questions", "validate_questions")

    graph.add_conditional_edges(
        "validate_questions",
        should_retry,
        {
            "regenerate_failed_questions": "regenerate_failed_questions",
            "finalize_paper": "finalize_paper"
        }
    )

    graph.add_edge("regenerate_failed_questions", "validate_questions")
    graph.add_edge("finalize_paper", END)

    return graph.compile()


if __name__ == "__main__":
    from app.llm.graph_flow import build_graph

    graph = build_graph()

    result = graph.invoke({
        "total_questions": 60,
        "cutoff_year": 2019,
        "retry_count": 0
    })

    final_qs = result.get("final_questions", result.get("validated_questions", []))

    print(f"Final questions: {len(final_qs)}")
    for q in final_qs:
        print("-" * 50)
        print(q["difficulty"], "|", q["concept"])
        print(q["question"])
