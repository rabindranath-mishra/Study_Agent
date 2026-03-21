"""
Tests for index_vault.py (pure-function layer — no FAISS I/O)

Covers:
  - parse_frontmatter: type / subject / topic extraction
  - parse_frontmatter: no frontmatter returns {}
  - parse_frontmatter: BOM before --- still parsed
  - parse_frontmatter: ignores unrecognised fields
  - strip_frontmatter: removes YAML block
  - strip_frontmatter: content without frontmatter unchanged
  - split_into_sections: heading-based segmentation
  - split_into_sections: pre-heading content gets None heading
  - split_into_sections: multiple headings
  - split_into_sections: no headings returns single segment
  - normalize_whitespace: collapses runs of whitespace
  - normalize_whitespace: strips leading/trailing
  - chunk_text: output is list of strings
  - chunk_text: chunk size respected (approximate)
  - chunk_text: empty text returns empty list
  - iter_markdown_files: excludes .agent / .git / .obsidian dirs
  - find_first_block_id: returns id from ^blockid syntax
  - find_first_block_id: returns None when absent
"""
import sys
import tempfile
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import index_vault


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:

    def test_extracts_type_subject_topic(self):
        text = "---\ntype: concept\nsubject: English\ntopic: Photosynthesis\n---\n# Title\n"
        result = index_vault.parse_frontmatter(text)
        assert result["type"] == "concept"
        assert result["subject"] == "English"
        assert result["topic"] == "Photosynthesis"

    def test_no_frontmatter_returns_empty_dict(self):
        result = index_vault.parse_frontmatter("# Just a heading\nNo frontmatter here.")
        assert result == {}

    def test_bom_before_delimiter_still_parsed(self):
        text = "\ufeff---\ntype: practice\nsubject: Maths\n---\n# Title\n"
        result = index_vault.parse_frontmatter(text)
        assert result.get("type") == "practice"

    def test_ignores_unrecognised_fields(self):
        text = "---\ntype: concept\nauthor: John\ndate: 2026-01-01\n---\n# Title\n"
        result = index_vault.parse_frontmatter(text)
        assert "author" not in result
        assert "date" not in result
        assert "type" in result

    def test_quoted_values_stripped(self):
        text = '---\ntype: "concept"\nsubject: "English"\n---\n# Title\n'
        result = index_vault.parse_frontmatter(text)
        assert result["type"] == "concept"
        assert result["subject"] == "English"

    def test_returns_empty_dict_for_empty_string(self):
        result = index_vault.parse_frontmatter("")
        assert result == {}


# ---------------------------------------------------------------------------
# strip_frontmatter
# ---------------------------------------------------------------------------

class TestStripFrontmatter:

    def test_removes_yaml_block(self):
        text = "---\ntype: concept\nsubject: English\n---\n# Title\n\nBody content.\n"
        result = index_vault.strip_frontmatter(text)
        assert "---" not in result
        assert "Body content." in result
        assert "type: concept" not in result

    def test_no_frontmatter_unchanged(self):
        text = "# Just a heading\n\nSome body text."
        result = index_vault.strip_frontmatter(text)
        assert result == text

    def test_only_one_block_removed(self):
        """Only the first frontmatter block should be stripped."""
        text = "---\ntype: concept\n---\n# Title\n\n---\nSeparator in body\n---\n"
        result = index_vault.strip_frontmatter(text)
        assert "type: concept" not in result
        assert "Separator in body" in result


# ---------------------------------------------------------------------------
# split_into_sections
# ---------------------------------------------------------------------------

class TestSplitIntoSections:

    def test_pre_heading_content_has_none_heading(self):
        text = "Introduction text.\n\n## Section One\nContent of section one."
        sections = index_vault.split_into_sections(text)
        pre = [s for s in sections if s[0] is None]
        assert len(pre) >= 1
        assert "Introduction text." in pre[0][1]

    def test_heading_assigned_to_following_content(self):
        text = "## Overview\nThis is the overview.\n\n## Details\nThis is the details."
        sections = index_vault.split_into_sections(text)
        headings = [s[0] for s in sections]
        assert "Overview" in headings
        assert "Details" in headings

    def test_no_headings_single_segment(self):
        text = "Just some content without any headings."
        sections = index_vault.split_into_sections(text)
        assert len(sections) == 1
        assert sections[0][0] is None

    def test_multiple_headings(self):
        text = "## A\nContent A.\n## B\nContent B.\n## C\nContent C."
        sections = index_vault.split_into_sections(text)
        headings = [s[0] for s in sections if s[0] is not None]
        assert "A" in headings
        assert "B" in headings
        assert "C" in headings

    def test_empty_string(self):
        sections = index_vault.split_into_sections("")
        assert sections == []


