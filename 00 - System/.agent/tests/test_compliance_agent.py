"""
Tests for compliance_agent.py

Covers:
  - §XI   No frontmatter → FAIL
  - §XI.1 Missing type field → FAIL
  - §XI.2 Invalid type value → FAIL
  - §XII.1 Missing subject for concept note → FAIL
  - §XII.2 Missing H1 heading → FAIL
  - §XII.3 Date prefix in title → FAIL (binding naming rule)
  - §XII.4 Annotation suffix in title → FAIL (binding naming rule)
  - §XIII.5 Missing generated_by → FAIL
  - §VII  Empty body content → FAIL
  - Full valid concept note → PASS, 0 violations
  - Full valid practice note → PASS
  - parse_frontmatter returns correct fields
  - parse_frontmatter handles BOM in content
"""
import sys
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import compliance_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_note(
    note_type="concept",
    subject="English",
    topic="A Photograph",
    generated_by="StudyAgent",
    title="A Photograph",
    h1="A Photograph",
    body="Some meaningful body content about the topic that exceeds minimum length.",
    extra_fields="",
):
    fm = f"---\ntype: {note_type}\nsubject: {subject}\ntopic: {topic}\ngenerated_by: {generated_by}\n{extra_fields}---\n"
    return f"{fm}# {h1}\n\n{body}\n"


def run_check(title, content, note_type="concept"):
    fields, body = compliance_agent.parse_frontmatter(content)
    violations = []
    violations += compliance_agent.check_frontmatter_present(fields, body)
    violations += compliance_agent.check_type_field(fields)
    violations += compliance_agent.check_subject_field(fields)
    violations += compliance_agent.check_generated_by(fields)
    violations += compliance_agent.check_h1_present(body)
    violations += compliance_agent.check_h1_matches_title(body, title)
    violations += compliance_agent.check_title_no_date_prefix(title)
    violations += compliance_agent.check_title_no_annotation_suffix(title)
    violations += compliance_agent.check_body_has_content(body)
    return violations


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:

    def test_parses_type_subject_topic(self):
        content = "---\ntype: concept\nsubject: English\ntopic: Osmosis\n---\n# Title\n"
        fields, body = compliance_agent.parse_frontmatter(content)
        assert fields is not None
        assert fields.get("type") == "concept"
        assert fields.get("subject") == "English"
        assert fields.get("topic") == "Osmosis"

    def test_no_frontmatter_returns_none(self):
        content = "# Just a heading\n\nSome text."
        fields, body = compliance_agent.parse_frontmatter(content)
        assert fields is None

    def test_bom_handled_in_frontmatter(self):
        content = "\ufeff---\ntype: concept\nsubject: English\n---\n# Title\n"
        fields, body = compliance_agent.parse_frontmatter(content)
        assert fields is not None
        assert fields.get("type") == "concept"

    def test_body_stripped_of_frontmatter(self):
        content = "---\ntype: concept\n---\n# Title\n\nBody text.\n"
        fields, body = compliance_agent.parse_frontmatter(content)
        assert "---" not in body
        assert "Body text." in body


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

class TestCheckFrontmatterPresent:

    def test_none_fields_fails(self):
        v = compliance_agent.check_frontmatter_present(None, "body")
        assert len(v) == 1
        assert v[0]["rule"] == "§XI"

    def test_valid_fields_passes(self):
        v = compliance_agent.check_frontmatter_present({"type": "concept"}, "body")
        assert v == []


class TestCheckTypeField:

    def test_missing_type_fails(self):
        v = compliance_agent.check_type_field({})
        assert any(v_item["rule"].startswith("§XI") for v_item in v)

    def test_invalid_type_fails(self):
        v = compliance_agent.check_type_field({"type": "gibberish"})
        assert len(v) == 1
        assert "§XI.2" in v[0]["rule"]

    def test_valid_types_all_pass(self):
        for t in compliance_agent.VALID_TYPES:
            v = compliance_agent.check_type_field({"type": t})
            assert v == [], f"Type '{t}' should be valid"


