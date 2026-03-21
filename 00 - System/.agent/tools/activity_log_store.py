#!/usr/bin/env python3
"""
activity_log_store.py — Activity Log State Store

Appends structured JSONL entries to activity-log.jsonl in the agent
logs directory alongside other session logs.

All logs live under: 00 - System/.agent/logs/
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any

_TOOLS_DIR = Path(__file__).resolve().parent
_AGENT_DIR = _TOOLS_DIR.parent
LOGS_DIR  = _AGENT_DIR / "logs"
LOG_FILE  = LOGS_DIR / "activity-log.jsonl"


def _ensure_logs_dir() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log_event(event_type: str, **kwargs: Any) -> None:
    """
    Append a structured event record to the activity log.

    Args:
        event_type: Short identifier for the event (e.g. 'profile_created').
        **kwargs: Additional key-value pairs to include in the log entry.
    """
    _ensure_logs_dir()
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        **kwargs,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_events(limit: int = 50) -> list:
    """
    Return the most recent N log entries.

    Args:
        limit: Maximum number of entries to return (most recent first).

    Returns:
        List of event dicts.
    """
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    recent = lines[-limit:]
    events = []
    for line in reversed(recent):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def get_events_by_type(event_type: str, limit: int = 20) -> list:
    """Return recent events matching a specific event_type."""
    return [e for e in get_events(limit=200) if e.get("event_type") == event_type][:limit]
