---
type: workflow-spec
status: draft
created: 2026-03-21
updated: 2026-03-21
version: 1.0
generated_by: copilot
---

# Student Profile Creation & Update Workflow

## Overview

This document defines the interactive workflow for students to create and update their learner profile. The profile drives personalized learning experiences, adaptive difficulty, and smart revision planning.

## Workflow Types

### 1. First-Time Onboarding (Profile Creation)
**Trigger:** Student opens plugin for the first time, no `learner-profile.json` exists

### 2. Profile Update (Modify Existing)
**Trigger:** Student asks "update my profile" or "add a subject"

### 3. Quick Subject Add
**Trigger:** Student starts studying a new subject not in profile

---

## 1. First-Time Onboarding Workflow

### Objective
Collect minimum viable information to get student started quickly, with sensible defaults.

### Interactive Questions (Conversational)

#### Q1: Student Name
```
👋 Welcome to your Study Agent!

What should I call you?
> [Student enters name]
```

**Validation:** Non-empty string
**Default:** "Student" (if skipped)

---

#### Q2: Academic Level
```
What's your current academic level?

[Multiple choice]
• Class 9 (CBSE/ICSE)
• Class 10 (CBSE/ICSE)
• Class 11 (CBSE/ICSE)
• Class 12 (CBSE/ICSE)
• Undergraduate (Year 1)
• Undergraduate (Year 2)
• Undergraduate (Year 3)
• Undergraduate (Year 4+)
• Other

> [Student selects]
```

**Stored as:**
```json
{
  "current_level": {
    "grade": "12",
    "board": "CBSE",
    "academic_year": "2025-2026"
  }
}
```

---

#### Q3: Primary Subjects
```
Which subjects are you currently studying?

You can add more subjects anytime. Just tell me the main ones for now.

Common subjects:
• Mathematics
• Physics
• Chemistry
• Biology
• Computer Science
• English
• History
• Geography
• Economics
• Political Science
• Accountancy
• Business Studies

> [Student enters comma-separated list or selects multiple]
Example: Biology, Physics, Chemistry
```

**Validation:** At least 1 subject
**Format:** Title case, trimmed
**Stored as:**
```json
{
  "subjects": [
    {"name": "Biology", "difficulty_level": "intermediate", "added_date": "2026-03-21"},
    {"name": "Physics", "difficulty_level": "intermediate", "added_date": "2026-03-21"},
    {"name": "Chemistry", "difficulty_level": "intermediate", "added_date": "2026-03-21"}
  ]
}
```

**Default difficulty:** `intermediate` (can be adjusted later)

---

#### Q4: Daily Study Time (Optional)
```
How much time can you dedicate to studying each day?

This helps me plan realistic revision schedules.

[Multiple choice]
• 30 minutes
• 1 hour
• 1.5 hours
• 2 hours (Recommended)
• 3 hours
• 4+ hours
• Skip for now

> [Student selects]
```

**Default:** 2.0 hours (if skipped)
**Stored as:**
```json
{
  "preferences": {
    "study_time_daily_hours": 2.0
  }
}
```

---

#### Q5: Learning Style Preference (Optional)
```
What's your preferred learning style?

This helps me adapt explanations to suit you.

[Multiple choice]
• Visual (diagrams, flowcharts, images)
• Reading/Writing (text-based notes, summaries)
• Practical (examples, problem-solving, practice)
• Balanced (mix of all)
• Skip for now

> [Student selects]
```

**Default:** `balanced` (if skipped)
**Stored as:**
```json
{
  "preferences": {
    "learning_style": "visual"
  }
}
```

---

#### Q6: Upcoming Exams (Optional)
```
Do you have any upcoming exams I should know about?

This helps me prioritize topics and create revision plans.

[Multiple choice]
• Yes, let me add them now
• No, I'll add them later
• Skip for now

> [Student selects]
```

**If "Yes":** Launch exam addition workflow (see Section 4)
**If "No/Skip":** Continue to profile creation

---

### Onboarding Completion

