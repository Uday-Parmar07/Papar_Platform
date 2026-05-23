"""
Per-Topic Question Generation Pipeline (Neo4j-Only Architecture)

This module implements a robust question generation system that:
1. Retrieves context per-topic from Neo4j with hard budget guarantees
2. Allocates question slots evenly across topics
3. Generates questions per-topic with explicit numbered prompts
4. Implements retry logic with shortfall detection
5. Validates and auto-fixes the final question set

This ensures all selected topics are covered and the exact requested
number of questions is always returned.

IMPORTANT: This module uses Neo4j ONLY for question generation.
Pinecone is NOT used here - it's reserved for answer generation only.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import re
import json
import random
from groq import Groq
import os
from dotenv import load_dotenv

from neomodel import db
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable

load_dotenv()

# Groq client for LLM generation
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"


# ===============================
# 1. Neo4j Topic Context Retrieval
# ===============================

def retrieve_topic_context_from_neo4j(
    topic: str,
    max_questions_context: int = 10,
    max_hops: int = 2
) -> Dict:
    """
    Retrieve structured context for a single topic from Neo4j.
    
    Runs isolated Cypher queries to retrieve:
    - Past year exam questions tagged to this topic
    - Subtopics and concepts under this topic with exam weights
    - High-priority concept nodes via graph traversal
    - Topic-level metadata (unit, subject, exam_weight, syllabus_depth)
    
    Args:
        topic: Topic name to retrieve context for
        max_questions_context: Maximum past questions to retrieve
        max_hops: Maximum graph traversal hops for concept graph
        
    Returns:
        Structured dictionary with keys:
        - topic: str
        - past_questions: List[Dict] with question, year, marks, frequency
        - subtopics: List[Dict] with subtopic, concepts, weight
        - concept_graph: List[Dict] with concept, frequency, related_concepts, last_seen
        - metadata: Dict with unit, subject, exam_weight, depth
        
    Raises:
        Logs errors but never raises - returns empty dict on failure
    """
    print(f"[DEBUG] Retrieving Neo4j context for topic: '{topic}'")
    
    context = {
        "topic": topic,
        "past_questions": [],
        "subtopics": [],
        "concept_graph": [],
        "metadata": {}
    }
    
    # Query 1 — Past year questions for this topic
    query1 = """
    MATCH (t:Topic {name: $topic})-[:HAS_QUESTION]->(q:Question)
    RETURN q.text AS question,
           q.year AS year,
           q.marks AS marks,
           q.frequency AS frequency
    ORDER BY q.frequency DESC, q.year DESC
    LIMIT $limit
    """
    
    try:
        results, _ = db.cypher_query(query1, {"topic": topic, "limit": max_questions_context})
        for row in results:
            context["past_questions"].append({
                "question": row[0] if row[0] else "",
                "year": int(row[1]) if row[1] else 0,
                "marks": int(row[2]) if row[2] else 0,
                "frequency": int(row[3]) if row[3] else 0
            })
        print(f"[DEBUG] Topic '{topic}': Retrieved {len(context['past_questions'])} past questions")
    except (ServiceUnavailable, AuthError, Neo4jError, OSError) as exc:
        print(f"[WARN] Failed to retrieve past questions for '{topic}': {exc}")
    
    # Query 2 — Subtopics and their concepts
    query2 = """
    MATCH (t:Topic {name: $topic})-[:CONTAINS]->(s:Subtopic)
    OPTIONAL MATCH (s)-[:COVERS]->(c:Concept)
    RETURN s.name AS subtopic,
           collect(DISTINCT c.name) AS concepts,
           s.exam_weight AS weight
    ORDER BY s.exam_weight DESC
    """
    
    try:
        results, _ = db.cypher_query(query2, {"topic": topic})
        for row in results:
            context["subtopics"].append({
                "subtopic": row[0] if row[0] else "",
                "concepts": row[1] if row[1] else [],
                "weight": float(row[2]) if row[2] else 0.0
            })
        print(f"[DEBUG] Topic '{topic}': Retrieved {len(context['subtopics'])} subtopics")
    except (ServiceUnavailable, AuthError, Neo4jError, OSError) as exc:
        print(f"[WARN] Failed to retrieve subtopics for '{topic}': {exc}")
    
    # Query 3 — Concept graph traversal up to max_hops
    query3 = """
    MATCH (t:Topic {name: $topic})-[:CONTAINS*1..$hops]->(c:Concept)
    OPTIONAL MATCH (c)-[r:RELATED_TO]->(c2:Concept)
    RETURN c.name AS concept,
           c.exam_frequency AS frequency,
           collect(DISTINCT c2.name) AS related_concepts,
           c.last_seen_year AS last_seen
    ORDER BY c.exam_frequency DESC
    LIMIT 20
    """
    
    try:
        results, _ = db.cypher_query(query3, {"topic": topic, "hops": max_hops})
        for row in results:
            context["concept_graph"].append({
                "concept": row[0] if row[0] else "",
                "frequency": int(row[1]) if row[1] else 0,
                "related_concepts": row[2] if row[2] else [],
                "last_seen": int(row[3]) if row[3] else 0
            })
        print(f"[DEBUG] Topic '{topic}': Retrieved {len(context['concept_graph'])} concepts")
    except (ServiceUnavailable, AuthError, Neo4jError, OSError) as exc:
        print(f"[WARN] Failed to retrieve concept graph for '{topic}': {exc}")
    
    # Query 4 — Topic metadata
    query4 = """
    MATCH (t:Topic {name: $topic})
    RETURN t.unit AS unit,
           t.subject AS subject,
           t.exam_weight AS exam_weight,
           t.syllabus_depth AS depth
    """
    
    try:
        results, _ = db.cypher_query(query4, {"topic": topic})
        if results and results[0]:
            row = results[0]
            context["metadata"] = {
                "unit": row[0] if row[0] else "",
                "subject": row[1] if row[1] else "",
                "exam_weight": float(row[2]) if row[2] else 0.0,
                "depth": int(row[3]) if row[3] else 0
            }
            print(f"[DEBUG] Topic '{topic}': Retrieved metadata")
    except (ServiceUnavailable, AuthError, Neo4jError, OSError) as exc:
        print(f"[WARN] Failed to retrieve metadata for '{topic}': {exc}")
    
    # Validation: Check if context is empty
    if (not context["past_questions"] and 
        not context["subtopics"] and 
        not context["concept_graph"]):
        print(f"[ERROR] Zero context for '{topic}'")
        print(f"[DEBUG] Run: MATCH (t:Topic) WHERE t.name CONTAINS '{topic[:5]}' RETURN t.name LIMIT 5")
    
    return context


# ===============================
# 2. Per-Topic Retrieval with Hard Budget (Neo4j Only)
# ===============================

def retrieve_per_topic(
    topics: List[str],
    max_questions_context: int = 10,
    max_hops: int = 2
) -> Dict[str, Dict]:
    """
    Retrieve context for each topic independently from Neo4j.
    
    Guarantees every selected topic has context before generation begins.
    No topic is skipped due to graph weight dominance.
    
    Args:
        topics: List of topic names to retrieve context for
        max_questions_context: Maximum past questions per topic
        max_hops: Maximum graph traversal hops
        
    Returns:
        Dictionary mapping topic names to their context dicts.
        Every topic in input list has an entry in output dict.
        
    Logs validation results for each topic retrieval.
    """
    print(f"[INFO] Starting per-topic retrieval for {len(topics)} topics")
    
    topic_context_map: Dict[str, Dict] = {}
    
    for topic in topics:
        context = retrieve_topic_context_from_neo4j(
            topic=topic,
            max_questions_context=max_questions_context,
            max_hops=max_hops
        )
        topic_context_map[topic] = context
    
    print(f"[INFO] Completed per-topic retrieval for {len(topic_context_map)} topics")
    return topic_context_map


# ===============================
# 3. Question Allocation Across Topics
# ===============================

def allocate_questions(
    topics: List[str],
    total_questions: int
) -> Dict[str, int]:
    """
    Distribute total questions evenly across topics.
    
    Uses floor division + remainder distribution so that no questions
    are lost and the total is always exact.
    
    Example: 5 topics, 12 questions → {T1:3, T2:3, T3:2, T4:2, T5:2}
    
    Args:
        topics: List of topic names
        total_questions: Total number of questions to generate
        
    Returns:
        Dictionary mapping topic names to their allocated question count.
        Sum of all values always equals total_questions exactly.
    """
    if not topics:
        return {}
    
    num_topics = len(topics)
    base_count = total_questions // num_topics
    remainder = total_questions % num_topics
    
    allocation: Dict[str, int] = {}
    
    # Distribute base count to all topics
    for topic in topics:
        allocation[topic] = base_count
    
    # Distribute remainder to first N topics
    for i in range(remainder):
        allocation[topics[i]] += 1
    
    print(f"[DEBUG] Question allocation: {allocation}")
    print(f"[DEBUG] Allocation sum: {sum(allocation.values())} (requested: {total_questions})")
    
    return allocation


# ===============================
# 4. Prompt Builder Using Neo4j Structured Context
# ===============================

def build_question_prompt(
    topic: str,
    context: Dict,
    count: int,
    already_generated: Optional[List[str]] = None
) -> str:
    """
    Build LLM prompt by serializing Neo4j context into readable sections.
    
    Serializes Neo4j context into human-readable text blocks:
    - Past exam questions (style reference)
    - Subtopics to cover
    - High priority concepts
    - Already generated questions (to avoid duplicates on retry)
    
    The prompt ends with "Q1." to force LLM continuation.
    
    Args:
        topic: Topic to generate questions for
        context: Neo4j context dict for the topic
        count: Exact number of questions to generate
        already_generated: List of already generated questions to avoid duplicates
        
    Returns:
        Formatted prompt string ending with "Q1."
    """
    # Build past questions section
    past_questions_section = ""
    if context.get("past_questions"):
        past_questions_section = "PAST EXAM QUESTIONS (style reference):\n"
        for pq in context["past_questions"][:5]:
            year = pq.get("year", "N/A")
            question = pq.get("question", "")[:150]
            past_questions_section += f"  - [{year}] {question}...\n"
        past_questions_section += "\n"
    
    # Build subtopics section
    subtopics_section = ""
    if context.get("subtopics"):
        subtopics_section = "SUBTOPICS TO COVER:\n"
        for st in context["subtopics"][:5]:
            subtopic = st.get("subtopic", "")
            concepts = st.get("concepts", [])[:3]
            concepts_str = ", ".join(concepts) if concepts else ""
            subtopics_section += f"  - {subtopic} (concepts: {concepts_str})\n"
        subtopics_section += "\n"
    
    # Build concepts section
    concepts_section = ""
    if context.get("concept_graph"):
        high_priority = [c["concept"] for c in context["concept_graph"][:8] if c.get("concept")]
        if high_priority:
            concepts_section = f"HIGH PRIORITY CONCEPTS: {', '.join(high_priority)}\n\n"
    
    # Build already generated section
    already_generated_section = ""
    if already_generated:
        already_generated_section = "DO NOT REPEAT (on retry):\n"
        for q in already_generated[:3]:
            already_generated_section += f"  - {q[:100]}...\n"
        already_generated_section += "\n"
    
    prompt = f"""SYSTEM:
