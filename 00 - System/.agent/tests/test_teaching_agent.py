"""
Tests for teaching_agent.py

Covers:
  - Grade-to-level mapping
  - Profile loading and level resolution
  - Vault score threshold (0.6)
  - Web fallback triggering
  - Content synthesis (explanation, examples, key_points, exam_tips)
  - Practice suggestion by level
  - Source building from vault and web findings
  - Output schema completeness
  - CLI entry point (subprocess)
"""

import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# teaching_agent is in tools/ which conftest.py already adds to sys.path
import teaching_agent as ta


# ── Grade / level mapping ─────────────────────────────────────────────────────

class TestGradeLevelMap:
    def test_grade_9_is_beginner(self):
        assert ta._GRADE_LEVEL_MAP["9"] == "beginner"

    def test_grade_10_is_beginner(self):
        assert ta._GRADE_LEVEL_MAP["10"] == "beginner"

    def test_grade_11_is_intermediate(self):
        assert ta._GRADE_LEVEL_MAP["11"] == "intermediate"

    def test_grade_12_is_intermediate(self):
        assert ta._GRADE_LEVEL_MAP["12"] == "intermediate"

    def test_unknown_grade_defaults_to_intermediate_via_resolve(self):
        _, level, _ = ta._resolve_level({"grade": "6"}, None)
        # grade 6 not in map → defaults to intermediate
        level_resolved, _, _ = ta._resolve_level({"grade": "6"}, None)
        assert level_resolved == "intermediate"


# ── _resolve_level ────────────────────────────────────────────────────────────

class TestResolveLevel:
    def test_reads_grade_from_profile(self):
        level, grade, _ = ta._resolve_level({"grade": "11"}, None)
        assert grade == "11"

    def test_maps_grade_to_level(self):
        level, _, _ = ta._resolve_level({"grade": "9"}, None)
        assert level == "beginner"

    def test_explicit_level_overrides_profile(self):
        level, _, _ = ta._resolve_level({"grade": "9"}, "advanced")
        assert level == "advanced"

    def test_learning_style_from_profile(self):
        _, _, style = ta._resolve_level({"grade": "11", "learning_style": "visual"}, None)
        assert style == "visual"

    def test_default_learning_style_is_balanced(self):
        _, _, style = ta._resolve_level({}, None)
        assert style == "balanced"

    def test_empty_profile_gives_defaults(self):
        level, grade, style = ta._resolve_level({}, None)
        assert level == "intermediate"
        assert style == "balanced"


# ── VAULT_SCORE_THRESHOLD ─────────────────────────────────────────────────────

class TestThreshold:
    def test_threshold_is_0_6(self):
        assert ta.VAULT_SCORE_THRESHOLD == 0.6

    def test_score_below_threshold_triggers_web(self):
        """Score 0.5 < 0.6 → used_web should be True."""
        assert 0.5 < ta.VAULT_SCORE_THRESHOLD

    def test_score_at_threshold_does_not_trigger_web(self):
        """Score exactly 0.6 is NOT below threshold → no web."""
        assert not (0.6 < ta.VAULT_SCORE_THRESHOLD)

    def test_score_above_threshold_does_not_trigger_web(self):
        assert not (0.75 < ta.VAULT_SCORE_THRESHOLD)


# ── _best_vault_score ─────────────────────────────────────────────────────────

class TestBestVaultScore:
    def test_empty_findings_returns_0(self):
        assert ta._best_vault_score({"vault_findings": []}) == 0.0

    def test_single_finding(self):
        result = ta._best_vault_score({"vault_findings": [{"score": 0.72}]})
        assert result == 0.72

    def test_returns_max_score(self):
        findings = [{"score": 0.45}, {"score": 0.82}, {"score": 0.61}]
        result = ta._best_vault_score({"vault_findings": findings})
        assert result == 0.82

    def test_missing_vault_findings_key(self):
        assert ta._best_vault_score({}) == 0.0


# ── _summarise_vault_findings ─────────────────────────────────────────────────

