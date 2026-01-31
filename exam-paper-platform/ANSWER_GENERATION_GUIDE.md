# Answer Generation System - Complete Guide

## Overview

This answer generation system leverages **Pinecone RAG** (Retrieval Augmented Generation) and **Groq LLM** to create comprehensive, context-aware answers for electrical engineering exam questions.

The system consists of three main components:

1. **`generate_answers.py`** - Core script for generating answers
2. **`generate_exam_with_answers.py`** - Complete workflow script
3. **`vector_store.py`** - Enhanced with query() method for RAG

## Architecture

```
Question Input
    ↓
Embedding (SentenceTransformer)
    ↓
Pinecone Vector Store Query
    ↓
Context Retrieval (Top-K similar chunks)
    ↓
LLM Prompt Construction
    ↓
Groq LLM Generation
    ↓
Answer Output
```

## Components

### 1. Core Answer Generation (`generate_answers.py`)

**Purpose**: Generate answers for electrical engineering questions using Pinecone RAG

**Key Functions**:
- `retrieve_context()` - Query Pinecone for relevant content
- `generate_answer()` - Generate answer using Groq with context
- `generate_answers_from_file()` - Batch process questions from JSON
- `generate_sample_answers()` - Generate sample answers for testing

**Usage**:
```bash
# Generate sample answers
python scripts/generate_answers.py --sample 3

# From questions file
python scripts/generate_answers.py --input questions.json --output answers.json

# Custom namespace
python scripts/generate_answers.py --sample 5 --namespace "Power Electronics"
```

### 2. Complete Workflow (`generate_exam_with_answers.py`)

**Purpose**: End-to-end workflow from question generation to answer generation

**Key Functions**:
- `generate_complete_exam()` - Generate questions and answers
- `generate_from_file()` - Generate answers for existing questions

**Usage**:
```bash
# Generate 10 questions + answers
python scripts/generate_exam_with_answers.py generate --total 10 --subject EE

# Generate answers for existing questions
python scripts/generate_exam_with_answers.py from-file questions.json
```

### 3. Vector Store Enhancement (`vector_store.py`)

**New Method**: `query()`
- Queries Pinecone index for similar vectors
- Returns matched chunks with metadata
- Handles errors gracefully

## Setup Instructions

### Prerequisites

1. **Python Environment**
   ```bash
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Environment Variables** (`.env`)
   ```env
   GROQ_API_KEY=your_groq_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_INDEX_NAME=exam-books
   SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
   ```

3. **Data Preparation**
   ```bash
   # Embed electrical engineering books into Pinecone
   python scripts/embed_books.py
   ```

## Usage Examples

### Example 1: Generate Sample Answers

```bash
python scripts/generate_answers.py --sample 3
```

**Output**: `answers.json`
```json
{
  "total_questions": 3,
  "namespace": "Electrical Engineering",
  "answers": [
    {
      "question": "A 3-phase synchronous motor...",
      "concept": "Synchronous Motor Operation",
      "difficulty": "Medium",
      "answer": "When excitation is increased...",
      "context_retrieved": true
    }
  ]
}
```

### Example 2: Generate from Questions File

**Create** `my_questions.json`:
```json
{
  "questions": [
    {
      "question": "What is the relationship between voltage and current in an inductor?",
      "concept": "AC Circuits",
      "difficulty": "Easy"
    },
    {
      "question": "Derive the expression for voltage regulation of a transformer.",
      "concept": "Transformer Theory",
      "difficulty": "Hard"
    }
  ]
}
```

**Generate answers**:
```bash
python scripts/generate_answers.py --input my_questions.json --output my_answers.json
```

### Example 3: Complete Exam Generation

```bash
# Generate 5 new questions + answers in one command
python scripts/generate_exam_with_answers.py generate --total 5 --subject EE --topics "Power Systems" "Control Systems"
```

**Output Files**:
- `exam_output/questions.json` - Questions only
- `exam_output/answers.json` - Answers only
- `exam_output/exam_with_solutions.json` - Combined Q&A

### Example 4: Python API Integration

```python
from scripts.generate_answers import generate_answer
from services.exam_service import generate_exam

# Generate exam questions
exam = generate_exam(
    total_questions=3,
    cutoff_year=2023,
    subject="EE"
)

# Generate answers for each question
results = []
for question in exam.questions:
    answer = generate_answer(
        question=question.question,
        concept=question.concept,
        difficulty=question.difficulty
    )
    results.append(answer)
    print(f"Q: {question.question}")
    print(f"A: {answer['answer']}\n")
```

## How It Works

### Step 1: Question Embedding
```python
from app.rag.embeddings import embed_texts

question = "What is the efficiency of a transformer?"
embedding = embed_texts([question])[0]  # Returns 384-dimensional vector
```

### Step 2: Context Retrieval
```python
from app.rag.vector_store import PineconeVectorStore

store = PineconeVectorStore(index_name="exam-books")
results = store.query(
    vector=embedding,
    top_k=5,
    namespace="Electrical Engineering",
    include_metadata=True
)
# Returns top 5 matching chunks with metadata
```

### Step 3: Answer Generation
```python
from groq import Groq

