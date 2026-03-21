#!/usr/bin/env python3
"""
PracticeAgent — generates practice questions from vault content.

Flow:
  1. Load student profile (grade, learning_style) from learner_profile_store
  2. Search vault for topic content
  3. If top vault score < 0.6: fall back to web search
  4. Extract testable content (definitions, facts, steps, comparisons)
  5. Generate questions of the requested types
  6. Return structured JSON ready for note writing

Supported question types:
  mcq          - Multiple choice (4 options, 1 correct)
  short_answer - Short written response ("Define / Explain / State…")
  long_answer  - Extended response ("Discuss / Analyse / Compare…")
  fill_blank   - Cloze sentences with key terms blanked
  true_false   - True/False statements with justification

Usage:
  python practice_agent.py --topic "photosynthesis" --subject "Biology"
  python practice_agent.py --topic "osmosis" --subject "Biology" --question-count 8 --difficulty intermediate
  python practice_agent.py --topic "integration" --subject "Mathematics" --question-types mcq,short_answer

Output:
  {
    "topic": "photosynthesis",
    "subject": "Biology",
    "difficulty": "intermediate",
    "grade": "11",
    "question_count": 10,
    "estimated_time": "20 minutes",
    "questions": [
      {
        "id": 1,
        "type": "mcq",
        "question": "...",
        "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
        "answer": "A",
        "explanation": "..."
      },
      ...
    ],
    "topics_covered": ["light reactions", "calvin cycle"],
    "sources": [{"type": "vault|web", "ref": "..."}],
    "vault_score": 0.72,
    "used_web": false,
    "note_content": "...",
    "suggested_note_title": "Photosynthesis — Practice Questions"
  }

Exit codes:
  0 — success
  1 — error
"""

import sys
import json
import re
import argparse
import subprocess
import os
from pathlib import Path
from datetime import date
from typing import Optional

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from paths import PYTHON_EXE
import marking_scheme_store as _mss

_UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

VAULT_SCORE_THRESHOLD = 0.6

# ── Time estimates (minutes per question by type) ─────────────────────────────
_TIME_PER_Q = {
    "mcq":          1.5,
    "short_answer": 3.0,
    "long_answer":  8.0,
    "fill_blank":   1.5,
    "true_false":   1.0,
}

_ALL_TYPES = list(_TIME_PER_Q.keys())

# ── Grade → difficulty defaults ───────────────────────────────────────────────
_GRADE_DIFFICULTY = {
    "9":  "beginner",
    "10": "beginner",
    "11": "intermediate",
    "12": "intermediate",
}

# ── Verb banks by difficulty ──────────────────────────────────────────────────
_SHORT_VERBS = {
    "beginner":     ["What is", "Name", "Define", "State", "List", "Identify"],
    "intermediate": ["Explain", "Describe", "Distinguish between", "Give two examples of", "Outline"],
    "advanced":     ["Analyse", "Evaluate", "Compare and contrast", "Justify", "Examine"],
}
_LONG_VERBS = {
    "beginner":     ["Describe in detail", "Explain with examples", "Write a short note on"],
    "intermediate": ["Discuss", "Explain the significance of", "Compare and contrast"],
    "advanced":     ["Critically evaluate", "Analyse the role of", "Examine the relationship between"],
}


# ── Subprocess helpers ────────────────────────────────────────────────────────