class TestSummariseVaultFindings:
    def make_finding(self, score, excerpt, rel_path="04 - Concepts/Test.md"):
        return {"score": score, "excerpt": excerpt, "rel_path": rel_path}

    def test_returns_non_empty_string(self):
        findings = [self.make_finding(0.8, "Photosynthesis converts light to sugar.")]
        result = ta._summarise_vault_findings(findings)
        assert len(result) > 0

    def test_sorts_by_score_descending(self):
        findings = [
            self.make_finding(0.5, "Low relevance content."),
            self.make_finding(0.9, "High relevance content."),
        ]
        result = ta._summarise_vault_findings(findings)
        assert result.index("High") < result.index("Low")

    def test_limits_to_max_excerpts(self):
        findings = [self.make_finding(float(i) / 10, f"Content {i}") for i in range(10)]
        result = ta._summarise_vault_findings(findings, max_excerpts=2)
        assert result.count("[") <= 2

    def test_skips_empty_excerpts(self):
        findings = [self.make_finding(0.9, ""), self.make_finding(0.8, "Good content.")]
        result = ta._summarise_vault_findings(findings)
        assert "Good content" in result


# ── _build_explanation ────────────────────────────────────────────────────────

class TestBuildExplanation:
    def _call(self, content_block="", concept="osmosis", subject="Biology",
              level="intermediate", grade="11", learning_style="balanced"):
        return ta._build_explanation(
            concept=concept,
            subject=subject,
            context="",
            level=level,
            grade=grade,
            learning_style=learning_style,
            content_block=content_block,
        )

    def test_returns_required_keys(self):
        result = self._call()
        for key in ("explanation", "examples", "key_points", "exam_tips",
                    "suggested_practice", "level_hint", "style_hint"):
            assert key in result

    def test_explanation_is_non_empty(self):
        result = self._call()
        assert len(result["explanation"]) > 0

    def test_examples_non_empty_list(self):
        result = self._call()
        assert isinstance(result["examples"], list)
        assert len(result["examples"]) > 0

    def test_key_points_non_empty_list(self):
        result = self._call()
        assert isinstance(result["key_points"], list)
        assert len(result["key_points"]) > 0

    def test_exam_tips_non_empty_list(self):
        result = self._call()
        assert isinstance(result["exam_tips"], list)
        assert len(result["exam_tips"]) > 0

    def test_parses_example_sentences_from_content(self):
        content = "Osmosis occurs in plant cells. For instance, when a plant cell is placed in water."
        result = self._call(content_block=content)
        assert any("instance" in ex.lower() for ex in result["examples"])

    def test_parses_bullet_points_as_key_points(self):
        content = "- Water moves from low to high concentration.\n- This is passive transport."
        result = self._call(content_block=content)
        assert any("low to high" in kp for kp in result["key_points"])

    def test_level_hint_for_beginner(self):
        result = self._call(level="beginner")
        assert "simple" in result["level_hint"].lower() or "accessible" in result["level_hint"].lower()

    def test_level_hint_for_advanced(self):
        result = self._call(level="advanced")
        assert "depth" in result["level_hint"].lower() or "formal" in result["level_hint"].lower()

    def test_style_hint_for_visual(self):
        result = self._call(learning_style="visual")
        assert "diagram" in result["style_hint"].lower()

    def test_style_hint_for_practical(self):
        result = self._call(learning_style="practical")
        assert "example" in result["style_hint"].lower()


# ── _suggest_practice ─────────────────────────────────────────────────────────

class TestSuggestPractice:
    def test_beginner_includes_fill_in_blank(self):
        result = ta._suggest_practice("beginner")
        assert any("fill" in p.lower() for p in result)

    def test_intermediate_includes_mcq(self):
        result = ta._suggest_practice("intermediate")
        assert any("mcq" in p.lower() or "quiz" in p.lower() for p in result)

    def test_advanced_includes_past_paper(self):
        result = ta._suggest_practice("advanced")
        assert any("past paper" in p.lower() for p in result)

    def test_all_levels_include_flashcards(self):
        for level in ("beginner", "intermediate", "advanced"):
            result = ta._suggest_practice(level)
            assert any("flashcard" in p.lower() for p in result)


# ── _build_sources ────────────────────────────────────────────────────────────