```
✅ Profile created successfully!

Here's what I know about you:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: Ravi Kumar
Level: Class 12 (CBSE)
Subjects: Biology, Physics, Chemistry
Study Time: 2 hours/day
Learning Style: Visual
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've created state files for each subject:
✓ Biology-mastery.json
✓ Physics-mastery.json  
✓ Chemistry-mastery.json
✓ Biology-revision-queue.json
✓ Physics-revision-queue.json
✓ Chemistry-revision-queue.json

You can update your profile anytime by saying:
"update my profile" or "add a subject"

Ready to start? Try:
• "Explain photosynthesis"
• "Create a quiz on Newton's laws"
• "Show my progress"
```

**System Actions:**
1. Create `learner-profile.json` with collected data
2. Create `{Subject}-mastery.json` for each subject (empty)
3. Create `{Subject}-revision-queue.json` for each subject (empty)
4. Create `exam-calendar.json` (empty if no exams added)
5. Create `activity-log.jsonl` (empty)
6. Log event: `profile_created`

---

## 2. Profile Update Workflow

### Trigger Phrases
- "update my profile"
- "change my preferences"
- "edit my profile"
- "add a subject"
- "remove a subject"

### Update Options Menu
```
What would you like to update?

[Multiple choice]
• Add a new subject
• Remove a subject
• Change daily study time
• Change learning style
• Update academic level
• View full profile
• Cancel

> [Student selects]
```

### 2.1 Add a New Subject
```
Which subject would you like to add?

> [Student enters subject name]
Example: Sanskrit

What's your current level in Sanskrit?

[Multiple choice]
• Beginner (just starting)
• Intermediate (some knowledge)
• Advanced (preparing for exams)

> [Student selects]
```

**System Actions:**
1. Add subject to `learner-profile.json`
2. Create `{Subject}-mastery.json`
3. Create `{Subject}-revision-queue.json`
4. Log event: `subject_added`

**Confirmation:**
```
✅ Sanskrit added to your profile!

I've created state files for Sanskrit:
✓ Sanskrit-mastery.json
✓ Sanskrit-revision-queue.json

Your subjects now: Biology, Physics, Chemistry, Sanskrit

Ready to study Sanskrit? Try:
"Explain Sanskrit grammar basics"
```

---

### 2.2 Remove a Subject
```
Which subject would you like to remove?

Current subjects: Biology, Physics, Chemistry

[Multiple choice - show current subjects]
• Biology
• Physics
• Chemistry
• Cancel

> [Student selects]
```

**⚠️ Warning:**
```
⚠️  WARNING: This will delete all data for Physics!

This includes:
• Mastery tracking (X topics)
• Revision queue (Y items)
• Practice history

This action cannot be undone. Are you sure?

[Multiple choice]
• Yes, remove Physics
• No, keep it

> [Student confirms]
```

**System Actions:**
1. Remove subject from `learner-profile.json`
2. Archive (not delete) `Physics-mastery.json` → `state/archive/`
3. Archive `Physics-revision-queue.json` → `state/archive/`
4. Log event: `subject_removed`

**Confirmation:**
```
✅ Physics removed from your profile.

Data archived to: state/archive/Physics-mastery-2026-03-21.json
(You can restore it manually if needed)

Your subjects now: Biology, Chemistry
```

---

### 2.3 Change Daily Study Time
```
Current study time: 2 hours/day

How much time can you dedicate daily?

[Multiple choice]
• 30 minutes
• 1 hour
• 1.5 hours
• 2 hours
• 3 hours
• 4+ hours
• Custom amount

> [Student selects]
```

**If "Custom":**
```
Enter your daily study time (in hours):
Example: 2.5

> [Student enters number]
```

**System Actions:**
1. Update `preferences.study_time_daily_hours` in profile
2. Recalculate revision schedules (if exams exist)
3. Log event: `preference_updated`

**Confirmation:**
```
✅ Daily study time updated to 3 hours.

This gives you more flexibility for revision planning!
```

---

### 2.4 Change Learning Style
```
Current learning style: Visual

What's your preferred learning style?

[Multiple choice]
• Visual (diagrams, flowcharts, images)
• Reading/Writing (text-based notes, summaries)
• Practical (examples, problem-solving, practice)
• Balanced (mix of all)

> [Student selects]
```