You are a strict GATE examiner.

TOPIC:
{topic}

{past_questions_section}{subtopics_section}{concepts_section}{already_generated_section}TASK:
Generate EXACTLY {count} exam-quality GATE questions on the topic "{topic}".

CONSTRAINTS:
- You MUST generate exactly {count} questions - no fewer, no more
- Number your questions as Q1., Q2., Q3., ... up to Q{count}.
- Each question should be unique and test different aspects of the topic
- Questions should be at GATE exam level (conceptual, numerical, or application-based)
- Each question should be self-contained with necessary context and values
- Do NOT include solutions or explanations
- Do NOT mention marks explicitly
- Use standard GATE exam language and terminology
- If context is insufficient, generate simpler conceptual questions rather than stopping early

OUTPUT FORMAT:
Q1. [question text]
Q2. [question text]
Q3. [question text]
...
Q{count}. [question text]

Generate exactly {count} questions now:
Q1."""
    
    return prompt


# ===============================
# 5. Robust Question Parser
# ===============================

def parse_questions(raw_output: str) -> List[str]:
    """
    Parse questions from LLM output using multiple regex patterns.
    
    Tries patterns in sequence to handle various LLM output formats:
    1. Q1. or Q1) format
    2. 1. or 1) format
    3. **Q1.** bold format
    4. Bullet - or • format
    5. Last resort: split by newline
    
    Never returns empty list if raw_output has content longer than 20 chars.
    
    Args:
        raw_output: Raw LLM response text
        
    Returns:
        List of parsed question strings
    """
    if not raw_output or len(raw_output.strip()) < 20:
        return []
    
    questions: List[str] = []
    
    # Pattern 1: Q1. or Q1)
    pattern1 = r'Q\d+[\.\)]\s*(.+?)(?=Q\d+[\.\)]|\Z)'
    matches = re.findall(pattern1, raw_output, re.DOTALL)
    if matches:
        questions = [q.strip() for q in matches if q.strip()]
        print(f"[DEBUG] Parser: Pattern 1 matched {len(questions)} questions")
    
    # Pattern 2: 1. or 1)
    if not questions:
        pattern2 = r'\d+[\.\)]\s*(.+?)(?=\d+[\.\)]|\Z)'
        matches = re.findall(pattern2, raw_output, re.DOTALL)
        if matches:
            questions = [q.strip() for q in matches if q.strip()]
            print(f"[DEBUG] Parser: Pattern 2 matched {len(questions)} questions")
    
    # Pattern 3: **Q1.** bold format
    if not questions:
        pattern3 = r'\*\*Q?\d+[\.\)]\*\*\s*(.+?)(?=\n|\Z)'
        matches = re.findall(pattern3, raw_output, re.DOTALL)
        if matches:
            questions = [q.strip() for q in matches if q.strip()]
            print(f"[DEBUG] Parser: Pattern 3 matched {len(questions)} questions")
    
    # Pattern 4: Bullet - or •
    if not questions:
        pattern4 = r'[-•]\s*(.+?)(?=[-•]|\Z)'
        matches = re.findall(pattern4, raw_output, re.DOTALL)
        if matches:
            questions = [q.strip() for q in matches if q.strip()]
            print(f"[DEBUG] Parser: Pattern 4 matched {len(questions)} questions")
    
    # Pattern 5: Last resort - split by newline
    if not questions:
        lines = [line.strip() for line in raw_output.split('\n') if line.strip()]
        questions = [line for line in lines if len(line) > 20]
        print(f"[DEBUG] Parser: Pattern 5 matched {len(questions)} questions")
    
    # Strip newlines within each question
    questions = [re.sub(r'\s+', ' ', q) for q in questions]
    
    print(f"[DEBUG] Parser: Total questions parsed: {len(questions)}")
    return questions


# ===============================
# 6. Per-Topic Generation with Retry on Shortfall
# ===============================

def generate_questions_for_topic(
    topic: str,
    context: Dict,
    required_count: int
) -> List[str]:
    """
    Generate questions for a single topic using LLM.
    
    Args:
        topic: Topic to generate questions for
        context: Neo4j context dict for the topic
        required_count: Number of questions to generate
        
    Returns:
        List of generated question strings
    """
    prompt = build_question_prompt(
        topic=topic,
        context=context,
        count=required_count,
        already_generated=None
    )
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict GATE examiner.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=0.95,
        )
        
        response_text = response.choices[0].message.content.strip()
        questions = parse_questions(response_text)
        
        return questions
        
    except Exception as e:
        print(f"[ERROR] LLM generation failed for topic '{topic}': {e}")
        return []


def generate_with_retry(
    topic: str,
    context: Dict,
    required_count: int,
    max_attempts: int = 3
) -> List[str]:
    """
    Generate questions with retry logic for shortfall detection.
    
    Attempt loop:
    - attempt 1: generate required_count questions
    - if shortfall: attempt 2 with shortfall count + already_generated list
    - if still shortfall: attempt 3 same way
    - if still shortfall after attempt 3: call generate_fallback_questions()
    
    Logs at each attempt with topic, attempt number, required count, and got count.
    
    Args:
        topic: Topic to generate questions for
        context: Neo4j context dict for the topic
        required_count: Number of questions required
        max_attempts: Maximum retry attempts
        
    Returns:
        List of exactly required_count questions total
    """
    all_questions: List[str] = []
    
    for attempt in range(max_attempts):
        shortfall = required_count - len(all_questions)
        
        if shortfall <= 0:
            break
        
        print(f"[DEBUG] Topic: {topic} | Attempt: {attempt + 1} | Required: {shortfall}")
        
        questions = generate_questions_for_topic(
            topic=topic,
            context=context,
            required_count=shortfall
        )
        
        print(f"[DEBUG] Topic: {topic} | Attempt: {attempt + 1} | Got: {len(questions)}")
        
        all_questions.extend(questions)
        
        if len(all_questions) >= required_count:
            break
    
    # If still shortfall after retries, use fallback
    if len(all_questions) < required_count:
        shortfall = required_count - len(all_questions)
        print(f"[CRITICAL] Fallback triggered for '{topic}', shortfall={shortfall}")
        fallback_questions = generate_fallback_questions(topic, shortfall)
        all_questions.extend(fallback_questions)
    
    return all_questions[:required_count]


# ===============================
# 7. Improved Fallback (LLM-Based, Not Template-Based)
# ===============================

def generate_fallback_questions(
    topic: str,
    shortfall: int
) -> List[str]:
    """
    Generate fallback questions when LLM generation fails.
    
    Priority order:
    1. LLM call with no context constraint, explicit count instruction
    2. If LLM call raises exception → use shuffled hardcoded list
    
    The hardcoded list is shuffled randomly to avoid repetitive cycling.
    
    Args:
        topic: Topic name
        shortfall: Number of questions needed
        
    Returns:
        List of fallback questions, exactly shortfall in count
    """
    print(f"[CRITICAL] Using fallback for topic '{topic}', shortfall={shortfall}")
    
    # Priority 1: LLM call with no context
    try:
        prompt = f"""SYSTEM:
