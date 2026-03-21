#!/usr/bin/env python3
"""
marking_scheme_store.py — Board-aware marking scheme definitions.

Single source of truth for how questions are marked across different
educational boards. The practice agent loads the appropriate scheme
from this store based on the student's board (read from their profile).

Supported boards (case-insensitive):
  CBSE        — Central Board of Secondary Education (India)
  ICSE / ISC  — Council for the Indian School Certificate Examinations
  IB          — International Baccalaureate
  Cambridge   — Cambridge IGCSE / A-Level (also: IGCSE, CIE)
  State       — Generic Indian State Board fallback
  Generic     — Universal fallback for unrecognised boards

Scheme structure per board:
  {
    <marks: int>: {
      "structure":         str,   # Plain-English description of the answer shape
      "value_point_count": int,   # Number of distinct scorable points
      "word_limit":        str,   # Recommended word range
      "partial_credit":    bool,  # Whether individual points earn partial marks
      "note":              str,   # Examiner guidance line
      "breakdown":         list   # One label per value point (used as slot headers)
    },
    ...
  }

Each board also defines:
  "mcq"        — MCQ marking rule
  "fill_blank" — Fill-in-the-blank marking rule
  "true_false" — True/False marking rule

Usage:
  import marking_scheme_store as mss
  scheme = mss.get_scheme("CBSE")       # → full scheme dict
  q_scheme = mss.get_q_scheme("CBSE", marks=5)   # → one mark-band entry
  board = mss.get_board_from_profile(profile)     # → "CBSE"
"""

from pathlib import Path
from typing import Dict, Any, Optional

# ── Canonical board name normalisation ───────────────────────────────────────

_BOARD_ALIASES: Dict[str, str] = {
    "cbse":          "CBSE",
    "icse":          "ICSE",
    "isc":           "ICSE",
    "ib":            "IB",
    "international baccalaureate": "IB",
    "cambridge":     "Cambridge",
    "igcse":         "Cambridge",
    "cie":           "Cambridge",
    "a-level":       "Cambridge",
    "a level":       "Cambridge",
    "state":         "State",
    "state board":   "State",
    "generic":       "Generic",
}


def normalise_board(board: str) -> str:
    """Return canonical board name, or 'Generic' if unrecognised."""
    return _BOARD_ALIASES.get(board.strip().lower(), "Generic")


# ── CBSE ──────────────────────────────────────────────────────────────────────
# Source: CBSE Marking Scheme Design Principles (Secondary & Senior Secondary)
# https://cbseacademic.nic.in

_CBSE: Dict[str, Any] = {
    "board_display": "CBSE (Central Board of Secondary Education)",
    "q_scheme": {
        1: {
            "structure":         "One precise fact, term, or definition.",
            "value_point_count": 1,
            "word_limit":        "1 sentence",
            "partial_credit":    False,
            "note":              "Full mark for correct answer only. No partial credit.",
            "breakdown":         ["Value point (1 mark)"],
        },
        2: {
            "structure":         "Two distinct value points, 1 mark each.",
            "value_point_count": 2,
            "word_limit":        "30–40 words",
            "partial_credit":    True,
            "note":              "Award 1 mark per correct value point.",
            "breakdown":         ["Value point 1 (1 mark)", "Value point 2 (1 mark)"],
        },
        3: {
            "structure":         "Three value points: definition + explanation + example.",
            "value_point_count": 3,
            "word_limit":        "60–80 words",
            "partial_credit":    True,
            "note":              "Award 1 mark per value point. Accept any 3 correct points.",
            "breakdown":         [
                "Definition / opening statement (1 mark)",
                "Explanation / mechanism (1 mark)",
                "Example / application (1 mark)",
            ],
        },
        5: {
            "structure":         "5 value points: introduction + 3 body points + conclusion/diagram.",
            "value_point_count": 5,
            "word_limit":        "150–200 words",
            "partial_credit":    True,
            "note":              "Award 1 mark per value point. Diagram (if applicable) = 1 mark.",
            "breakdown":         [
                "Introduction / definition (1 mark)",
                "Key point 1 (1 mark)",
                "Key point 2 (1 mark)",
                "Key point 3 (1 mark)",
                "Conclusion / example / diagram (1 mark)",
            ],
        },
        8: {
            "structure":         "8 value points covering the full scope of the topic.",
            "value_point_count": 8,
            "word_limit":        "250–300 words",
            "partial_credit":    True,
            "note":              "Award 1 mark per value point. Half-mark for partially correct points.",
            "breakdown":         [
                "Introduction / context (1 mark)",
                "Key concept 1 (1 mark)",
                "Key concept 2 (1 mark)",
                "Key concept 3 (1 mark)",
                "Key concept 4 (1 mark)",
                "Application / significance (1 mark)",
                "Critical analysis / comparison (1 mark)",
                "Conclusion / diagram / example (1 mark)",
            ],
        },
    },
    "mcq": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct option only. No negative marking unless specified.",
    },
    "fill_blank": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct answer. Accept correct spelling variants.",
    },
    "true_false": {
        "marks_answer":        0.5,
        "marks_justification": 0.5,
        "partial_credit":      True,
        "note": "0.5 for correct T/F + 0.5 for correct justification. "
                "For Class 11–12: full 1 mark only if justification is also correct.",
    },
}


