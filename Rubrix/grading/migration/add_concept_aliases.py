"""
Concept Alias Migration Script — Answer Grading Pipeline
==========================================================
Migration order: Run AFTER migrate_must_relate_edges.py (A3).

Adds aliases to Concept nodes so student answers can be matched
even when students use abbreviations, formulas, or informal names.

Step 1: Apply hardcoded seed aliases for common EE concepts.
Step 2: For remaining concepts with no aliases, call LLM.

Usage:
    python -m grading.migration.add_concept_aliases
"""

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=True)

from groq import Groq
from app.database import get_database


# ── LLM client ────────────────────────────────────────────────────────
llm_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "llama-3.3-70b-versatile"


# ── Seed aliases for the most common EE concepts ──────────────────────
SEED_ALIASES = {
    "Kirchhoff's Voltage Law":     ["KVL", "voltage loop law",
                                    "sum of voltages", "mesh equation"],
    "Kirchhoff's Current Law":     ["KCL", "current node law",
                                    "sum of currents", "nodal equation"],
    "Ohm's Law":                   ["V=IR", "voltage-current relationship",
                                    "ohmic relationship", "resistance law"],
    "Faraday's Law":               ["electromagnetic induction",
                                    "flux linkage", "EMF induction"],
    "Lenz's Law":                  ["back EMF", "opposing flux",
                                    "induced opposition"],
    "Transformer":                 ["step-up", "step-down", "turns ratio",
                                    "mutual inductance device", "voltage transformer"],
    "Power Factor":                ["cos phi", "pf", "lagging", "leading",
                                    "reactive power ratio"],
    "Thevenin's Theorem":          ["thevenin equivalent", "vth", "rth",
                                    "equivalent circuit"],
    "Norton's Theorem":            ["norton equivalent", "iN", "rN",
                                    "current source equivalent"],
    "Superposition Theorem":       ["superposition principle",
                                    "linear superposition"],
    "Resonance":                   ["resonant frequency", "LC resonance",
                                    "series resonance", "parallel resonance"],
    "Impedance":                   ["Z", "complex resistance",
                                    "AC resistance", "complex impedance"],
    "Reactance":                   ["XL", "XC", "inductive reactance",
                                    "capacitive reactance"],
    "Transfer Function":           ["H(s)", "G(s)", "laplace transform ratio",
                                    "s-domain ratio"],
    "Bode Plot":                   ["frequency response", "magnitude plot",
                                    "phase plot", "gain vs frequency"],
    "Nyquist Criterion":           ["stability criterion", "nyquist plot",
                                    "encirclement condition"],
    "BJT":                         ["bipolar junction transistor",
                                    "NPN", "PNP", "transistor amplifier"],
    "MOSFET":                      ["field effect transistor", "FET",
                                    "NMOS", "PMOS", "gate controlled"],
    "Op-Amp":                      ["operational amplifier", "741",
                                    "differential amplifier", "virtual ground"],
    "Fourier Transform":           ["frequency domain", "spectral analysis",
                                    "fourier series", "harmonic analysis"],
    "Laplace Transform":           ["s-domain", "s-plane",
                                    "complex frequency domain"],
}


def apply_seed_aliases(driver) -> int:
    """
    Apply SEED_ALIASES to matching Concept nodes.
    Match by exact name (case-insensitive).
    Returns count of concepts updated.
    """
    updated = 0
    query = """
    MATCH (c:Concept)
    WHERE toLower(c.name) = toLower($name)
    SET c.aliases = $aliases
    RETURN count(c) AS cnt
    """

    with driver.session() as session:
        for concept_name, aliases in SEED_ALIASES.items():
            try:
                result = session.run(query, name=concept_name, aliases=aliases)
                record = result.single()
                cnt = record["cnt"] if record else 0
                if cnt > 0:
                    updated += cnt
                    print(f"  [ALIAS] '{concept_name}' → {len(aliases)} aliases added")
                else:
                    print(f"  [SKIP]  '{concept_name}' not found in graph")
            except Exception as e:
                print(f"  [ERROR] Failed for '{concept_name}': {e}")

    return updated


