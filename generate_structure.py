from pathlib import Path

BASE_DIR = Path("exam-paper-platform")

STRUCTURE = {
    "app": {
        "main.py": "",
        "core": {
            "config.py": "",
            "logging.py": "",
            "security.py": "",
        },
        "api": {
            "v1": {
                "__init__.py": "",
                "exam.py": "",
                "auth.py": "",
                "health.py": "",
            }
        },
        "db": {
            "base.py": "",
            "session.py": "",
            "models": {
                "user.py": "",
                "exam_request.py": "",
            },
        },
        "graph": {
            "neo4j.py": "",
            "schema.py": "",
            "queries.py": "",
            "validators.py": "",
        },
        "rag": {
            "embeddings.py": "",
            "vector_store.py": "",
            "retriever.py": "",
            "prompts": {
                "question.txt": "",
                "paper.txt": "",
            },
        },
        "llm": {
            "models.py": "",
            "graph_flow.py": "",
            "nodes": {
                "concept_select.py": "",
                "retrieve.py": "",
                "generate.py": "",
                "validate.py": "",
            },
        },
        "evaluation": {
            "metrics.py": "",
            "judges.py": "",
            "scorer.py": "",
        },
        "services": {
            "exam_service.py": "",
            "pdf_service.py": "",
        },
        "schemas": {
            "exam.py": "",
            "auth.py": "",
            "response.py": "",
        },
        "utils": {
            "exceptions.py": "",
            "constants.py": "",
            "helpers.py": "",
        },
    },
    "scripts": {
        "ingest_syllabus.py": "",
        "ingest_pyqs.py": "",
        "rebuild_graph.py": "",
    },
    "tests": {
        "unit": {
            "test_graph.py": "",
            "test_rag.py": "",
            "test_eval.py": "",
        },
        "integration": {
            "test_generate_paper.py": "",
        },
        "conftest.py": "",
    },
    "migrations": {},
    ".env.example": "",
    ".gitignore": "",
    ".python-version": "3.10.13\n",
    "requirements.txt": "",
    "README.md": "# Exam Paper Prediction Platform\n",
    "docker-compose.yml": "",
}


def create_structure(base: Path, structure: dict):
    for name, content in structure.items():
        path = base / name
        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            create_structure(path, content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
            if content:
                path.write_text(content)


if __name__ == "__main__":
    BASE_DIR.mkdir(exist_ok=True)
    create_structure(BASE_DIR, STRUCTURE)
    print(f"✅ Project structure created at: {BASE_DIR.resolve()}")
