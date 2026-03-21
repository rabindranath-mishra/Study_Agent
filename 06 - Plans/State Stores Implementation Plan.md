---
type: revision-plan
status: active
created: 2026-03-20
updated: 2026-03-20
version: 1.0
generated_by: copilot
---

# State Stores Implementation Plan

## Problem Statement

Build 5 JSON-based state stores to track all learner data within the vault boundary. These stores provide CRUD operations for learner profile, mastery levels, revision queue, exam calendar, and activity logging. All state files must be stored in `00 - System\.agent\state\` and remain within the vault for portability and privacy.

## Scope

**In Scope:**
- 5 Python state store modules with consistent CRUD APIs
- JSON schema definitions for each state file
- Initialization of empty state files with proper structure
- Thread-safe file I/O with atomic writes
- Validation and error handling
- Study-domain specific fields (mastery, spaced repetition, exam tracking)

**Out of Scope:**
- Database backends (SQLite, PostgreSQL) - keeping it simple with JSON
- Multi-user support (single student per vault)
- Real-time sync (file-based state, not live)
- State migration/versioning (v1.0 schemas only)

## Approach

### Design Principles

1. **Vault-first:** All state inside `00 - System\.agent\state\` boundary
2. **JSON-based:** Simple, human-readable, git-friendly format
3. **Consistent API:** All stores expose `get()`, `set()`, `update()`, `delete()` methods
4. **Atomic writes:** Write to temp file → rename (prevents corruption)
5. **Validation:** JSON schema validation on read/write
6. **Fail-safe:** Create default state if file missing/corrupted

### State Store Architecture

```
00 - System\.agent\state\
├── learner-profile.json       # Single profile object
├── subject-mastery.json       # Map of topic → mastery level
├── revision-queue.json        # Array of scheduled reviews
├── exam-calendar.json         # Array of upcoming exams
└── activity-log.jsonl         # Append-only log (newline-delimited JSON)