**System Actions:**
1. Update `preferences.learning_style` in profile
2. Log event: `preference_updated`

**Confirmation:**
```
✅ Learning style updated to Practical.

I'll focus more on examples and problem-solving exercises!
```

---

### 2.5 Update Academic Level
```
Current level: Class 12 (CBSE)

What's your current academic level?

[Multiple choice]
• Class 9
• Class 10
• Class 11
• Class 12
• Undergraduate (Year 1)
• Undergraduate (Year 2)
• Undergraduate (Year 3)
• Undergraduate (Year 4+)
• Other

> [Student selects]
```

**System Actions:**
1. Update `current_level` in profile
2. Log event: `level_updated`

**Confirmation:**
```
✅ Academic level updated to Undergraduate (Year 1).

Congratulations on moving up! 🎓
```

---

### 2.6 View Full Profile
```
📋 YOUR PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 Name: Ravi Kumar
📚 Level: Class 12 (CBSE)
🎓 Academic Year: 2025-2026

📖 SUBJECTS (3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Biology (Intermediate)
• Physics (Intermediate)
• Chemistry (Intermediate)

⚙️  PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Study Time: 2 hours/day
Learning Style: Visual
Difficulty: Progressive

🎯 LEARNING GOALS (2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Score 95+ in Biology (Target: May 15, 2026)
2. Master Organic Chemistry (Target: Apr 30, 2026)

💪 STRENGTHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Photosynthesis, Cell Biology, Thermodynamics

⚠️  AREAS TO IMPROVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Genetics, Electromagnetism

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Profile created: Mar 20, 2026
Last updated: Mar 21, 2026

To update: "update my profile"
```

---

## 3. Quick Subject Add (During Study)

### Trigger
Student asks: "Explain [topic] in [new subject]"

**Example:** "Explain verbs in Sanskrit" (Sanskrit not in profile)

### Workflow
```
I notice you're asking about Sanskrit, but it's not in your profile yet.

Would you like to add Sanskrit to your subjects?

[Multiple choice]
• Yes, add Sanskrit (Beginner)
• Yes, add Sanskrit (Intermediate)
• Yes, add Sanskrit (Advanced)
• No, just explain once (don't track progress)

> [Student selects]
```

**If Yes:**
- Add subject with selected difficulty
- Create state files
- Proceed with explanation
- Log event: `subject_auto_added`

**If No:**
- Provide explanation only
- Don't create state files
- Don't track mastery

---

## 4. Exam Addition Workflow

### Trigger
- During onboarding (Q6)
- Student asks: "add an exam" or "I have an exam coming up"

### Interactive Questions

#### Q1: Subject
```
Which subject is the exam for?

[Multiple choice - show student's subjects]
• Biology
• Physics
• Chemistry

> [Student selects]
```

---

#### Q2: Exam Name
```
What's the name of the exam?

Examples:
• "CBSE Biology Board Exam"
• "Unit Test - Mechanics"
• "Mid-term Exam"

> [Student enters name]
```

---

#### Q3: Exam Date
```
When is the exam?

Enter date in format: YYYY-MM-DD
Example: 2026-05-15

> [Student enters date]
```

**Validation:** Date must be in future
**Auto-calculate:** Days remaining

---

#### Q4: Exam Type
```
What type of exam is this?

[Multiple choice]
• Board Exam (final/main exam)
• Unit Test (chapter/topic test)
• Mid-term Exam
• Mock/Practice Exam
• Competitive Exam (JEE/NEET/etc.)

> [Student selects]
```

---

#### Q5: Syllabus Coverage (Optional)
```
How much of the syllabus does this exam cover?

[Multiple choice]
• Full syllabus (100%)
• Most of syllabus (75%)
• Half syllabus (50%)
• One or two chapters (25%)
• Skip for now

> [Student selects]
```

**Default:** 1.0 (if skipped)

---

