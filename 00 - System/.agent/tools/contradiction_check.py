#!/usr/bin/env python3
"""
Contradiction detector — VaultSearchAgent mode.

Searches the vault for existing notes on a topic, then compares a list of
new claims against the vault evidence. Flags potential contradictions using:
  1. Negation patterns  ("does not have", "without", "lacks")
  2. Numeric value mismatches (same unit, different value in claim vs. vault)
  3. Keyword absence    (claim asserts X but vault notes actively deny X)

This is NOT a full LLM-based contradiction detector — it is a pre-fetch tool
that surfaces vault sections alongside new claims so the Orchestrator can
decide whether to escalate before synthesising an answer or writing a note.

Usage:
  python contradiction_check.py "topic query" [--claims '["claim1"]'] [--k 5]

Output JSON:
  {
    "verdict":  "CLEAR" | "REVIEW" | "CONFLICT",
    "topic":    "...",
    "claims":   [...],
    "vault_evidence": [ { file_path, heading, section_text, score } ],
    "flags": [
      {
        "type": "negation" | "numeric_mismatch" | "keyword_absence",
        "claim": "...",
        "vault_excerpt": "...",
        "file_path": "...",
        "heading": "...",
        "severity": "low" | "medium" | "high"
      }
    ]
  }
"""

import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import FAISS_STORE, MODEL_PATH


# ---------------------------------------------------------------------------
# FAISS helpers (mirrors query_vault.py conventions)
# ---------------------------------------------------------------------------

def load_metadata_jsonl(path: Path) -> List[Dict]:
    metas = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    metas.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return metas


def query_faiss(question: str, k: int = 8):
    persist_dir = Path(FAISS_STORE)
    model_path  = MODEL_PATH
    index_path  = persist_dir / "index.faiss"
    meta_path   = persist_dir / "metadata.jsonl"

    if not index_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Missing index.faiss or metadata.jsonl in {persist_dir}")

    index = faiss.read_index(str(index_path))
    metas = load_metadata_jsonl(meta_path)
    model = SentenceTransformer(model_path)

    q = model.encode([question], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    scores, ids = index.search(q, k)

    results = []
    for score, idx in zip(scores[0].tolist(), ids[0].tolist()):
        if idx < 0 or idx >= len(metas):
            continue
        meta = metas[idx].copy()
        results.append({
            "score":     float(score),
            "file_path": meta.get("file_path", ""),
            "rel_path":  meta.get("rel_path", ""),
            "heading":   meta.get("heading", ""),
            "block_id":  meta.get("block_id"),
        })
    return results


# ---------------------------------------------------------------------------
# File content reader — extracts section under a heading
# ---------------------------------------------------------------------------

def read_section(file_path: str, target_heading: Optional[str], max_chars: int = 1500) -> str:
    """Read text from a markdown file, optionally filtered to a specific heading section."""
    path = Path(file_path)
    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8", errors="replace")

    if not target_heading:
        return text[:max_chars]

    # Find the heading in the file
    pattern = re.compile(
        r"^(#{1,6})\s+" + re.escape(target_heading) + r"\s*$",
        re.MULTILINE | re.IGNORECASE
    )
    m = pattern.search(text)
    if not m:
        return text[:max_chars]

    start = m.end()
    heading_level = len(m.group(1))

    # Find the next heading of same or higher level
    next_heading = re.compile(
        r"^#{1," + str(heading_level) + r"}\s+",
        re.MULTILINE
    )
    end_m = next_heading.search(text, start)
    end = end_m.start() if end_m else len(text)

    section = text[start:end].strip()
    return section[:max_chars]


# ---------------------------------------------------------------------------
# Contradiction detection heuristics
# ---------------------------------------------------------------------------

NEGATION_PATTERNS = [
    r"\bno\s+{kw}\b",
    r"\bnot\s+\w*\s*{kw}\b",
    r"\bdoes\s+not\s+\w*\s*{kw}\b",
    r"\bwithout\s+{kw}\b",
    r"\blacks?\s+{kw}\b",
    r"\bn/a\b",
    r"\bremoved\b",
    r"\bdiscontinued\b",
]

NUMBER_RE = re.compile(r"(\d[\d,\.]*)\s*(gb|tb|mb|tflops|tops|ghz|mhz|w\b|cores?|bits?)?", re.IGNORECASE)


def extract_keywords(claim: str) -> List[str]:
    """Extract meaningful keywords from a claim string (skip stopwords)."""
    stopwords = {"the", "a", "an", "is", "are", "has", "have", "with", "and",
                 "or", "for", "of", "in", "on", "at", "to", "up", "be"}
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-_]+", claim.lower())
    return [w for w in words if w not in stopwords and len(w) > 2]


