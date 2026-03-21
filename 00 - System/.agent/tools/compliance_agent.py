#!/usr/bin/env python3
"""
ComplianceAgent — validates a draft note against the Vault Constitution.

Checks (in order):
  §XI   — Note type declared and valid
  §XII  — Frontmatter present; recommended fields present for note type
  §XII  — Binding naming rule: H1 exists, matches title, no date prefix, no annotation suffix
  §XIII — Agent-created notes must be inspectable (generated_by field)
  §VII  — Note body has meaningful content

Usage:
  python compliance_agent.py --title "Gradient Descent" --content "---\ntype: concept\n..." [--note-type concept]

Output:
  {
    "status": "PASS" | "FAIL",
    "violations": [
      { "rule": "§XI.2", "location": "frontmatter", "message": "...", "fix": "..." }
    ],
    "checks_run": N,
    "violation_count": N
  }
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import VAULT_ROOT


# ---------------------------------------------------------------------------
# Constitution constants
# ---------------------------------------------------------------------------

VALID_TYPES = {
    "source", "subject-map", "topic", "concept", "practice",
    "review", "revision-plan", "exam", "dashboard", "output",
    # system types (not student-facing but valid)
    "system", "system-map",
}

# Note types that require subject: field (§XII)
SUBJECT_REQUIRED_TYPES = {"concept", "topic", "practice", "review", "source", "output", "exam"}

# Annotation suffixes that violate §XII binding naming rule
ANNOTATION_SUFFIXES = re.compile(
    r"[\s\-_]+(MOC|moc|index|INDEX|hub|HUB|review|REVIEW|map|MAP|"
    r"summary|SUMMARY|notes?|NOTES?)$"
)

# Date prefix patterns that violate §XII binding naming rule
DATE_PREFIX = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}")

RE_FRONTMATTER = re.compile(r"^\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", flags=re.DOTALL)
RE_H1 = re.compile(r"^#\s+(.+)$", flags=re.MULTILINE)


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> Tuple[Optional[Dict[str, str]], str]:
    """
    Returns (fields_dict, body_text).
    fields_dict is None if no frontmatter block found.
    """
    m = RE_FRONTMATTER.match(content)
    if not m:
        return None, content

    fields: Dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip().lower()] = val.strip().strip('"').strip("'")

    body = RE_FRONTMATTER.sub("", content, count=1).strip()
    return fields, body


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------

def check_frontmatter_present(fields: Optional[Dict], body: str) -> List[Dict]:
    if fields is None:
        return [{
            "rule":     "§XI",
            "location": "frontmatter",
            "message":  "No YAML frontmatter block found",
            "fix":      "Add a frontmatter block starting with --- at the top of the note",
        }]
    return []


def check_type_field(fields: Optional[Dict]) -> List[Dict]:
    if fields is None:
        return []
    violations = []
    note_type = fields.get("type", "")
    if not note_type:
        violations.append({
            "rule":     "§XI.1",
            "location": "frontmatter.type",
            "message":  "Required field 'type:' is missing from frontmatter",
            "fix":      f"Add 'type: <value>' where value is one of: {', '.join(sorted(VALID_TYPES))}",
        })
    elif note_type not in VALID_TYPES:
        violations.append({
            "rule":     "§XI.2",
            "location": "frontmatter.type",
            "message":  f"Unrecognised note type: '{note_type}'",
            "fix":      f"Change type to one of: {', '.join(sorted(VALID_TYPES))}",
        })
    return violations


def check_subject_field(fields: Optional[Dict]) -> List[Dict]:
    if fields is None:
        return []
    note_type = fields.get("type", "")
    if note_type in SUBJECT_REQUIRED_TYPES and not fields.get("subject", ""):
        return [{
            "rule":     "§XII.1",
            "location": "frontmatter.subject",
            "message":  f"Field 'subject:' is required for note type '{note_type}' but is missing",
            "fix":      "Add 'subject: <subject name>' to frontmatter",
        }]
    return []


def check_generated_by(fields: Optional[Dict]) -> List[Dict]:
    if fields is None:
        return []
    # Exempt notes explicitly marked as human-authored
    if fields.get("authored_by", "").lower() in ("human", "student", "teacher"):
        return []
    if not fields.get("generated_by", ""):
        return [{
            "rule":     "§XIII.5",
            "location": "frontmatter.generated_by",
            "message":  "Agent-created notes must declare 'generated_by:' for inspectability",
            "fix":      "Add 'generated_by: <agent_name>' to frontmatter, or 'authored_by: human' if human-authored",
        }]
    return []


def check_h1_present(body: str) -> List[Dict]:
    if not RE_H1.search(body):
        return [{
            "rule":     "§XII.2",
            "location": "body",
            "message":  "Note body has no H1 heading",
            "fix":      "Add a '# Title' heading as the first line of the note body",
        }]
    return []


def check_h1_matches_title(body: str, title: str) -> List[Dict]:
    if not title:
        return []
    m = RE_H1.search(body)
    if not m:
        return []  # already caught by check_h1_present
    h1 = m.group(1).strip()
    if h1.lower() != title.strip().lower():
        return [{
            "rule":     "§XII.3",
            "location": "body.h1",
            "message":  f"H1 heading '{h1}' does not match note title '{title}'",
            "fix":      f"Change the H1 heading to exactly '# {title.strip()}'",
        }]
    return []


def check_title_no_date_prefix(title: str) -> List[Dict]:
    if DATE_PREFIX.match(title.strip()):
        return [{
            "rule":     "§XII.4",
            "location": "title",
            "message":  f"Title '{title}' starts with a date prefix — violates naming rule",
            "fix":      "Remove the date prefix; use 'date:' in frontmatter instead",
        }]
    return []


def check_title_no_annotation_suffix(title: str) -> List[Dict]:
    if ANNOTATION_SUFFIXES.search(title.strip()):
        return [{
            "rule":     "§XII.5",
            "location": "title",
            "message":  f"Title '{title}' has an annotation suffix — violates naming rule",
            "fix":      "Remove the annotation suffix; use 'type:' in frontmatter instead",
        }]
    return []


def check_body_has_content(body: str) -> List[Dict]:
    # Strip headings and whitespace to check for actual content
    stripped = re.sub(r"^#{1,6}\s+.*$", "", body, flags=re.MULTILINE).strip()
    if len(stripped) < 30:
        return [{
            "rule":     "§VII",
            "location": "body",
            "message":  "Note body has no meaningful content beyond headings",
            "fix":      "Add substantive content to the note body",
        }]
    return []


def check_no_absolute_paths(body: str) -> List[Dict]:
    # Absolute Windows/Unix paths in note content suggest leaked implementation details
    if re.search(r"[A-Z]:\\|/home/|/usr/|C:/", body):
        return [{
            "rule":     "§VI",
            "location": "body",
            "message":  "Note body contains an absolute file path — vault containment violation",
            "fix":      "Replace absolute paths with vault-relative links [[Note Name]]",
        }]
    return []


# ---------------------------------------------------------------------------
# Main compliance runner
# ---------------------------------------------------------------------------

def run_compliance(title: str, content: str, declared_type: Optional[str] = None) -> Dict:
    fields, body = parse_frontmatter(content)

    violations: List[Dict] = []
    violations += check_frontmatter_present(fields, body)
    violations += check_type_field(fields)
    violations += check_subject_field(fields)
    violations += check_generated_by(fields)
    violations += check_h1_present(body)
    violations += check_h1_matches_title(body, title)
    violations += check_title_no_date_prefix(title)
    violations += check_title_no_annotation_suffix(title)
    violations += check_body_has_content(body)
    violations += check_no_absolute_paths(body)

    # Cross-check declared type vs frontmatter type if both provided
    if declared_type and fields and fields.get("type", "") not in ("", declared_type):
        violations.append({
            "rule":     "§XI.3",
            "location": "frontmatter.type",
            "message":  f"Declared type '{declared_type}' does not match frontmatter type '{fields.get('type')}'",
            "fix":      f"Align frontmatter 'type:' with the intended type '{declared_type}'",
        })

    checks_run = 10
    return {
        "status":          "PASS" if not violations else "FAIL",
        "violations":      violations,
        "checks_run":      checks_run,
        "violation_count": len(violations),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ComplianceAgent — vault constitution checker")
    parser.add_argument("--title",     required=True, help="Proposed note title (= filename without .md)")
    parser.add_argument("--content",   required=True, help="Full note markdown content (frontmatter + body)")
    parser.add_argument("--note-type", default=None,  help="Expected note type for cross-validation")
    args = parser.parse_args()

    result = run_compliance(args.title, args.content, args.note_type)

    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
