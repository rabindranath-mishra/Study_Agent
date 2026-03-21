#!/usr/bin/env python3
"""
NoteWriterAgent — the ONLY entry point to vault write operations.
Enforces both hard gates at code level before calling create_note_stdin.ps1.

Gates (sequential, fail-fast):
  Gate 1 (Facts):      fact_check_result.pass must be True
  Gate 2 (Compliance): compliance_result.status must be "PASS"

Usage:
  python note_writer_agent.py \
    --title "My Note Title" \
    --content "# My Note\n..." \
    --note-type concept \
    --subject Mathematics \
    --topic "Calculus" \
    --fact-check-result '{"pass": true, "violations": [], "claims_checked": 3}' \
    --compliance-result '{"status": "PASS", "violations": []}'

  # --folder overrides the auto type→folder mapping when needed:
  python note_writer_agent.py --title "..." --content "..." --folder "01 - Inbox" ...

Output:
  {
    "path": "...",
    "indexed": true,
    "index_time_ms": N,
    "gate_state": { "fact_check": "PASS", "compliance": "PASS" }
  }

Exit codes:
  0 — success (note written and indexed)
  1 — general error
  2 — Gate 1 failed (fact check)
  3 — Gate 2 failed (compliance check)
  4 — Note write failed
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

from paths import (
    VAULT_ROOT, PYTHON_EXE, PS_SCRIPT_CREATE_NOTE as PS_SCRIPT,
    INBOX_DIR, SOURCES_DIR, SUBJECTS_DIR, CONCEPTS_DIR,
    PRACTICE_DIR, PLANS_DIR, OUTPUTS_DIR,
)

# Maps note type → absolute vault folder path (§XI valid types)
_TYPE_FOLDER_MAP = {
    "source":        SOURCES_DIR,
    "subject-map":   SUBJECTS_DIR,
    "topic":         SUBJECTS_DIR,
    "concept":       CONCEPTS_DIR,
    "practice":      PRACTICE_DIR,
    "review":        PRACTICE_DIR,
    "revision-plan": PLANS_DIR,
    "exam":          PLANS_DIR,
    "output":        OUTPUTS_DIR,
    "dashboard":     OUTPUTS_DIR,
}


def resolve_folder(note_type: str, explicit_folder: str) -> str:
    """Return target folder: explicit_folder wins; else type→folder map; else Inbox."""
    if explicit_folder:
        return explicit_folder
    return _TYPE_FOLDER_MAP.get(note_type.lower(), INBOX_DIR)


def validate_fact_check(fact_check_result: dict) -> tuple:
    """Returns (passed: bool, reason: str)."""
    if not isinstance(fact_check_result, dict):
        return False, "fact_check_result is not a valid object"
    passed = fact_check_result.get("pass")
    if passed is None:
        return False, "fact_check_result.pass is missing (fact check not run)"
    if passed is False:
        violations = fact_check_result.get("violations", [])
        v_count = len(violations)
        return False, f"Fact check failed: {v_count} violation(s) found"
    return True, "PASS"


def validate_compliance(compliance_result: dict) -> tuple:
    """Returns (passed: bool, reason: str)."""
    if not isinstance(compliance_result, dict):
        return False, "compliance_result is not a valid object"
    status = compliance_result.get("status")
    if status is None:
        return False, "compliance_result.status is missing (compliance check not run)"
    if status != "PASS":
        violations = compliance_result.get("violations", [])
        v_count = len(violations)
        return False, f"Compliance check failed ({status}): {v_count} violation(s) found"
    return True, "PASS"


def write_note(title: str, content: str, folder: str) -> dict:
    """Call create_note_stdin.ps1 via PowerShell subprocess."""
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", PS_SCRIPT,
        "-VaultPath", VAULT_ROOT,
        "-Title", title,
        "-Content", content,
    ]
    if folder:
        cmd += ["-Folder", folder]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
        }


def main():
    parser = argparse.ArgumentParser(description="NoteWriterAgent — gated vault write")
    parser.add_argument("--title",    required=True, help="Note title (must match H1 heading)")
    parser.add_argument("--content",  required=True, help="Note markdown content (must include frontmatter)")
    parser.add_argument("--note-type", default="",   help="Note type (concept, topic, practice, …) — used for auto folder routing")
    parser.add_argument("--subject",   default="",   help="Subject area (forwarded to frontmatter if missing)")
    parser.add_argument("--topic",     default="",   help="Topic within subject")
    parser.add_argument("--folder",    default="",   help="Override vault folder — if omitted, resolved from --note-type")
    parser.add_argument("--fact-check-result", required=True,
                        help="JSON from fact_checker_agent.py or FactCheckerAgent")
    parser.add_argument("--compliance-result", required=True,
                        help="JSON from compliance_agent.py or ComplianceAgent")
    args = parser.parse_args()

    # Parse gate results
    try:
        fact_check_result = json.loads(args.fact_check_result)
        compliance_result = json.loads(args.compliance_result)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON gate result: {e}"}))
        sys.exit(1)

    # Gate 1: Fact check
    fc_passed, fc_reason = validate_fact_check(fact_check_result)
    if not fc_passed:
        print(json.dumps({
            "error": "Gate 1 (FactCheck) FAILED — write blocked",
            "reason": fc_reason,
            "gate_state": {"fact_check": "FAIL", "compliance": "NOT_RUN"},
            "violations": fact_check_result.get("violations", []),
        }, indent=2))
        sys.exit(2)

    # Gate 2: Compliance check
    co_passed, co_reason = validate_compliance(compliance_result)
    if not co_passed:
        print(json.dumps({
            "error": "Gate 2 (Compliance) FAILED — write blocked",
            "reason": co_reason,
            "gate_state": {"fact_check": "PASS", "compliance": "FAIL"},
            "violations": compliance_result.get("violations", []),
        }, indent=2))
        sys.exit(3)

    # Both gates passed — resolve folder and write the note
    target_folder = resolve_folder(args.note_type, args.folder)
    write_result = write_note(args.title, args.content, target_folder)

    if not write_result.get("success", False):
        print(json.dumps({
            "error": "Note write failed after gates passed",
            "write_result": write_result,
            "gate_state": {"fact_check": "PASS", "compliance": "PASS"},
        }, indent=2))
        sys.exit(4)

    # Success
    output = {
        "path":          write_result.get("path", ""),
        "note_type":     args.note_type or "unknown",
        "folder":        target_folder,
        "indexed":       write_result.get("indexed", False),
        "index_time_ms": write_result.get("index_time_ms", 0),
        "gate_state": {
            "fact_check":  "PASS",
            "compliance":  "PASS",
        },
    }
    sys.stdout.buffer.write(json.dumps(output, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