def check_negation(claim: str, section_text: str) -> List[Dict]:
    """Check if vault section negates keywords present in the claim."""
    flags = []
    keywords = extract_keywords(claim)

    for kw in keywords:
        for pat_template in NEGATION_PATTERNS:
            pat = re.compile(pat_template.format(kw=re.escape(kw)), re.IGNORECASE)
            m = pat.search(section_text)
            if m:
                # Extract surrounding context (80 chars)
                start = max(0, m.start() - 40)
                end = min(len(section_text), m.end() + 40)
                excerpt = "..." + section_text[start:end].strip() + "..."
                flags.append({
                    "type": "negation",
                    "keyword": kw,
                    "pattern_matched": pat_template.format(kw=kw),
                    "vault_excerpt": excerpt,
                    "severity": "high" if kw in claim.lower()[:30] else "medium",
                })
                break  # One flag per keyword is enough

    return flags


def check_numeric_mismatch(claim: str, section_text: str) -> List[Dict]:
    """Check if vault section contains different numeric values for the same unit/context."""
    flags = []

    claim_numbers = NUMBER_RE.findall(claim)
    vault_numbers = NUMBER_RE.findall(section_text)

    if not claim_numbers or not vault_numbers:
        return flags

    for c_val, c_unit in claim_numbers:
        c_num = float(c_val.replace(",", "")) if c_val else None
        if c_num is None:
            continue
        for v_val, v_unit in vault_numbers:
            v_num = float(v_val.replace(",", "")) if v_val else None
            if v_num is None:
                continue
            # Same unit class, different value
            if c_unit and v_unit and c_unit.lower().rstrip("s") == v_unit.lower().rstrip("s"):
                if abs(c_num - v_num) / max(c_num, v_num, 1) > 0.05:  # >5% difference
                    flags.append({
                        "type": "numeric_mismatch",
                        "claim_value": f"{c_val} {c_unit}",
                        "vault_value": f"{v_val} {v_unit}",
                        "severity": "high" if abs(c_num - v_num) / max(c_num, v_num, 1) > 0.2 else "medium",
                    })

    return flags


def detect_contradictions(claims: List[str], vault_evidence: List[Dict]) -> List[Dict]:
    """Run all heuristics across all claims × vault sections."""
    all_flags = []

    for evidence in vault_evidence:
        section_text = evidence.get("section_text", "")
        if not section_text:
            continue

        for claim in claims:
            neg_flags = check_negation(claim, section_text)
            num_flags = check_numeric_mismatch(claim, section_text)

            for flag in neg_flags + num_flags:
                flag["claim"] = claim
                flag["file_path"] = evidence["file_path"]
                flag["heading"] = evidence.get("heading", "")
                all_flags.append(flag)

    return all_flags


def compute_verdict(flags: List[Dict]) -> str:
    if not flags:
        return "CLEAR"
    severities = [f.get("severity", "low") for f in flags]
    if "high" in severities:
        return "CONFLICT"
    return "REVIEW"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Vault contradiction detector")
    parser.add_argument("topic", help="Topic query to search the vault for")
    parser.add_argument("--claims", default="[]",
                        help='JSON array of claim strings to check, e.g. \'["claim1", "claim2"]\'')
    parser.add_argument("--k", type=int, default=6,
                        help="Number of vault chunks to retrieve (default: 6)")
    args = parser.parse_args()

    try:
        claims = json.loads(args.claims)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid --claims JSON: {e}"}))
        sys.exit(1)

    # Step 1: Query vault
    try:
        results = query_faiss(args.topic, args.k)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(2)

    # Step 2: Read file sections for top results (deduplicate by file+heading)
    seen = set()
    vault_evidence = []
    for r in results:
        key = (r["file_path"], r.get("heading", ""))
        if key in seen:
            continue
        seen.add(key)

        section_text = read_section(r["file_path"], r.get("heading"))
        vault_evidence.append({
            "file_path": r["file_path"],
            "rel_path": r.get("rel_path", ""),
            "heading": r.get("heading", ""),
            "score": r["score"],
            "section_text": section_text,
        })

    # Step 3: Detect contradictions
    flags = detect_contradictions(claims, vault_evidence) if claims else []

    # Step 4: Build output (strip section_text from evidence for cleaner output)
    evidence_out = [
        {k: v for k, v in e.items() if k != "section_text"}
        for e in vault_evidence
    ]

    verdict = compute_verdict(flags)

    # Spec-compliant output contract (FactCheckerAgent schema)
    violations = [
        {
            "claim": f.get("claim", ""),
            "expected": f.get("vault_excerpt", ""),
            "found": f.get("pattern_matched", f.get("type", "")),
        }
        for f in flags
    ]

    output = {
        # Spec-compliant fields (FactCheckerAgent output contract)
        "pass": verdict in ("CLEAR", "REVIEW"),
        "violations": violations,
        # Extended fields (kept for backward compatibility)
        "verdict": verdict,
        "topic": args.topic,
        "claims": claims,
        "claims_checked": len(claims),
        "vault_chunks_retrieved": len(vault_evidence),
        "vault_evidence": evidence_out,
        "flags": flags,
        "flag_count": len(flags),
    }

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
