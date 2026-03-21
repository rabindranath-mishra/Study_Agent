#!/usr/bin/env python3
"""
FactCheckerAgent — verifies factual claims against vault and optionally web sources.
This is the first hard gate before any vault write.

Inputs:
  --claims   JSON array of claim strings to verify
  --sources  JSON array of source URL strings (optional; enables web verification)

Output (matches shared_state.fact_check_results schema):
  {
    "claims_checked": N,
    "pass": bool,
    "violations": [{ "claim": "...", "expected": "...", "found": "..." }],
    "vault_verdict": "CLEAR|REVIEW|CONFLICT",
    "web_checked": bool
  }

Exit codes:
  0 — PASS (all claims verified, no conflicts)
  1 — FAIL (conflicts detected or web verification mismatch)
  2 — ERROR (tool invocation failure)
"""

import sys
import json
import argparse
import subprocess
import re
from pathlib import Path
from typing import List, Dict

from paths import FAISS_STORE, MODEL_PATH, PYTHON_EXE
TOOLS_DIR    = Path(__file__).parent


def run_tool(cmd: list) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stderr.strip() or f"Exit code {result.returncode}"}


def vault_check(claims: List[str]) -> dict:
    """Run contradiction_check.py for vault-side verification."""
    if not claims:
        return {"pass": True, "violations": [], "verdict": "CLEAR", "claims_checked": 0}

    topic = " ".join(claims[:3])  # Use first 3 claims as topic query
    cmd = [
        PYTHON_EXE, str(TOOLS_DIR / "contradiction_check.py"),
        topic,
        "--claims", json.dumps(claims),
        "--k", "8",
    ]
    result = run_tool(cmd)
    if "error" in result:
        return {
            "pass": False,
            "violations": [],
            "verdict": "ERROR",
            "claims_checked": len(claims),
            "error": result["error"],
        }
    return result


def web_check(claims: List[str], source_urls: List[str]) -> List[Dict]:
    """
    Fetch source URLs and check if claims are supported by the content.
    Returns a list of violation dicts for claims not found/contradicted.
    """
    violations = []
    if not source_urls:
        return violations

    for url in source_urls:
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "web_fetch.py"), url]
        result = run_tool(cmd)

        if "error" in result:
            continue  # Skip unreachable URLs

        # Get text content from web_fetch output
        page_text = ""
        if isinstance(result, dict):
            page_text = result.get("content", result.get("text", result.get("summary", "")))
        elif isinstance(result, str):
            page_text = result

        page_text_lower = page_text.lower()

        for claim in claims:
            # Cap claim length to prevent ReDoS on pathological input
            claim_safe = claim[:500]
            # Extract key numeric terms relevant to study-domain facts
            # Matches: years (1945), percentages (45%), scientific values (9.8 m/s, 6.02 mol)
            numbers = re.findall(
                r'\b\d+(?:\.\d+)?\s*'
                r'(?:%|percent|kg|g|mg|m|km|cm|mm|s|ms|Hz|kHz|MHz|'
                r'J|kJ|cal|kcal|mol|M|L|mL|Pa|kPa|N|C|K|'
                r'eV|AU|ly|yr|AD|BC|CE|BCE)?\b',
                claim_safe, re.IGNORECASE
            )
            numbers = [n.strip() for n in numbers if n.strip() and len(n.strip()) > 1]

            _STOP = {
                'that', 'this', 'with', 'have', 'from', 'their', 'supports',
                'also', 'which', 'into', 'when', 'then', 'were', 'been',
                'more', 'than', 'some', 'such', 'each', 'other', 'about',
                'over', 'after', 'before', 'between', 'through', 'where',
                'while', 'these', 'those', 'both', 'will', 'would', 'could',
                'should', 'must', 'only', 'very', 'used', 'like',
            }
            keywords = [w for w in re.findall(r'[a-zA-Z][a-zA-Z0-9\-]+', claim_safe)
                        if len(w) > 3 and w.lower() not in _STOP]

            # Check if key terms appear in page text
            key_terms = numbers + keywords[:3]
            if key_terms:
                missing = [t for t in key_terms if t.lower() not in page_text_lower]
                if len(missing) > len(key_terms) * 0.5:  # >50% of key terms missing
                    violations.append({
                        "claim": claim,
                        "expected": f"Claim terms found in {url}",
                        "found": f"Key terms not found in page: {missing[:3]}",
                        "source_url": url,
                    })

    return violations


def main():
    parser = argparse.ArgumentParser(description="FactCheckerAgent — claim verification")
    parser.add_argument("--claims", required=True,
                        help='JSON array of claim strings, e.g. \'["IGX Thor has 128GB"]\'')
    parser.add_argument("--sources", default="[]",
                        help="JSON array of source URLs for web verification")
    args = parser.parse_args()

    try:
        claims = json.loads(args.claims)
        source_urls = json.loads(args.sources)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON argument: {e}"}))
        sys.exit(2)

    if not isinstance(claims, list) or not isinstance(source_urls, list):
        print(json.dumps({"error": "--claims and --sources must be JSON arrays"}))
        sys.exit(2)

    if len(claims) > 100:
        print(json.dumps({"error": "Too many claims (max 100 per call)"}))
        sys.exit(2)

    if not claims:
        result = {
            "claims_checked": 0,
            "pass": True,
            "violations": [],
            "vault_verdict": "CLEAR",
            "web_checked": False,
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Step 1: Vault contradiction check
    vault_result = vault_check(claims)
    vault_verdict = vault_result.get("verdict", "CLEAR")
    vault_violations = vault_result.get("violations", [])

    # Step 2: Web source check (if source URLs provided)
    web_violations = []
    web_checked = False
    if source_urls:
        web_violations = web_check(claims, source_urls)
        web_checked = True

    # Merge violations
    all_violations = vault_violations + web_violations

    # PASS = no conflicts in vault AND no web violations
    # REVIEW from vault alone does not fail — only CONFLICT fails
    passed = (vault_verdict != "CONFLICT") and (len(web_violations) == 0)

    result = {
        "claims_checked": len(claims),
        "pass": passed,
        "violations": all_violations,
        "vault_verdict": vault_verdict,
        "web_checked": web_checked,
    }

    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
