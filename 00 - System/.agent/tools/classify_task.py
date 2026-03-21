#!/usr/bin/env python3
"""
Task classifier for the sub-agent routing architecture.
Classifies a research query into one of 5 task types with a confidence score.

Task types (from architecture spec v1.2):
  simple_lookup        — single topic, vault-answerable
  vault_only           — explicit request for vault-only knowledge
  multi_topic_research — comparison or multi-topic query
  verified_research    — factual spec claims needing fact-checking
  note_creation        — explicit intent to create/write a note

Usage:
  python classify_task.py "your research query"

Output:
  { "task_type": "...", "confidence": 0.0-1.0, "signals": [...], "escalated": false }

Escalation rule (Architecture Decision 1):
  If confidence < 0.7, auto-escalate to the next more thorough task type.
  Order: simple_lookup < vault_only < multi_topic_research < verified_research < note_creation
"""

import sys
import json
import re
import argparse
from typing import List, Tuple, Dict


# ---------------------------------------------------------------------------
# Signal definitions per task type
# ---------------------------------------------------------------------------

# Each entry: (pattern, weight)  — weight contributes to confidence score
# Patterns are checked case-insensitively against the full query

VAULT_ONLY_SIGNALS = [
    (r"\bmy vault\b", 1.0),
    (r"\bmy notes?\b", 0.8),
    (r"\bmy research\b", 0.8),
    (r"\bwhat does (my vault|the vault) (say|contain|have)\b", 1.0),
    (r"\bin (my|the) vault\b", 0.9),
    (r"\bexisting notes?\b", 0.7),
    (r"\bwhat (have i|did i) (written|noted|researched)\b", 1.0),
]

NOTE_CREATION_SIGNALS = [
    (r"\bcreate (a |an )?(note|evergreen|research note|source note)\b", 1.0),
    (r"\bwrite (a |an )?(note|evergreen|summary)\b", 1.0),
    (r"\badd (this |it )?to (the )?vault\b", 1.0),
    (r"\bsave (this|it)\b", 0.8),
    (r"\bdocument this\b", 0.9),
    (r"\bmake (a |an )?(note|record)\b", 0.8),
    (r"\bstore (this|it) (as|in)\b", 0.8),
    (r"\bcreate an evergreen\b", 1.0),
    (r"\badd (a )?note\b", 0.9),
    (r"\bwrite (it )?up\b", 0.7),
]

MULTI_TOPIC_SIGNALS = [
    (r"\bcompare\b", 1.0),
    (r"\bversus\b", 1.0),
    (r"\bvs\.?\b", 0.9),
    (r"\bdifference(s)? between\b", 1.0),
    (r"\bcontrast\b", 0.9),
    (r"\b(pros and cons|trade-?offs?)\b", 0.8),
    (r"\bboth\b.*\band\b", 0.6),
    (r"\bwhich is better\b", 0.9),
    (r"\b\w+ (and|or) \w+ (for|in|on)\b", 0.5),  # "X and Y for Z"
]

VERIFIED_RESEARCH_SIGNALS = [
    # Numeric spec claims
    (r"\b\d+\s*(GB|TB|MB|TFLOPS|TOPS|GHz|MHz|W|watts|cores?|channels?)\b", 1.0),
    (r"\b(specification|spec)\b", 0.9),
    (r"\bperformance\b", 0.7),
    (r"\bbenchmark\b", 0.9),
    (r"\bverif(y|ied|ication)\b", 1.0),
    (r"\baccurate(ly)?\b", 0.8),
    (r"\bfact(-?check)?\b", 1.0),
    (r"\bclaim\b", 0.9),
    (r"\blatest (data|numbers?|specs?|info)\b", 0.8),
    (r"\b(supports?|compatible with|certified)\b", 0.6),
]

# ---------------------------------------------------------------------------
# Task type ordering (for escalation)
# ---------------------------------------------------------------------------

TASK_ORDER = [
    "simple_lookup",
    "vault_only",
    "multi_topic_research",
    "verified_research",
    "note_creation",
]

