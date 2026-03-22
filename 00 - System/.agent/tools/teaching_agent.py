#!/usr/bin/env python3
"""
TeachingAgent — explains concepts using pedagogical strategies.

Flow:
  1. Load student profile (grade, learning_style) from learner_profile_store
  2. Search vault for existing content
  3. If top vault score < 0.6: fall back to web search
  4. Compose explanation adapted to student level and learning style
  5. Return structured JSON

Usage:
  python teaching_agent.py --concept "photosynthesis" --subject "Biology"
  python teaching_agent.py --concept "osmosis" --subject "Biology" --context "exam prep"
  python teaching_agent.py --concept "integration" --subject "Mathematics" --student-level advanced

Output:
  {
    "concept": "photosynthesis",
    "subject": "Biology",
    "student_level": "intermediate",
    "grade": "11",
    "learning_style": "balanced",
    "explanation": "...",
    "examples": ["...", "..."],
    "key_points": ["...", "..."],
    "exam_tips": ["...", "..."],
    "suggested_practice": ["quiz", "flashcards"],
    "sources": [{"type": "vault|web", "ref": "..."}],
    "vault_score": 0.72,
    "used_web": false
  }

Exit codes:
  0 — success
  1 — error (profile missing, tool failure, etc.)
"""

import sys
import json
import argparse
import subprocess
import os
from pathlib import Path
from typing import Optional

# Add tools dir to path so we can import local modules
TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from paths import PYTHON_EXE

_UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

# Vault-search fallback threshold — if best score is below this, web search is triggered
VAULT_SCORE_THRESHOLD = 0.6

# ── Grade-level descriptors ───────────────────────────────────────────────────
_GRADE_LEVEL_MAP = {
    "9":  "beginner",
    "10": "beginner",
    "11": "intermediate",
    "12": "intermediate",
}

_LEVEL_INSTRUCTIONS = {
    "beginner": (
        "Use simple, accessible language. Avoid jargon — when you must use a technical term, "
        "immediately explain it in plain words. Lead with a relatable real-world analogy. "
        "Break the explanation into short, numbered steps. Use concrete, everyday examples."
    ),
    "intermediate": (
        "Use precise subject-specific terminology, but define any advanced terms. "
        "Connect the concept to related topics the student likely knows. "
        "Include at least one worked example or case study. "
        "Highlight exam-relevant points explicitly."
    ),
    "advanced": (
        "Assume strong subject knowledge. Go into mechanistic depth. "
        "Reference formal definitions, edge cases, and underlying principles. "
        "Connect to higher-level or cross-disciplinary applications. "
        "Frame key points in exam/assessment language."
    ),
}

_STYLE_INSTRUCTIONS = {
    "visual": (
        "Structure the explanation so it maps easily to a diagram or flowchart. "
        "Suggest a diagram the student could draw. Use tables or structured lists where possible."
    ),
    "reading": (
        "Provide a dense but well-structured text explanation. "
        "Use clear headings and bullet-point summaries. "
        "Include definition boxes for key terms."
    ),
    "practical": (
        "Lead with a worked example or real-world scenario. "
        "Show the concept in action before explaining the theory. "
        "Include step-by-step problem-solving guidance."
    ),
    "balanced": (
        "Mix text explanation, a worked example, and a brief diagram suggestion. "
        "Cover both conceptual understanding and practical application."
    ),
}


# ── Subprocess helpers ────────────────────────────────────────────────────────