class TestCheckSubjectField:

    def test_concept_without_subject_fails(self):
        v = compliance_agent.check_subject_field({"type": "concept"})
        assert len(v) == 1

    def test_concept_with_subject_passes(self):
        v = compliance_agent.check_subject_field({"type": "concept", "subject": "English"})
        assert v == []

    def test_system_type_no_subject_required(self):
        v = compliance_agent.check_subject_field({"type": "system"})
        assert v == []


class TestCheckH1:

    def test_missing_h1_fails(self):
        body = "No heading here."
        v = compliance_agent.check_h1_present(body)
        assert len(v) >= 1
        assert any("H1" in vi["message"] or "heading" in vi["message"].lower() for vi in v)

    def test_present_h1_passes(self):
        body = "# My Title\n\nBody.\n"
        v = compliance_agent.check_h1_present(body)
        assert v == []

    def test_h1_matches_title_passes(self):
        body = "# My Title\n\nBody.\n"
        v = compliance_agent.check_h1_matches_title(body, "My Title")
        assert v == []

    def test_date_prefix_in_title_fails(self):
        v = compliance_agent.check_title_no_date_prefix("2026-03-21 My Title")
        assert len(v) >= 1

    def test_clean_title_no_date_prefix_passes(self):
        v = compliance_agent.check_title_no_date_prefix("My Title")
        assert v == []

    def test_annotation_suffix_moc_fails(self):
        v = compliance_agent.check_title_no_annotation_suffix("My Title MOC")
        assert len(v) >= 1

    def test_clean_title_no_annotation_passes(self):
        v = compliance_agent.check_title_no_annotation_suffix("My Title")
        assert v == []


class TestCheckGeneratedBy:

    def test_missing_generated_by_fails(self):
        v = compliance_agent.check_generated_by({"type": "concept"})
        assert len(v) == 1
        assert "§XIII" in v[0]["rule"]

    def test_present_generated_by_passes(self):
        v = compliance_agent.check_generated_by({"type": "concept", "generated_by": "StudyAgent"})
        assert v == []


class TestCheckBodyContent:

    def test_empty_body_fails(self):
        v = compliance_agent.check_body_has_content("")
        assert len(v) >= 1

    def test_whitespace_only_fails(self):
        v = compliance_agent.check_body_has_content("   \n  \t  ")
        assert len(v) >= 1

    def test_meaningful_body_passes(self):
        v = compliance_agent.check_body_has_content("This is a meaningful body with content about the topic.")
        assert v == []


# ---------------------------------------------------------------------------
# Full pipeline (PASS / FAIL)
# ---------------------------------------------------------------------------

class TestFullCompliance:

    def test_valid_concept_note_passes(self):
        content = _make_note()
        violations = run_check("A Photograph", content, "concept")
        assert violations == [], f"Expected PASS, got: {violations}"

    def test_valid_practice_note_passes(self):
        content = _make_note(note_type="practice", h1="Practice Questions", title="Practice Questions")
        violations = run_check("Practice Questions", content, "practice")
        assert violations == []

    def test_no_frontmatter_fails(self):
        content = "# My Note\n\nSome content here."
        violations = run_check("My Note", content)
        assert len(violations) >= 1

    def test_missing_generated_by_fails(self):
        content = "---\ntype: concept\nsubject: English\ntopic: Test\n---\n# A Photograph\n\nBody content.\n"
        violations = run_check("A Photograph", content)
        assert any("generated_by" in str(v) for v in violations)

    def test_missing_subject_for_concept_fails(self):
        content = "---\ntype: concept\ntopic: Test\ngenerated_by: StudyAgent\n---\n# A Photograph\n\nBody content.\n"
        violations = run_check("A Photograph", content)
        assert any("subject" in str(v).lower() for v in violations)
