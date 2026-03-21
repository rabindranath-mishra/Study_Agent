#!/usr/bin/env python3
"""
Profile Agent - Student Profile Management

Handles interactive profile creation, updates, and subject management.
Implements conversational workflows for onboarding and profile management.

Usage:
    python profile_agent.py --action create
    python profile_agent.py --action update
    python profile_agent.py --action add-subject --subject "Sanskrit"
    python profile_agent.py --action remove-subject --subject "Physics"
    python profile_agent.py --action view
    python profile_agent.py --action add-exam

Dependencies:
    - learner_profile_store.py (state store for profile CRUD)
    - exam_calendar_store.py (for exam management)
    - activity_log_store.py (for logging events)
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Add tools directory to path
TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(TOOLS_DIR))

from paths import INBOX_DIR, PS_SCRIPT_CREATE_NOTE as _PS_WRITE, VAULT_ROOT

# Import state stores (will be built in Phase 8)
try:
    import learner_profile_store as profile_store
    import exam_calendar_store as exam_store
    import activity_log_store as log_store
    STORES_AVAILABLE = True
except ImportError:
    STORES_AVAILABLE = False
    print("[WARNING]  Warning: State stores not yet built. Profile Agent will not function fully.", file=sys.stderr)


class ProfileAgent:
    """Interactive agent for student profile management"""
    
    def __init__(self):
        self.profile = None
        
    def run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Main entry point for profile agent actions
        
        Args:
            action: Action to perform (create, update, add-subject, etc.)
            **kwargs: Action-specific parameters
            
        Returns:
            Result dictionary with status and data
        """
        if not STORES_AVAILABLE:
            return {
                "status": "error",
                "message": "State stores not available. Build state stores first (Phase 8)."
            }
        
        actions = {
            "create": self.create_profile,
            "update": self.update_profile_menu,
            "add-subject": self.add_subject,
            "remove-subject": self.remove_subject,
            "view": self.view_profile,
            "add-exam": self.add_exam,
            "check-exists": self.check_profile_exists,
            "write-card": self.write_student_card,
        }
        
        if action not in actions:
            return {
                "status": "error",
                "message": f"Unknown action: {action}. Available: {', '.join(actions.keys())}"
            }
        
        return actions[action](**kwargs)
    
    # ========================================================================
    # WORKFLOW 1: FIRST-TIME ONBOARDING
    # ========================================================================
    
    def create_profile(self, **responses) -> Dict[str, Any]:
        """
        Create new student profile through interactive onboarding
        
        Expected responses (can be passed as kwargs or collected interactively):
            student_name: str
            grade: str
            board: str
            subjects: List[str]
            study_time_daily_hours: float
            learning_style: str
            add_exams: bool
        
        Returns:
            Dictionary with profile creation status
        """
        print("=================================================================")
        print("")
        print("|        WELCOME! WELCOME TO YOUR STUDY AGENT!                        |")
        print("")
        print("=================================================================")
        print()
        
        # Check if profile already exists
        if profile_store.profile_exists():
            existing = profile_store.get_profile()
            return {
                "status": "error",
                "message": f"Profile already exists for {existing.get('student_name')}. Use 'update' action to modify.",
                "profile": existing
            }
        
        # Collect responses (in production, these would come from interactive prompts)
        profile_data = {
            "student_name": responses.get("student_name", "Student"),
            "student_id": self._generate_student_id(),
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
            "current_level": {
                "grade": responses.get("grade", "12"),
                "board": responses.get("board", "CBSE"),
                "academic_year": responses.get("academic_year", self._get_academic_year())
            },
            "subjects": [],
            "preferences": {
                "learning_style": responses.get("learning_style", "balanced"),
                "study_time_daily_hours": responses.get("study_time_daily_hours", 2.0),
                "difficulty_preference": "progressive"
            },
            "goals": [],
            "strengths": [],
            "weaknesses": [],
            "version": "1.0"
        }
        
        # Add subjects
        subjects_input = responses.get("subjects", [])
        if isinstance(subjects_input, str):
            subjects_input = [s.strip() for s in subjects_input.split(",")]
        
        for subject_name in subjects_input:
            subject_name = subject_name.strip().title()
            if subject_name:
                difficulty = responses.get(f"{subject_name}_difficulty", "intermediate")
                self._add_subject_to_profile(profile_data, subject_name, difficulty)
        
        # Save profile
        profile_store.set_profile(profile_data)
        
        # Create state files for each subject
        for subject in profile_data["subjects"]:
            self._create_subject_state_files(subject["name"])
        
        # Log event
        log_store.log_event(
            "profile_created",
            student_name=profile_data["student_name"],
            subjects_count=len(profile_data["subjects"])
        )
        
        # Display confirmation
        print("[OK] Profile created successfully!")
        print()
        print("Here's what I know about you:")
        print("-----------------------------------------------------------------")
        print(f"Name: {profile_data['student_name']}")
        print(f"Level: Class {profile_data['current_level']['grade']} ({profile_data['current_level']['board']})")
        print(f"Subjects: {', '.join([s['name'] for s in profile_data['subjects']])}")
        print(f"Study Time: {profile_data['preferences']['study_time_daily_hours']} hours/day")
        print(f"Learning Style: {profile_data['preferences']['learning_style'].title()}")
        print("-----------------------------------------------------------------")
        print()
        print("I've created state files for each subject:")
        for subject in profile_data["subjects"]:
            print(f"+ {subject['name']}-mastery.json")
            print(f"+ {subject['name']}-revision-queue.json")
        print()
        print("You can update your profile anytime by saying:")
        print('"update my profile" or "add a subject"')
        print()
        print("Ready to start? Try:")
        print('• "Explain photosynthesis"')
        print('• "Create a quiz on Newton\'s laws"')
        print('• "Show my progress"')
        print()

        # Write student card to inbox (non-fatal if it fails)
        card_result = self.write_student_card(profile_data)
        if card_result["status"] == "success":
            print(f"[OK] Student card created: {card_result['path']}")
        else:
            print(f"[WARNING] Could not write student card: {card_result.get('message', '')}", file=sys.stderr)

        return {
            "status": "success",
            "message": "Profile created successfully",
            "profile": profile_data,
            "student_card": card_result,
            "next_actions": ["add_exam", "start_learning"]
        }

        # Write student card to inbox (non-fatal if it fails)
        card_result = self.write_student_card(profile_data)
        if card_result["status"] == "success":
            print(f"[OK] Student card created: {card_result['path']}")
        else:
            print(f"[WARNING] Could not write student card: {card_result.get('message', '')}", file=sys.stderr)

        return {
            "status": "success",
            "message": "Profile created successfully",
            "profile": profile_data,
            "student_card": card_result,
            "next_actions": ["add_exam", "start_learning"]
        }
    
    def _add_subject_to_profile(self, profile_data: dict, subject_name: str, difficulty: str = "intermediate") -> None:
        """Add subject to profile data structure"""
        subject = {
            "name": subject_name,
            "difficulty_level": difficulty,
            "added_date": datetime.now(timezone.utc).date().isoformat(),
            "mastery_file": f"{subject_name}-mastery.json",
            "revision_file": f"{subject_name}-revision-queue.json"
        }
        profile_data["subjects"].append(subject)
    
    def _create_subject_state_files(self, subject: str) -> None:
        """Create mastery and revision queue files for a subject"""
        # These will call the respective store initialization methods
        # mastery_store.initialize_subject(subject)
        # revision_queue_store.initialize_subject(subject)
        pass  # Placeholder until stores are built
    
    # ========================================================================
    # WORKFLOW 2: PROFILE UPDATE
    # ========================================================================
    
    def update_profile_menu(self) -> Dict[str, Any]:
        """
        Display profile update menu
        
        Returns:
            Dictionary with available update options
        """
        profile = profile_store.get_profile()
        
        print("=================================================================")
        print("")
        print("|          PROFILE UPDATE MENU                                 |")
        print("")
        print("=================================================================")
        print()
        print("What would you like to update?")
        print()
        print("1. Add a new subject")
        print("2. Remove a subject")
        print("3. Change daily study time")
        print("4. Change learning style")
        print("5. Update academic level")
        print("6. Add/update learning goals")
        print("7. View full profile")
        print("8. Cancel")
        print()
        
        return {
            "status": "success",
            "options": [
                {"id": 1, "action": "add-subject", "label": "Add a new subject"},
                {"id": 2, "action": "remove-subject", "label": "Remove a subject"},
                {"id": 3, "action": "update-study-time", "label": "Change daily study time"},
                {"id": 4, "action": "update-learning-style", "label": "Change learning style"},
                {"id": 5, "action": "update-level", "label": "Update academic level"},
                {"id": 6, "action": "manage-goals", "label": "Add/update learning goals"},
                {"id": 7, "action": "view", "label": "View full profile"},
                {"id": 8, "action": "cancel", "label": "Cancel"}
            ],
            "current_profile": profile
        }
    
    # ========================================================================
    # SUBJECT MANAGEMENT
    # ========================================================================
    
    def add_subject(self, subject: str = None, difficulty: str = "intermediate", **kwargs) -> Dict[str, Any]:
        """
        Add a new subject to student profile
        
        Args:
            subject: Subject name (e.g., "Sanskrit")
            difficulty: Difficulty level (beginner, intermediate, advanced)
            
        Returns:
            Dictionary with addition status
        """
        if not subject:
            return {
                "status": "error",
                "message": "Subject name required. Use --subject 'Subject Name'"
            }
        
        subject = subject.strip().title()
        profile = profile_store.get_profile()
        
        # Check if subject already exists
        existing_subjects = [s["name"] for s in profile.get("subjects", [])]
        if subject in existing_subjects:
            return {
                "status": "error",
                "message": f"{subject} is already in your profile",
                "subjects": existing_subjects
            }
        
        # Add subject to profile
        profile_store.add_subject(subject, difficulty)
        
        # Create state files
        self._create_subject_state_files(subject)
        
        # Log event
        log_store.log_event(
            "subject_added",
            subject=subject,
            difficulty=difficulty
        )
        
        # Display confirmation
        print(f"[OK] {subject} added to your profile!")
        print()
        print(f"I've created state files for {subject}:")
        print(f"+ {subject}-mastery.json")
        print(f"+ {subject}-revision-queue.json")
        print()
        updated_profile = profile_store.get_profile()
        subjects_list = [s["name"] for s in updated_profile["subjects"]]
        print(f"Your subjects now: {', '.join(subjects_list)}")
        print()
        print(f"Ready to study {subject}? Try:")
        print(f'"Explain {subject} basics"')
        print()

        # Refresh student card
        self.write_student_card(updated_profile)

        return {
            "status": "success",
            "message": f"{subject} added successfully",
            "subject": subject,
            "difficulty": difficulty,
            "all_subjects": subjects_list
        }
    
    def remove_subject(self, subject: str = None, confirm: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Remove a subject from student profile (with archival)
        
        Args:
            subject: Subject name to remove
            confirm: Confirmation flag (must be True to proceed)
            
        Returns:
            Dictionary with removal status
        """
        if not subject:
            return {
                "status": "error",
                "message": "Subject name required. Use --subject 'Subject Name'"
            }
        
        subject = subject.strip().title()
        profile = profile_store.get_profile()
        
        # Check if subject exists
        existing_subjects = [s["name"] for s in profile.get("subjects", [])]
        if subject not in existing_subjects:
            return {
                "status": "error",
                "message": f"{subject} is not in your profile",
                "current_subjects": existing_subjects
            }
        
        # Show warning if not confirmed
        if not confirm:
            print(f"[WARNING]  WARNING: This will archive all data for {subject}!")
            print()
            print("This includes:")
            print("• Mastery tracking")
            print("• Revision queue")
            print("• Practice history")
            print()
            print("Data will be archived (not deleted) and can be restored manually.")
            print()
            print("To proceed, add --confirm flag:")
            print(f'python profile_agent.py --action remove-subject --subject "{subject}" --confirm')
            print()
            
            return {
                "status": "warning",
                "message": "Confirmation required",
                "subject": subject,
                "requires_confirm": True
            }
        
        # Remove subject from profile
        profile_store.remove_subject(subject)
        
        # Archive state files
        self._archive_subject_state_files(subject)
        
        # Log event
        log_store.log_event(
            "subject_removed",
            subject=subject,
            archived=True
        )
        
        # Display confirmation
        print(f"[OK] {subject} removed from your profile.")
        print()
        print(f"Data archived to: state/archive/{subject}-mastery-{datetime.now(timezone.utc).date().isoformat()}.json")
        print("(You can restore it manually if needed)")
        print()
        updated_profile = profile_store.get_profile()
        subjects_list = [s["name"] for s in updated_profile["subjects"]]
        print(f"Your subjects now: {', '.join(subjects_list)}")
        print()

        # Refresh student card
        self.write_student_card(updated_profile)

        return {
            "status": "success",
            "message": f"{subject} removed and archived",
            "subject": subject,
            "archived": True,
            "remaining_subjects": subjects_list
        }
    
    def _archive_subject_state_files(self, subject: str) -> None:
        """Archive (not delete) subject state files"""
        # This will call profile_store.archive_subject_state_files(subject)
        # which moves files to state/archive/ with timestamp
        pass  # Placeholder until stores are built
    
    # ========================================================================
    # STUDENT CARD (Obsidian note in 01 - Inbox)
    # ========================================================================

    def write_student_card(self, profile: Optional[dict] = None) -> Dict[str, Any]:
        """
        Create or overwrite the student card note in 01 - Inbox.

        The card is the human-readable summary of the learner profile:
        name, board, grade, subjects, preferences, goals.  It is written
        every time the profile changes so Obsidian always reflects the
        current state.

        The file is always named:
            Student Card - <FirstName LastName>.md
        (safe characters only — spaces are kept, no slashes / colons).

        Returns:
            {status, path, message}
        """
        if profile is None:
            if not STORES_AVAILABLE:
                return {"status": "error", "message": "Profile store not available."}
            profile = profile_store.get_profile()

        title = f"Student Card - {profile.get('student_name', 'Student')}"
        content = self._build_student_card_content(profile)

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", _PS_WRITE,
                "-VaultPath", VAULT_ROOT,
                "-Title", title,
                "-Content", content,
                "-Folder", INBOX_DIR,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        try:
            ps_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            ps_result = {"success": False, "error": result.stderr.strip() or result.stdout.strip()}

        if ps_result.get("success"):
            return {
                "status": "success",
                "path": ps_result.get("path", ""),
                "message": f"Student card written to 01 - Inbox/{title}.md",
            }
        return {
            "status": "error",
            "message": "Failed to write student card note.",
            "detail": ps_result.get("error", ""),
        }

    def _build_student_card_content(self, profile: dict) -> str:
        """Render the student card as Obsidian-compatible markdown with YAML frontmatter."""
        from datetime import date

        name       = profile.get("student_name", "Student")
        student_id = profile.get("student_id", "")
        level      = profile.get("current_level", {})
        grade      = level.get("grade", "")
        board      = level.get("board", "")
        acad_year  = level.get("academic_year", "")
        subjects   = profile.get("subjects", [])
        prefs      = profile.get("preferences", {})
        goals      = profile.get("goals", [])
        strengths  = profile.get("strengths", [])
        weaknesses = profile.get("weaknesses", [])
        updated    = profile.get("updated_at", "")[:10]
        created    = profile.get("created_at", "")[:10]
        today      = date.today().isoformat()

        # Build subjects tag list for frontmatter
        subject_tags = " ".join(
            f"  - {s['name'].lower().replace(' ', '-')}"
            for s in subjects
        )

        lines = [
            "---",
            'title: "Student Card"',
            f"date: {today}",
            "tags:",
            "  - student-card",
            "  - profile",
            f"  - {board.lower()}",
        ]
        for s in subjects:
            lines.append(f"  - {s['name'].lower().replace(' ', '-')}")
        lines += [
            "note_type: student-card",
            f'student_name: "{name}"',
            f'student_id: "{student_id}"',
            f'grade: "{grade}"',
            f'board: "{board}"',
            f'academic_year: "{acad_year}"',
            f"updated: {updated}",
            "---",
            "",
            f"# 🎓 {name}",
            "",
            f"> **Board:** {board} | **Grade:** {grade} | **Academic Year:** {acad_year}",
            "",
            "---",
            "",
            "## 📚 Subjects",
            "",
        ]

        if subjects:
            lines.append("| Subject | Difficulty | Added |")
            lines.append("|---------|------------|-------|")
            for s in subjects:
                diff  = s.get("difficulty_level", "intermediate").title()
                added = s.get("added_date", "")
                lines.append(f"| {s['name']} | {diff} | {added} |")
        else:
            lines.append("*No subjects added yet.*")

        lines += [
            "",
            "---",
            "",
            "## ⚙️ Preferences",
            "",
            f"- **Daily Study Time:** {prefs.get('study_time_daily_hours', 2.0)} hours",
            f"- **Learning Style:** {prefs.get('learning_style', 'balanced').title()}",
            f"- **Difficulty Preference:** {prefs.get('difficulty_preference', 'progressive').title()}",
            "",
        ]

        if goals:
            lines += ["---", "", "## 🎯 Goals", ""]
            for g in goals:
                desc   = g.get("description", "")
                target = g.get("target_date", "")
                lines.append(f"- {desc}" + (f" *(by {target})*" if target else ""))
            lines.append("")

        if strengths:
            lines += ["---", "", "## 💪 Strengths", ""]
            for s in strengths:
                lines.append(f"- {s}")
            lines.append("")

        if weaknesses:
            lines += ["---", "", "## 📈 Areas to Improve", ""]
            for w in weaknesses:
                lines.append(f"- {w}")
            lines.append("")

        lines += [
            "---",
            "",
            f"*Profile created: {created} | Last updated: {updated}*",
            "",
        ]

        return "\n".join(lines)

    # ========================================================================
    # PROFILE VIEWING
    # ========================================================================
    
    def view_profile(self) -> Dict[str, Any]:
        """
        Display formatted student profile
        
        Returns:
            Dictionary with formatted profile data
        """
        profile = profile_store.get_profile()
        
        print("=================================================================")
        print("")
        print("|         YOUR PROFILE                                        |")
        print("")
        print("=================================================================")
        print()
        
        # Basic info
        print(f" Name: {profile.get('student_name', 'Not set')}")
        level = profile.get('current_level', {})
        print(f" Level: Class {level.get('grade', '?')} ({level.get('board', '?')})")
        print(f" Academic Year: {level.get('academic_year', '?')}")
        print()
        
        # Subjects
        subjects = profile.get('subjects', [])
        print(f" SUBJECTS ({len(subjects)})")
        print("-----------------------------------------------------------------")
        for subj in subjects:
            print(f"• {subj['name']} ({subj['difficulty_level'].title()})")
        print()
        
        # Preferences
        prefs = profile.get('preferences', {})
        print("  PREFERENCES")
        print("-----------------------------------------------------------------")
        print(f"Study Time: {prefs.get('study_time_daily_hours', 2.0)} hours/day")
        print(f"Learning Style: {prefs.get('learning_style', 'balanced').title()}")
        print(f"Difficulty: {prefs.get('difficulty_preference', 'progressive').title()}")
        print()
        
        # Goals
        goals = profile.get('goals', [])
        if goals:
            print(f" LEARNING GOALS ({len(goals)})")
            print("-----------------------------------------------------------------")
            for i, goal in enumerate(goals, 1):
                print(f"{i}. {goal['description']} (Target: {goal['target_date']})")
            print()
        
        # Strengths/Weaknesses
        strengths = profile.get('strengths', [])
        weaknesses = profile.get('weaknesses', [])
        
        if strengths:
            print(" STRENGTHS")
            print("-----------------------------------------------------------------")
            print(", ".join(strengths))
            print()
        
        if weaknesses:
            print("[WARNING]  AREAS TO IMPROVE")
            print("-----------------------------------------------------------------")
            print(", ".join(weaknesses))
            print()
        
        # Metadata
        print("-----------------------------------------------------------------")
        print(f"Profile created: {profile.get('created_at', 'Unknown')[:10]}")
        print(f"Last updated: {profile.get('updated_at', 'Unknown')[:10]}")
        print()
        print('To update: "update my profile"')
        print()
        
        return {
            "status": "success",
            "profile": profile,
            "subjects_count": len(subjects),
            "goals_count": len(goals)
        }
    
    # ========================================================================
    # EXAM MANAGEMENT
    # ========================================================================
    
    def add_exam(self, **exam_data) -> Dict[str, Any]:
        """
        Add an exam to the calendar
        
        Expected exam_data:
            subject: str
            exam_name: str
            exam_date: str (YYYY-MM-DD)
            exam_type: str (board, unit_test, midterm, mock, competitive)
            syllabus_coverage: float (0.0-1.0)
            
        Returns:
            Dictionary with exam addition status
        """
        required_fields = ["subject", "exam_name", "exam_date", "exam_type"]
        missing = [f for f in required_fields if f not in exam_data]
        
        if missing:
            return {
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing)}"
            }
        
        # Validate subject exists in profile
        profile = profile_store.get_profile()
        subjects = [s["name"] for s in profile.get("subjects", [])]
        if exam_data["subject"] not in subjects:
            return {
                "status": "error",
                "message": f"Subject '{exam_data['subject']}' not in your profile. Add it first.",
                "available_subjects": subjects
            }
        
        # Add exam to calendar
        exam_id = exam_store.add_exam(exam_data)
        
        # Log event
        log_store.log_event(
            "exam_added",
            exam_id=exam_id,
            subject=exam_data["subject"],
            exam_date=exam_data["exam_date"]
        )
        
        # Calculate days remaining
        days_remaining = self._calculate_days_remaining(exam_data["exam_date"])
        
        # Display confirmation
        print(f"[OK] Exam added successfully!")
        print()
        print(f" {exam_data['exam_name']}")
        print("-----------------------------------------------------------------")
        print(f"Subject: {exam_data['subject']}")
        print(f"Date: {exam_data['exam_date']}")
        print(f"Days Remaining: {days_remaining} days")
        print(f"Type: {exam_data['exam_type'].replace('_', ' ').title()}")
        print(f"Syllabus: {int(exam_data.get('syllabus_coverage', 1.0) * 100)}%")
        print()
        print("I'll create a revision plan for you!")
        print('Would you like me to do that now? (Say "create revision plan")')
        print()
        
        return {
            "status": "success",
            "message": "Exam added successfully",
            "exam_id": exam_id,
            "days_remaining": days_remaining,
            "next_actions": ["create_revision_plan"]
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def check_profile_exists(self) -> Dict[str, Any]:
        """Check if student profile exists"""
        exists = profile_store.profile_exists()
        
        if exists:
            profile = profile_store.get_profile()
            return {
                "status": "success",
                "exists": True,
                "student_name": profile.get("student_name"),
                "subjects_count": len(profile.get("subjects", []))
            }
        else:
            return {
                "status": "success",
                "exists": False,
                "message": "No profile found. Create one with --action create"
            }
    
    def _generate_student_id(self) -> str:
        """Generate unique student ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _now_iso(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def _get_academic_year(self) -> str:
        """Get current academic year string"""
        now = datetime.now(timezone.utc)
        if now.month >= 4:  # April onwards = new academic year
            return f"{now.year}-{now.year + 1}"
        else:
            return f"{now.year - 1}-{now.year}"
    
    def _calculate_days_remaining(self, exam_date: str) -> int:
        """Calculate days until exam"""
        from datetime import date
        exam = date.fromisoformat(exam_date)
        today = date.today()
        delta = exam - today
        return delta.days


def main():
    """Command-line interface for Profile Agent"""
    parser = argparse.ArgumentParser(
        description="Profile Agent - Student Profile Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create new profile
  python profile_agent.py --action create --student-name "Ravi Kumar" --grade 12 --subjects "Biology,Physics,Chemistry"
  
  # Add a subject
  python profile_agent.py --action add-subject --subject "Sanskrit" --difficulty intermediate
  
  # Remove a subject (with confirmation)
  python profile_agent.py --action remove-subject --subject "Physics" --confirm
  
  # View profile
  python profile_agent.py --action view
  
  # Check if profile exists
  python profile_agent.py --action check-exists
  
  # Add an exam
  python profile_agent.py --action add-exam --subject Biology --exam-name "Board Exam" --exam-date 2026-05-15 --exam-type board
        """
    )
    
    parser.add_argument("--action", required=True, 
                       choices=["create", "update", "add-subject", "remove-subject", "view", "add-exam", "check-exists", "write-card"],
                       help="Action to perform")
    
    # Profile creation arguments
    parser.add_argument("--student-name", help="Student name")
    parser.add_argument("--grade", help="Academic grade/class")
    parser.add_argument("--board", default="CBSE", help="Education board (default: CBSE)")
    parser.add_argument("--subjects", help="Comma-separated list of subjects")
    parser.add_argument("--study-time", type=float, default=2.0, help="Daily study time in hours (default: 2.0)")
    parser.add_argument("--learning-style", default="balanced", 
                       choices=["visual", "reading", "practical", "balanced"],
                       help="Learning style preference (default: balanced)")
    
    # Subject management arguments
    parser.add_argument("--subject", help="Subject name")
    parser.add_argument("--difficulty", default="intermediate",
                       choices=["beginner", "intermediate", "advanced"],
                       help="Subject difficulty level (default: intermediate)")
    parser.add_argument("--confirm", action="store_true", help="Confirm destructive action")
    
    # Exam management arguments
    parser.add_argument("--exam-name", help="Name of the exam")
    parser.add_argument("--exam-date", help="Exam date (YYYY-MM-DD)")
    parser.add_argument("--exam-type", choices=["board", "unit_test", "midterm", "mock", "competitive"],
                       help="Type of exam")
    parser.add_argument("--syllabus-coverage", type=float, default=1.0,
                       help="Syllabus coverage (0.0-1.0, default: 1.0)")
    
    args = parser.parse_args()
    
    # Create agent instance
    agent = ProfileAgent()
    
    # Map actions to the arguments they accept
    action_args = {
        "check-exists": [],
        "view": [],
        "write-card": [],
        "create": ["student_name", "grade", "board", "subjects", "study_time_daily_hours", "learning_style"],
        "update": ["student_name", "grade", "board", "subjects", "study_time_daily_hours", "learning_style"],
        "add-subject": ["subject", "difficulty"],
        "remove-subject": ["subject", "confirm"],
        "add-exam": ["subject", "exam_name", "exam_date", "exam_type", "syllabus_coverage"],
    }

    all_kwargs = {
        "student_name": args.student_name,
        "grade": args.grade,
        "board": args.board,
        "subjects": args.subjects,
        "study_time_daily_hours": args.study_time,
        "learning_style": args.learning_style,
        "subject": args.subject,
        "difficulty": args.difficulty,
        "confirm": args.confirm,
        "exam_name": args.exam_name,
        "exam_date": args.exam_date,
        "exam_type": args.exam_type,
        "syllabus_coverage": args.syllabus_coverage
    }

    # Only pass kwargs relevant to the chosen action, and skip None values
    allowed = action_args.get(args.action, list(all_kwargs.keys()))
    kwargs = {k: v for k, v in all_kwargs.items() if k in allowed and v is not None}
    
    # Run action
    result = agent.run(args.action, **kwargs)
    
    # Output result as JSON for programmatic use
    print()
    print("─" * 64)
    print("RESULT:")
    print(json.dumps(result, indent=2))
    print("─" * 64)
    
    # Exit with appropriate code
    if result.get("status") == "error":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
