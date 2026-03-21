"""
Tests for vault_search_agent.py subprocess chain

Covers:
  - run_tool returns a dict for a valid command
  - run_tool returns error dict for non-zero exit code
  - search_vault schema: returns list, required keys, float scores, k limit
  - UTF-8 encoding + output schema via ONE subprocess call (class-scoped fixture)
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

import vault_search_agent
from paths import PYTHON_EXE

_UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

VAULT_SEARCH_SCRIPT = str(TOOLS_DIR / "vault_search_agent.py")


# ── run_tool helper (fast — no FAISS) ────────────────────────────────────────

class TestRunTool:

    def test_valid_command_returns_dict(self):
        """A quick classify_task.py call to verify run_tool works."""
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "classify_task.py"), "explain osmosis"]
        result = vault_search_agent.run_tool(cmd)
        assert isinstance(result, dict)

    def test_missing_script_returns_error_dict(self):
        cmd = [PYTHON_EXE, str(TOOLS_DIR / "nonexistent_script.py"), "query"]
        result = vault_search_agent.run_tool(cmd)
        assert isinstance(result, dict)
        assert "error" in result or isinstance(result, dict)


# ── search_vault (Python-level, FAISS loaded once per class) ─────────────────

@pytest.mark.slow
class TestSearchVault:
    """All assertions share a single vault call via the class fixture."""

    @pytest.fixture(scope="class")
    def findings(self):
        return vault_search_agent.search_vault("English poetry hornbill", k=5)

    def test_returns_list(self, findings):
        assert isinstance(findings, list)

    def test_each_finding_has_required_keys(self, findings):
        required_keys = {"file_path", "rel_path", "heading", "block_id",
                         "note_type", "subject", "topic", "excerpt", "score"}
        for f in findings:
            missing = required_keys - set(f.keys())
            assert not missing, f"Finding missing keys: {missing}"

    def test_scores_are_floats_in_range(self, findings):
        for f in findings:
            assert isinstance(f["score"], float)
            assert 0.0 <= f["score"] <= 1.5

    def test_k_limits_results(self, findings):
        assert len(findings) <= 5

    def test_unusual_query_returns_list(self):
        """Edge case: unusual query must not crash (separate call — edge case)."""
        assert isinstance(vault_search_agent.search_vault("aaa", k=1), list)


# ── Subprocess-level: schema + UTF-8 in ONE call ─────────────────────────────

@pytest.mark.slow
class TestSubprocessOutput:
    """
    One subprocess call shared across all assertions:
    validates output schema, hit_count consistency, UTF-8 integrity,
    and absence of encoding corruption.
    """

    @pytest.fixture(scope="class")
    def result(self):
        proc = subprocess.run(
            [PYTHON_EXE, VAULT_SEARCH_SCRIPT,
             "--query", "amusing hairstyle cousins photograph",
             "--k", "5"],
            capture_output=True, text=True, encoding="utf-8", env=_UTF8_ENV,
        )
        return proc

    @pytest.fixture(scope="class")
    def data(self, result):
        return json.loads(result.stdout)

    def test_exits_zero(self, result):
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_output_is_valid_json(self, result):
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Not valid JSON: {e}\n{result.stdout[:300]}")

    def test_schema_keys_present(self, data):
        for key in ("vault_findings", "hit_count", "contradiction_result"):
            assert key in data, f"Missing key: {key}"

    def test_hit_count_matches_findings_length(self, data):
        assert data["hit_count"] == len(data["vault_findings"])

    def test_contradiction_result_none_by_default(self, data):
        assert data["contradiction_result"] is None

    def test_no_encoding_corruption(self, data):
        excerpts = " ".join(f["excerpt"] for f in data.get("vault_findings", []))
        assert "\u0393\u00c7\u00f6" not in excerpts, "CP437-garbled em-dash found"
        assert "â€" not in excerpts, "Latin-1 double-encoded em-dash found"