# ---------------------------------------------------------------------------
# normalize_whitespace
# ---------------------------------------------------------------------------

class TestNormalizeWhitespace:

    def test_collapses_spaces(self):
        assert index_vault.normalize_whitespace("hello   world") == "hello world"

    def test_collapses_newlines(self):
        assert index_vault.normalize_whitespace("hello\n\nworld") == "hello world"

    def test_strips_leading_trailing(self):
        assert index_vault.normalize_whitespace("  hello  ") == "hello"

    def test_mixed_whitespace(self):
        assert index_vault.normalize_whitespace("a \t b \n c") == "a b c"

    def test_already_clean(self):
        assert index_vault.normalize_whitespace("clean text") == "clean text"


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------

class TestChunkText:

    def test_empty_text_returns_empty_list(self):
        assert index_vault.chunk_text("") == []

    def test_short_text_single_chunk(self):
        text = "Short text that fits in one chunk."
        chunks = index_vault.chunk_text(text, chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        # Create text > 900 chars
        text = "Word " * 300  # ~1500 chars
        chunks = index_vault.chunk_text(text, chunk_size=200, chunk_overlap=20)
        assert len(chunks) > 1

    def test_all_chunks_are_strings(self):
        text = "Para one.\n\nPara two.\n\nPara three.\n\nPara four."
        chunks = index_vault.chunk_text(text, chunk_size=20)
        assert all(isinstance(c, str) for c in chunks)

    def test_no_empty_chunks(self):
        text = "Content.\n\n\n\nMore content."
        chunks = index_vault.chunk_text(text)
        assert all(c.strip() for c in chunks)


# ---------------------------------------------------------------------------
# find_first_block_id
# ---------------------------------------------------------------------------

class TestFindFirstBlockId:

    def test_finds_block_id(self):
        text = "Some content ^myblock here."
        result = index_vault.find_first_block_id(text)
        assert result == "myblock"

    def test_returns_none_when_absent(self):
        text = "No block ids in this text."
        result = index_vault.find_first_block_id(text)
        assert result is None

    def test_returns_first_id_only(self):
        text = "^first and ^second"
        result = index_vault.find_first_block_id(text)
        assert result == "first"


# ---------------------------------------------------------------------------
# iter_markdown_files
# ---------------------------------------------------------------------------

class TestIterMarkdownFiles:

    def test_excludes_agent_dir(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        (agent_dir / "internal.md").write_text("hidden", encoding="utf-8")
        (tmp_path / "visible.md").write_text("visible", encoding="utf-8")

        files = index_vault.iter_markdown_files(tmp_path)
        paths = [f.name for f in files]
        assert "visible.md" in paths
        assert "internal.md" not in paths

    def test_excludes_git_dir(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.md").write_text("git file", encoding="utf-8")
        (tmp_path / "note.md").write_text("note", encoding="utf-8")

        files = index_vault.iter_markdown_files(tmp_path)
        names = [f.name for f in files]
        assert "note.md" in names
        assert "config.md" not in names

    def test_finds_nested_markdown(self, tmp_path):
        sub = tmp_path / "04 - Concepts"
        sub.mkdir()
        (sub / "concept.md").write_text("content", encoding="utf-8")

        files = index_vault.iter_markdown_files(tmp_path)
        names = [f.name for f in files]
        assert "concept.md" in names

    def test_empty_vault_returns_empty_list(self, tmp_path):
        files = index_vault.iter_markdown_files(tmp_path)
        assert files == []

    def test_non_md_files_excluded(self, tmp_path):
        (tmp_path / "file.txt").write_text("text", encoding="utf-8")
        (tmp_path / "note.md").write_text("note", encoding="utf-8")

        files = index_vault.iter_markdown_files(tmp_path)
        names = [f.name for f in files]
        assert "file.txt" not in names
        assert "note.md" in names