client = Groq(api_key="your_key")
message = client.messages.create(
    model="mixtral-8x7b-32768",
    messages=[{"role": "user", "content": prompt_with_context}]
)
answer = message.content[0].text
```

## Configuration Tuning

### Retrieval Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| `RETRIEVAL_TOP_K` | 5 | More context = potentially better answers but slower |
| `MAX_CONTEXT_CHARS` | 4000 | Limits context size to keep prompts manageable |

### LLM Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `model` | mixtral-8x7b-32768 | Fast, good quality for educational content |
| `max_tokens` | 2000 | Maximum answer length |

### Embedding Model

| Setting | Default | Notes |
|---------|---------|-------|
| `SENTENCE_TRANSFORMER_MODEL` | all-MiniLM-L6-v2 | 384-dim, lightweight, good for EE domain |

## Performance Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Embedding | ~100ms | Per question |
| Pinecone Query | ~50-200ms | Network dependent |
| LLM Generation | ~2-5s | Varies by answer complexity |
| **Total per Q** | ~10-15s | End-to-end |
| **Batch of 5** | ~1-2 min | ~12-15s per question |
| **Batch of 10** | ~2-3 min | ~12-18s per question |

## Troubleshooting

### Issue: "No context retrieved"

**Causes**:
- Books not embedded in Pinecone
- Wrong index name
- Pinecone connectivity issues

**Solutions**:
```bash
# Check Pinecone index exists
python -c "from app.rag.vector_store import PineconeVectorStore; store = PineconeVectorStore()"

# Embed books
python scripts/embed_books.py

# Verify index has data
python -c "
from app.rag.vector_store import PineconeVectorStore
store = PineconeVectorStore()
print(store.index.describe_index_stats())
"
```

### Issue: "API Key not found"

**Solution**:
```bash
# Verify .env file exists and contains:
cat .env | grep GROQ_API_KEY
cat .env | grep PINECONE_API_KEY
```

### Issue: "Generic or irrelevant answers"

**Causes**:
- Poor question phrasing
- Insufficient context in knowledge base
- Domain mismatch

**Solutions**:
1. Use more specific technical terminology in questions
2. Increase `RETRIEVAL_TOP_K` to get more context
3. Verify books are from electrical engineering domain
4. Try different embedding model

### Issue: "Rate limiting from Groq"

**Solution**:
- Add delay between requests
- Use batch processing with delays
- Check Groq API limits

## Advanced Usage

### Custom Prompt Templates

Modify `build_answer_prompt()` in `generate_answers.py`:

```python
def build_answer_prompt(question, concept, difficulty, context):
    # Custom template for specific domains
    if "transformer" in concept.lower():
        return f"""..."""
    # Default template
    return f"""..."""
```

### Caching Embeddings

```python
import pickle

# Cache embeddings to avoid recomputation
embedding_cache = {}

def get_embedding(text):
    if text not in embedding_cache:
        embedding_cache[text] = embed_texts([text])[0]
    return embedding_cache[text]
```

### Multi-threading

```python
from concurrent.futures import ThreadPoolExecutor

def generate_answers_parallel(questions, max_workers=3):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(generate_answer, questions))
    return results
```

## Integration Points

### With Question Generation
```python
from services.exam_service import generate_exam
from scripts.generate_answers import generate_answer

exam = generate_exam(total_questions=5, subject="EE")
for q in exam.questions:
    answer = generate_answer(q.question, q.concept, q.difficulty)
```

### With PDF Generation
```python
from services.pdf_service import generate_pdf

# Generate answers first
answers = generate_answers_from_file("questions.json", "answers.json")

# Create PDF with Q&A
generate_pdf(
    questions_file="questions.json",
    answers_file="answers.json",
    output_file="exam_with_solutions.pdf"
)
```

### With Database Storage
```python
import json

# Save to database
with open("answers.json") as f:
    data = json.load(f)
    for answer in data["answers"]:
        # Save to your database
        store_answer_in_db(answer)
```

## Next Steps

1. **Test with Sample Data**
   ```bash
   python scripts/generate_answers.py --sample 3
   ```

2. **Verify Pinecone Integration**
   ```bash
   # Check if books are embedded
   python -c "from app.rag.vector_store import PineconeVectorStore; PineconeVectorStore()"
   ```

3. **Generate Real Exam**
   ```bash
   python scripts/generate_exam_with_answers.py generate --total 5
   ```

4. **Review and Validate**
   - Check output JSON files
   - Review answer quality
   - Iterate on prompts if needed

5. **Deploy to Production**
   - Integrate with your exam system
   - Add answer storage/retrieval
   - Implement caching if needed

## Support & Debugging

For issues, check:

1. **Environment**: `.env` file setup
2. **Dependencies**: `pip list | grep -E "groq|pinecone|langchain"`
3. **Logs**: Add `-v` flag for verbose output
4. **Connectivity**: Test API keys manually

```bash
# Test Groq
python -c "from groq import Groq; Groq().models.list()"

# Test Pinecone
python -c "from pinecone import Pinecone; Pinecone().list_indexes()"
```

## References

- [Pinecone Documentation](https://docs.pinecone.io/)
- [Groq API Reference](https://console.groq.com/docs/api)
- [LangChain RAG Guide](https://python.langchain.com/docs/use_cases/question_answering/)
- [Sentence Transformers](https://www.sbert.net/)