def generate_aliases_via_llm(
    concept_name: str,
    client
) -> list[str]:
    """
    For concepts not in SEED_ALIASES, use LLM to generate aliases.

    Returns: list of alias strings, max 8 per concept.
    """
    prompt = f"""SYSTEM:
You are an expert in Electrical Engineering terminology.

CONCEPT: {concept_name}

TASK:
List all common abbreviations, formulas, informal names, and alternative
phrasings a student might use in a GATE exam answer when referring to
this concept.

RULES:
- Return a JSON array of strings only
- Maximum 8 aliases
- Include abbreviations, formula names, and informal terms
- Do NOT include the original concept name itself
- No preamble, no markdown fences

Example: ["KVL", "voltage loop law", "sum of voltages"]

Generate aliases now:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You generate concept aliases. Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        aliases = json.loads(raw)

        if not isinstance(aliases, list):
            return []

        # Validate: only strings, max 8, no empty
        validated = [str(a).strip() for a in aliases if isinstance(a, str) and a.strip()]
        return validated[:8]

    except json.JSONDecodeError:
        print(f"  [ERROR] JSON parse failed for '{concept_name}'")
        return []
    except Exception as e:
        print(f"  [ERROR] LLM call failed for '{concept_name}': {e}")
        return []


def run_alias_migration(
    driver,
    client,
    batch_size: int = 10,
    delay_between_batches: float = 1.0
) -> dict:
    """
    Step 1: Apply seed aliases to all matching concepts.
    Step 2: For remaining concepts with no aliases, call LLM.
    Step 3: Store results.

    Returns summary: {seed_applied: int, llm_generated: int, failed: int}
    """
    print("=" * 60)
    print("  CONCEPT ALIAS MIGRATION")
    print("=" * 60)

    # Step 1: Seed aliases
    print("\n[STEP 1] Applying seed aliases...")
    seed_count = apply_seed_aliases(driver)
    print(f"[INFO] Seed aliases applied to {seed_count} concepts")

    # Step 2: Find concepts still missing aliases
    print("\n[STEP 2] Finding concepts missing aliases...")
    query = """
    MATCH (c:Concept)
    WHERE c.aliases IS NULL
    RETURN c.name AS name
    """
    with driver.session() as session:
        result = session.run(query)
        remaining = [record["name"] for record in result]

    print(f"[INFO] {len(remaining)} concepts still need aliases (LLM generation)")

    llm_generated = 0
    failed = 0

    store_query = """
    MATCH (c:Concept {name: $name})
    SET c.aliases = $aliases
    RETURN count(c) AS cnt
    """

    for i, concept_name in enumerate(remaining):
        aliases = generate_aliases_via_llm(concept_name, client)

        if aliases:
            try:
                with driver.session() as session:
                    session.run(store_query, name=concept_name, aliases=aliases)
                llm_generated += 1
                print(f"  [{i + 1}/{len(remaining)}] '{concept_name}' → {len(aliases)} aliases")
            except Exception as e:
                failed += 1
                print(f"  [{i + 1}/{len(remaining)}] '{concept_name}' → FAILED: {e}")
        else:
            failed += 1
            print(f"  [{i + 1}/{len(remaining)}] '{concept_name}' → no aliases generated")

        # Rate limiting
        if (i + 1) % batch_size == 0 and i + 1 < len(remaining):
            print(f"  [BATCH] Processed {i + 1}/{len(remaining)}, pausing {delay_between_batches}s...")
            time.sleep(delay_between_batches)

    summary = {
        "seed_applied": seed_count,
        "llm_generated": llm_generated,
        "failed": failed,
    }

    print()
    print("=" * 60)
    print("  ALIAS MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Seed aliases applied : {summary['seed_applied']}")
    print(f"  LLM aliases generated: {summary['llm_generated']}")
    print(f"  Failed               : {summary['failed']}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    driver = get_database()
    try:
        run_alias_migration(driver, llm_client)
    finally:
        pass
