#!/usr/bin/env python3
"""
VaultSearchAgent — entry point for all vault read operations.
Wraps query_vault.py and optionally contradiction_check.py with decision logic.

Usage:
  python vault_search_agent.py --query "explain gradient descent"
  python vault_search_agent.py --query "..." --claims '["claim1"]' --check-contradictions
  python vault_search_agent.py --query "..." --k 8

Output:
  {
    "vault_findings": [{ "file_path", "rel_path", "heading", "block_id", "note_type", "subject", "topic", "excerpt", "score" }],
    "contradiction_result": { "pass", "verdict", "violations", "flags" } | null,
    "hit_count": N
  }
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

from paths import PYTHON_EXE
TOOLS_DIR    = Path(__file__).parent


def run_tool(cmd: list) -> dict:
    """Run a tool subprocess, return parsed JSON output."""
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode not in (0, 1):  # 1 = some tools use 1 for FAIL (not error)
        return {"error": result.stderr.strip() or f"Exit code {result.returncode}"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"Non-JSON output: {result.stdout[:200]}"}


def search_vault(query: str, k: int = 8) -> list:
    """Run query_vault.py and normalize output to vault_findings schema."""
    cmd = [PYTHON_EXE, str(TOOLS_DIR / "query_vault.py"), query, str(k)]
    raw = run_tool(cmd)

    if "error" in raw:
        return []

    findings = []
    results = raw if isinstance(raw, list) else raw.get("results", [])
    for r in results:
        meta = r.get("metadata", r)
        findings.append({
            "file_path": meta.get("file_path", ""),
            "rel_path":  meta.get("rel_path", ""),
            "heading":   meta.get("heading", "") or "",
            "block_id":  meta.get("block_id", "") or "",
            "note_type": meta.get("note_type", ""),
            "subject":   meta.get("subject", ""),
            "topic":     meta.get("topic", ""),
            "excerpt":   r.get("text", ""),
            "score":     r.get("score", 0.0),
        })
    return findings


def check_contradictions(query: str, claims: list, k: int = 6) -> dict:
    """Run contradiction_check.py and return its output."""
    cmd = [
        PYTHON_EXE, str(TOOLS_DIR / "contradiction_check.py"),
        query,
        "--claims", json.dumps(claims),
        "--k", str(k),
    ]
    return run_tool(cmd)


def main():
    parser = argparse.ArgumentParser(description="VaultSearchAgent — vault read + contradiction check")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--claims", default="[]", help="JSON array of factual claims to check")
    parser.add_argument("--check-contradictions", action="store_true",
                        help="Run contradiction_check.py if claims are provided")
    parser.add_argument("--k", type=int, default=8, help="Number of vault chunks to retrieve")
    args = parser.parse_args()

    try:
        claims = json.loads(args.claims)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid --claims JSON: {e}"}))
        sys.exit(1)

    # Step 1: Search vault
    vault_findings = search_vault(args.query, args.k)

    # Step 2: Contradiction check (only if requested and claims provided)
    contradiction_result = None
    if args.check_contradictions and claims:
        contradiction_result = check_contradictions(args.query, claims, args.k)

    output = {
        "vault_findings": vault_findings,
        "contradiction_result": contradiction_result,
        "hit_count": len(vault_findings),
    }
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