# ── ICSE / ISC ────────────────────────────────────────────────────────────────
# Source: CISCE Marking Scheme guidelines (ISC/ICSE)
# ICSE uses 1/2/3/4-mark bands more than CBSE's 1/2/3/5 pattern.
# ISC (Class 11–12) uses 2/4/6/8-mark bands.

_ICSE: Dict[str, Any] = {
    "board_display": "ICSE/ISC (Council for the Indian School Certificate Examinations)",
    "q_scheme": {
        1: {
            "structure":         "One word, phrase, or very short answer.",
            "value_point_count": 1,
            "word_limit":        "1–2 words or 1 sentence",
            "partial_credit":    False,
            "note":              "Full mark for correct answer only.",
            "breakdown":         ["Correct answer (1 mark)"],
        },
        2: {
            "structure":         "Two relevant points or one well-explained point.",
            "value_point_count": 2,
            "word_limit":        "40–50 words",
            "partial_credit":    True,
            "note":              "1 mark per point. Accept any 2 relevant points.",
            "breakdown":         ["Point 1 (1 mark)", "Point 2 (1 mark)"],
        },
        3: {
            "structure":         "Three points or explanation with evidence.",
            "value_point_count": 3,
            "word_limit":        "80–100 words",
            "partial_credit":    True,
            "note":              "1 mark per point.",
            "breakdown":         ["Point 1 (1 mark)", "Point 2 (1 mark)", "Point 3 (1 mark)"],
        },
        4: {
            "structure":         "Four points OR two well-developed points (2 marks each).",
            "value_point_count": 4,
            "word_limit":        "120–150 words",
            "partial_credit":    True,
            "note":              "1 mark per point OR 2 marks per developed point. Examiner's discretion.",
            "breakdown":         [
                "Point 1 (1 mark)",
                "Point 2 (1 mark)",
                "Point 3 (1 mark)",
                "Point 4 (1 mark)",
            ],
        },
        6: {
            "structure":         "Introduction + 4 developed points + conclusion.",
            "value_point_count": 6,
            "word_limit":        "180–220 words",
            "partial_credit":    True,
            "note":              "1 mark per point. Reward depth of explanation.",
            "breakdown":         [
                "Introduction (1 mark)",
                "Developed point 1 (1 mark)",
                "Developed point 2 (1 mark)",
                "Developed point 3 (1 mark)",
                "Developed point 4 (1 mark)",
                "Conclusion (1 mark)",
            ],
        },
        8: {
            "structure":         "Comprehensive essay: introduction + 6 points + conclusion.",
            "value_point_count": 8,
            "word_limit":        "250–300 words",
            "partial_credit":    True,
            "note":              "1 mark per point. Half-mark for partially correct points. Penalise irrelevant content.",
            "breakdown":         [
                "Introduction / context (1 mark)",
                "Point 1 with explanation (1 mark)",
                "Point 2 with explanation (1 mark)",
                "Point 3 with explanation (1 mark)",
                "Point 4 with explanation (1 mark)",
                "Point 5 with explanation (1 mark)",
                "Application / significance (1 mark)",
                "Conclusion (1 mark)",
            ],
        },
    },
    "mcq": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct option. No negative marking.",
    },
    "fill_blank": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct answer. Accept all correct spellings.",
    },
    "true_false": {
        "marks_answer":        1,
        "marks_justification": 0,
        "partial_credit":      False,
        "note": "1 mark for correct answer. ICSE does not separately mark justification "
                "for T/F unless the question explicitly asks for it.",
    },
}