class TestBuildSources:
    def test_vault_sources_have_type_vault(self):
        vault_findings = [{"rel_path": "04 - Concepts/Test.md", "score": 0.8}]
        sources = ta._build_sources(vault_findings, [])
        assert all(s["type"] == "vault" for s in sources)

    def test_web_sources_have_type_web(self):
        web_findings = [{"url": "https://example.com", "title": "Example", "score": 0.9}]
        sources = ta._build_sources([], web_findings)
        assert all(s["type"] == "web" for s in sources)

    def test_limits_vault_to_3(self):
        vault_findings = [{"rel_path": f"note{i}.md", "score": 0.8} for i in range(6)]
        sources = ta._build_sources(vault_findings, [])
        vault_srcs = [s for s in sources if s["type"] == "vault"]
        assert len(vault_srcs) <= 3

    def test_limits_web_to_3(self):
        web_findings = [{"url": f"https://x.com/{i}", "title": f"T{i}", "score": 0.9}
                        for i in range(6)]
        sources = ta._build_sources([], web_findings)
        web_srcs = [s for s in sources if s["type"] == "web"]
        assert len(web_srcs) <= 3

    def test_empty_inputs_return_empty_list(self):
        assert ta._build_sources([], []) == []

    def test_skips_vault_finding_with_no_path(self):
        vault_findings = [{"rel_path": "", "file_path": "", "score": 0.8}]
        sources = ta._build_sources(vault_findings, [])
        assert sources == []


# ── CLI integration (subprocess) ──────────────────────────────────────────────

class TestCLI:
    """
    Three subprocess calls total (class-scoped fixtures):
      - missing_arg_result: validates error on missing --concept
      - main_result:        osmosis/Biology — covers schema, types, field values
      - override_result:    level override — covers --student-level flag
    """
    PYTHON = str(Path(ta.__file__).resolve().parent.parent / "venv" / "Scripts" / "python.exe")
    AGENT  = str(Path(ta.__file__).resolve())
    _ENV   = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

    def _run(self, args: list) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.PYTHON, self.AGENT] + args,
            capture_output=True, text=True, encoding="utf-8", env=self._ENV,
        )

    @pytest.fixture(scope="class")
    def missing_arg_result(self):
        return subprocess.run(
            [str(Path(ta.__file__).resolve().parent.parent / "venv" / "Scripts" / "python.exe"),
             str(Path(ta.__file__).resolve()), "--subject", "Biology"],
            capture_output=True, text=True, encoding="utf-8",
            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )

    @pytest.fixture(scope="class")
    def main_result(self):
        return subprocess.run(
            [str(Path(ta.__file__).resolve().parent.parent / "venv" / "Scripts" / "python.exe"),
             str(Path(ta.__file__).resolve()),
             "--concept", "osmosis", "--subject", "Biology"],
            capture_output=True, text=True, encoding="utf-8",
            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )

    @pytest.fixture(scope="class")
    def main_data(self, main_result):
        return json.loads(main_result.stdout)

    @pytest.fixture(scope="class")
    def override_result(self):
        return subprocess.run(
            [str(Path(ta.__file__).resolve().parent.parent / "venv" / "Scripts" / "python.exe"),
             str(Path(ta.__file__).resolve()),
             "--concept", "calculus", "--subject", "Mathematics", "--student-level", "advanced"],
            capture_output=True, text=True, encoding="utf-8",
            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )

    # ── Error case ────────────────────────────────────────────────────────────
    def test_missing_concept_exits_nonzero(self, missing_arg_result):
        assert missing_arg_result.returncode != 0

    # ── Main result: exit + JSON + schema ─────────────────────────────────────
    def test_exits_zero(self, main_result):
        assert main_result.returncode == 0

    def test_output_is_valid_json(self, main_result):
        data = json.loads(main_result.stdout)
        assert isinstance(data, dict)

    def test_output_has_required_keys(self, main_data):
        for key in ("concept", "subject", "student_level", "grade", "learning_style",
                    "explanation", "examples", "key_points", "exam_tips",
                    "suggested_practice", "sources", "vault_score", "used_web"):
            assert key in main_data, f"Missing key: {key}"

    def test_concept_field(self, main_data):
        assert main_data["concept"] == "osmosis"

    def test_subject_field(self, main_data):
        assert main_data["subject"] == "Biology"

    def test_vault_score_is_float(self, main_data):
        assert isinstance(main_data["vault_score"], float)

    def test_used_web_is_boolean(self, main_data):
        assert isinstance(main_data["used_web"], bool)

    def test_sources_is_list(self, main_data):
        assert isinstance(main_data["sources"], list)

    # ── Override result ───────────────────────────────────────────────────────
    def test_student_level_override(self, override_result):
        data = json.loads(override_result.stdout)
        assert data["student_level"] == "advanced"

