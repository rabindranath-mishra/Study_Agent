"""
Tests for archive_and_reset.py

Covers:
  - find_markdown_files: finds .md files in correct folders
  - find_markdown_files: skips folders that do not exist
  - find_markdown_files: skips folders that exist but contain no .md files
  - find_markdown_files: finds .md files in nested subdirectories
  - find_markdown_files: never returns non-.md files
  - archive_files: dry-run prints intent without moving files
  - archive_files: live run moves files preserving directory structure
  - archive_files: live run creates archive batch folder with today's date
  - archive_files: returned move count matches number of files
  - archive_files: handles multiple source folders in one batch
  - reindex_vault: dry-run returns True without calling subprocess
  - reindex_vault: live run calls subprocess with python + index_vault.py (no extra args)
  - reindex_vault: returns False when python exe is missing
  - reindex_vault: returns False when subprocess exits non-zero
  - reindex_vault: returns False on TimeoutExpired
  - SOURCE_FOLDERS: matches actual Study Agent vault layout
"""

import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest

# ---------------------------------------------------------------------------
# Path bootstrap — import the module under test
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import archive_and_reset as aar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_md_file(directory: Path, name: str, content: str = "# Test") -> Path:
    """Create a markdown file inside *directory*, creating parents as needed."""
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# SOURCE_FOLDERS contract
# ---------------------------------------------------------------------------

class TestSourceFolders:

    EXPECTED = {
        "01 - Inbox",
        "02 - Sources",
        "03 - Subjects",
        "04 - Concepts",
        "05 - Practice",
        "06 - Plans",
        "07 - Outputs",
    }

    def test_contains_all_expected_study_agent_folders(self):
        assert set(aar.SOURCE_FOLDERS) == self.EXPECTED

    def test_does_not_contain_legacy_folder_research(self):
        assert "03 - Research" not in aar.SOURCE_FOLDERS

    def test_does_not_contain_legacy_folder_evergreen(self):
        assert "04 - Evergreen" not in aar.SOURCE_FOLDERS

    def test_does_not_contain_legacy_folder_maps(self):
        assert "05 - Maps" not in aar.SOURCE_FOLDERS

    def test_does_not_contain_legacy_folder_projects(self):
        assert "06 - Projects" not in aar.SOURCE_FOLDERS

    def test_does_not_contain_legacy_folder_writing(self):
        assert "07 - Writing" not in aar.SOURCE_FOLDERS

    def test_includes_inbox(self):
        assert "01 - Inbox" in aar.SOURCE_FOLDERS

    def test_does_not_include_templates(self):
        assert "08 - Templates" not in aar.SOURCE_FOLDERS


# ---------------------------------------------------------------------------
# find_markdown_files
# ---------------------------------------------------------------------------

class TestFindMarkdownFiles:

    def test_finds_md_files_in_existing_folder(self, tmp_path):
        make_md_file(tmp_path / "02 - Sources", "note.md")
        result = aar.find_markdown_files(["02 - Sources"], vault_root=str(tmp_path))
        assert "02 - Sources" in result
        assert len(result["02 - Sources"]) == 1

    def test_skips_missing_folders(self, tmp_path):
        result = aar.find_markdown_files(["02 - Sources", "03 - Subjects"], vault_root=str(tmp_path))
        assert result == {}

    def test_skips_folder_with_no_md_files(self, tmp_path):
        folder = tmp_path / "04 - Concepts"
        folder.mkdir()
        (folder / "image.png").write_bytes(b"")
        result = aar.find_markdown_files(["04 - Concepts"], vault_root=str(tmp_path))
        assert result == {}

    def test_finds_md_files_in_nested_subdirectory(self, tmp_path):
        make_md_file(tmp_path / "04 - Concepts" / "Biology" / "sub", "deep.md")
        result = aar.find_markdown_files(["04 - Concepts"], vault_root=str(tmp_path))
        assert "04 - Concepts" in result
        assert any(p.name == "deep.md" for p in result["04 - Concepts"])

    def test_does_not_return_non_md_files(self, tmp_path):
        folder = tmp_path / "05 - Practice"
        folder.mkdir()
        make_md_file(folder, "quiz.md")
        (folder / "quiz.pdf").write_bytes(b"")
        result = aar.find_markdown_files(["05 - Practice"], vault_root=str(tmp_path))
        for f in result["05 - Practice"]:
            assert f.suffix == ".md"

    def test_handles_multiple_folders(self, tmp_path):
        make_md_file(tmp_path / "02 - Sources", "src.md")
        make_md_file(tmp_path / "04 - Concepts", "concept.md")
        result = aar.find_markdown_files(["02 - Sources", "04 - Concepts"], vault_root=str(tmp_path))
        assert "02 - Sources" in result
        assert "04 - Concepts" in result

    def test_returns_empty_dict_when_all_folders_missing(self, tmp_path):
        result = aar.find_markdown_files(aar.SOURCE_FOLDERS, vault_root=str(tmp_path))
        assert result == {}


