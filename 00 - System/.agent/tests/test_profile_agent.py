#!/usr/bin/env python3
"""
Comprehensive Test Suite for Profile Agent

Tests all workflows:
- First-time onboarding
- Profile updates
- Subject management
- Profile viewing
- Exam management

Run with:
    python test_profile_agent.py
    python -m pytest test_profile_agent.py -v
"""

import sys
import os
import json
import io
import unittest
from pathlib import Path
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add tools directory to path
TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

# Mock the state stores before importing profile_agent
sys.modules['learner_profile_store'] = MagicMock()
sys.modules['exam_calendar_store'] = MagicMock()
sys.modules['activity_log_store'] = MagicMock()

# Now import profile_agent
import profile_agent


class TestProfileAgent(unittest.TestCase):
    """Test suite for Profile Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.agent = profile_agent.ProfileAgent()
        
        # Mock profile store
        self.mock_profile_store = sys.modules['learner_profile_store']
        self.mock_exam_store = sys.modules['exam_calendar_store']
        self.mock_log_store = sys.modules['activity_log_store']
        
        # Enable stores
        profile_agent.STORES_AVAILABLE = True
        
        # Sample profile data
        self.sample_profile = {
            "student_name": "Test Student",
            "student_id": "test-uuid-123",
            "created_at": "2026-03-21T10:00:00Z",
            "updated_at": "2026-03-21T10:00:00Z",
            "current_level": {
                "grade": "12",
                "board": "CBSE",
                "academic_year": "2025-2026"
            },
            "subjects": [
                {
                    "name": "Biology",
                    "difficulty_level": "intermediate",
                    "added_date": "2026-03-21",
                    "mastery_file": "Biology-mastery.json",
                    "revision_file": "Biology-revision-queue.json"
                }
            ],
            "preferences": {
                "learning_style": "visual",
                "study_time_daily_hours": 2.0,
                "difficulty_preference": "progressive"
            },
            "goals": [],
            "strengths": [],
            "weaknesses": [],
            "version": "1.0"
        }
    
    def tearDown(self):
        """Clean up after tests"""
        # Reset mocks completely including side_effect
        self.mock_profile_store.reset_mock()
        self.mock_exam_store.reset_mock()
        self.mock_log_store.reset_mock()
        
        # Clear side_effect to prevent iterator exhaustion
        self.mock_profile_store.get_profile.side_effect = None
        self.mock_profile_store.profile_exists.side_effect = None
        self.mock_exam_store.add_exam.side_effect = None
        self.mock_log_store.log_event.side_effect = None
    
    # ========================================================================
    # TEST WORKFLOW 1: FIRST-TIME ONBOARDING
    # ========================================================================
    
    def test_create_profile_success(self):
        """Test successful profile creation"""
        # Mock profile doesn't exist
        self.mock_profile_store.profile_exists.return_value = False
        self.mock_profile_store.set_profile.return_value = None
        self.mock_log_store.log_event.return_value = "evt-001"
        
        # Create profile
        result = self.agent.create_profile(
            student_name="Ravi Kumar",
            grade="12",
            board="CBSE",
            subjects="Biology,Physics,Chemistry",
            study_time_daily_hours=2.0,
            learning_style="visual"
        )
        
        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Profile created successfully")
        self.assertIn("profile", result)
        self.assertEqual(result["profile"]["student_name"], "Ravi Kumar")
        self.assertEqual(len(result["profile"]["subjects"]), 3)
        
        # Verify stores were called
        self.mock_profile_store.set_profile.assert_called_once()
        self.mock_log_store.log_event.assert_called_once()
    
    def test_create_profile_already_exists(self):
        """Test profile creation when profile already exists"""
        # Mock profile exists
        self.mock_profile_store.profile_exists.return_value = True
        self.mock_profile_store.get_profile.return_value = self.sample_profile
        
        # Attempt to create profile
        result = self.agent.create_profile(
            student_name="New Student",
            grade="11"
        )
        
        # Should return error
        self.assertEqual(result["status"], "error")
        self.assertIn("already exists", result["message"])
        
        # Should not call set_profile
        self.mock_profile_store.set_profile.assert_not_called()
    
    def test_create_profile_with_defaults(self):
        """Test profile creation with default values"""
        # Mock profile doesn't exist
        self.mock_profile_store.profile_exists.return_value = False
        
        # Create profile with minimal data
        result = self.agent.create_profile(
            subjects="Mathematics"
        )
        
        # Should use defaults
        self.assertEqual(result["status"], "success")
        profile = result["profile"]
        self.assertEqual(profile["student_name"], "Student")
        self.assertEqual(profile["preferences"]["learning_style"], "balanced")
        self.assertEqual(profile["preferences"]["study_time_daily_hours"], 2.0)
    
    def test_create_profile_subjects_parsing(self):
        """Test various subject input formats"""
        self.mock_profile_store.profile_exists.return_value = False
        
        # Test comma-separated string
        result = self.agent.create_profile(subjects="Biology, Physics, Chemistry")
        self.assertEqual(len(result["profile"]["subjects"]), 3)
        
        # Test list
        result = self.agent.create_profile(subjects=["Biology", "Physics"])
        self.assertEqual(len(result["profile"]["subjects"]), 2)
        
        # Test with extra spaces
        result = self.agent.create_profile(subjects="  Biology  ,  Physics  ")
        self.assertEqual(len(result["profile"]["subjects"]), 2)
        self.assertEqual(result["profile"]["subjects"][0]["name"], "Biology")
    
    # ========================================================================
    # TEST WORKFLOW 2: SUBJECT MANAGEMENT
    # ========================================================================
    
    def test_add_subject_success(self):
        """Test adding a new subject"""
        # Mock profile exists without Sanskrit
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        self.mock_profile_store.add_subject.return_value = None
        self.mock_log_store.log_event.return_value = "evt-002"
        
        # Add subject
        result = self.agent.add_subject(subject="Sanskrit", difficulty="beginner")
        
        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["subject"], "Sanskrit")
        self.assertEqual(result["difficulty"], "beginner")
        
        # Verify stores were called
        self.mock_profile_store.add_subject.assert_called_once_with("Sanskrit", "beginner")
        self.mock_log_store.log_event.assert_called_once()
    
    def test_add_subject_already_exists(self):
        """Test adding a subject that already exists"""
        # Mock profile with Biology
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        
        # Try to add Biology again
        result = self.agent.add_subject(subject="Biology")
        
        # Should return error
        self.assertEqual(result["status"], "error")
        self.assertIn("already in your profile", result["message"])
        
        # Should not call add_subject
        self.mock_profile_store.add_subject.assert_not_called()
    
    def test_add_subject_no_name(self):
        """Test adding subject without name"""
        result = self.agent.add_subject()
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Subject name required", result["message"])
    
    def test_add_subject_title_case(self):
        """Test subject name is converted to title case"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        self.mock_profile_store.add_subject.return_value = None
        
        # Add subject in lowercase
        result = self.agent.add_subject(subject="sanskrit")
        
        # Should convert to title case
        self.assertEqual(result["subject"], "Sanskrit")
        self.mock_profile_store.add_subject.assert_called_with("Sanskrit", "intermediate")
    
    def test_remove_subject_without_confirmation(self):
        """Test removing subject without confirmation"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        
        # Try to remove without confirm flag
        result = self.agent.remove_subject(subject="Biology", confirm=False)
        
        # Should require confirmation
        self.assertEqual(result["status"], "warning")
        self.assertTrue(result["requires_confirm"])
        
        # Should not call remove_subject
        self.mock_profile_store.remove_subject.assert_not_called()
    
    def test_remove_subject_with_confirmation(self):
        """Test removing subject with confirmation"""
        # Setup mocks - use side_effect for multiple calls
        profile_before = self.sample_profile.copy()
        profile_after = self.sample_profile.copy()
        profile_after["subjects"] = []
        
        # First call returns profile with Biology, second call returns empty subjects
        self.mock_profile_store.get_profile.side_effect = [profile_before, profile_after]
        self.mock_profile_store.remove_subject.return_value = None
        self.mock_log_store.log_event.return_value = "evt-003"
        
        # Remove with confirmation
        result = self.agent.remove_subject(subject="Biology", confirm=True)
        
        # Should succeed
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["subject"], "Biology")
        self.assertTrue(result["archived"])
        
        # Verify stores were called
        self.mock_profile_store.remove_subject.assert_called_once_with("Biology")
        self.mock_log_store.log_event.assert_called_once()
    
    def test_remove_subject_not_in_profile(self):
        """Test removing subject that doesn't exist"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        
        # Try to remove non-existent subject
        result = self.agent.remove_subject(subject="Sanskrit", confirm=True)
        
        # Should return error
        self.assertEqual(result["status"], "error")
        self.assertIn("not in your profile", result["message"])
    
    # ========================================================================
    # TEST WORKFLOW 3: PROFILE VIEWING
    # ========================================================================
    
    def test_view_profile_complete(self):
        """Test viewing complete profile"""
        # Profile with all fields
        complete_profile = self.sample_profile.copy()
        complete_profile["goals"] = [
            {
                "goal_id": "goal-001",
                "description": "Score 95+ in Biology",
                "target_date": "2026-05-15",
                "priority": "high"
            }
        ]
        complete_profile["strengths"] = ["photosynthesis", "cell biology"]
        complete_profile["weaknesses"] = ["genetics"]
        
        self.mock_profile_store.get_profile.return_value = complete_profile
        
        # View profile
        result = self.agent.view_profile()
        
        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["subjects_count"], 1)
        self.assertEqual(result["goals_count"], 1)
        self.assertIn("profile", result)
    
    def test_view_profile_minimal(self):
        """Test viewing minimal profile"""
        minimal_profile = {
            "student_name": "Test",
            "current_level": {"grade": "10", "board": "CBSE"},
            "subjects": [],
            "preferences": {},
            "goals": [],
            "strengths": [],
            "weaknesses": []
        }
        
        self.mock_profile_store.get_profile.return_value = minimal_profile
        
        # View profile
        result = self.agent.view_profile()
        
        # Should succeed even with minimal data
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["subjects_count"], 0)
        self.assertEqual(result["goals_count"], 0)
    
    # ========================================================================
    # TEST WORKFLOW 4: EXAM MANAGEMENT
    # ========================================================================
    
    def test_add_exam_success(self):
        """Test adding exam successfully"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        self.mock_exam_store.add_exam.return_value = "exam-001"
        self.mock_log_store.log_event.return_value = "evt-004"
        
        # Add exam
        exam_data = {
            "subject": "Biology",
            "exam_name": "Board Exam",
            "exam_date": "2026-05-15",
            "exam_type": "board",
            "syllabus_coverage": 1.0
        }
        
        result = self.agent.add_exam(**exam_data)
        
        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["exam_id"], "exam-001")
        self.assertIn("days_remaining", result)
        
        # Verify stores were called
        self.mock_exam_store.add_exam.assert_called_once_with(exam_data)
        self.mock_log_store.log_event.assert_called_once()
    
    def test_add_exam_missing_fields(self):
        """Test adding exam with missing required fields"""
        result = self.agent.add_exam(subject="Biology")
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Missing required fields", result["message"])
    
    def test_add_exam_subject_not_in_profile(self):
        """Test adding exam for subject not in profile"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        
        exam_data = {
            "subject": "Sanskrit",  # Not in profile
            "exam_name": "Test",
            "exam_date": "2026-05-15",
            "exam_type": "board"
        }
        
        result = self.agent.add_exam(**exam_data)
        
        # Should return error
        self.assertEqual(result["status"], "error")
        self.assertIn("not in your profile", result["message"])
        self.assertIn("available_subjects", result)
    
    def test_add_exam_days_remaining_calculation(self):
        """Test days remaining calculation"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        self.mock_exam_store.add_exam.return_value = "exam-001"
        
        # Add exam 30 days in future
        future_date = (date.today() + __import__('datetime').timedelta(days=30)).isoformat()
        
        exam_data = {
            "subject": "Biology",
            "exam_name": "Test",
            "exam_date": future_date,
            "exam_type": "unit_test"
        }
        
        result = self.agent.add_exam(**exam_data)
        
        # Should calculate ~30 days remaining
        self.assertAlmostEqual(result["days_remaining"], 30, delta=1)
    
    # ========================================================================
    # TEST HELPER METHODS
    # ========================================================================
    
    def test_check_profile_exists_true(self):
        """Test checking profile existence when it exists"""
        self.mock_profile_store.profile_exists.return_value = True
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        
        result = self.agent.check_profile_exists()
        
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["exists"])
        self.assertEqual(result["student_name"], "Test Student")
        self.assertEqual(result["subjects_count"], 1)
    
    def test_check_profile_exists_false(self):
        """Test checking profile existence when it doesn't exist"""
        self.mock_profile_store.profile_exists.return_value = False
        
        result = self.agent.check_profile_exists()
        
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["exists"])
        self.assertIn("No profile found", result["message"])
    
    def test_generate_student_id(self):
        """Test student ID generation"""
        student_id = self.agent._generate_student_id()
        
        # Should be a valid UUID string
        self.assertIsInstance(student_id, str)
        self.assertGreater(len(student_id), 30)
        self.assertIn("-", student_id)
    
    def test_now_iso_format(self):
        """Test ISO timestamp generation"""
        timestamp = self.agent._now_iso()
        
        # Should be ISO format with Z suffix
        self.assertTrue(timestamp.endswith("Z"))
        self.assertIn("T", timestamp)
        
        # Should be parseable
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    def test_get_academic_year(self):
        """Test academic year calculation"""
        academic_year = self.agent._get_academic_year()
        
        # Should be in format YYYY-YYYY
        self.assertRegex(academic_year, r"\d{4}-\d{4}")
        
        # Should span consecutive years
        start_year, end_year = academic_year.split("-")
        self.assertEqual(int(end_year), int(start_year) + 1)
    
    def test_calculate_days_remaining(self):
        """Test days remaining calculation"""
        # Test future date (30 days from now)
        future_date = (date.today() + __import__('datetime').timedelta(days=30)).isoformat()
        days = self.agent._calculate_days_remaining(future_date)
        self.assertAlmostEqual(days, 30, delta=1)
        
        # Test past date
        past_date = (date.today() - __import__('datetime').timedelta(days=10)).isoformat()
        days = self.agent._calculate_days_remaining(past_date)
        self.assertLess(days, 0)
        
        # Test today
        today = date.today().isoformat()
        days = self.agent._calculate_days_remaining(today)
        self.assertEqual(days, 0)
    
    # ========================================================================
    # TEST UPDATE PROFILE MENU
    # ========================================================================
    
    def test_update_profile_menu(self):
        """Test profile update menu display"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        
        result = self.agent.update_profile_menu()
        
        # Should return menu options
        self.assertEqual(result["status"], "success")
        self.assertIn("options", result)
        self.assertEqual(len(result["options"]), 8)  # 8 menu options
        
        # Verify option structure
        for option in result["options"]:
            self.assertIn("id", option)
            self.assertIn("action", option)
            self.assertIn("label", option)
    
    # ========================================================================
    # TEST ERROR HANDLING
    # ========================================================================
    
    def test_run_with_invalid_action(self):
        """Test running agent with invalid action"""
        result = self.agent.run("invalid_action")
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown action", result["message"])
    
    def test_run_without_stores(self):
        """Test running agent when stores unavailable"""
        # Disable stores
        profile_agent.STORES_AVAILABLE = False
        
        result = self.agent.run("create")
        
        self.assertEqual(result["status"], "error")
        self.assertIn("State stores not available", result["message"])
        
        # Re-enable for other tests
        profile_agent.STORES_AVAILABLE = True
    
    # ========================================================================
    # TEST INTEGRATION SCENARIOS
    # ========================================================================
    
    def test_complete_onboarding_workflow(self):
        """Test complete onboarding workflow"""
        # Step 1: Check profile doesn't exist
        self.mock_profile_store.profile_exists.return_value = False
        result = self.agent.check_profile_exists()
        self.assertFalse(result["exists"])
        
        # Step 2: Create profile
        self.mock_profile_store.set_profile.return_value = None
        result = self.agent.create_profile(
            student_name="Ravi Kumar",
            grade="12",
            subjects="Biology,Physics"
        )
        self.assertEqual(result["status"], "success")
        
        # Step 3: Profile now exists
        self.mock_profile_store.profile_exists.return_value = True
        result = self.agent.check_profile_exists()
        self.assertTrue(result["exists"])
    
    def test_subject_lifecycle(self):
        """Test complete subject lifecycle: add -> use -> remove"""
        profile = self.sample_profile.copy()
        self.mock_profile_store.get_profile.return_value = profile
        
        # Step 1: Add Sanskrit
        self.mock_profile_store.add_subject.return_value = None
        result = self.agent.add_subject(subject="Sanskrit", difficulty="beginner")
        self.assertEqual(result["status"], "success")
        
        # Step 2: Try to add again (should fail)
        profile["subjects"].append({
            "name": "Sanskrit",
            "difficulty_level": "beginner",
            "added_date": "2026-03-21"
        })
        result = self.agent.add_subject(subject="Sanskrit")
        self.assertEqual(result["status"], "error")
        
        # Step 3: Remove Sanskrit
        self.mock_profile_store.remove_subject.return_value = None
        result = self.agent.remove_subject(subject="Sanskrit", confirm=True)
        self.assertEqual(result["status"], "success")
    
    def test_exam_workflow(self):
        """Test exam addition workflow"""
        self.mock_profile_store.get_profile.return_value = self.sample_profile.copy()
        self.mock_exam_store.add_exam.return_value = "exam-001"
        
        # Add exam for Biology (exists in profile)
        result = self.agent.add_exam(
            subject="Biology",
            exam_name="Board Exam",
            exam_date="2026-05-15",
            exam_type="board"
        )
        
        self.assertEqual(result["status"], "success")
        self.assertIn("next_actions", result)
        self.assertIn("create_revision_plan", result["next_actions"])


class TestProfileAgentCLI(unittest.TestCase):
    """Test command-line interface"""

    def test_check_exists_outputs_json_with_legacy_encoding(self):
        """The startup check produces parseable JSON even with cp1252 stdout."""
        raw = io.BytesIO()
        output = io.TextIOWrapper(raw, encoding="cp1252")
        result = {"status": "success", "exists": True, "student_name": "José"}
        with patch.object(sys, "argv", ["profile_agent.py", "--action", "check-exists"]), \
             patch.object(sys, "stdout", output), \
             patch.object(profile_agent.ProfileAgent, "run", return_value=result):
            with self.assertRaises(SystemExit) as exit_info:
                profile_agent.main()
        output.flush()
        self.assertEqual(exit_info.exception.code, 0)
        self.assertEqual(json.loads(raw.getvalue().decode("cp1252")), result)
    
    def test_cli_help(self):
        """Test CLI help message"""
        # This would test argparse, skipping for now
        pass
    
    def test_cli_action_mapping(self):
        """Test that all CLI actions are mapped"""
        agent = profile_agent.ProfileAgent()
        
        # These actions should be available
        actions = ["create", "update", "add-subject", "remove-subject", "view", "add-exam", "check-exists", "write-card"]
        
        # All should be valid
        for action in actions:
            result = agent.run(action)
            # Should not be "unknown action" error
            if result["status"] == "error":
                self.assertNotIn("Unknown action", result["message"])


class TestStudentCard(unittest.TestCase):
    """Tests for student card generation (unit — no subprocess/vault I/O)."""

    def setUp(self):
        self.agent = profile_agent.ProfileAgent()
        self.full_profile = {
            "student_name": "Priya Sharma",
            "student_id": "abc-123",
            "created_at": "2026-01-15T08:00:00Z",
            "updated_at": "2026-03-20T10:00:00Z",
            "current_level": {
                "grade": "Class 12",
                "board": "CBSE",
                "academic_year": "2025-2026",
            },
            "subjects": [
                {"name": "Physics", "difficulty_level": "intermediate", "added_date": "2026-01-15"},
                {"name": "Chemistry", "difficulty_level": "advanced",    "added_date": "2026-01-15"},
                {"name": "Maths",    "difficulty_level": "beginner",     "added_date": "2026-02-01"},
            ],
            "preferences": {
                "learning_style": "visual",
                "study_time_daily_hours": 3.0,
                "difficulty_preference": "progressive",
            },
            "goals": [
                {"description": "Score 95% in boards", "target_date": "2026-05-15"},
            ],
            "strengths":  ["Problem solving", "Analytical thinking"],
            "weaknesses": ["Organic Chemistry"],
        }

    # ── _build_student_card_content ───────────────────────────────────────────

    def test_content_is_string(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert isinstance(content, str)

    def test_frontmatter_delimiters_present(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert content.count("---") >= 2

    def test_frontmatter_has_tags_block(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "tags:" in content
        assert "- student-card" in content
        assert "- profile" in content

    def test_frontmatter_subject_tags_present(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "- physics" in content
        assert "- chemistry" in content
        assert "- maths" in content

    def test_frontmatter_board_tag(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "- cbse" in content

    def test_frontmatter_metadata_fields(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert 'note_type: student-card' in content
        assert 'student_name: "Priya Sharma"' in content
        assert 'grade: "Class 12"' in content
        assert 'board: "CBSE"' in content

    def test_h1_heading_contains_name(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "# Student Card - Priya Sharma" in content

    def test_board_grade_summary_line(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "**Board:** CBSE" in content
        assert "**Grade:** Class 12" in content

    def test_subjects_table_present(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "## 📚 Subjects" in content
        assert "| Subject |" in content
        assert "| Physics |" in content
        assert "| Chemistry |" in content

    def test_preferences_section(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "## ⚙️ Preferences" in content
        assert "3.0 hours" in content
        assert "Visual" in content

    def test_goals_section(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "## 🎯 Goals" in content
        assert "Score 95% in boards" in content

    def test_strengths_section(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "## 💪 Strengths" in content
        assert "Problem solving" in content

    def test_weaknesses_section(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "## 📈 Areas to Improve" in content
        assert "Organic Chemistry" in content

    def test_empty_goals_section_absent(self):
        profile = {**self.full_profile, "goals": []}
        content = self.agent._build_student_card_content(profile)
        assert "## 🎯 Goals" not in content

    def test_empty_strengths_section_absent(self):
        profile = {**self.full_profile, "strengths": [], "weaknesses": []}
        content = self.agent._build_student_card_content(profile)
        assert "## 💪 Strengths" not in content
        assert "## 📈 Areas to Improve" not in content

    def test_no_subjects_shows_placeholder(self):
        profile = {**self.full_profile, "subjects": []}
        content = self.agent._build_student_card_content(profile)
        assert "*No subjects added yet.*" in content

    def test_difficulty_capitalised_in_table(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert "| Intermediate |" in content or "Intermediate" in content

    def test_academic_year_in_frontmatter(self):
        content = self.agent._build_student_card_content(self.full_profile)
        assert 'academic_year: "2025-2026"' in content

    def test_card_draft_requires_approval(self):
        with patch("subprocess.run") as mock_run:
            result = self.agent.write_student_card(self.full_profile)
        assert result["status"] == "approval_required"
        assert "# Student Card - Priya Sharma" in result["content"]
        mock_run.assert_not_called()

    def test_card_draft_passes_compliance(self):
        from compliance_agent import run_compliance
        content = self.agent._build_student_card_content(self.full_profile)
        result = run_compliance("Student Card - Priya Sharma", content, "dashboard")
        assert result["status"] == "PASS", result

    def test_approved_card_uses_both_gates_then_writer(self):
        responses = [
            {"pass": True, "vault_verdict": "CLEAR"},
            {"status": "PASS"},
            {"path": "card.md", "indexed": True},
        ]
        with tempfile.TemporaryDirectory() as inbox, \
             patch.object(profile_agent, "INBOX_DIR", inbox), \
             patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=json.dumps(r), stderr="", returncode=0) for r in responses
            ]
            result = self.agent.write_student_card(self.full_profile, approved=True)
        assert result["status"] == "success"
        commands = [call.args[0] for call in mock_run.call_args_list]
        assert [Path(cmd[1]).name for cmd in commands] == [
            "fact_checker_agent.py", "compliance_agent.py", "note_writer_agent.py",
        ]
        assert inbox in commands[-1]

    def test_failed_fact_check_stops_before_writing(self):
        response = {"pass": False, "vault_verdict": "CONFLICT"}
        with tempfile.TemporaryDirectory() as inbox, \
             patch.object(profile_agent, "INBOX_DIR", inbox), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=json.dumps(response), stderr="", returncode=0)
            result = self.agent.write_student_card(self.full_profile, approved=True)
        assert result["status"] == "error"
        assert mock_run.call_count == 1

    def test_gate_error_verdict_does_not_pass(self):
        response = {"pass": True, "vault_verdict": "ERROR"}
        with tempfile.TemporaryDirectory() as inbox, \
             patch.object(profile_agent, "INBOX_DIR", inbox), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=json.dumps(response), stderr="", returncode=0)
            result = self.agent.write_student_card(self.full_profile, approved=True)
        assert result["status"] == "error"
        assert mock_run.call_count == 1

    def test_compliance_failure_stops_before_writing(self):
        responses = [{"pass": True, "vault_verdict": "CLEAR"}, {"status": "FAIL"}]
        with tempfile.TemporaryDirectory() as inbox, \
             patch.object(profile_agent, "INBOX_DIR", inbox), \
             patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=json.dumps(r), stderr="", returncode=0) for r in responses
            ]
            result = self.agent.write_student_card(self.full_profile, approved=True)
        assert result["status"] == "error"
        assert mock_run.call_count == 2

    def test_index_failure_is_reported_as_partial(self):
        responses = [
            {"pass": True, "vault_verdict": "CLEAR"},
            {"status": "PASS"},
            {"path": "card.md", "indexed": False},
        ]
        with tempfile.TemporaryDirectory() as inbox, \
             patch.object(profile_agent, "INBOX_DIR", inbox), \
             patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout=json.dumps(r), stderr="", returncode=0) for r in responses
            ]
            result = self.agent.write_student_card(self.full_profile, approved=True)
        assert result["status"] == "partial"
        assert result["path"] == "card.md"

    def test_existing_card_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as inbox, \
             patch.object(profile_agent, "INBOX_DIR", inbox), \
             patch("subprocess.run") as mock_run:
            Path(inbox, "Student Card - Priya Sharma.md").touch()
            result = self.agent.write_student_card(self.full_profile, approved=True)
        assert result["status"] == "error"
        mock_run.assert_not_called()


def run_tests():
    """Run all tests and display results"""
    print("=" * 65)
    print(" " * 20 + "PROFILE AGENT TEST SUITE")
    print("=" * 65)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestProfileAgent))
    suite.addTests(loader.loadTestsFromTestCase(TestProfileAgentCLI))
    suite.addTests(loader.loadTestsFromTestCase(TestStudentCard))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Display summary
    print()
    print("=" * 65)
    print(" " * 25 + "TEST RESULTS")
    print("=" * 65)
    print()
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print()
    
    if result.wasSuccessful():
        print("ALL TESTS PASSED!")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
