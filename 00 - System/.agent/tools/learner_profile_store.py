#!/usr/bin/env python3
"""
learner_profile_store.py — Learner Profile State Store

Manages learner-profile.json in the vault state directory.
Provides CRUD operations for student profile data.

Constitution §XIV: Learner state must exist inside the vault.
State stored under: 00 - System/.agent/state/learner-profile.json
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Resolve state directory from this file's location
_TOOLS_DIR = Path(__file__).resolve().parent
_AGENT_DIR = _TOOLS_DIR.parent
STATE_DIR = _AGENT_DIR / "state"
PROFILE_FILE = STATE_DIR / "learner-profile.json"


def _ensure_state_dir() -> None:
    """Ensure state directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def profile_exists() -> bool:
    """
    Check if a learner profile file exists and is non-empty.

    Returns:
        True if profile exists, False otherwise.
    """
    return PROFILE_FILE.exists() and PROFILE_FILE.stat().st_size > 0


def get_profile() -> Dict[str, Any]:
    """
    Load and return the learner profile.

    Returns:
        Profile dict, or empty dict if not found.
    """
    if not profile_exists():
        return {}
    with open(PROFILE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def set_profile(profile_data: Dict[str, Any]) -> None:
    """
    Persist the full profile data to disk.

    Args:
        profile_data: Complete profile dictionary to write.
    """
    _ensure_state_dir()
    profile_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)


def add_subject(subject_name: str, difficulty: str = "intermediate") -> None:
    """
    Add a subject entry to the profile.

    Args:
        subject_name: Title-cased subject name.
        difficulty: beginner | intermediate | advanced
    """
    profile = get_profile()
    subjects: List[Dict] = profile.get("subjects", [])

    subject_entry = {
        "name": subject_name,
        "difficulty_level": difficulty,
        "added_date": datetime.utcnow().date().isoformat(),
        "mastery_file": f"{subject_name}-mastery.json",
        "revision_file": f"{subject_name}-revision-queue.json",
    }
    subjects.append(subject_entry)
    profile["subjects"] = subjects
    set_profile(profile)


def remove_subject(subject_name: str) -> None:
    """
    Remove a subject from the profile.

    Args:
        subject_name: Name of subject to remove.
    """
    profile = get_profile()
    profile["subjects"] = [
        s for s in profile.get("subjects", []) if s["name"] != subject_name
    ]
    set_profile(profile)


def update_preferences(preferences: Dict[str, Any]) -> None:
    """
    Merge updates into the profile preferences block.

    Args:
        preferences: Dict of preference keys/values to update.
    """
    profile = get_profile()
    existing = profile.get("preferences", {})
    existing.update(preferences)
    profile["preferences"] = existing
    set_profile(profile)


def get_subjects() -> List[str]:
    """Return list of subject names currently in the profile."""
    profile = get_profile()
    return [s["name"] for s in profile.get("subjects", [])]


def get_board() -> str:
    """
    Return the student's board from their profile.

    Handles both profile shapes:
      - profile.current_level.board  (standard ProfileAgent structure)
      - profile.board                (flat fallback)

    Returns:
        Board string, e.g. "CBSE", "ICSE", "IB". Defaults to "Generic".
    """
    profile = get_profile()
    current_level = profile.get("current_level", {})
    return current_level.get("board") or profile.get("board", "Generic")


def get_grade() -> str:
    """
    Return the student's grade from their profile.

    Handles both profile shapes:
      - profile.current_level.grade  (standard ProfileAgent structure, e.g. "Class 11")
      - profile.grade                (flat fallback, e.g. "11")

    Returns:
        Grade string. Extracts numeric part if stored as "Class 11".
    """
    profile = get_profile()
    current_level = profile.get("current_level", {})
    raw = current_level.get("grade") or profile.get("grade", "11")
    # Strip "Class " prefix if present → "Class 11" → "11"
    m = re.search(r'\d+', str(raw))
    return m.group(0) if m else str(raw)

