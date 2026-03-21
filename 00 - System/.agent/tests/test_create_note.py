"""
Tests for create_note.py

Covers:
  - normalise_tags: inline array → block list
  - normalise_tags: already block list → unchanged
  - normalise_tags: no tags field → unchanged
  - normalise_tags: only inside frontmatter, body left alone
  - BOM stripped from content before write
  - No double-frontmatter when content already has ---
  - Fallback frontmatter injected when content lacks ---
  - File written as UTF-8 (em-dash survives)
  - Folder routing (explicit folder wins)
  - Duplicate filename counter
  - Correct filename from title
"""
import sys
import json
import tempfile
import shutil
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import create_note


# ---------------------------------------------------------------------------
# normalise_tags
# ---------------------------------------------------------------------------

class TestNormaliseTags:

    def test_inline_array_converted_to_block_list(self):
        content = "---\ntype: concept\ntags: [english, poetry, class-11]\n---\n# Title\n"
        result = create_note.normalise_tags(content)
        assert "tags:" in result
        assert "  - english" in result
        assert "  - poetry" in result
        assert "  - class-11" in result
        assert "[english" not in result

    def test_already_block_list_unchanged(self):
        content = "---\ntype: concept\ntags:\n  - english\n  - poetry\n---\n# Title\n"
        result = create_note.normalise_tags(content)
        assert result == content

    def test_no_tags_field_unchanged(self):
        content = "---\ntype: concept\nsubject: English\n---\n# Title\n"
        result = create_note.normalise_tags(content)
        assert result == content

    def test_tags_only_normalised_inside_frontmatter(self):
        """Body text containing tags: [...] must not be modified."""
        content = (
            "---\ntype: concept\ntags: [english]\n---\n"
            "# Title\n\nSee tags: [note1, note2] for more.\n"
        )
        result = create_note.normalise_tags(content)
        assert "  - english" in result
        # Body reference must survive intact
        assert "tags: [note1, note2]" in result

    def test_multiple_tags_all_present(self):
        tags = "english, poetry, hornbill, class-11, cbse"
        content = f"---\ntype: concept\ntags: [{tags}]\n---\n# Title\n"
        result = create_note.normalise_tags(content)
        for tag in ["english", "poetry", "hornbill", "class-11", "cbse"]:
            assert f"  - {tag}" in result

    def test_no_frontmatter_returns_unchanged(self):
        content = "# Just a heading\n\nSome text."
        result = create_note.normalise_tags(content)
        assert result == content

    def test_quoted_tags_stripped(self):
        content = '---\ntype: concept\ntags: ["english", "poetry"]\n---\n# Title\n'
        result = create_note.normalise_tags(content)
        assert "  - english" in result
        assert '"english"' not in result


# ---------------------------------------------------------------------------
# create_note (disk I/O tests use a temp vault)
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_vault(tmp_path):
    """A temporary vault directory."""
    return str(tmp_path)


class TestCreateNote:

    def test_bom_stripped_before_write(self, tmp_vault):
        """BOM prepended by PowerShell must not appear in the saved file."""
        content = "\ufeff---\ntype: concept\nsubject: English\ngenerated_by: StudyAgent\n---\n# My Note\n\nBody.\n"
        path = create_note.create_note(tmp_vault, "My Note", content)
        saved = Path(path).read_text(encoding="utf-8")
        assert not saved.startswith("\ufeff"), "BOM should be stripped"
        assert saved.startswith("---"), "Frontmatter should start immediately"

    def test_no_double_frontmatter(self, tmp_vault):
        """Content that already has --- must not get a second frontmatter injected."""
        content = "---\ntype: concept\nsubject: English\ngenerated_by: StudyAgent\n---\n# My Note\n\nBody.\n"
        path = create_note.create_note(tmp_vault, "My Note", content)
        saved = Path(path).read_text(encoding="utf-8")
        # Count frontmatter delimiters — should be exactly 2 (opening + closing ---)
        delimiters = [i for i, line in enumerate(saved.splitlines()) if line.strip() == "---"]
        assert len(delimiters) == 2, f"Expected 2 '---' delimiters, found {len(delimiters)}"

    def test_bom_plus_frontmatter_no_double_block(self, tmp_vault):
        """BOM + existing frontmatter must result in exactly one frontmatter block."""
        content = "\ufeff---\ntype: concept\nsubject: English\ngenerated_by: StudyAgent\n---\n# Note\n\nBody.\n"
        path = create_note.create_note(tmp_vault, "Note", content)
        saved = Path(path).read_text(encoding="utf-8")
        delimiters = [line for line in saved.splitlines() if line.strip() == "---"]
        assert len(delimiters) == 2

    def test_fallback_frontmatter_added_when_missing(self, tmp_vault):
        """Content without frontmatter should get title + date block prepended."""
        content = "# Simple Note\n\nJust some text.\n"
        path = create_note.create_note(tmp_vault, "Simple Note", content)
        saved = Path(path).read_text(encoding="utf-8")
        assert saved.startswith("---"), "Fallback frontmatter should be prepended"
        assert "title:" in saved

    def test_utf8_emdash_survives_write(self, tmp_vault):
        """Em-dash in content must be preserved in the written file."""
        content = "---\ntype: concept\nsubject: English\ngenerated_by: StudyAgent\n---\n# Note\n\nTransience \u2014 time.\n"
        path = create_note.create_note(tmp_vault, "Note", content)
        saved = Path(path).read_text(encoding="utf-8")
        assert "\u2014" in saved, "Em-dash (U+2014) should survive the write"

    def test_explicit_folder_used(self, tmp_vault):
        """When --folder is passed, note lands in that subfolder."""
        folder = "04 - Concepts"
        content = "---\ntype: concept\nsubject: English\ngenerated_by: StudyAgent\n---\n# Folder Note\n\nBody.\n"
        path = create_note.create_note(tmp_vault, "Folder Note", content, folder=folder)
        assert "04 - Concepts" in path

    def test_tags_normalised_in_written_file(self, tmp_vault):
        """Inline tag array in content must become block list in the saved file."""
        content = "---\ntype: concept\ntags: [english, poetry]\nsubject: English\ngenerated_by: StudyAgent\n---\n# Tag Note\n\nBody.\n"
        path = create_note.create_note(tmp_vault, "Tag Note", content)
        saved = Path(path).read_text(encoding="utf-8")
        assert "  - english" in saved
        assert "  - poetry" in saved
        assert "[english" not in saved

    def test_duplicate_filename_counter(self, tmp_vault):
        """Second note with same title must get a -1 suffix."""
        content = "---\ntype: concept\nsubject: English\ngenerated_by: StudyAgent\n---\n# Dup Note\n\nBody.\n"
        path1 = create_note.create_note(tmp_vault, "Dup Note", content)
        path2 = create_note.create_note(tmp_vault, "Dup Note", content)
        assert path1 != path2
        assert "-1" in Path(path2).name

    def test_file_written_as_utf8(self, tmp_vault):
        """File must be saved in UTF-8 (verify via raw bytes)."""
        content = "---\ntype: concept\nsubject: English\ngenerated_by: StudyAgent\n---\n# UTF Note\n\nCaf\u00e9.\n"
        path = create_note.create_note(tmp_vault, "UTF Note", content)
        raw = Path(path).read_bytes()
        # Café in UTF-8 is C3 A9 for é
        assert b"\xc3\xa9" in raw
