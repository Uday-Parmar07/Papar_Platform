# Rubrix

## Overview

An intelligent exam paper generation system that uses Graph RAG to create high-quality exam questions based on syllabus, previous year questions (PYQs), and domain knowledge.

**Pipeline:**
```
Syllabus (what can be asked)
↓
PYQs (what has been asked)
↓
Graph RAG (what should be asked)
↓
LLM (how it is worded)
```

## 🎯 Features

### Multi-Subject Support
- **Question Generation**: ✅ All 7 subjects supported
  - EE (Electrical Engineering)
  - CS (Computer Science)
  - CE (Civil Engineering)
  - EC (Electronics & Communication)
  - ME (Mechanical Engineering)
  - CH (Chemical Engineering)
  - MT (Metallurgical Engineering)

- **Answer Generation**: ⚡ Currently EE only (expandable)
  - Uses RAG (Retrieval Augmented Generation) with Pinecone vector store
  - LLM-powered detailed solutions with LaTeX math support
  - Context-aware answers from embedded textbooks

### Core Capabilities
- Neo4j graph database for syllabus and PYQ relationships
- Smart question distribution (frequency, recency, never-asked)
- LangGraph-based question generation workflow
- FastAPI REST API
- PDF generation for exam papers
- Question validation and verification

## 🚀 Quick Start

### Generate Questions (Any Subject)

```bash
# Electrical Engineering (with answers)
python scripts/generate_exam_with_answers.py generate \
  --subject "EE 2026" --total 10

# Computer Science (questions only)
python scripts/generate_exam_with_answers.py generate \
  --subject "CS 2026" --total 10

# See all options
python scripts/generate_exam_with_answers.py --help
```

### API Usage

```bash
# List all subjects
curl http://localhost:8000/api/v1/exam/subjects

# Generate questions for any subject
curl -X POST http://localhost:8000/api/v1/exam/generate \
  -H "Content-Type: application/json" \
  -d '{"subject": "CS 2026", "total_questions": 10, "cutoff_year": 2023}'

# Generate answers (EE only)
curl -X POST http://localhost:8000/api/v1/exam/answers \
  -H "Content-Type: application/json" \
  -d '{"questions": [...], "subject": "EE 2026"}'
```

## 📚 Documentation

- [**MULTI_SUBJECT_SUPPORT.md**](MULTI_SUBJECT_SUPPORT.md) - Comprehensive guide to multi-subject features
- [**IMPLEMENTATION_SUMMARY.md**](IMPLEMENTATION_SUMMARY.md) - Technical implementation details
- [**COMMAND_REFERENCE.md**](COMMAND_REFERENCE.md) - Quick command reference for all subjects
- [**ANSWER_GENERATION_GUIDE.md**](ANSWER_GENERATION_GUIDE.md) - Answer generation system guide

## 🏗️ Architecture

```
Rubrix/
├── app/
│   ├── api/v1/          # FastAPI endpoints
│   ├── services/        # Business logic (exam, answer generation)
│   ├── llm/             # LangGraph workflows
│   ├── rag/             # Vector store & embeddings
│   ├── graph/           # Neo4j queries & schema
│   └── schemas/         # Pydantic models
├── scripts/             # CLI tools for generation & ingestion
├── Books/               # Subject textbooks (for RAG)
└── json_syllabus/       # Structured syllabus data
```

## 🎓 Subject Support Status

| Subject | Code | Question Gen | Answer Gen | Books Available |
|---------|------|-------------|------------|-----------------|
| Electrical Engineering | EE 2026 | ✅ | ✅ | ✅ |
| Computer Science | CS 2026 | ✅ | ❌* | ❌ |
| Civil Engineering | CE 2026 | ✅ | ❌* | ❌ |
| Electronics & Comm | EC 2026 | ✅ | ❌* | ❌ |
| Mechanical Engineering | ME 2026 | ✅ | ❌* | ❌ |
| Chemical Engineering | CH 2026 | ✅ | ❌* | ❌ |
| Metallurgical Eng | MT 2026 | ✅ | ❌* | ❌ |

*To enable answer generation: Embed subject books into Pinecone vector store

## 🛠️ Setup

### Prerequisites
- Python 3.10+
- Neo4j Database
- Pinecone Account (for answer generation)
- Groq API Key (for LLM)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Ingest syllabus data
python scripts/ingest_syllabus.py

# Ingest PYQs (previous year questions)
python scripts/ingest_pyqs.py

# (Optional) Embed books for answer generation
python app/rag/embed_books.py
```

## 📖 Examples

### Run Interactive Demo
```bash
python3 examples/demo_multi_subject.py
```

### Generate Exam for Multiple Subjects
```bash
subjects=("EE 2026" "CS 2026" "CE 2026")
for subject in "${subjects[@]}"; do
  python scripts/generate_exam_with_answers.py generate \
    --subject "$subject" --total 10 --output "output/${subject// /_}"
done
```

## 🔮 Future Enhancements

- [ ] Embed books for CS, CE, EC, ME, CH, MT
- [ ] Multi-language support
- [ ] Question difficulty calibration
- [ ] Automated test paper balancing
- [ ] Student performance analytics
- [ ] Question bank management UI

## 📝 License

[Add your license here]

## 🤝 Contributing

Contributions welcome! Please see CONTRIBUTING.md for details.

---

For detailed usage instructions, see [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)