# ── IB (International Baccalaureate) ─────────────────────────────────────────
# Source: IB Diploma Programme Assessment Principles and Practices
# IB uses "marking points" — similar to value points.
# Extended responses use Levels of Achievement descriptors.

_IB: Dict[str, Any] = {
    "board_display": "IB (International Baccalaureate Diploma Programme)",
    "q_scheme": {
        1: {
            "structure":         "One marking point: correct fact, term, or identification.",
            "value_point_count": 1,
            "word_limit":        "1–2 sentences",
            "partial_credit":    False,
            "note":              "Award [1] for correct marking point. Do not accept vague answers.",
            "breakdown":         ["Marking point (1 mark)"],
        },
        2: {
            "structure":         "Two marking points.",
            "value_point_count": 2,
            "word_limit":        "3–5 sentences",
            "partial_credit":    True,
            "note":              "Award [1] per marking point up to [2]. Marking points may be in any order.",
            "breakdown":         ["Marking point 1 (1 mark)", "Marking point 2 (1 mark)"],
        },
        4: {
            "structure":         "Four marking points or two points each developed with evidence/example.",
            "value_point_count": 4,
            "word_limit":        "100–150 words",
            "partial_credit":    True,
            "note":              "Award [1] per marking point. Award OFR (own figure rule) where applicable.",
            "breakdown":         [
                "Marking point 1 (1 mark)",
                "Marking point 2 (1 mark)",
                "Marking point 3 (1 mark)",
                "Marking point 4 (1 mark)",
            ],
        },
        6: {
            "structure":         "Level-based extended response: levels 1–3 (2 marks each).",
            "value_point_count": 6,
            "word_limit":        "250–350 words",
            "partial_credit":    True,
            "note":              "Use the IB levels-of-achievement descriptor. "
                                 "Level 1–2: surface; Level 3–4: detailed; Level 5–6: analytical.",
            "breakdown":         [
                "Level 1–2: Identifies/describes basic concepts (up to 2 marks)",
                "Level 3–4: Explains with evidence or examples (up to 2 marks)",
                "Level 5–6: Analyses, evaluates, or synthesises (up to 2 marks)",
            ],
        },
        8: {
            "structure":         "Level-based extended response: levels 1–4 (2 marks each).",
            "value_point_count": 8,
            "word_limit":        "300–400 words",
            "partial_credit":    True,
            "note":              "Use IB extended essay marking criteria. Reward originality and synthesis.",
            "breakdown":         [
                "Level 1–2: Surface knowledge (up to 2 marks)",
                "Level 3–4: Detailed understanding (up to 2 marks)",
                "Level 5–6: Analysis and application (up to 2 marks)",
                "Level 7–8: Synthesis and evaluation (up to 2 marks)",
            ],
        },
    },
    "mcq": {
        "marks": 1,
        "partial_credit": False,
        "note": "Award [1] for correct answer only. IB uses no negative marking in standard papers.",
    },
    "fill_blank": {
        "marks": 1,
        "partial_credit": False,
        "note": "Award [1] for correct term. Accept scientifically/linguistically equivalent answers.",
    },
    "true_false": {
        "marks_answer":        0.5,
        "marks_justification": 0.5,
        "partial_credit":      True,
        "note": "IB T/F typically requires justification. "
                "Award [0.5] for correct answer + [0.5] for valid justification.",
    },
}


# ── Cambridge IGCSE / A-Level ─────────────────────────────────────────────────
# Source: Cambridge Assessment International Education marking guidelines