Python modules (state store tools):
00 - System\.agent\tools\
├── learner_profile_store.py   # CRUD for profile
├── mastery_store.py           # CRUD for mastery tracking
├── revision_queue_store.py    # CRUD for spaced repetition
├── exam_calendar_store.py     # CRUD for exam deadlines
└── activity_log_store.py      # Append-only logging
```

**Architecture:** Python tools in `tools\`, JSON data files in `state\`

## JSON Schemas

### 1. learner-profile.json

```json
{
  "student_name": "Student Name",
  "student_id": "uuid-v4",
  "created_at": "2026-03-20T16:53:00Z",
  "updated_at": "2026-03-20T16:53:00Z",
  "preferences": {
    "learning_style": "visual",
    "difficulty_preference": "progressive",
    "study_time_daily_hours": 2.0,
    "preferred_subjects": ["Biology", "Physics"]
  },
  "current_level": {
    "grade": "12",
    "board": "CBSE",
    "academic_year": "2025-2026"
  },
  "goals": [
    {
      "goal_id": "goal-001",
      "description": "Score 95+ in Biology",
      "target_date": "2026-05-15",
      "priority": "high"
    }
  ],
  "strengths": ["photosynthesis", "cell biology"],
  "weaknesses": ["genetics", "evolution"],
  "version": "1.0"
}
```

### 2. subject-mastery.json

```json
{
  "mastery_map": {
    "Biology::Photosynthesis": {
      "topic_path": "Biology::Photosynthesis",
      "subject": "Biology",
      "topic": "Photosynthesis",
      "mastery_level": 0.85,
      "confidence": 0.90,
      "last_practiced": "2026-03-20T10:00:00Z",
      "practice_count": 12,
      "avg_score": 0.87,
      "status": "strong"
    },
    "Biology::Genetics": {
      "topic_path": "Biology::Genetics",
      "subject": "Biology",
      "topic": "Genetics",
      "mastery_level": 0.42,
      "confidence": 0.60,
      "last_practiced": "2026-03-18T14:00:00Z",
      "practice_count": 5,
      "avg_score": 0.45,
      "status": "weak"
    }
  },
  "updated_at": "2026-03-20T16:53:00Z",
  "version": "1.0"
}
```

**Mastery Levels:**
- `0.00-0.40`: weak (needs reteaching)
- `0.41-0.69`: developing (needs practice)
- `0.70-0.84`: competent (occasional review)
- `0.85-1.00`: strong (maintain with spaced review)

### 3. revision-queue.json

```json
{
  "queue": [
    {
      "item_id": "rev-001",
      "topic_path": "Biology::Photosynthesis",
      "subject": "Biology",
      "topic": "Photosynthesis",
      "scheduled_date": "2026-03-22",
      "priority": 3,
      "interval_days": 7,
      "repetition_number": 3,
      "last_reviewed": "2026-03-15",
      "next_interval_days": 14,
      "status": "pending"
    },
    {
      "item_id": "rev-002",
      "topic_path": "Biology::Genetics",
      "subject": "Biology",
      "topic": "Genetics",
      "scheduled_date": "2026-03-21",
      "priority": 1,
      "interval_days": 3,
      "repetition_number": 1,
      "last_reviewed": "2026-03-18",
      "next_interval_days": 7,
      "status": "pending"
    }
  ],
  "updated_at": "2026-03-20T16:53:00Z",
  "version": "1.0"
}
```

**Priority Levels:**
- `1`: Urgent (due today/overdue)
- `2`: High (due within 3 days)
- `3`: Medium (due within 7 days)
- `4`: Low (due later)

**Status Values:**
- `pending`: Scheduled, not yet reviewed
- `completed`: Reviewed today
- `skipped`: Manually postponed

### 4. exam-calendar.json

```json
{
  "exams": [
    {
      "exam_id": "exam-001",
      "subject": "Biology",
      "exam_name": "CBSE Biology Board Exam",
      "exam_date": "2026-05-15",
      "exam_type": "board",
      "syllabus_coverage": 1.0,
      "preparation_status": 0.65,
      "topics_count": 24,
      "topics_mastered": 16,
      "days_remaining": 56,
      "priority": "high",
      "notes": "Final board exam - covers all chapters"
    },
    {
      "exam_id": "exam-002",
      "subject": "Physics",
      "exam_name": "Unit Test - Mechanics",
      "exam_date": "2026-04-10",
      "exam_type": "unit_test",
      "syllabus_coverage": 0.25,
      "preparation_status": 0.80,
      "topics_count": 6,
      "topics_mastered": 5,
      "days_remaining": 21,
      "priority": "medium",
      "notes": "Chapters 1-3 only"
    }
  ],
  "updated_at": "2026-03-20T16:53:00Z",
  "version": "1.0"
}
```

**Exam Types:**
- `board`: Final board exam (CBSE, ICSE, etc.)
- `unit_test`: Chapter/unit test
- `midterm`: Mid-term exam
- `mock`: Practice/mock exam
- `competitive`: JEE/NEET/etc.

### 5. activity-log.jsonl

**Format:** Newline-delimited JSON (one event per line)

```jsonl
{"event_id": "evt-001", "timestamp": "2026-03-20T10:00:00Z", "event_type": "practice_completed", "subject": "Biology", "topic": "Photosynthesis", "activity": "quiz", "score": 0.85, "questions_count": 10, "correct_count": 8, "time_spent_minutes": 15}
{"event_id": "evt-002", "timestamp": "2026-03-20T11:30:00Z", "event_type": "note_created", "subject": "Biology", "topic": "Photosynthesis", "note_type": "concept", "note_path": "04 - Concepts/Photosynthesis.md"}
{"event_id": "evt-003", "timestamp": "2026-03-20T14:00:00Z", "event_type": "mastery_updated", "subject": "Biology", "topic": "Photosynthesis", "old_mastery": 0.80, "new_mastery": 0.85, "reason": "quiz_score_0.85"}
{"event_id": "evt-004", "timestamp": "2026-03-20T15:00:00Z", "event_type": "revision_completed", "subject": "Biology", "topic": "Cell Structure", "interval_days": 7, "repetition_number": 2, "performance": "good"}
```

**Event Types:**
- `practice_completed`: Quiz/drill finished
- `note_created`: New note added to vault
- `mastery_updated`: Mastery level changed
- `revision_completed`: Spaced repetition review done
- `exam_added`: New exam scheduled
- `goal_set`: Learning goal created
- `session_started`: Study session begun
- `session_ended`: Study session finished

## Implementation Specs

### Common Patterns (All Stores)

```python
import json
import os
from pathlib import Path
from datetime import datetime
import shutil
from typing import Dict, List, Optional, Any

# Path constants
# Tools are in 00 - System\.agent\tools\
# State files are in 00 - System\.agent\state\
STATE_DIR = Path(__file__).parent.parent / "state"
STATE_FILE = STATE_DIR / "filename.json"

class StoreError(Exception):
    """Base exception for state store errors"""
    pass