def _run_tool(cmd: list) -> dict:
    """Run a tool subprocess and return parsed JSON, or an error dict."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_UTF8_ENV,
    )
    if result.returncode not in (0, 1):
        return {"error": result.stderr.strip() or f"Exit code {result.returncode}"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"Non-JSON output: {result.stdout[:300]}"}


def _search_vault(query: str, k: int = 8) -> dict:
    cmd = [
        PYTHON_EXE,
        str(TOOLS_DIR / "vault_search_agent.py"),
        "--query", query,
        "--k", str(k),
    ]
    return _run_tool(cmd)


def _search_web(query: str, max_results: int = 6) -> dict:
    cmd = [
        PYTHON_EXE,
        str(TOOLS_DIR / "web_search_agent.py"),
        "--query", query,
        "--max-results", str(max_results),
        "--search-depth", "advanced",
    ]
    return _run_tool(cmd)


# ── Profile helpers ───────────────────────────────────────────────────────────

def _load_profile() -> dict:
    """Load the learner profile. Returns empty dict if unavailable."""
    try:
        import learner_profile_store as store
        return store.get_profile()
    except Exception:
        return {}


def _resolve_level(profile: dict, explicit_level: Optional[str]) -> tuple:
    """
    Returns (student_level, grade, learning_style).
    explicit_level overrides profile if provided.
    """
    grade = str(profile.get("grade", "11")).strip()
    learning_style = profile.get("learning_style", "balanced")

    if explicit_level:
        level = explicit_level
    else:
        level = _GRADE_LEVEL_MAP.get(grade, "intermediate")

    return level, grade, learning_style


# ── Content synthesis ─────────────────────────────────────────────────────────

def _best_vault_score(vault_result: dict) -> float:
    """Return the highest similarity score from vault findings."""
    findings = vault_result.get("vault_findings", [])
    if not findings:
        return 0.0
    return max(f.get("score", 0.0) for f in findings)


def _summarise_vault_findings(findings: list, max_excerpts: int = 4) -> str:
    """Distill top vault excerpts into a compact reference block."""
    top = sorted(findings, key=lambda f: f.get("score", 0.0), reverse=True)[:max_excerpts]
    parts = []
    for f in top:
        ref = f.get("rel_path", f.get("file_path", "vault"))
        excerpt = f.get("excerpt", "").strip()
        if excerpt:
            parts.append(f"[{ref}]: {excerpt}")
    return "\n\n".join(parts)


def _summarise_web_findings(findings: list, max_results: int = 3) -> str:
    """Distill top web results into a compact reference block."""
    top = sorted(findings, key=lambda f: f.get("score", 0.0), reverse=True)[:max_results]
    parts = []
    for f in top:
        title = f.get("title", "")
        content = (f.get("content", "") or "").strip()[:600]
        url = f.get("url", "")
        if content:
            parts.append(f"[{title} — {url}]: {content}")
    return "\n\n".join(parts)


def _build_explanation(
    concept: str,
    subject: str,
    context: str,
    level: str,
    grade: str,
    learning_style: str,
    content_block: str,
) -> dict:
    """
    Synthesise a structured teaching response from retrieved content.
    Returns the explanation dict (explanation, examples, key_points, exam_tips,
    suggested_practice).
    """
    level_hint = _LEVEL_INSTRUCTIONS.get(level, _LEVEL_INSTRUCTIONS["intermediate"])
    style_hint = _STYLE_INSTRUCTIONS.get(learning_style, _STYLE_INSTRUCTIONS["balanced"])
    context_hint = f" in the context of {context}" if context else ""

    # Parse the content block into sections heuristically.
    # We look for headings, bullet points, and key sentence patterns.
    lines = content_block.splitlines()
    examples, key_points, exam_tips = [], [], []
    explanation_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(kw in lower for kw in ("example:", "e.g.", "for instance", "such as")):
            examples.append(stripped)
        elif any(kw in lower for kw in ("exam tip", "cbse", "board exam", "marks", "question pattern")):
            exam_tips.append(stripped)
        elif stripped.startswith(("- ", "• ", "* ", "→ ")):
            key_points.append(stripped.lstrip("-•*→ "))
        else:
            explanation_lines.append(stripped)

    explanation = " ".join(explanation_lines[:30]) if explanation_lines else (
        f"{concept} is a key concept in {subject}."
    )

    # Ensure we always return something meaningful even if content is thin
    if not examples:
        examples = [f"Refer to your {subject} textbook for worked examples on {concept}."]
    if not key_points:
        key_points = [f"Understand the definition and mechanism of {concept}."]
    if not exam_tips:
        exam_tips = [
            f"CBSE Class {grade} questions on {concept} often test definitions and applications.",
            "Write answers in point form for better marks.",
        ]

    suggested_practice = _suggest_practice(level)

    return {
        "explanation": explanation,
        "examples": examples[:5],
        "key_points": key_points[:8],
        "exam_tips": exam_tips[:4],
        "suggested_practice": suggested_practice,
        "level_hint": level_hint,
        "style_hint": style_hint,
    }


def _suggest_practice(level: str) -> list:
    base = ["flashcards", "short-answer questions"]
    if level == "beginner":
        return base + ["fill-in-the-blank exercises"]
    if level == "intermediate":
        return base + ["MCQ quiz", "diagram labelling"]
    return base + ["long-answer questions", "past paper practice"]


def _build_sources(vault_findings: list, web_findings: list) -> list:
    sources = []
    for f in vault_findings[:3]:
        ref = f.get("rel_path") or f.get("file_path", "")
        if ref:
            sources.append({"type": "vault", "ref": ref, "score": round(f.get("score", 0.0), 3)})
    for f in web_findings[:3]:
        url = f.get("url", "")
        title = f.get("title", "")
        if url:
            sources.append({"type": "web", "ref": url, "title": title})
    return sources


def _collect_raw_content(vault_findings: list, web_findings: list) -> list:
    """
    Return full unprocessed text chunks from vault and web results.
    These give the LLM-layer agent maximum material to elaborate from,
    beyond the regex-extracted fragments in examples/key_points/exam_tips.
    """
    raw = []
    for f in vault_findings[:6]:
        excerpt = (f.get("excerpt") or f.get("content") or "").strip()
        ref = f.get("rel_path") or f.get("file_path", "vault")
        score = round(f.get("score", 0.0), 3)
        if excerpt:
            raw.append({"source": "vault", "ref": ref, "score": score, "text": excerpt})
    for f in web_findings[:4]:
        content = (f.get("content") or f.get("excerpt") or "").strip()
        url = f.get("url", "")
        title = f.get("title", "")
        if content:
            raw.append({"source": "web", "ref": url, "title": title, "text": content})
    return raw


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TeachingAgent — concept explanation with level adaptation")
    parser.add_argument("--concept",       required=True, help="Concept to explain")
    parser.add_argument("--subject",       default="",   help="Subject area (e.g. Biology, Mathematics)")
    parser.add_argument("--context",       default="",   help="Learning context (e.g. 'exam preparation')")
    parser.add_argument("--student-level", default="",
                        help="Override level: beginner | intermediate | advanced")
    args = parser.parse_args()

    # 1. Load profile
    profile = _load_profile()
    level, grade, learning_style = _resolve_level(profile, args.student_level or None)

    # 2. Search vault
    search_query = f"{args.concept} {args.subject}".strip()
    vault_result = _search_vault(search_query)
    vault_score = _best_vault_score(vault_result)
    vault_findings = vault_result.get("vault_findings", [])

    # 3. Web fallback if vault score below threshold
    used_web = False
    web_findings = []
    if vault_score < VAULT_SCORE_THRESHOLD:
        grade_hint = f"CBSE class {grade}" if grade else ""
        web_query = f"{args.concept} {args.subject} {grade_hint} {args.context}".strip()
        web_result = _search_web(web_query)
        web_findings = web_result.get("web_findings", [])
        if "error" not in web_result:
            used_web = True

    # 4. Build content block from whichever source(s) we have
    content_parts = []
    if vault_findings:
        content_parts.append(_summarise_vault_findings(vault_findings))
    if web_findings:
        content_parts.append(_summarise_web_findings(web_findings))
    content_block = "\n\n".join(content_parts)

    # 5. Synthesise explanation
    built = _build_explanation(
        concept=args.concept,
        subject=args.subject,
        context=args.context,
        level=level,
        grade=grade,
        learning_style=learning_style,
        content_block=content_block,
    )

    # 6. Assemble output
    output = {
        "concept":        args.concept,
        "subject":        args.subject,
        "student_level":  level,
        "grade":          grade,
        "learning_style": learning_style,
        "explanation":    built["explanation"],
        "examples":       built["examples"],
        "key_points":     built["key_points"],
        "exam_tips":      built["exam_tips"],
        "pedagogy": {
            "level_guidance": built["level_hint"],
            "style_guidance": built["style_hint"],
        },
        "suggested_practice": built["suggested_practice"],
        "sources":        _build_sources(vault_findings, web_findings),
        "raw_content":    _collect_raw_content(vault_findings, web_findings),
        "vault_score":    round(vault_score, 3),
        "used_web":       used_web,
    }

    sys.stdout.buffer.write(json.dumps(output, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