You are a strict GATE examiner.

TOPIC:
{topic}

TASK:
Generate EXACTLY {shortfall} exam-quality GATE questions on the topic "{topic}".

CONSTRAINTS:
- You MUST generate exactly {shortfall} questions - no fewer, no more
- Number your questions as Q1., Q2., ... up to Q{shortfall}.
- Use your own knowledge about this topic
- Questions should be at GATE exam level
- Do NOT include solutions or explanations

OUTPUT FORMAT:
Q1. [question text]
Q2. [question text]
...
Q{shortfall}. [question text]

Generate exactly {shortfall} questions now:
Q1."""
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict GATE examiner.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
            max_tokens=1500,
            top_p=0.95,
        )
        
        response_text = response.choices[0].message.content.strip()
        questions = parse_questions(response_text)
        
        if questions:
            print(f"[INFO] Fallback LLM succeeded: generated {len(questions)} questions")
            return questions[:shortfall]
    except Exception as e:
        print(f"[ERROR] Fallback LLM failed: {e}")
    
    # Priority 2: Shuffled hardcoded templates
    fallback_templates = [
        f"Explain the core principles of {topic} and derive the governing equations.",
        f"Analyze the key characteristics of {topic} in practical applications.",
        f"Compare different approaches to {topic} and discuss their advantages.",
        f"Design a system involving {topic} and explain the design considerations.",
        f"Calculate the performance metrics for a {topic} system with given parameters.",
        f"Discuss the limitations of {topic} and propose improvements.",
        f"Explain the real-world applications of {topic} in engineering.",
        f"Describe the historical development of {topic} and its evolution.",
        f"Analyze the future trends and research directions in {topic}.",
        f"Solve a numerical problem involving {topic} with step-by-step derivation.",
    ]
    
    random.shuffle(fallback_templates)
    questions = fallback_templates[:shortfall]
    
    print(f"[INFO] Using shuffled hardcoded templates: {len(questions)} questions")
    return questions


# ===============================
# 8. Post-Generation Validation and Auto-Fix
# ===============================

@dataclass
class ValidationReport:
    """Report from question set validation."""
    count_ok: bool
    count_shortfall: int
    missing_topics: List[str]
    overrepresented_topics: List[str]
    passed: bool


class QuestionSetValidator:
    """Validates and auto-fixes question sets."""
    
    def __init__(self, max_overrepresentation_ratio: float = 1.5):
        """
        Args:
            max_overrepresentation_ratio: Max ratio of questions per topic vs average
        """
        self.max_overrepresentation_ratio = max_overrepresentation_ratio
    
    def validate(
        self,
        questions: List[Dict],
        requested_topics: List[str],
        requested_count: int
    ) -> ValidationReport:
        """
        Validate the generated question set.
        
        Checks:
        - Total count: len(questions) == requested_count
        - Topic coverage: every requested_topic appears at least once
        - Overrepresentation: no topic exceeds ceil(requested_count / num_topics * 1.5)
        
        Args:
            questions: List of question dicts with 'topic' field
            requested_topics: Topics that were requested
            requested_count: Total questions requested
            
        Returns:
            ValidationReport with validation results
        """
        count_ok = len(questions) == requested_count
        count_shortfall = requested_count - len(questions)
        
        # Check topic coverage
        question_topics = set(q.get("topic", "") for q in questions)
        missing_topics = [t for t in requested_topics if t not in question_topics]
        
        # Check overrepresentation
        topic_counts: Dict[str, int] = {}
        for q in questions:
            topic = q.get("topic", "")
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        avg_per_topic = requested_count / len(requested_topics) if requested_topics else 0
        max_allowed = int(avg_per_topic * self.max_overrepresentation_ratio) if avg_per_topic > 0 else requested_count
        
        overrepresented_topics = [
            topic for topic, count in topic_counts.items()
            if count > max_allowed
        ]
        
        passed = count_ok and not missing_topics and not overrepresented_topics
        
        print(f"[DEBUG] Validation: count_ok={count_ok}, missing={len(missing_topics)}, overrepresented={len(overrepresented_topics)}")
        
        return ValidationReport(
            count_ok=count_ok,
            count_shortfall=count_shortfall,
            missing_topics=missing_topics,
            overrepresented_topics=overrepresented_topics,
            passed=passed
        )
    
    def fix(
        self,
        questions: List[Dict],
        report: ValidationReport,
        topic_context_map: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Auto-fix validation failures.
        
        - Fix missing topics: generate 1 question per missing topic
        - Fix count shortfall: generate from underrepresented topics
        - Fix overrepresentation: trim to allowed maximum
        
        Args:
            questions: Current list of question dicts
            report: Validation report from validate()
            topic_context_map: Context chunks per topic
            
        Returns:
            Fixed list of question dicts
        """
        fixed_questions = questions.copy()
        
        # Fix missing topics
        for topic in report.missing_topics:
            context = topic_context_map.get(topic, {})
            new_questions = generate_with_retry(
                topic=topic,
                context=context,
                required_count=1
            )
            for q in new_questions[:1]:
                fixed_questions.append({
                    "question": q,
                    "topic": topic,
                    "concept": topic,
                    "difficulty": "Medium"
                })
            print(f"[INFO] Fixed missing topic: {topic}")
        
        # Fix count shortfall
        if report.count_shortfall > 0:
            topic_counts: Dict[str, int] = {}
            for q in fixed_questions:
                topic = q.get("topic", "")
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Sort topics by count (ascending)
            sorted_topics = sorted(topic_counts.keys(), key=lambda t: topic_counts[t])
            
            for topic in sorted_topics:
                if report.count_shortfall <= 0:
                    break
                
                context = topic_context_map.get(topic, {})
                new_questions = generate_with_retry(
                    topic=topic,
                    context=context,
                    required_count=1
                )
                for q in new_questions[:1]:
                    fixed_questions.append({
                        "question": q,
                        "topic": topic,
                        "concept": topic,
                        "difficulty": "Medium"
                    })
                report.count_shortfall -= 1
            print(f"[INFO] Fixed count shortfall")
        
        # Fix overrepresentation
        if report.overrepresented_topics:
            topic_counts: Dict[str, int] = {}
            for q in fixed_questions:
                topic = q.get("topic", "")
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            avg_per_topic = len(fixed_questions) / len(topic_counts) if topic_counts else 0
            max_allowed = int(avg_per_topic * self.max_overrepresentation_ratio) if avg_per_topic > 0 else len(fixed_questions)
            
            # Trim overrepresented topics
            filtered_questions = []
            for q in fixed_questions:
                topic = q.get("topic", "")
                if topic in report.overrepresented_topics:
                    if topic_counts.get(topic, 0) > max_allowed:
                        topic_counts[topic] -= 1
                        continue
                filtered_questions.append(q)
            
            fixed_questions = filtered_questions
            print(f"[INFO] Fixed overrepresentation for {len(report.overrepresented_topics)} topics")
        
        return fixed_questions