### Exam Addition Confirmation
```
✅ Exam added successfully!

📅 CBSE Biology Board Exam
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subject: Biology
Date: May 15, 2026
Days Remaining: 55 days
Type: Board Exam
Syllabus: 100%

I'll create a revision plan for you!
Would you like me to do that now?

[Multiple choice]
• Yes, create revision plan
• No, I'll ask later

> [Student selects]
```

**System Actions:**
1. Add exam to `exam-calendar.json`
2. Log event: `exam_added`
3. Optionally trigger revision planner agent

---

## 5. Profile Data Storage

### learner-profile.json (Slim Structure)
```json
{
  "student_name": "Ravi Kumar",
  "student_id": "uuid-v4-here",
  "created_at": "2026-03-20T10:00:00Z",
  "updated_at": "2026-03-21T10:16:00Z",
  
  "current_level": {
    "grade": "12",
    "board": "CBSE",
    "academic_year": "2025-2026"
  },
  
  "subjects": [
    {
      "name": "Biology",
      "difficulty_level": "intermediate",
      "added_date": "2026-03-20",
      "mastery_file": "Biology-mastery.json",
      "revision_file": "Biology-revision-queue.json"
    },
    {
      "name": "Physics",
      "difficulty_level": "intermediate",
      "added_date": "2026-03-20",
      "mastery_file": "Physics-mastery.json",
      "revision_file": "Physics-revision-queue.json"
    },
    {
      "name": "Chemistry",
      "difficulty_level": "advanced",
      "added_date": "2026-03-20",
      "mastery_file": "Chemistry-mastery.json",
      "revision_file": "Chemistry-revision-queue.json"
    }
  ],
  
  "preferences": {
    "learning_style": "visual",
    "study_time_daily_hours": 2.0,
    "difficulty_preference": "progressive"
  },
  
  "goals": [
    {
      "goal_id": "goal-001",
      "description": "Score 95+ in Biology",
      "target_date": "2026-05-15",
      "priority": "high",
      "status": "active"
    }
  ],
  
  "strengths": ["photosynthesis", "cell biology"],
  "weaknesses": ["genetics", "evolution"],
  
  "version": "1.0"
}
```

**File Size:** ~1.5 KB (very lightweight!)

---

## 6. Implementation Notes

### Profile Store API (tools/learner_profile_store.py)

```python
# Core CRUD
def get_profile() -> dict
def set_profile(profile: dict) -> None
def update_profile(updates: dict) -> None

# Subject management
def add_subject(name: str, difficulty: str) -> None
def remove_subject(name: str) -> None
def get_subjects() -> List[dict]
def subject_exists(name: str) -> bool

# Preferences
def get_preference(key: str) -> Any
def set_preference(key: str, value: Any) -> None

# Goals
def add_goal(goal: dict) -> str
def remove_goal(goal_id: str) -> None
def update_goal(goal_id: str, updates: dict) -> None
def get_goals() -> List[dict]

# Strengths/Weaknesses
def update_strengths_weaknesses(strengths: List[str], weaknesses: List[str]) -> None

# Subject-specific state file management
def create_subject_state_files(subject: str) -> None
def archive_subject_state_files(subject: str) -> None
```

---

## 7. Workflow Integration

### Chat Command Examples

**Profile Creation:**
- "setup my profile"
- "create profile"
- "first time setup"

**Profile Updates:**
- "update my profile"
- "change my study time to 3 hours"
- "add Sanskrit to my subjects"
- "remove Physics"
- "show my profile"

**Quick Actions:**
- "add an exam"
- "set a learning goal"
- "I'm studying History now" (auto-add subject)

---

## 8. Success Criteria

✅ Student can create profile in < 2 minutes
✅ Profile only stores essential information (< 2 KB)
✅ Subject addition/removal is simple and safe
✅ Preferences are easy to change
✅ Profile data is human-readable (JSON)
✅ Automatic subject detection works smoothly
✅ Data archival prevents accidental loss

---

## 9. Future Enhancements (v2.0)

- Profile import/export (JSON file)
- Multi-profile support (siblings sharing vault)
- Profile templates (CBSE Class 12 template)
- Smart defaults based on academic level
- Profile analytics dashboard
- Strength/weakness auto-detection from mastery

---

**This workflow design is ready for implementation!** 🎯
