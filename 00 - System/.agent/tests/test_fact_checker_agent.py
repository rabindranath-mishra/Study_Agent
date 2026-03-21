"""
Tests for fact_checker_agent.py

Covers:
  - vault_check with empty claims → pass=True, verdict=CLEAR
  - run_tool returns dict
  - CLI: empty claims smoke test (1 subprocess call)
  - CLI: full schema + type + count checks (1 subprocess call, class-scoped fixture)
  - UTF-8 integrity
"""
import sys
import json
import subprocess
import os
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import fact_checker_agent
from paths import PYTHON_EXE

_UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
SCRIPT = str(TOOLS_DIR / "fact_checker_agent.py")


# ── Pure Python (no subprocess) ───────────────────────────────────────────────

class TestVaultCheck:

    def test_empty_claims_returns_pass(self):
        result = fact_checker_agent.vault_check([])
        assert result["pass"] is True
        assert result["violations"] == []
        assert result["verdict"] == "CLEAR"

    def test_empty_claims_zero_checked(self):
        result = fact_checker_agent.vault_check([])
        assert result["claims_checked"] == 0


class TestRunTool:

    def test_classify_task_invocation(self):
        """run_tool should return a dict from a working subprocess."""
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "classify_task.py"), "create a note"]
        result = fact_checker_agent.run_tool(cmd)
        assert isinstance(result, dict)


# ── CLI subprocess tests — 2 calls total via class-scoped fixtures ────────────

@pytest.mark.slow
class TestFactCheckerCLI:
    """
    Two subprocess calls shared across all tests:
      - empty_result: empty claims list (fast, no vault search)
      - full_result: three real claims (exercises vault search path)
    """

    @pytest.fixture(scope="class")
    def empty_result(self):
        return subprocess.run(
            [PYTHON_EXE, SCRIPT, "--claims", "[]"],
            capture_output=True, text=True, encoding="utf-8", env=_UTF8_ENV,
        )

    @pytest.fixture(scope="class")
    def full_result(self):
        claims = ["osmosis is the movement of water", "water is H2O", "A Photograph \u2014 Shirley Toulson is a poem"]
        return subprocess.run(
            [PYTHON_EXE, SCRIPT, "--claims", json.dumps(claims)],
            capture_output=True, text=True, encoding="utf-8", env=_UTF8_ENV,
        )

    @pytest.fixture(scope="class")
    def full_data(self, full_result):
        return json.loads(full_result.stdout)

    # Empty-claims smoke
    def test_empty_claims_exits_zero(self, empty_result):
        assert empty_result.returncode == 0, f"stderr: {empty_result.stderr}"

    def test_empty_claims_pass_true(self, empty_result):
        data = json.loads(empty_result.stdout)
        assert data["pass"] is True

    # Full schema from one shared call
    def test_output_is_valid_json(self, full_result):
        try:
            json.loads(full_result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Not valid JSON: {e}")

    def test_schema_keys_present(self, full_data):
        for key in ("claims_checked", "pass", "violations", "vault_verdict", "web_checked"):
            assert key in full_data, f"Missing key: {key}"

    def test_claims_checked_count(self, full_data):
        assert full_data["claims_checked"] == 3

    def test_vault_verdict_is_valid(self, full_data):
        assert full_data["vault_verdict"] in ("CLEAR", "REVIEW", "CONFLICT")

    def test_violations_is_list(self, full_data):
        assert isinstance(full_data["violations"], list)

    def test_web_checked_is_bool(self, full_data):
        assert isinstance(full_data["web_checked"], bool)

    def test_utf8_encoding_intact(self, full_result):
        """Em-dash claim must not produce encoding corruption in output."""
        assert full_result.returncode in (0, 1)
        full_result.stdout.encode("utf-8")  # must not raise
        assert "â€" not in full_result.stdout, "Latin-1 double-encoded em-dash found"