def _run_tool(cmd: list) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=_UTF8_ENV)
    if result.returncode not in (0, 1):
        return {"error": result.stderr.strip() or f"Exit code {result.returncode}"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": f"Non-JSON output: {result.stdout[:300]}"}


def _search_vault(query: str, k: int = 10) -> dict:
    return _run_tool([PYTHON_EXE, str(TOOLS_DIR / "vault_search_agent.py"), "--query", query, "--k", str(k)])


def _search_web(query: str, max_results: int = 6) -> dict:
    return _run_tool([
        PYTHON_EXE, str(TOOLS_DIR / "web_search_agent.py"),
        "--query", query, "--max-results", str(max_results), "--search-depth", "advanced",
    ])


# ── Profile helpers ───────────────────────────────────────────────────────────

def _load_profile() -> dict:
    try:
        import learner_profile_store as store
        return store.get_profile()
    except Exception:
        return {}


def _resolve_context(profile: dict, explicit_difficulty: Optional[str]) -> tuple:
    """
    Returns (difficulty, grade, board) from profile + optional override.

    Reads grade from profile.current_level.grade (strips "Class " prefix),
    falls back to profile.grade for flat profiles.
    """
    # Board
    board = _mss.get_board_from_profile(profile)

    # Grade — handle "Class 11" and plain "11" shapes
    current_level = profile.get("current_level", {})
    raw_grade = current_level.get("grade") or profile.get("grade", "11")
    import re as _re
    m = _re.search(r'\d+', str(raw_grade))
    grade = m.group(0) if m else str(raw_grade)

    # Difficulty
    if explicit_difficulty:
        difficulty = explicit_difficulty
    else:
        difficulty = _GRADE_DIFFICULTY.get(grade, "intermediate")

    return difficulty, grade, board


# ── Content extraction ────────────────────────────────────────────────────────

def _best_vault_score(vault_result: dict) -> float:
    findings = vault_result.get("vault_findings", [])
    return max((f.get("score", 0.0) for f in findings), default=0.0)


def _extract_content_blocks(vault_findings: list, web_findings: list) -> list:
    """
    Return a flat list of text blocks from all findings, deduplicated.
    Each block is a non-empty string of meaningful length.
    """
    blocks = []
    seen = set()

    def _add(text: str):
        text = text.strip()
        if text and len(text) > 20 and text not in seen:
            seen.add(text)
            blocks.append(text)

    for f in vault_findings:
        _add(f.get("excerpt", ""))

    for f in web_findings:
        content = f.get("content", "") or ""
        # Split web content into paragraphs
        for para in content.split("\n\n"):
            _add(para.strip())

    return blocks


def _extract_sentences(blocks: list) -> list:
    """Split blocks into individual sentences."""
    sentences = []
    for block in blocks:
        # Split on sentence boundaries
        parts = re.split(r'(?<=[.!?])\s+', block)
        for p in parts:
            p = p.strip()
            if len(p) > 15:
                sentences.append(p)
    return sentences


def _extract_definitions(sentences: list, topic: str) -> list:
    """Find sentences that look like definitions."""
    defs = []
    patterns = [
        r'\bis\b.{5,100}',
        r'\bare\b.{5,100}',
        r'\brefers to\b',
        r'\bdefined as\b',
        r'\bmeans\b',
        r'\bknown as\b',
    ]
    for s in sentences:
        if any(re.search(p, s, re.I) for p in patterns):
            defs.append(s)
    return defs[:10]


def _extract_key_terms(sentences: list) -> list:
    """Extract capitalised or bold-marked terms as key vocabulary."""
    terms = []
    seen = set()
    for s in sentences:
        # Bold terms in markdown
        for match in re.finditer(r'\*\*(.+?)\*\*', s):
            t = match.group(1).strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                terms.append(t)
        # Sentence-initial capitalised words (skip "The", "A", "An", "In", etc.)
        stop = {"the", "a", "an", "in", "on", "at", "by", "for", "with",
                "and", "or", "but", "if", "when", "where", "this", "that",
                "these", "those", "it", "its", "from", "to", "of", "is",
                "are", "was", "were"}
        words = re.findall(r'\b[A-Z][a-z]{3,}\b', s)
        for w in words:
            if w.lower() not in stop and w.lower() not in seen:
                seen.add(w.lower())
                terms.append(w)
    return terms[:20]


def _extract_list_items(blocks: list) -> list:
    """Extract bullet/numbered list items as discrete facts."""
    items = []
    for block in blocks:
        for line in block.splitlines():
            m = re.match(r'^[\-\*\•\d\.]+\s+(.+)', line.strip())
            if m:
                item = m.group(1).strip()
                if len(item) >= 5:
                    items.append(item)
    return items[:15]


# ── CBSE value-point builder ──────────────────────────────────────────────────

def _build_value_points(
    marks: int,
    topic: str,
    subject: str,
    sentences: list,
    key_terms: list,
    list_items: list,
    board_q_scheme: Optional[dict] = None,
) -> list:
    """
    Generate value points aligned to the board's marking scheme for
    the given mark allocation.

    Each value point is a concrete, self-contained statement worth 1 mark.
    Returns exactly `marks` points (padded with generic points if content is thin).
    """
    # Resolve scheme entry from the board's q_scheme or fall back to generic
    scheme = None
    if board_q_scheme:
        # Find closest mark band
        if marks in board_q_scheme:
            scheme = board_q_scheme[marks]
        else:
            candidates = sorted(board_q_scheme.keys())
            lower = [k for k in candidates if k <= marks]
            key = lower[-1] if lower else candidates[0]
            scheme = board_q_scheme.get(key)

    if scheme:
        n = scheme.get("value_point_count", marks)
        breakdown = scheme.get("breakdown", [f"Value point {i+1} (1 mark)" for i in range(n)])
    else:
        n = marks
        breakdown = [f"Value point {i+1} (1 mark)" for i in range(n)]

    # Pool of content sentences: prefer definition-like sentences first
    def_sentences = [s for s in sentences if re.search(
        r'\b(is|are|refers to|defined as|means|known as)\b', s, re.I)]
    fact_sentences = [s for s in sentences if s not in def_sentences]
    example_sentences = [s for s in sentences if re.search(
        r'\b(example|instance|e\.g\.|such as|for instance|application)\b', s, re.I)]

    # Build value points following CBSE structure for each breakdown slot
    value_points = []
    used_sentences = set()

    def _pick_sentence(pool: list, fallback: str) -> str:
        for s in pool:
            if s not in used_sentences and len(s) > 15:
                used_sentences.add(s)
                return s[:250]
        return fallback

    for i, slot_label in enumerate(breakdown[:n]):
        slot_lower = slot_label.lower()

        if i == 0 and ("intro" in slot_lower or "definition" in slot_lower):
            # Slot 0: always a definition
            point = _pick_sentence(
                def_sentences,
                f"{topic} is an important concept in {subject}."
            )
        elif "example" in slot_lower or "application" in slot_lower or "diagram" in slot_lower:
            # Last slot: example / application / diagram note
            point = _pick_sentence(
                example_sentences,
                f"Example: {list_items[0] if list_items else topic + ' has practical applications in ' + subject + '.'}",
            )
        elif list_items and i < len(list_items):
            # Body slots: pull from list items (most fact-dense content)
            item = list_items[i]
            if item not in used_sentences:
                used_sentences.add(item)
                point = item[:250]
            else:
                point = _pick_sentence(fact_sentences, f"Key fact {i+1} about {topic}.")
        else:
            point = _pick_sentence(
                fact_sentences,
                f"Key fact {i+1}: {key_terms[i] if i < len(key_terms) else topic} is significant in {subject}.",
            )

        value_points.append({
            "slot":   slot_label,
            "point":  point,
            "marks":  1,
        })

    return value_points


def _marks_for_difficulty(q_type: str, difficulty: str) -> int:
    """Return standard mark allocation per question type and difficulty."""
    if q_type == "short_answer":
        return 2 if difficulty == "beginner" else 3
    if q_type == "long_answer":
        return 5 if difficulty != "advanced" else 8
    return 1  # mcq, fill_blank, true_false



def _make_mcq(topic: str, subject: str, sentences: list, key_terms: list,
              list_items: list, difficulty: str, start_id: int,
              mcq_scheme: Optional[dict] = None) -> list:
    questions = []
    qid = start_id

    # Strategy 1: definition-based MCQ from sentences
    defs = [s for s in sentences if re.search(r'\bis\b|\bare\b|\bdefined\b', s, re.I)]
    for defn in defs[:3]:
        # Extract the subject of the definition (first noun phrase)
        subj_match = re.match(r'^([A-Za-z\s\-]{3,40})\s+(?:is|are|refers)', defn, re.I)
        if not subj_match:
            continue
        term = subj_match.group(1).strip()
        questions.append({
            "id": qid,
            "type": "mcq",
            "question": f"Which of the following best describes {term}?",
            "options": {
                "A": defn[:120],
                "B": f"A process unrelated to {term} in {subject}.",
                "C": f"The opposite of what {term} actually means.",
                "D": f"A term synonymous with {topic} but distinct from {term}.",
            },
            "answer": "A",
            "explanation": f"Option A correctly describes {term} as stated in the study material.",
            "marking_scheme": mcq_scheme or _mss.get_scheme("Generic")["mcq"],
        })
        qid += 1
        if len(questions) >= 3:
            break

    # Strategy 2: list-item MCQ (which of these is correct?)
    if list_items and len(questions) < 4:
        correct = list_items[0] if list_items else f"{topic} is important in {subject}."
        questions.append({
            "id": qid,
            "type": "mcq",
            "question": f"Which of the following statements about {topic} is correct?",
            "options": {
                "A": correct[:120],
                "B": f"{topic} has no significance in {subject}.",
                "C": f"{topic} and photosynthesis are the same process.",
                "D": f"{topic} only occurs in animals, not plants.",
            },
            "answer": "A",
            "explanation": f"Option A is directly supported by the study material on {topic}.",
            "marking_scheme": mcq_scheme or _mss.get_scheme("Generic")["mcq"],
        })
        qid += 1

    # Strategy 3: key-term identification
    if key_terms and len(questions) < 5:
        term = key_terms[0]
        questions.append({
            "id": qid,
            "type": "mcq",
            "question": f"In the context of {topic}, what is the role of {term}?",
            "options": {
                "A": f"{term} plays a central role in {topic}.",
                "B": f"{term} is irrelevant to {topic}.",
                "C": f"{term} inhibits all processes in {topic}.",
                "D": f"{term} is found only outside the scope of {subject}.",
            },
            "answer": "A",
            "explanation": f"{term} is a key component mentioned in the {topic} material.",
            "marking_scheme": mcq_scheme or _mss.get_scheme("Generic")["mcq"],
        })
        qid += 1

    return questions


def _make_short_answer(topic: str, subject: str, sentences: list,
                       key_terms: list, list_items: list,
                       difficulty: str, start_id: int,
                       board_q_scheme: Optional[dict] = None) -> list:
    verbs = _SHORT_VERBS.get(difficulty, _SHORT_VERBS["intermediate"])
    questions = []
    qid = start_id
    marks = _marks_for_difficulty("short_answer", difficulty)
    _q_scheme = board_q_scheme or _mss.get_scheme("Generic")["q_scheme"]
    scheme = _mss.get_q_scheme_by_marks(_q_scheme, marks)

    prompts = [
        (verbs[0], topic),
        (verbs[1] if len(verbs) > 1 else verbs[0], topic),
    ]
    for i, term_name in enumerate(key_terms[:2]):
        prompts.append((verbs[i % len(verbs)], term_name))

    for verb, term in prompts[:4]:
        value_points = _build_value_points(marks, term, subject, sentences, key_terms, list_items, board_q_scheme)
        questions.append({
            "id":    qid,
            "type":  "short_answer",
            "question": f"{verb} {term}.",
            "marks": marks,
            "word_limit": scheme["word_limit"],
            "marking_scheme": {
                "total_marks":     marks,
                "structure":       scheme["structure"],
                "partial_credit":  scheme["partial_credit"],
                "examiner_note":   scheme["note"],
                "value_points":    value_points,
            },
        })
        qid += 1

    return questions


def _make_long_answer(topic: str, subject: str, sentences: list,
                      key_terms: list, list_items: list,
                      difficulty: str, start_id: int,
                      board_q_scheme: Optional[dict] = None) -> list:
    verbs = _LONG_VERBS.get(difficulty, _LONG_VERBS["intermediate"])
    questions = []
    qid = start_id
    marks = _marks_for_difficulty("long_answer", difficulty)
    _q_scheme = board_q_scheme or _mss.get_scheme("Generic")["q_scheme"]
    scheme = _mss.get_q_scheme_by_marks(_q_scheme, marks)

    prompts = [
        (verbs[0], topic),
        (verbs[1] if len(verbs) > 1 else verbs[0], topic),
    ]
    if key_terms and len(key_terms) >= 2:
        prompts.append((verbs[-1], f"{key_terms[0]} and {key_terms[1]}"))

    for verb, term in prompts[:2]:
        value_points = _build_value_points(marks, term, subject, sentences, key_terms, list_items, board_q_scheme)
        questions.append({
            "id":    qid,
            "type":  "long_answer",
            "question": f"{verb} {term}.",
            "marks": marks,
            "word_limit": scheme["word_limit"],
            "marking_scheme": {
                "total_marks":    marks,
                "structure":      scheme["structure"],
                "partial_credit": scheme["partial_credit"],
                "examiner_note":  scheme["note"],
                "value_points":   value_points,
            },
        })
        qid += 1

    return questions


def _make_fill_blank(topic: str, sentences: list, key_terms: list,
                     start_id: int, fill_blank_scheme: Optional[dict] = None) -> list:
    questions = []
    qid = start_id
    _fb_scheme = fill_blank_scheme or _mss.get_scheme("Generic")["fill_blank"]

    # Blank out key terms in sentences that contain them
    used_terms = set()
    for sentence in sentences[:20]:
        for term in key_terms:
            if term in sentence and term.lower() not in used_terms and len(sentence) > 20:
                blanked = sentence.replace(term, "_______", 1)
                if blanked != sentence:  # replacement happened
                    questions.append({
                        "id": qid,
                        "type": "fill_blank",
                        "question": f"Fill in the blank: {blanked}",
                        "answer": term,
                        "marking_scheme": _fb_scheme,
                    })
                    used_terms.add(term.lower())
                    qid += 1
                    if len(questions) >= 4:
                        return questions
                    break

    # Fallback: generic blanks from topic name
    if not questions:
        questions.append({
            "id": qid,
            "type": "fill_blank",
            "question": f"_______ is a key concept studied in the topic of {topic}.",
            "answer": topic,
            "marking_scheme": _fb_scheme,
        })

    return questions


def _make_true_false(topic: str, subject: str, sentences: list, start_id: int,
                     true_false_scheme: Optional[dict] = None) -> list:
    questions = []
    qid = start_id
    _tf_scheme = true_false_scheme or _mss.get_scheme("Generic")["true_false"]

    # True statements from sentences
    for s in sentences[:3]:
        if len(s) > 20:
            questions.append({
                "id": qid,
                "type": "true_false",
                "question": s[:150],
                "answer": "True",
                "justification": "This is directly stated in the study material.",
                "marking_scheme": _tf_scheme,
            })
            qid += 1

    # False statements (negated topic facts)
    false_stmts = [
        f"{topic} has no practical applications in real life.",
        f"{topic} is not covered in the {subject} curriculum.",
        f"{topic} was only relevant in historical contexts.",
    ]
    for stmt in false_stmts[:2]:
        questions.append({
            "id": qid,
            "type": "true_false",
            "question": stmt,
            "answer": "False",
            "justification": f"This contradicts the established facts about {topic} in {subject}.",
            "marking_scheme": _tf_scheme,
        })
        qid += 1

    return questions


# ── Question orchestration ────────────────────────────────────────────────────

def _distribute_questions(total: int, types: list) -> dict:
    """Distribute total question count evenly across requested types."""
    if not types:
        types = ["mcq", "short_answer"]
    per_type = max(1, total // len(types))
    remainder = total - per_type * len(types)
    dist = {t: per_type for t in types}
    # Give remainder to first type
    if remainder > 0:
        dist[types[0]] += remainder
    return dist


def _estimate_time(questions: list) -> str:
    total_mins = sum(_TIME_PER_Q.get(q.get("type", "mcq"), 2.0) for q in questions)
    total_mins = round(total_mins)
    return f"{total_mins} minutes"


def _build_answer_key(questions: list) -> list:
    """
    Build a board-aware answer key for all questions.

    For SA/LA: renders value points with per-point mark allocation.
    For MCQ/fill_blank/true_false: renders answer + examiner note.
    """
    key = []
    for q in questions:
        entry = {"id": q["id"], "type": q["type"], "marks": q.get("marks", 1)}
        ms = q.get("marking_scheme", {})

        if q["type"] == "mcq":
            entry["answer"] = q.get("answer", "")
            entry["explanation"] = q.get("explanation", "")
            entry["examiner_note"] = ms.get("note", "Full mark for correct answer only.")

        elif q["type"] in ("short_answer", "long_answer"):
            entry["total_marks"]    = ms.get("total_marks", q.get("marks", 3))
            entry["structure"]      = ms.get("structure", "")
            entry["partial_credit"] = ms.get("partial_credit", True)
            entry["examiner_note"]  = ms.get("examiner_note", "")
            entry["value_points"]   = ms.get("value_points", [])

        elif q["type"] == "fill_blank":
            entry["answer"] = q.get("answer", "")
            entry["examiner_note"] = ms.get("note", "Accept exact answer or accepted variants.")

        elif q["type"] == "true_false":
            entry["answer"] = q.get("answer", "")
            entry["justification"] = q.get("justification", "")
            entry["marks_answer"] = ms.get("marks_answer", 0.5)
            entry["marks_justification"] = ms.get("marks_justification", 0.5)
            entry["examiner_note"] = ms.get("note", "Mark awarded for correct statement AND justification.")

        key.append(entry)
    return key


def _build_sources(vault_findings: list, web_findings: list) -> list:
    sources = []
    for f in vault_findings[:3]:
        ref = f.get("rel_path") or f.get("file_path", "")
        if ref:
            sources.append({"type": "vault", "ref": ref, "score": round(f.get("score", 0.0), 3)})
    for f in web_findings[:2]:
        url = f.get("url", "")
        if url:
            sources.append({"type": "web", "ref": url, "title": f.get("title", "")})
    return sources


# ── Note content builder ──────────────────────────────────────────────────────

def _build_note_content(
    title: str, topic: str, subject: str, difficulty: str,
    grade: str, question_count: int, estimated_time: str,
    questions: list, topics_covered: list,
    board: str = "CBSE",
) -> str:
    today = date.today().isoformat()
    subject_tag = subject.lower().replace(" ", "-") if subject else "general"
    board_display = _mss.get_scheme(board).get("board_display", board)

    lines = [
        "---",
        f'title: "{title}"',
        f"date: {today}",
        "tags:",
        "  - practice",
        f"  - {subject_tag}",
        "note_type: practice",
        f'subject: "{subject}"',
        f'topic: "{topic}"',
        f'grade: "{grade}"',
        f'difficulty: "{difficulty}"',
        f"question_count: {question_count}",
        f'estimated_time: "{estimated_time}"',
        "---",
        "",
        f"# {title}",
        "",
        f"> **Subject:** {subject} | **Topic:** {topic} | **Difficulty:** {difficulty} | **Board:** {board_display} | **Time:** {estimated_time}",
        "",
        "---",
        "",
    ]

    # Group questions by type
    by_type = {}
    for q in questions:
        by_type.setdefault(q["type"], []).append(q)

    section_titles = {
        "mcq":          "Multiple Choice Questions",
        "short_answer": "Short Answer Questions",
        "long_answer":  "Long Answer Questions",
        "fill_blank":   "Fill in the Blanks",
        "true_false":   "True / False",
    }

    for qtype, section_title in section_titles.items():
        qs = by_type.get(qtype, [])
        if not qs:
            continue
        lines += [f"## {section_title}", ""]
        for q in qs:
            lines.append(f"**Q{q['id']}.** {q['question']}")
            if qtype == "mcq":
                opts = q.get("options", {})
                for letter, opt in opts.items():
                    lines.append(f"   {letter}) {opt}")
            elif qtype == "long_answer":
                marks = q.get("marks", 5)
                wlimit = q.get("word_limit", "200-300")
                lines.append(f"   *({marks} marks | Word limit: {wlimit} words)*")
            elif qtype == "short_answer":
                marks = q.get("marks", 3)
                lines.append(f"   *({marks} marks)*")
            lines.append("")

    # Answer key — board marking scheme format
    lines += ["---", "", "## Answer Key", "",
              f"> *Marking as per {board_display} scheme. Award marks only for value points listed.*",
              ""]
    answer_key = _build_answer_key(questions)
    for entry in answer_key:
        qid = entry["id"]
        qtype = entry["type"]
        marks = entry.get("marks", 1)

        if qtype == "mcq":
            lines.append(f"**Q{qid}.** *(1 mark)* Correct answer: **{entry.get('answer', '')}**")
            lines.append(f"   {entry.get('explanation', '')}")
            lines.append(f"   *{entry.get('examiner_note', '')}*")

        elif qtype == "fill_blank":
            lines.append(f"**Q{qid}.** *(1 mark)* **{entry.get('answer', '')}**")
            lines.append(f"   *{entry.get('examiner_note', '')}*")

        elif qtype == "true_false":
            ans = entry.get("answer", "")
            just = entry.get("justification", "")
            ma = entry.get("marks_answer", 0.5)
            mj = entry.get("marks_justification", 0.5)
            lines.append(f"**Q{qid}.** *(1 mark total: {ma}+{mj})*  **{ans}**")
            lines.append(f"   Justification: {just}")
            lines.append(f"   *{entry.get('examiner_note', '')}*")

        elif qtype in ("short_answer", "long_answer"):
            total = entry.get("total_marks", marks)
            lines.append(f"**Q{qid}.** *({total} marks)*")
            lines.append(f"   **Structure:** {entry.get('structure', '')}")
            vps = entry.get("value_points", [])
            if vps:
                lines.append("   **Value Points** *(1 mark each)*:")
                for vp in vps:
                    slot = vp.get("slot", "")
                    point = vp.get("point", "")
                    lines.append(f"   - **[{slot}]** {point}")
            note = entry.get("examiner_note", "")
            if note:
                lines.append(f"   *Examiner note: {note}*")

        lines.append("")

    # Topics covered
    if topics_covered:
        lines += ["---", "", "## Topics Covered", ""]
        for t in topics_covered:
            lines.append(f"- {t}")
        lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PracticeAgent — question generation with level adaptation")
    parser.add_argument("--topic",          required=True, help="Topic to generate questions for")
    parser.add_argument("--subject",        default="",    help="Subject area")
    parser.add_argument("--question-count", type=int, default=10, help="Total number of questions")
    parser.add_argument("--difficulty",     default="",
                        help="Override difficulty: beginner | intermediate | advanced")
    parser.add_argument("--question-types", default="",
                        help="Comma-separated question types: mcq,short_answer,long_answer,fill_blank,true_false")
    args = parser.parse_args()

    # 1. Load profile
    profile = _load_profile()
    difficulty, grade, board = _resolve_context(profile, args.difficulty or None)

    # Board-specific schemes
    board_scheme   = _mss.get_scheme(board)
    board_q_scheme = board_scheme.get("q_scheme", {})
    mcq_scheme     = board_scheme.get("mcq", {})
    fb_scheme      = board_scheme.get("fill_blank", {})
    tf_scheme      = board_scheme.get("true_false", {})

    # 2. Parse question types
    if args.question_types:
        requested_types = [t.strip() for t in args.question_types.split(",") if t.strip() in _ALL_TYPES]
    else:
        requested_types = ["mcq", "short_answer", "long_answer"]
    if not requested_types:
        requested_types = ["mcq", "short_answer"]

    # 3. Search vault
    search_query = f"{args.topic} {args.subject}".strip()
    vault_result = _search_vault(search_query)
    vault_score = _best_vault_score(vault_result)
    vault_findings = vault_result.get("vault_findings", [])

    # 4. Web fallback
    used_web = False
    web_findings = []
    if vault_score < VAULT_SCORE_THRESHOLD:
        grade_hint = f"{board} class {grade}" if grade else ""
        web_result = _search_web(f"{args.topic} {args.subject} {grade_hint}".strip())
        web_findings = web_result.get("web_findings", [])
        if "error" not in web_result:
            used_web = True

    # 5. Extract testable content
    all_blocks = _extract_content_blocks(vault_findings, web_findings)
    sentences = _extract_sentences(all_blocks)
    key_terms = _extract_key_terms(all_blocks)
    list_items = _extract_list_items(all_blocks)

    # 6. Distribute questions across types
    distribution = _distribute_questions(args.question_count, requested_types)

    # 7. Generate questions
    all_questions = []
    qid = 1

    generators = {
        "mcq":          lambda s: _make_mcq(args.topic, args.subject, sentences, key_terms, list_items, difficulty, s, mcq_scheme),
        "short_answer": lambda s: _make_short_answer(args.topic, args.subject, sentences, key_terms, list_items, difficulty, s, board_q_scheme),
        "long_answer":  lambda s: _make_long_answer(args.topic, args.subject, sentences, key_terms, list_items, difficulty, s, board_q_scheme),
        "fill_blank":   lambda s: _make_fill_blank(args.topic, sentences, key_terms, s, fb_scheme),
        "true_false":   lambda s: _make_true_false(args.topic, args.subject, sentences, s, tf_scheme),
    }

    for qtype in requested_types:
        count_wanted = distribution.get(qtype, 0)
        generated = generators[qtype](qid)
        # Trim or pad to requested count
        trimmed = generated[:count_wanted]
        all_questions.extend(trimmed)
        qid += len(trimmed)

    # 8. Build metadata
    estimated_time = _estimate_time(all_questions)
    topics_covered = [args.topic] + key_terms[:4]
    sources = _build_sources(vault_findings, web_findings)

    # 9. Build note content
    title = f"{args.topic} — Practice Questions"
    if args.subject:
        title = f"{args.topic} — {args.subject} Practice Questions"
    note_content = _build_note_content(
        title=title,
        topic=args.topic,
        subject=args.subject,
        difficulty=difficulty,
        grade=grade,
        question_count=len(all_questions),
        estimated_time=estimated_time,
        questions=all_questions,
        topics_covered=topics_covered,
        board=board,
    )

    # 10. Assemble output
    output = {
        "topic":                args.topic,
        "subject":              args.subject,
        "difficulty":           difficulty,
        "grade":                grade,
        "board":                board,
        "question_count":       len(all_questions),
        "estimated_time":       estimated_time,
        "question_types_used":  requested_types,
        "questions":            all_questions,
        "topics_covered":       topics_covered,
        "sources":              sources,
        "vault_score":          round(vault_score, 3),
        "used_web":             used_web,
        "suggested_note_title": title,
        "note_content":         note_content,
    }

    sys.stdout.buffer.write(json.dumps(output, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
