"""
Tests for paths.py

Covers:
  - VAULT_ROOT is a string pointing to the vault root directory
  - VAULT_ROOT contains expected vault folders
  - FAISS_STORE path is under .agent
  - STATE_DIR is under .agent
  - LOGS_DIR is under .agent
  - PYTHON_EXE points to venv python
  - All paths are absolute (not relative)
  - All vault folder constants are under VAULT_ROOT
"""
import sys
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import paths


class TestPaths:

    def test_vault_root_is_string(self):
        assert isinstance(paths.VAULT_ROOT, str)

    def test_vault_root_is_absolute(self):
        assert Path(paths.VAULT_ROOT).is_absolute()

    def test_vault_root_exists(self):
        assert Path(paths.VAULT_ROOT).exists(), f"VAULT_ROOT does not exist: {paths.VAULT_ROOT}"

    def test_vault_root_contains_system_dir(self):
        """00 - System must exist under VAULT_ROOT."""
        system = Path(paths.VAULT_ROOT) / "00 - System"
        assert system.exists(), f"'00 - System' not found under VAULT_ROOT"

    def test_faiss_store_under_agent(self):
        faiss = Path(paths.FAISS_STORE)
        agent = Path(paths.VAULT_ROOT) / "00 - System" / ".agent"
        assert str(faiss).startswith(str(agent))

    def test_state_dir_under_agent(self):
        state = Path(paths.STATE_DIR)
        agent = Path(paths.VAULT_ROOT) / "00 - System" / ".agent"
        assert str(state).startswith(str(agent))

    def test_logs_dir_under_agent(self):
        logs = Path(paths.LOGS_DIR)
        agent = Path(paths.VAULT_ROOT) / "00 - System" / ".agent"
        assert str(logs).startswith(str(agent))

    def test_python_exe_under_venv(self):
        assert "venv" in paths.PYTHON_EXE

    def test_all_vault_folders_under_root(self):
        vault = Path(paths.VAULT_ROOT)
        folder_constants = [
            paths.INBOX_DIR, paths.SOURCES_DIR, paths.SUBJECTS_DIR,
            paths.CONCEPTS_DIR, paths.PRACTICE_DIR, paths.PLANS_DIR,
            paths.OUTPUTS_DIR, paths.TEMPLATES_DIR, paths.ARCHIVE_DIR,
        ]
        for folder in folder_constants:
            assert str(folder).startswith(str(vault)), f"{folder} is not under VAULT_ROOT"

    def test_concepts_dir_number(self):
        assert "04" in paths.CONCEPTS_DIR

    def test_practice_dir_number(self):
        assert "05" in paths.PRACTICE_DIR

    def test_plans_dir_number(self):
        assert "06" in paths.PLANS_DIR

    def test_sources_dir_number(self):
        assert "02" in paths.SOURCES_DIR

    def test_inbox_dir_number(self):
        assert "01" in paths.INBOX_DIR

    def test_archive_dir_number(self):
        assert "99" in paths.ARCHIVE_DIR

    def test_session_log_under_logs(self):
        assert str(paths.SESSION_LOG).startswith(paths.LOGS_DIR)

    def test_ps_script_create_note_exists(self):
        assert Path(paths.PS_SCRIPT_CREATE_NOTE).exists(), "create_note_stdin.ps1 not found"

    def test_tools_dir_derivable(self):
        """tools dir = VAULT_ROOT / 00 - System / .agent / tools"""
        expected = Path(paths.VAULT_ROOT) / "00 - System" / ".agent" / "tools"
        assert expected.exists()