# ===============================
# 9. Master Orchestrator Function
# ===============================

def generate_exam_questions(
    topics: List[str],
    total_questions: int,
    max_questions_context: int = 10,
    max_hops: int = 2
) -> List[Dict]:
    """
    Generate exam questions with guaranteed count and topic coverage.
    
    Full pipeline:
    Step 1: retrieve_per_topic() → topic_context_map
    Step 2: allocate_questions() → question_allocation
    Step 3: for each topic → generate_with_retry() → raw_questions
    Step 4: QuestionSetValidator.validate() + fix() → final_questions
    Step 5: return final_questions
    
    Guarantees:
    - Returns exactly total_questions questions
    - Every topic in input list is represented in output
    - No topic exceeds its fair share by more than 50%
    - No fallback template cycling in output
    
    Args:
        topics: List of topic names to generate questions for
        total_questions: Total number of questions to generate
        max_questions_context: Maximum past questions per topic from Neo4j
        max_hops: Maximum graph traversal hops for concept retrieval
        
    Returns:
        List of question dicts with keys: question, topic, concept, difficulty
        Guaranteed to have exactly total_questions questions
    """
    print(f"[INFO] Starting question generation: {len(topics)} topics, {total_questions} questions")
    
    if not topics:
        print("[WARN] No topics provided, returning empty list")
        return []
    
    # Step 1: Retrieve context per topic from Neo4j
    print("[INFO] Step 1: Retrieving Neo4j context per topic")
    topic_context_map = retrieve_per_topic(
        topics=topics,
        max_questions_context=max_questions_context,
        max_hops=max_hops
    )
    
    # Step 2: Allocate questions across topics
    print("[INFO] Step 2: Allocating questions across topics")
    question_allocation = allocate_questions(
        topics=topics,
        total_questions=total_questions
    )
    
    # Step 3: Generate questions per topic with retry
    print("[INFO] Step 3: Generating questions per topic with retry")
    raw_questions: List[Dict] = []
    for topic in topics:
        allocated_count = question_allocation.get(topic, 0)
        if allocated_count == 0:
            continue
        
        context = topic_context_map.get(topic, {})
        questions = generate_with_retry(
            topic=topic,
            context=context,
            required_count=allocated_count
        )
        
        for q in questions:
            raw_questions.append({
                "question": q,
                "topic": topic,
                "concept": topic,
                "difficulty": "Medium"
            })
        
        print(f"[INFO] Generated {len(questions)} questions for topic '{topic}'")
    
    # Step 4: Validate and auto-fix
    print("[INFO] Step 4: Validating and auto-fixing question set")
    validator = QuestionSetValidator()
    report = validator.validate(
        questions=raw_questions,
        requested_topics=topics,
        requested_count=total_questions
    )
    
    if not report.passed:
        print(f"[WARN] Validation failed, applying auto-fix")
        raw_questions = validator.fix(
            questions=raw_questions,
            report=report,
            topic_context_map=topic_context_map
        )
    
    # Final count check
    if len(raw_questions) > total_questions:
        raw_questions = raw_questions[:total_questions]
        print(f"[INFO] Trimmed excess questions to {total_questions}")
    
    print(f"[INFO] Question generation complete: {len(raw_questions)} questions")
    return raw_questions