# ---------------------------------------------------------------------------
# archive_files
# ---------------------------------------------------------------------------

class TestArchiveFiles:

    def _make_vault_with_files(self, tmp_path):
        """Create a minimal vault with one file per content folder."""
        vault = tmp_path / "vault"
        make_md_file(vault / "02 - Sources", "source.md")
        make_md_file(vault / "04 - Concepts", "concept.md")
        return vault

    def test_dry_run_does_not_move_files(self, tmp_path, capsys):
        vault = self._make_vault_with_files(tmp_path)
        files = aar.find_markdown_files(["02 - Sources", "04 - Concepts"], vault_root=str(vault))

        aar.archive_files(files, dry_run=True,
                          vault_root=str(vault), archive_root=str(vault / "99 - Archive"))

        assert (vault / "02 - Sources" / "source.md").exists()
        assert (vault / "04 - Concepts" / "concept.md").exists()

    def test_dry_run_prints_dry_run_prefix(self, tmp_path, capsys):
        vault = self._make_vault_with_files(tmp_path)
        files = aar.find_markdown_files(["02 - Sources"], vault_root=str(vault))

        aar.archive_files(files, dry_run=True,
                          vault_root=str(vault), archive_root=str(vault / "99 - Archive"))

        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out

    def test_live_run_moves_files(self, tmp_path):
        vault = self._make_vault_with_files(tmp_path)
        files = aar.find_markdown_files(["02 - Sources"], vault_root=str(vault))

        aar.archive_files(files, dry_run=False,
                          vault_root=str(vault), archive_root=str(vault / "99 - Archive"))

        assert not (vault / "02 - Sources" / "source.md").exists()

    def test_live_run_preserves_directory_structure(self, tmp_path):
        vault = tmp_path / "vault"
        make_md_file(vault / "04 - Concepts" / "Biology", "cells.md")
        files = aar.find_markdown_files(["04 - Concepts"], vault_root=str(vault))

        archive_dir = vault / "99 - Archive"
        _, batch = aar.archive_files(files, dry_run=False,
                                     vault_root=str(vault), archive_root=str(archive_dir))

        archived = batch / "04 - Concepts" / "Biology" / "cells.md"
        assert archived.exists()

    def test_live_run_archive_batch_contains_todays_date(self, tmp_path):
        vault = self._make_vault_with_files(tmp_path)
        files = aar.find_markdown_files(["02 - Sources"], vault_root=str(vault))
        today = datetime.now().strftime("%Y-%m-%d")

        archive_dir = vault / "99 - Archive"
        _, batch = aar.archive_files(files, dry_run=False,
                                     vault_root=str(vault), archive_root=str(archive_dir))

        assert today in batch.name

    def test_move_count_matches_file_count(self, tmp_path):
        vault = self._make_vault_with_files(tmp_path)
        make_md_file(vault / "02 - Sources", "extra.md")
        files = aar.find_markdown_files(["02 - Sources", "04 - Concepts"], vault_root=str(vault))
        total = sum(len(v) for v in files.values())

        count, _ = aar.archive_files(files, dry_run=False,
                                     vault_root=str(vault), archive_root=str(vault / "99 - Archive"))

        assert count == total

    def test_dry_run_move_count_matches_file_count(self, tmp_path):
        vault = self._make_vault_with_files(tmp_path)
        files = aar.find_markdown_files(["02 - Sources", "04 - Concepts"], vault_root=str(vault))
        total = sum(len(v) for v in files.values())

        count, _ = aar.archive_files(files, dry_run=True,
                                     vault_root=str(vault), archive_root=str(vault / "99 - Archive"))

        assert count == total


# ---------------------------------------------------------------------------
# reindex_vault
# ---------------------------------------------------------------------------