def _atomic_write(file_path: Path, data: dict):
    """Write JSON atomically using temp file + rename"""
    temp_path = file_path.with_suffix('.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        shutil.move(str(temp_path), str(file_path))
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise StoreError(f"Failed to write {file_path.name}: {e}")

def _read_json(file_path: Path, default: dict) -> dict:
    """Read JSON with fallback to default if missing/corrupted"""
    if not file_path.exists():
        return default
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def _now_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.utcnow().isoformat() + 'Z'
```

### 1. learner_profile_store.py

**API:**
```python
def get_profile() -> dict
    """Get entire profile, return default if not exists"""

def set_profile(profile: dict) -> None
    """Overwrite entire profile (validates schema)"""

def update_profile(updates: dict) -> None
    """Deep merge updates into existing profile"""

def get_preference(key: str) -> Any
    """Get single preference value"""

def set_preference(key: str, value: Any) -> None
    """Update single preference"""

def add_goal(goal: dict) -> str
    """Add new goal, return goal_id"""

def remove_goal(goal_id: str) -> None
    """Remove goal by ID"""

def update_strengths_weaknesses(strengths: List[str], weaknesses: List[str]) -> None
    """Update learning strengths/weaknesses"""

def initialize_default() -> None
    """Create default profile if none exists"""
```

### 2. mastery_store.py

**API:**
```python
def get_mastery(topic_path: str) -> Optional[dict]
    """Get mastery data for topic, None if not tracked"""

def set_mastery(topic_path: str, mastery_level: float, **metadata) -> None
    """Set/update mastery for topic"""

def update_mastery_score(topic_path: str, score: float) -> None
    """Update mastery based on new quiz score (weighted average)"""

def get_all_mastery() -> dict
    """Get entire mastery map"""

def get_weak_topics(threshold: float = 0.40) -> List[dict]
    """Get all topics below mastery threshold"""

def get_strong_topics(threshold: float = 0.85) -> List[dict]
    """Get all topics above mastery threshold"""

def get_by_subject(subject: str) -> dict
    """Get mastery for all topics in subject"""

def delete_topic(topic_path: str) -> None
    """Remove topic from mastery tracking"""

def calculate_status(mastery_level: float) -> str
    """Return status: weak/developing/competent/strong"""
```

### 3. revision_queue_store.py

**API:**
```python
def add_item(topic_path: str, subject: str, topic: str, scheduled_date: str) -> str
    """Add topic to revision queue, return item_id"""

def remove_item(item_id: str) -> None
    """Remove item from queue"""

def get_item(item_id: str) -> Optional[dict]
    """Get single queue item"""

def get_due_today() -> List[dict]
    """Get all items scheduled for today"""

def get_overdue() -> List[dict]
    """Get all items past scheduled date"""

def mark_completed(item_id: str, performance: str = "good") -> None
    """Mark item as completed, calculate next interval"""

def reschedule(item_id: str, new_date: str) -> None
    """Move item to new date"""

def get_all_pending() -> List[dict]
    """Get all pending items sorted by date"""

def calculate_next_interval(current_interval: int, repetition_num: int, performance: str) -> int
    """Calculate next review interval (SM-2 algorithm variant)"""
```

**Spaced Repetition Logic:**
- Performance `good`: next_interval = current_interval * 2
- Performance `easy`: next_interval = current_interval * 2.5
- Performance `hard`: next_interval = max(1, current_interval / 2)
- Performance `again`: next_interval = 1

### 4. exam_calendar_store.py

**API:**
```python
def add_exam(exam: dict) -> str
    """Add exam to calendar, return exam_id"""

def update_exam(exam_id: str, updates: dict) -> None
    """Update exam details"""

def remove_exam(exam_id: str) -> None
    """Remove exam from calendar"""

def get_exam(exam_id: str) -> Optional[dict]
    """Get single exam"""

def get_all_exams() -> List[dict]
    """Get all exams sorted by date"""

def get_upcoming_exams(days: int = 30) -> List[dict]
    """Get exams within next N days"""

def update_preparation_status(exam_id: str, status: float) -> None
    """Update preparation percentage (0.0-1.0)"""

def calculate_days_remaining(exam_date: str) -> int
    """Calculate days until exam"""
```

### 5. activity_log_store.py

**API:**
```python
def log_event(event_type: str, **data) -> str
    """Append event to log, return event_id"""

def get_recent_events(limit: int = 50) -> List[dict]
    """Get most recent N events"""

def get_events_by_type(event_type: str, limit: int = 100) -> List[dict]
    """Get events filtered by type"""

def get_events_by_subject(subject: str, limit: int = 100) -> List[dict]
    """Get events for specific subject"""

def get_events_by_date_range(start_date: str, end_date: str) -> List[dict]
    """Get events within date range"""

def count_events_by_type(event_type: str, days: int = 7) -> int
    """Count events of type in last N days"""

def get_study_streak() -> int
    """Calculate consecutive days with practice_completed events"""
```

**Note:** JSONL format (append-only, one line per event) for efficient appends

## Testing Approach

### Unit Tests (for each store)

1. **Initialization:** Default file creation
2. **CRUD Operations:** Create, read, update, delete
3. **Edge Cases:** Missing files, corrupted JSON, concurrent writes
4. **Validation:** Schema validation, type checking
5. **Atomic Writes:** Temp file cleanup on errors

### Integration Tests

1. **Cross-store consistency:** Mastery update → activity log
2. **State persistence:** Write → read → verify
3. **Concurrent access:** Multiple reads/writes

### Manual Verification

1. Inspect JSON files in `00 - System\.agent\state\`
2. Verify human-readable format
3. Check timestamps, IDs, schema compliance

## Implementation Todos

### Phase 1: Foundation (Common Utilities)
- **state-001**: Create `00 - System\.agent\state\` directory if not exists
- **state-002**: Implement common utilities (`_atomic_write`, `_read_json`, `_now_iso`) in each store module

### Phase 2: Individual Stores (in tools\ folder)
- **state-003**: Build `tools\learner_profile_store.py` with full API
- **state-004**: Build `tools\mastery_store.py` with full API
- **state-005**: Build `tools\revision_queue_store.py` with spaced repetition logic
- **state-006**: Build `tools\exam_calendar_store.py` with countdown calculations
- **state-007**: Build `tools\activity_log_store.py` with JSONL append logic

### Phase 3: Initialization
- **state-008**: Create `tools\initialize_state.py` script to set up all default JSON files
- **state-009**: Run initialization script to create empty state files in `state\` folder

### Phase 4: Testing
- **state-010**: Test each store's CRUD operations manually
- **state-011**: Test atomic writes (simulate corruption)
- **state-012**: Test default fallback when files missing

### Phase 5: Documentation
- **state-013**: Add docstrings to all public functions
- **state-014**: Create `STATE_STORE_README.md` with API reference and examples

## Dependencies

```
state-001 (create directory)
  └─→ state-002 (common utilities)
       └─→ state-003 (profile store)
       └─→ state-004 (mastery store)
       └─→ state-005 (revision queue)
       └─→ state-006 (exam calendar)
       └─→ state-007 (activity log)
            └─→ state-008 (init script)
                 └─→ state-009 (run init)
                      └─→ state-010 (test CRUD)
                      └─→ state-011 (test atomic writes)
                      └─→ state-012 (test defaults)
                           └─→ state-013 (docstrings)
                           └─→ state-014 (documentation)
```

## Success Criteria

✅ All 5 Python modules created with consistent APIs
✅ All 5 JSON/JSONL state files initialized
✅ Atomic writes prevent data corruption
✅ Default schemas created when files missing
✅ All state files remain within vault boundary
✅ Manual testing passes for all CRUD operations
✅ Documentation complete with usage examples

## Estimated Effort

- **state-001 to state-002**: 30 minutes (setup + common code)
- **state-003 to state-007**: 3-4 hours (5 stores × 40-50 min each)
- **state-008 to state-009**: 30 minutes (init script)
- **state-010 to state-012**: 1 hour (testing)
- **state-013 to state-014**: 45 minutes (docs)

**Total: ~6 hours** for complete implementation and testing

## Notes

- **Keep it simple:** JSON files, not databases. Easy to inspect, git-friendly, portable.
- **Atomic writes critical:** Use temp file + rename pattern to prevent corruption during crashes.
- **Spaced repetition:** Simple SM-2 variant, not full SuperMemo algorithm (good enough for v1.0).
- **Activity log:** JSONL format allows efficient appends without loading entire file.
- **Validation:** Basic type checking, no complex JSON schema validators (minimize dependencies).
- **Thread safety:** File locking not needed (single student, single Copilot CLI instance).

## Next Steps After Completion

Once state stores are built:
1. Build Memory Agent (uses all 5 stores)
2. Build Diagnostic Agent (uses mastery + activity log)
3. Build Revision Planner Agent (uses mastery + exam calendar + revision queue)
4. Build Teaching/Practice agents (use mastery to adapt difficulty)

State stores are the **foundation** for all agents! 🏗️
