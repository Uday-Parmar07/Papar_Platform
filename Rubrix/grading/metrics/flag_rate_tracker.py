"""
Flag Rate Tracker — Answer Grading Pipeline
=============================================
Records every Stage 1 decision to PostgreSQL for analysis.
The flag rate must be measured for one week before thresholds are adjusted.

Usage:
    from grading.metrics.flag_rate_tracker import log_screening_decision, get_flag_rate_report
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text


# ── Table creation DDL ─────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS grading_audit (
    id              SERIAL PRIMARY KEY,
    question_id     VARCHAR(100),
    student_id      VARCHAR(100),
    decision        VARCHAR(10),
    ce_score        FLOAT,
    sim_score       FLOAT,
    flag_reasons    TEXT[],
    response_time_ms FLOAT,
    grading_stage   VARCHAR(20) DEFAULT 'STAGE1',
    created_at      TIMESTAMP DEFAULT NOW()
)
"""


def ensure_table(audit_db) -> None:
    """Create grading_audit table if it doesn't exist."""
    try:
        with audit_db.connect() as conn:
            conn.execute(text(CREATE_TABLE_SQL))
            conn.commit()
    except Exception as e:
        print(f"[AUDIT] Warning: could not create grading_audit table: {e}")


def log_screening_decision(
    audit_db,
    question_id: str,
    student_id: str,
    decision: str,
    ce_score: float,
    sim_score: float,
    flag_reasons: list[str],
    response_time_ms: float
) -> None:
    """
    Insert one row into grading_audit table.
    Wraps in try/except — logging must never crash the grading pipeline.
    """
    try:
        ensure_table(audit_db)
        insert_sql = text("""
            INSERT INTO grading_audit
                (question_id, student_id, decision, ce_score, sim_score,
                 flag_reasons, response_time_ms, grading_stage)
            VALUES
                (:question_id, :student_id, :decision, :ce_score, :sim_score,
                 :flag_reasons, :response_time_ms, 'STAGE1')
        """)
        with audit_db.connect() as conn:
            conn.execute(insert_sql, {
                "question_id": question_id,
                "student_id": student_id,
                "decision": decision,
                "ce_score": ce_score,
                "sim_score": sim_score,
                "flag_reasons": flag_reasons,
                "response_time_ms": response_time_ms,
            })
            conn.commit()
    except Exception as e:
        print(f"[AUDIT] Warning: failed to log screening decision: {e}")


def get_flag_rate_report(audit_db, hours: int = 168) -> dict:
    """
    Compute flag rate statistics over the last N hours (default 168 = 1 week).

    Returns dict with:
    - total_screened, total_flagged, flag_rate
    - flag_reason_counts, mean_ce_score
    - ce_score_distribution (bucketed)
    - recommendation
    """
    try:
        ensure_table(audit_db)

        with audit_db.connect() as conn:
            # Total screened and flagged
            totals_sql = text("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE decision = 'FLAG') AS flagged,
                    avg(ce_score) AS mean_ce
                FROM grading_audit
                WHERE created_at >= NOW() - INTERVAL ':hours hours'
                  AND grading_stage = 'STAGE1'
            """.replace(":hours", str(int(hours))))

            row = conn.execute(totals_sql).fetchone()
            total_screened = row[0] if row else 0
            total_flagged = row[1] if row else 0
            mean_ce_score = float(row[2]) if row and row[2] is not None else 0.0

            flag_rate = total_flagged / total_screened if total_screened > 0 else 0.0

            # Flag reason counts
            reasons_sql = text("""
                SELECT unnest(flag_reasons) AS reason, count(*) AS cnt
                FROM grading_audit
                WHERE created_at >= NOW() - INTERVAL ':hours hours'
                  AND grading_stage = 'STAGE1'
                  AND flag_reasons IS NOT NULL
                GROUP BY reason
                ORDER BY cnt DESC
            """.replace(":hours", str(int(hours))))

            reason_rows = conn.execute(reasons_sql).fetchall()
            flag_reason_counts = {row[0]: row[1] for row in reason_rows}

            # CE score distribution (bucketed)
            dist_sql = text("""
                SELECT
                    count(*) FILTER (WHERE ce_score >= 0.0 AND ce_score < 0.2) AS b1,
                    count(*) FILTER (WHERE ce_score >= 0.2 AND ce_score < 0.4) AS b2,
                    count(*) FILTER (WHERE ce_score >= 0.4 AND ce_score < 0.6) AS b3,
                    count(*) FILTER (WHERE ce_score >= 0.6 AND ce_score < 0.8) AS b4,
                    count(*) FILTER (WHERE ce_score >= 0.8 AND ce_score <= 1.0) AS b5
                FROM grading_audit
                WHERE created_at >= NOW() - INTERVAL ':hours hours'
                  AND grading_stage = 'STAGE1'
            """.replace(":hours", str(int(hours))))

            dist_row = conn.execute(dist_sql).fetchone()
            ce_score_distribution = {
                "0.0-0.2": dist_row[0] if dist_row else 0,
                "0.2-0.4": dist_row[1] if dist_row else 0,
                "0.4-0.6": dist_row[2] if dist_row else 0,
                "0.6-0.8": dist_row[3] if dist_row else 0,
                "0.8-1.0": dist_row[4] if dist_row else 0,
            }

        # Recommendation logic
        if flag_rate > 0.25:
            recommendation = "Flag rate too high. Widen CE_PASS_HIGH threshold."
        elif flag_rate < 0.05:
            recommendation = "Flag rate too low. Tighten CE thresholds."
        elif 0.10 <= flag_rate <= 0.20:
            recommendation = "Flag rate healthy. No action needed."
        else:
            recommendation = "Flag rate acceptable. Monitor for one more week."

        return {
            "total_screened": total_screened,
            "total_flagged": total_flagged,
            "flag_rate": round(flag_rate, 4),
            "flag_reason_counts": flag_reason_counts,
            "mean_ce_score": round(mean_ce_score, 4),
            "ce_score_distribution": ce_score_distribution,
            "recommendation": recommendation,
        }

    except Exception as e:
        print(f"[AUDIT] Warning: failed to generate flag rate report: {e}")
        return {
            "total_screened": 0,
            "total_flagged": 0,
            "flag_rate": 0.0,
            "flag_reason_counts": {},
            "mean_ce_score": 0.0,
            "ce_score_distribution": {},
            "recommendation": f"Report generation failed: {e}",
        }