class TestReindexVault:

    def test_dry_run_returns_true_without_subprocess(self, capsys):
        with patch("subprocess.run") as mock_run:
            result = aar.reindex_vault(dry_run=True)
        assert result is True
        mock_run.assert_not_called()

    def test_dry_run_prints_dry_run_message(self, capsys):
        aar.reindex_vault(dry_run=True)
        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out

    def test_live_run_calls_python_and_index_script_only(self, tmp_path):
        """subprocess must be called with exactly [python_exe, index_script] — no extra args."""
        fake_py = tmp_path / "python.exe"
        fake_py.write_bytes(b"")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch.object(aar, "PYTHON_EXE", str(fake_py)), \
             patch("subprocess.run", return_value=mock_result) as mock_run:
            aar.reindex_vault(dry_run=False)

        args_called = mock_run.call_args[0][0]
        assert len(args_called) == 2, (
            f"subprocess called with {len(args_called)} args (expected 2): {args_called}"
        )
        assert args_called[0] == str(fake_py)
        assert args_called[1].endswith("index_vault.py")

    def test_live_run_returns_true_on_success(self, tmp_path):
        fake_py = tmp_path / "python.exe"
        fake_py.write_bytes(b"")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "indexed 42 passages"

        with patch.object(aar, "PYTHON_EXE", str(fake_py)), \
             patch("subprocess.run", return_value=mock_result):
            result = aar.reindex_vault(dry_run=False)

        assert result is True

    def test_live_run_returns_false_when_python_missing(self, tmp_path):
        with patch.object(aar, "PYTHON_EXE", str(tmp_path / "missing_python.exe")):
            result = aar.reindex_vault(dry_run=False)
        assert result is False

    def test_live_run_returns_false_on_non_zero_exit(self, tmp_path):
        fake_py = tmp_path / "python.exe"
        fake_py.write_bytes(b"")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "some error"

        with patch.object(aar, "PYTHON_EXE", str(fake_py)), \
             patch("subprocess.run", return_value=mock_result):
            result = aar.reindex_vault(dry_run=False)

        assert result is False

    def test_live_run_returns_false_on_timeout(self, tmp_path):
        fake_py = tmp_path / "python.exe"
        fake_py.write_bytes(b"")

        with patch.object(aar, "PYTHON_EXE", str(fake_py)), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=300)):
            result = aar.reindex_vault(dry_run=False)

        assert result is False

    def test_live_run_returns_false_on_unexpected_exception(self, tmp_path):
        fake_py = tmp_path / "python.exe"
        fake_py.write_bytes(b"")

        with patch.object(aar, "PYTHON_EXE", str(fake_py)), \
             patch("subprocess.run", side_effect=OSError("permission denied")):
            result = aar.reindex_vault(dry_run=False)

        assert result is False


# ---------------------------------------------------------------------------
# main() integration (via sys.argv patching)
# ---------------------------------------------------------------------------

class TestMain:

    def test_main_exits_0_when_no_files_to_archive(self, tmp_path):
        with patch("sys.argv", ["archive_and_reset.py"]), \
             patch.object(aar, "_VAULT_PATH", tmp_path), \
             patch.object(aar, "_ARCHIVE_PATH", tmp_path / "99 - Archive"):
            with pytest.raises(SystemExit) as exc:
                aar.main()
        assert exc.value.code == 0

    def test_main_dry_run_does_not_move_files(self, tmp_path):
        make_md_file(tmp_path / "04 - Concepts", "note.md")

        with patch("sys.argv", ["archive_and_reset.py", "--dry-run"]), \
             patch.object(aar, "_VAULT_PATH", tmp_path), \
             patch.object(aar, "_ARCHIVE_PATH", tmp_path / "99 - Archive"):
            aar.main()

        assert (tmp_path / "04 - Concepts" / "note.md").exists()

    def test_main_yes_flag_skips_prompt_and_moves_files(self, tmp_path):
        make_md_file(tmp_path / "04 - Concepts", "note.md")

        mock_reindex = MagicMock(return_value=True)
        with patch("sys.argv", ["archive_and_reset.py", "--yes"]), \
             patch.object(aar, "_VAULT_PATH", tmp_path), \
             patch.object(aar, "_ARCHIVE_PATH", tmp_path / "99 - Archive"), \
             patch.object(aar, "reindex_vault", mock_reindex):
            aar.main()

        assert not (tmp_path / "04 - Concepts" / "note.md").exists()
        mock_reindex.assert_called_once()

    def test_main_live_without_yes_prompts_and_cancels(self, tmp_path):
        make_md_file(tmp_path / "04 - Concepts", "note.md")

        with patch("sys.argv", ["archive_and_reset.py"]), \
             patch.object(aar, "_VAULT_PATH", tmp_path), \
             patch.object(aar, "_ARCHIVE_PATH", tmp_path / "99 - Archive"), \
             patch("builtins.input", return_value="no"):
            with pytest.raises(SystemExit) as exc:
                aar.main()

        assert exc.value.code == 0
        assert (tmp_path / "04 - Concepts" / "note.md").exists()

    def test_main_result_includes_vault_root(self, tmp_path, capsys):
        with patch("sys.argv", ["archive_and_reset.py", "--dry-run"]), \
             patch.object(aar, "_VAULT_PATH", tmp_path), \
             patch.object(aar, "_ARCHIVE_PATH", tmp_path / "99 - Archive"):
            with pytest.raises(SystemExit):
                aar.main()

        captured = capsys.readouterr()
        assert str(tmp_path) in captured.out
