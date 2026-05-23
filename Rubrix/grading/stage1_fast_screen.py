"""
Stage 1 Fast Screening Pipeline — Answer Grading Pipeline
============================================================
Fast path that handles 85-90% of student answers without Neo4j involvement.

Uses:
- Embedding similarity (sentence-transformers)
- Cross-Encoder scoring (primary grading signal)
- Five heuristic flags to detect ambiguous answers

Initial thresholds are intentionally wide. They will be tightened after
one week of real traffic data is collected.

Usage:
    from grading.stage1_fast_screen import FastScreeningPipeline
    pipeline = FastScreeningPipeline()
    result = pipeline.screen(student_answer, reference_answer, question_id)
"""

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer, CrossEncoder


class FastScreeningPipeline:

    def __init__(self):
        """
        Load models and set initial thresholds.

        Thresholds are intentionally WIDE at launch:
        - CE_UNCERTAIN range = 0.60 width
        - Research target is 0.30 width (0.35-0.65) after calibration
        """
        print("[STAGE1] Loading SentenceTransformer model...")
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        print("[STAGE1] Loading CrossEncoder model...")
        self.cross_encoder = CrossEncoder("cross-encoder/stsb-roberta-base")

        print("[STAGE1] Loading spaCy model...")
        self.nlp = spacy.load("en_core_web_sm")

        # ── Thresholds (WIDE — do not tighten until calibration) ───────
        self.CE_PASS_HIGH = 0.80    # clearly correct, fast pass
        self.CE_FAIL_LOW = 0.20     # clearly wrong, fast fail
        self.SIM_HIGH = 0.75        # embedding similarity danger zone
        self.SIM_LOW = 0.30         # too dissimilar
        self.CE_UNCERTAIN = (0.20, 0.80)  # everything in between → Stage 2

        print("[STAGE1] Pipeline initialized. Thresholds:")
        print(f"  CE_PASS_HIGH  = {self.CE_PASS_HIGH}")
        print(f"  CE_FAIL_LOW   = {self.CE_FAIL_LOW}")
        print(f"  CE_UNCERTAIN  = {self.CE_UNCERTAIN}")
        print(f"  SIM_HIGH      = {self.SIM_HIGH}")
        print(f"  SIM_LOW       = {self.SIM_LOW}")

    def compute_embedding_similarity(
        self,
        student_answer: str,
        reference_answer: str
    ) -> float:
        """
        Encode both answers using SentenceTransformer.
        Compute cosine similarity. Returns float in [0, 1].
        """
        embeddings = self.embedder.encode(
            [student_answer, reference_answer],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        similarity = float(np.dot(embeddings[0], embeddings[1]))
        # Clip to [0, 1]
        return max(0.0, min(1.0, similarity))

    def compute_cross_encoder_score(
        self,
        student_answer: str,
        reference_answer: str
    ) -> float:
        """
        Run CrossEncoder on (student_answer, reference_answer) pair.
        Clip output to [0, 1] range. Returns float in [0, 1].
        """
        raw_score = self.cross_encoder.predict(
            [(student_answer, reference_answer)]
        )
        score = float(raw_score[0]) if hasattr(raw_score, '__len__') else float(raw_score)
        # CrossEncoder stsb-roberta-base outputs ~0-5 range, normalize to 0-1
        score = score / 5.0
        return max(0.0, min(1.0, score))

    def apply_heuristic_flags(
        self,
        student_answer: str,
        sim_score: float,
        ce_score: float
    ) -> list[str]:
        """
        Apply all five heuristic patterns. Returns list of triggered flag names.
        Returns empty list if none triggered.
        """
        flags = []

        # Flag 1 — SEMANTIC_OPTIMISM
        # Embedding says similar but CE says wrong → classic false positive
        if sim_score > self.SIM_HIGH and ce_score < 0.45:
            flags.append("SEMANTIC_OPTIMISM")

        # Flag 2 — CONTRADICTORY_SIGNALS
        # Embedding says dissimilar but CE says correct → model confusion
        if sim_score < self.SIM_LOW and ce_score > 0.50:
            flags.append("CONTRADICTORY_SIGNALS")

        # Flag 3 — BORDERLINE_UNCERTAINTY
        # Score is in the uncertain band → needs Stage 2
        if self.CE_UNCERTAIN[0] <= ce_score <= self.CE_UNCERTAIN[1]:
            flags.append("BORDERLINE_UNCERTAINTY")

        # Flag 4 — SHORT_ANSWER_TRAP
        # Very short answer scoring high → likely keyword match
        if len(student_answer.split()) < 12 and ce_score > 0.50:
            flags.append("SHORT_ANSWER_TRAP")

        # Flag 5 — NEGATION_DETECTED
        # Answer contains negation and CE > 0.40 → polarity confusion
        if ce_score > 0.40:
            doc = self.nlp(student_answer)
            for token in doc:
                if token.dep_ == "neg":
                    flags.append("NEGATION_DETECTED")
                    break

        return flags

    def screen(
        self,
        student_answer: str,
        reference_answer: str,
        question_id: str
    ) -> dict:
        """
        Full Stage 1 pipeline.

        Returns:
        {
            'decision':     'PASS' | 'FLAG',
            'stage1_score': float,   # ce_score is the primary score
            'sim_score':    float,
            'flag_reasons': list[str],
            'confidence':   'HIGH' | 'MEDIUM' | 'LOW'
        }

        On exception: returns decision='FLAG' with flag_reasons=['SCREENING_ERROR']
        so it safely falls to Stage 2.
        """
        try:
            # Step 1: Embedding similarity
            sim_score = self.compute_embedding_similarity(student_answer, reference_answer)

            # Step 2: Cross-Encoder score
            ce_score = self.compute_cross_encoder_score(student_answer, reference_answer)

            # Step 3: Heuristic flags
            flags = self.apply_heuristic_flags(student_answer, sim_score, ce_score)

            # ── Decision logic ─────────────────────────────────────────
            if ce_score > self.CE_PASS_HIGH and not flags:
                decision = "PASS"
                confidence = "HIGH"
            elif ce_score > self.CE_PASS_HIGH and flags:
                decision = "FLAG"
                confidence = "MEDIUM"
            elif ce_score < self.CE_FAIL_LOW and not flags:
                # Clearly wrong, no ambiguity
                decision = "PASS"
                confidence = "HIGH"
            elif flags:
                decision = "FLAG"
                confidence = "LOW"
            else:
                decision = "PASS"
                confidence = "MEDIUM"

            return {
                "decision": decision,
                "stage1_score": ce_score,
                "sim_score": sim_score,
                "flag_reasons": flags,
                "confidence": confidence,
            }

        except Exception as e:
            print(f"[STAGE1 ERROR] question_id={question_id}: {e}")
            return {
                "decision": "FLAG",
                "stage1_score": 0.0,
                "sim_score": 0.0,
                "flag_reasons": ["SCREENING_ERROR"],
                "confidence": "LOW",
            }