ESCALATION_MAP = {
    "simple_lookup":        "vault_only",
    "vault_only":           "multi_topic_research",
    "multi_topic_research": "verified_research",
    "verified_research":    "note_creation",
    "note_creation":        "note_creation",  # Already maximum
}


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

def score_signals(query: str, signals: List[Tuple[str, float]]) -> Tuple[float, List[str]]:
    """Return (raw_score, matched_signal_labels) for a set of signal patterns."""
    matched = []
    total_score = 0.0
    for pattern, weight in signals:
        if re.search(pattern, query, re.IGNORECASE):
            matched.append(pattern)
            total_score += weight
    return total_score, matched


def classify(query: str) -> Dict:
    """Classify a query into a task_type with confidence score."""
    query = query.strip()

    # Score all signal sets
    note_score,  note_signals  = score_signals(query, NOTE_CREATION_SIGNALS)
    vault_score, vault_signals = score_signals(query, VAULT_ONLY_SIGNALS)
    multi_score, multi_signals = score_signals(query, MULTI_TOPIC_SIGNALS)
    verif_score, verif_signals = score_signals(query, VERIFIED_RESEARCH_SIGNALS)

    # Note creation takes hard priority — explicit intent beats all
    if note_score > 0:
        max_possible = sum(w for _, w in NOTE_CREATION_SIGNALS)
        confidence = min(1.0, note_score / max(max_possible * 0.3, 1))
        return _result("note_creation", confidence, note_signals, query)

    # Vault-only: explicit vault reference
    if vault_score > 0:
        max_possible = sum(w for _, w in VAULT_ONLY_SIGNALS)
        confidence = min(1.0, vault_score / max(max_possible * 0.3, 1))
        return _result("vault_only", confidence, vault_signals, query)

    # Multi-topic: comparison or multi-subject
    if multi_score > 0 and verif_score > 0:
        # Both signals → verified_research
        combined_score = multi_score + verif_score
        max_possible = (
            sum(w for _, w in MULTI_TOPIC_SIGNALS) * 0.3
            + sum(w for _, w in VERIFIED_RESEARCH_SIGNALS) * 0.3
        )
        confidence = min(1.0, combined_score / max(max_possible, 1))
        return _result("verified_research", confidence, multi_signals + verif_signals, query)

    if multi_score > 0:
        max_possible = sum(w for _, w in MULTI_TOPIC_SIGNALS)
        confidence = min(1.0, multi_score / max(max_possible * 0.3, 1))
        return _result("multi_topic_research", confidence, multi_signals, query)

    # Verified research: spec/factual signals alone
    if verif_score > 0:
        max_possible = sum(w for _, w in VERIFIED_RESEARCH_SIGNALS)
        confidence = min(1.0, verif_score / max(max_possible * 0.3, 1))
        return _result("verified_research", confidence, verif_signals, query)

    # Default: simple lookup
    return _result("simple_lookup", 0.6, [], query)  # 0.6 = below escalation threshold


def _result(task_type: str, confidence: float, signals: List[str], query: str) -> Dict:
    """Build and optionally escalate the classification result."""
    confidence = round(confidence, 3)
    escalated = False
    original_type = task_type

    if confidence < 0.7 and task_type != "note_creation":
        escalated_type = ESCALATION_MAP[task_type]
        if escalated_type != task_type:
            task_type = escalated_type
            escalated = True

    return {
        "task_type": task_type,
        "original_task_type": original_type,
        "confidence": confidence,
        "escalated": escalated,
        "signals_matched": signals,
        "signal_count": len(signals),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Classify a research query into a task_type with confidence score"
    )
    parser.add_argument("query", nargs="?", help="Research query string to classify")
    args = parser.parse_args()

    if args.query:
        query = args.query
    else:
        query = sys.stdin.read().strip()

    if not query:
        print(json.dumps({"error": "No query provided"}))
        sys.exit(1)

    result = classify(query)
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")


if __name__ == "__main__":
    main()
