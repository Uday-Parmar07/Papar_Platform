"""
Grading Service — FastAPI Endpoint for Two-Stage Answer Grading
=================================================================
Stage 1: Fast screening (CPU, <50ms) — Cross-Encoder + heuristic flags
Stage 2: Deep reasoning (GPU, ~500ms) — Neo4j concept graph + LLM rubric

Usage:
    uvicorn grading.grading_service:app --host 0.0.0.0 --port 8001
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=False)

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from grading.stage1_fast_screen import FastScreeningPipeline
from grading.metrics.flag_rate_tracker import log_screening_decision, get_flag_rate_report

# ── Optional imports (gracefully degrade if not available) ─────────────
try:
    import redis
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
    )
    redis_client.ping()
    print("[GRADING] Redis connected.")
except Exception as e:
    redis_client = None
    print(f"[GRADING] Redis unavailable ({e}). Caching disabled.")

try:
    from sqlalchemy import create_engine
    pg_url = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", ""))
    if pg_url:
        audit_db = create_engine(pg_url)
        print("[GRADING] PostgreSQL audit DB connected.")
    else:
        audit_db = None
        print("[GRADING] No DATABASE_URL set. Audit logging disabled.")
except Exception as e:
    audit_db = None
    print(f"[GRADING] PostgreSQL unavailable ({e}). Audit logging disabled.")

try:
    from app.database import get_database
    neo4j_driver = get_database()
    print("[GRADING] Neo4j driver connected.")
except Exception as e:
    neo4j_driver = None
    print(f"[GRADING] Neo4j unavailable ({e}). Stage 2 will fail gracefully.")


# ── Initialize Stage 1 pipeline ───────────────────────────────────────
stage1 = FastScreeningPipeline()

# ── Stage 2 grader placeholder (import existing if available) ─────────
stage2 = None
# TODO: Import existing Neo4jGrader class when available
# from app.evaluation.scorer import Neo4jGrader
# stage2 = Neo4jGrader(neo4j_driver, llm_client)


# ── FastAPI app ────────────────────────────────────────────────────────
app = FastAPI(title="Answer Grading Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GradeRequest(BaseModel):
    student_id: str
    question_id: str
    student_answer: str
    reference_answer: str


class GradeResponse(BaseModel):
    grade: float
    confidence: str
    method: str
    flagged: bool
    latency_ms: float
    stage1_score: float | None = None
    stage2_score: float | None = None
    reasoning: str | None = None
    concerns: list[str] | None = None


def _cache_key(req: GradeRequest) -> str:
    """Build cache key: grade:{student_id}:{question_id}:{hash(answer)}"""
    answer_hash = hashlib.md5(req.student_answer.encode()).hexdigest()[:12]
    return f"grade:{req.student_id}:{req.question_id}:{answer_hash}"


def _cache_get(key: str) -> dict | None:
    """Get cached result from Redis."""
    if not redis_client:
        return None
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


def _cache_set(key: str, value: dict, ttl: int = 3600) -> None:
    """Cache result in Redis with TTL."""
    if not redis_client:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def queue_for_human_review(req: GradeRequest, result: dict) -> None:
    """Queue low-confidence results for human review."""
    print(f"[HUMAN REVIEW] question_id={req.question_id} student_id={req.student_id} "
          f"grade={result.get('grade')} concerns={result.get('concerns')}")
    # TODO: Push to review queue (Redis list, PostgreSQL table, etc.)


@app.post("/grade", response_model=GradeResponse)
async def grade_answer(req: GradeRequest, background: BackgroundTasks):
    """
    Two-stage answer grading endpoint.
    Stage 1: Fast screening via Cross-Encoder + heuristics
    Stage 2: Deep reasoning via Neo4j + LLM (if flagged)
    """
    # 1. Check cache
    cache_key = _cache_key(req)
    cached = _cache_get(cache_key)
    if cached:
        return GradeResponse(**cached)

    # 2. Record start time
    start = time.perf_counter()

    # 3. Stage 1 screening
    stage1_result = stage1.screen(
        student_answer=req.student_answer,
        reference_answer=req.reference_answer,
        question_id=req.question_id,
    )

    elapsed = (time.perf_counter() - start) * 1000  # ms

    # 4. Log to audit table (non-blocking)
    if audit_db:
        background.add_task(
            log_screening_decision,
            audit_db,
            req.question_id,
            req.student_id,
            stage1_result["decision"],
            stage1_result["stage1_score"],
            stage1_result["sim_score"],
            stage1_result["flag_reasons"],
            elapsed,
        )

    # 5. Decision routing
    if stage1_result["decision"] == "PASS":
        result = {
            "grade": stage1_result["stage1_score"],
            "confidence": stage1_result["confidence"],
            "method": "STAGE1_CROSS_ENCODER",
            "flagged": False,
            "latency_ms": round(elapsed, 2),
        }
    else:
        # FLAG → attempt Stage 2
        if stage2 is not None:
            try:
                stage2_result = stage2.grade(
                    req.student_answer,
                    req.question_id,
                    stage1_result,
                )
                elapsed = (time.perf_counter() - start) * 1000

                result = {
                    "grade": stage2_result["final_grade"],
                    "confidence": "ADJUSTED",
                    "method": "STAGE2_GRAPH_LLM",
                    "flagged": True,
                    "stage1_score": stage2_result.get("stage1_score"),
                    "stage2_score": stage2_result.get("stage2_score"),
                    "reasoning": stage2_result.get("reasoning"),
                    "concerns": stage2_result.get("concerns", []),
                    "latency_ms": round(elapsed, 2),
                }

                # Queue for human review if low confidence
                if result["grade"] < 0.3 or len(result.get("concerns", [])) > 2:
                    background.add_task(queue_for_human_review, req, result)

            except Exception as e:
                print(f"[STAGE2 ERROR] {e}")
                result = {
                    "grade": stage1_result["stage1_score"],
                    "confidence": "LOW",
                    "method": "STAGE1_FALLBACK",
                    "flagged": True,
                    "latency_ms": round(elapsed, 2),
                }
        else:
            # Stage 2 not available — return Stage 1 result with flag
            result = {
                "grade": stage1_result["stage1_score"],
                "confidence": "LOW",
                "method": "STAGE1_ONLY",
                "flagged": True,
                "latency_ms": round(elapsed, 2),
            }

    # 6. Cache result
    _cache_set(cache_key, result)

    return GradeResponse(**result)


@app.get("/metrics/flag-rate")
async def get_flag_rate(hours: int = 168):
    """Return flag rate report from the tracker."""
    if not audit_db:
        return {"error": "Audit database not configured"}
    return get_flag_rate_report(audit_db, hours=hours)


@app.get("/health")
async def health_check():
    """Check health of all grading service components."""
    status = {}

    # Neo4j
    try:
        if neo4j_driver:
            with neo4j_driver.session() as session:
                session.run("RETURN 1 AS alive")
            status["neo4j"] = "ok"
        else:
            status["neo4j"] = "not_configured"
    except Exception as e:
        status["neo4j"] = f"error: {e}"

    # Redis
    try:
        if redis_client:
            redis_client.ping()
            status["redis"] = "ok"
        else:
            status["redis"] = "not_configured"
    except Exception as e:
        status["redis"] = f"error: {e}"

    # Models
    status["embedder"] = "ok" if stage1.embedder is not None else "not_loaded"
    status["cross_encoder"] = "ok" if stage1.cross_encoder is not None else "not_loaded"
    status["stage2"] = "ok" if stage2 is not None else "not_configured"

    overall = "ok" if status["embedder"] == "ok" and status["cross_encoder"] == "ok" else "degraded"
    return {"status": overall, "components": status}
