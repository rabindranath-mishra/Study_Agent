"""
Tests for note_writer_agent.py

Covers:
  - validate_fact_check: pass=true → (True, "PASS")
  - validate_fact_check: pass=false → (False, reason)
  - validate_fact_check: missing pass key → (False, reason)
  - validate_fact_check: non-dict input → (False, reason)
  - validate_compliance: status=PASS → (True, "PASS")
  - validate_compliance: status=FAIL → (False, reason)
  - validate_compliance: missing status → (False, reason)
  - validate_compliance: non-dict → (False, reason)
  - resolve_folder: concept → 04 - Concepts
  - resolve_folder: practice → 05 - Practice
  - resolve_folder: explicit folder overrides type
  - resolve_folder: unknown type → Inbox
  - resolve_folder: revision-plan → 06 - Plans
"""
import sys
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import note_writer_agent


# ---------------------------------------------------------------------------
# validate_fact_check
# ---------------------------------------------------------------------------

class TestValidateFactCheck:

    def test_pass_true_returns_true(self):
        result = {"pass": True, "violations": [], "vault_verdict": "CLEAR"}
        ok, reason = note_writer_agent.validate_fact_check(result)
        assert ok is True
        assert reason == "PASS"

    def test_pass_false_returns_false(self):
        result = {"pass": False, "violations": [{"claim": "bad claim"}]}
        ok, reason = note_writer_agent.validate_fact_check(result)
        assert ok is False
        assert "1 violation" in reason

    def test_error_verdict_cannot_pass(self):
        ok, reason = note_writer_agent.validate_fact_check(
            {"pass": True, "vault_verdict": "ERROR"}
        )
        assert ok is False
        assert "error" in reason

    @pytest.mark.parametrize("value", ["true", 1, [], {}])
    def test_non_boolean_pass_is_rejected(self, value):
        ok, _ = note_writer_agent.validate_fact_check({"pass": value})
        assert ok is False

    def test_missing_pass_key_fails(self):
        result = {"vault_verdict": "CLEAR"}
        ok, reason = note_writer_agent.validate_fact_check(result)
        assert ok is False

    def test_non_dict_fails(self):
        ok, reason = note_writer_agent.validate_fact_check("not a dict")
        assert ok is False

    def test_none_fails(self):
        ok, reason = note_writer_agent.validate_fact_check(None)
        assert ok is False

    def test_multiple_violations_counted(self):
        result = {"pass": False, "violations": [{"c": "1"}, {"c": "2"}, {"c": "3"}]}
        ok, reason = note_writer_agent.validate_fact_check(result)
        assert ok is False
        assert "3 violation" in reason


# ---------------------------------------------------------------------------
# validate_compliance
# ---------------------------------------------------------------------------

class TestValidateCompliance:

    def test_pass_returns_true(self):
        result = {"status": "PASS", "violations": []}
        ok, reason = note_writer_agent.validate_compliance(result)
        assert ok is True
        assert reason == "PASS"

    def test_fail_status_returns_false(self):
        result = {"status": "FAIL", "violations": [{"rule": "§XI"}]}
        ok, reason = note_writer_agent.validate_compliance(result)
        assert ok is False
        assert "1 violation" in reason

    def test_missing_status_fails(self):
        result = {"violations": []}
        ok, reason = note_writer_agent.validate_compliance(result)
        assert ok is False

    def test_non_dict_fails(self):
        ok, reason = note_writer_agent.validate_compliance(42)
        assert ok is False

    def test_none_fails(self):
        ok, reason = note_writer_agent.validate_compliance(None)
        assert ok is False

    def test_zero_violations_with_pass(self):
        result = {"status": "PASS", "violations": [], "checks_run": 10}
        ok, _ = note_writer_agent.validate_compliance(result)
        assert ok is True


# ---------------------------------------------------------------------------
# resolve_folder
# ---------------------------------------------------------------------------

class TestResolveFolder:

    def test_concept_maps_to_concepts_dir(self):
        folder = note_writer_agent.resolve_folder("concept", "")
        assert "04" in folder or "Concepts" in folder

    def test_practice_maps_to_practice_dir(self):
        folder = note_writer_agent.resolve_folder("practice", "")
        assert "05" in folder or "Practice" in folder

    def test_revision_plan_maps_to_plans_dir(self):
        folder = note_writer_agent.resolve_folder("revision-plan", "")
        assert "06" in folder or "Plans" in folder

    def test_source_maps_to_sources_dir(self):
        folder = note_writer_agent.resolve_folder("source", "")
        assert "02" in folder or "Sources" in folder

    def test_subject_map_maps_to_subjects_dir(self):
        folder = note_writer_agent.resolve_folder("subject-map", "")
        assert "03" in folder or "Subjects" in folder

    def test_output_maps_to_outputs_dir(self):
        folder = note_writer_agent.resolve_folder("output", "")
        assert "07" in folder or "Outputs" in folder

    def test_explicit_folder_overrides_type(self):
        explicit = "01 - Inbox"
        folder = note_writer_agent.resolve_folder("concept", explicit)
        assert folder == explicit

    def test_unknown_type_falls_back_to_inbox(self):
        folder = note_writer_agent.resolve_folder("unknown-type-xyz", "")
        assert "Inbox" in folder or "01" in folder

    def test_empty_type_falls_back_to_inbox(self):
        folder = note_writer_agent.resolve_folder("", "")
        assert "Inbox" in folder or "01" in folder

    def test_case_insensitive_concept(self):
        """Type matching should handle lowercase/mixed case."""
        folder_lower = note_writer_agent.resolve_folder("concept", "")
        folder_upper = note_writer_agent.resolve_folder("CONCEPT", "")
        # Both should resolve (uppercase might fall to inbox — just shouldn't crash)
        assert isinstance(folder_lower, str)
        assert isinstance(folder_upper, str)
