# Generate Answers Script

This script generates comprehensive answers for exam questions using Pinecone RAG (Retrieval Augmented Generation) and Groq LLM for electrical engineering subjects.

## Features

- **RAG-based Answer Generation**: Retrieves relevant context from electrical engineering books embedded in Pinecone
- **Multi-source Context**: Automatically combines information from multiple relevant sources
- **Groq Integration**: Uses Groq's fast inference for high-quality answers
- **Batch Processing**: Generate answers for multiple questions at once
- **Flexible Input**: Supports both file-based and sample question generation

## Prerequisites

1. **Environment Setup**: Ensure `.env` contains:
   ```
   GROQ_API_KEY=<your-groq-api-key>
   PINECONE_API_KEY=<your-pinecone-api-key>
   PINECONE_INDEX_NAME=exam-books  # or your index name
   ```

2. **Embedded Data**: Electrical engineering books must be embedded in Pinecone
   ```bash
   python scripts/embed_books.py  # or your embedding script
   ```

3. **Dependencies**: Install requirements
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Generate Sample Answers

Generate answers for 3 pre-defined electrical engineering questions:
```bash
cd exam-paper-platform
python scripts/generate_answers.py --sample 3
```

### Generate Answers from Questions File

Create a JSON file with questions (e.g., `questions.json`):
```json
{
  "questions": [
    {
      "question": "What is the power factor in a three-phase circuit with Z = 10∠30° Ω?",
      "concept": "Power Factor",
      "difficulty": "Easy"
    },
    {
      "question": "Derive the expression for voltage regulation of a transmission line.",
      "concept": "Transmission Line Parameters",
      "difficulty": "Hard"
    }
  ]
}
```

Generate answers:
```bash
python scripts/generate_answers.py --input questions.json --output answers.json
```

### Advanced Options

Specify a custom Pinecone namespace:
```bash
python scripts/generate_answers.py --sample 5 --namespace "Power Electronics"
```

## Output Format

The script generates a JSON file with answers:
```json
{
  "total_questions": 2,
  "namespace": "Electrical Engineering",
  "answers": [
    {
      "question": "What is the power factor...",
      "concept": "Power Factor",
      "difficulty": "Easy",
      "answer": "The power factor is cos(30°) = 0.866 lagging...",
      "context_retrieved": true
    }
  ]
}
```

## How It Works

1. **Question Embedding**: The question is converted to an embedding using SentenceTransformer
2. **Context Retrieval**: Pinecone searches the index for the 5 most similar chunks from electrical engineering books
3. **Context Formatting**: Retrieved context is formatted with source and topic information
4. **Answer Generation**: Groq LLM generates a comprehensive answer using the question and retrieved context
5. **Result Storage**: Answers are saved to the output JSON file

## Configuration

Adjust these constants in the script:

| Setting | Default | Description |
|---------|---------|-------------|
| `RETRIEVAL_TOP_K` | 5 | Number of context chunks to retrieve per question |
| `MAX_CONTEXT_CHARS` | 4000 | Maximum context characters to include |
| `GROQ_MODEL` | mixtral-8x7b-32768 | Groq model to use |

## Example: Questions File Structure

For file-based generation, your JSON should contain:

```json
{
  "questions": [
    {
      "question": "String describing the exam question",
      "concept": "Main concept being tested",
      "difficulty": "Easy|Medium|Hard"
    }
  ]
}
```

Or as a simple list:
```json
[
  {
    "question": "...",
    "concept": "...",
    "difficulty": "..."
  }
]
```

## Troubleshooting

**Error: GROQ_API_KEY not set**
- Add `GROQ_API_KEY` to your `.env` file

**Error: PINECONE_API_KEY not set**
- Add `PINECONE_API_KEY` to your `.env` file

**No context retrieved**
- Verify that electrical engineering books are embedded in Pinecone
- Check that the index exists and is accessible
- Run the embedding script to populate the index

**Answers are generic or irrelevant**
- Ensure the question phrasing matches electrical engineering terminology
- Verify the Pinecone index contains relevant electrical engineering content
- Try increasing `RETRIEVAL_TOP_K` to retrieve more context

## Integration with Question Generation

After generating questions using `generate_exam()` from `exam_service.py`, you can directly generate answers:

```python
from services.exam_service import generate_exam
from scripts.generate_answers import generate_answer

# Generate exam questions
exam = generate_exam(
    total_questions=5,
    cutoff_year=2023,
    subject="EE",
    topics=["Power Systems", "Control Systems"]
)

# Generate answers for each question
for question in exam.questions:
    answer = generate_answer(
        question=question.question,
        concept=question.concept,
        difficulty=question.difficulty
    )
    print(f"Q: {question.question}")
    print(f"A: {answer['answer']}\n")
```

## Performance Notes

- **Embedding Time**: ~100ms per question
- **Context Retrieval**: ~50-200ms per question  
- **Answer Generation**: ~2-5 seconds per question (varies with Groq model)
- **Total Time**: ~10-15 seconds per question (dependent on model choice)

For batch processing 10 questions, expect ~2-3 minutes total.

## Future Enhancements

- [ ] Multi-threading for batch processing
- [ ] Caching of embeddings
- [ ] Support for other LLM providers (OpenAI, Claude, etc.)
- [ ] Answer quality validation
- [ ] Topic-specific prompt templates
- [ ] Integration with answer verification API