_CAMBRIDGE: Dict[str, Any] = {
    "board_display": "Cambridge (IGCSE / A-Level — Cambridge Assessment International Education)",
    "q_scheme": {
        1: {
            "structure":         "One correct point, term, or identification.",
            "value_point_count": 1,
            "word_limit":        "1 sentence",
            "partial_credit":    False,
            "note":              "Award 1 mark for correct response. Accept any correct phrasing.",
            "breakdown":         ["Correct point (1 mark)"],
        },
        2: {
            "structure":         "Two credit-worthy points.",
            "value_point_count": 2,
            "word_limit":        "30–50 words",
            "partial_credit":    True,
            "note":              "1 mark per point. Points may be in any order.",
            "breakdown":         ["Point 1 (1 mark)", "Point 2 (1 mark)"],
        },
        3: {
            "structure":         "Three credit-worthy points or one developed point (1 + 2 marks).",
            "value_point_count": 3,
            "word_limit":        "60–80 words",
            "partial_credit":    True,
            "note":              "1 mark per basic point. Award up to 2 marks for a developed point.",
            "breakdown":         [
                "Basic point (1 mark)",
                "Developed point or second basic point (1 mark)",
                "Third point or further development (1 mark)",
            ],
        },
        4: {
            "structure":         "Four credit-worthy points OR two developed points (up to 2 marks each).",
            "value_point_count": 4,
            "word_limit":        "100–130 words",
            "partial_credit":    True,
            "note":              "1 mark per basic point; up to 2 marks for a developed point with evidence.",
            "breakdown":         [
                "Point 1 (1 mark)",
                "Development of point 1 / Point 2 (1 mark)",
                "Point 3 (1 mark)",
                "Development of point 3 / Point 4 (1 mark)",
            ],
        },
        6: {
            "structure":         "Extended response: Level-of-response marking (3 levels).",
            "value_point_count": 6,
            "word_limit":        "200–250 words",
            "partial_credit":    True,
            "note":              "Mark using Level of Response descriptors. Reward quality over quantity.",
            "breakdown":         [
                "Level 1 (1–2 marks): Limited, generalised response",
                "Level 2 (3–4 marks): Developed with some relevant detail",
                "Level 3 (5–6 marks): Well-developed, specific evidence, clear analysis",
            ],
        },
        8: {
            "structure":         "Extended essay: Level-of-response marking (4 levels).",
            "value_point_count": 8,
            "word_limit":        "300–400 words",
            "partial_credit":    True,
            "note":              "Mark using Level of Response descriptors. "
                                 "Level 4 requires evaluation and judgement.",
            "breakdown":         [
                "Level 1 (1–2 marks): Basic/limited understanding",
                "Level 2 (3–4 marks): Some relevant knowledge and understanding",
                "Level 3 (5–6 marks): Developed analysis with accurate knowledge",
                "Level 4 (7–8 marks): Evaluative, well-argued, with supported judgement",
            ],
        },
    },
    "mcq": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct answer. No negative marking unless stated.",
    },
    "fill_blank": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct answer. Accept correct variations in phrasing.",
    },
    "true_false": {
        "marks_answer":        1,
        "marks_justification": 0,
        "partial_credit":      False,
        "note": "Cambridge T/F: 1 mark for correct answer. Justification earns a separate follow-up mark if asked.",
    },
}


# ── Generic / State Board fallback ────────────────────────────────────────────

