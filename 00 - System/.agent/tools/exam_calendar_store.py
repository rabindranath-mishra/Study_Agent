#!/usr/bin/env python3
"""
exam_calendar_store.py — Exam Calendar State Store

Manages exam-calendar.json in the vault state directory.
Provides CRUD operations for exam scheduling data.

Constitution §XIV: Learner state must exist inside the vault.
State stored under: 00 - System/.agent/state/exam-calendar.json
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import STATE_DIR as _STATE_DIR_STR

STATE_DIR     = Path(_STATE_DIR_STR)
CALENDAR_FILE = STATE_DIR / "exam-calendar.json"


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _load_calendar() -> Dict[str, Any]:
    """Load calendar file, returning empty structure if not found."""
    if not CALENDAR_FILE.exists():
        return {"exams": [], "updated_at": None}
    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_calendar(calendar: Dict[str, Any]) -> None:
    _ensure_state_dir()
    calendar["updated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(calendar, f, indent=2, ensure_ascii=False)


def add_exam(exam_data: Dict[str, Any]) -> str:
    """
    Add an exam entry to the calendar.

    Args:
        exam_data: Dict with keys: subject, exam_name, exam_date,
                   exam_type, syllabus_coverage (optional).

    Returns:
        Generated exam_id (UUID string).
    """
    calendar = _load_calendar()
    exam_id = str(uuid.uuid4())[:8]

    entry = {
        "exam_id": exam_id,
        "subject": exam_data.get("subject"),
        "exam_name": exam_data.get("exam_name"),
        "exam_date": exam_data.get("exam_date"),
        "exam_type": exam_data.get("exam_type"),
        "syllabus_coverage": exam_data.get("syllabus_coverage", 1.0),
        "added_at": datetime.utcnow().isoformat() + "Z",
        "status": "upcoming",
    }
    calendar["exams"].append(entry)
    _save_calendar(calendar)
    return exam_id


def get_exams() -> List[Dict[str, Any]]:
    """Return all exam entries sorted by exam_date ascending."""
    calendar = _load_calendar()
    exams = calendar.get("exams", [])
    return sorted(exams, key=lambda e: e.get("exam_date", ""))


def get_exams_for_subject(subject: str) -> List[Dict[str, Any]]:
    """Return exam entries for a specific subject."""
    return [e for e in get_exams() if e.get("subject") == subject]


def remove_exam(exam_id: str) -> bool:
    """
    Remove an exam by exam_id.

    Returns:
        True if removed, False if not found.
    """
    calendar = _load_calendar()
    before = len(calendar["exams"])
    calendar["exams"] = [e for e in calendar["exams"] if e["exam_id"] != exam_id]
    if len(calendar["exams"]) < before:
        _save_calendar(calendar)
        return True
    return False


def get_upcoming_exams(days_ahead: int = 30) -> List[Dict[str, Any]]:
    """Return exams within the next N days."""
    cutoff = date.today().isoformat()
    future_limit = date.fromordinal(date.today().toordinal() + days_ahead).isoformat()
    return [
        e for e in get_exams()
        if e.get("exam_date") and cutoff <= e["exam_date"] <= future_limit
    ]