_GENERIC: Dict[str, Any] = {
    "board_display": "Generic (State Board / Unspecified)",
    "q_scheme": {
        1: {
            "structure":         "One fact or definition.",
            "value_point_count": 1,
            "word_limit":        "1 sentence",
            "partial_credit":    False,
            "note":              "1 mark for a correct, complete answer.",
            "breakdown":         ["Value point (1 mark)"],
        },
        2: {
            "structure":         "Two key points.",
            "value_point_count": 2,
            "word_limit":        "40–50 words",
            "partial_credit":    True,
            "note":              "1 mark per point.",
            "breakdown":         ["Point 1 (1 mark)", "Point 2 (1 mark)"],
        },
        3: {
            "structure":         "Three key points.",
            "value_point_count": 3,
            "word_limit":        "60–80 words",
            "partial_credit":    True,
            "note":              "1 mark per point.",
            "breakdown":         [
                "Point 1 (1 mark)",
                "Point 2 (1 mark)",
                "Point 3 (1 mark)",
            ],
        },
        5: {
            "structure":         "Five key points covering the topic.",
            "value_point_count": 5,
            "word_limit":        "150–200 words",
            "partial_credit":    True,
            "note":              "1 mark per point. Award partial marks for partially correct answers.",
            "breakdown":         [
                "Introduction / definition (1 mark)",
                "Key point 1 (1 mark)",
                "Key point 2 (1 mark)",
                "Key point 3 (1 mark)",
                "Conclusion / example (1 mark)",
            ],
        },
        8: {
            "structure":         "Eight key points.",
            "value_point_count": 8,
            "word_limit":        "250–300 words",
            "partial_credit":    True,
            "note":              "1 mark per point.",
            "breakdown":         [f"Point {i+1} (1 mark)" for i in range(8)],
        },
    },
    "mcq": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct answer.",
    },
    "fill_blank": {
        "marks": 1,
        "partial_credit": False,
        "note": "1 mark for correct answer.",
    },
    "true_false": {
        "marks_answer":        1,
        "marks_justification": 0,
        "partial_credit":      False,
        "note": "1 mark for correct True/False answer.",
    },
}


# ── Master registry ───────────────────────────────────────────────────────────

_SCHEMES: Dict[str, Dict] = {
    "CBSE":      _CBSE,
    "ICSE":      _ICSE,
    "IB":        _IB,
    "Cambridge": _CAMBRIDGE,
    "State":     _GENERIC,
    "Generic":   _GENERIC,
}


# ── Public API ────────────────────────────────────────────────────────────────

def get_scheme(board: str) -> Dict[str, Any]:
    """
    Return the full marking scheme for a given board.

    Args:
        board: Board name (case-insensitive). Unknown boards fall back to Generic.

    Returns:
        Scheme dict with 'q_scheme', 'mcq', 'fill_blank', 'true_false',
        and 'board_display' keys.
    """
    canonical = normalise_board(board)
    return _SCHEMES.get(canonical, _GENERIC)


def get_q_scheme(board: str, marks: int) -> Optional[Dict[str, Any]]:
    """
    Return the mark-band entry for a specific mark allocation.

    Finds the closest defined band if the exact mark count is not present.
    E.g. get_q_scheme("CBSE", 4) returns the 3-mark band (nearest below).

    Args:
        board:  Board name.
        marks:  Number of marks for the question.

    Returns:
        Mark-band dict, or None if the scheme has no entries at all.
    """
    scheme = get_scheme(board)
    q_scheme = scheme.get("q_scheme", {})
    if not q_scheme:
        return None
    if marks in q_scheme:
        return q_scheme[marks]
    # Closest band ≤ marks, else the smallest available
    candidates = sorted(q_scheme.keys())
    lower = [k for k in candidates if k <= marks]
    key = lower[-1] if lower else candidates[0]
    return q_scheme[key]


def get_q_scheme_by_marks(q_scheme: Optional[dict], marks: int) -> Optional[Dict[str, Any]]:
    """
    Return the mark-band entry from a pre-fetched q_scheme dict.

    Use this when you already have `scheme["q_scheme"]` and want to avoid
    re-looking up the board.

    Args:
        q_scheme:  The `q_scheme` sub-dict from `get_scheme(board)`.
        marks:     Number of marks for the question.

    Returns:
        Mark-band dict, or None if q_scheme is empty/None.
    """
    if not q_scheme:
        return None
    if marks in q_scheme:
        return q_scheme[marks]
    candidates = sorted(q_scheme.keys())
    lower = [k for k in candidates if k <= marks]
    key = lower[-1] if lower else candidates[0]
    return q_scheme[key]


def get_board_from_profile(profile: dict) -> str:
    """
    Extract the canonical board name from a learner profile dict.

    Handles both profile shapes:
      - profile.current_level.board  (ProfileAgent structure)
      - profile.board                (flat fallback)

    Returns:
        Canonical board name string, e.g. "CBSE".
    """
    current_level = profile.get("current_level", {})
    board = current_level.get("board") or profile.get("board", "Generic")
    return normalise_board(board)


def list_supported_boards() -> list:
    """Return list of canonical board names."""
    return [b for b in _SCHEMES if b != "Generic"]
