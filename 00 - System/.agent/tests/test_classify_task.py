"""
Tests for classify_task.py

Covers:
  - note_creation signals detected
  - vault_only signals detected
  - multi_topic_research signals detected
  - verified_research signals detected
  - simple_lookup default (no signals)
  - escalation when confidence < 0.7
  - escalation does NOT occur for note_creation
  - combined multi + verified → verified_research
  - output schema shape (task_type, confidence, escalated, signals_matched)
  - score_signals helper
"""
import sys
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).parent
TOOLS_DIR = TESTS_DIR.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import classify_task


class TestScoreSignals:

    def test_no_match_returns_zero(self):
        score, matched = classify_task.score_signals("hello world", classify_task.NOTE_CREATION_SIGNALS)
        assert score == 0.0
        assert matched == []

    def test_single_match(self):
        score, matched = classify_task.score_signals("create a note about photosynthesis", classify_task.NOTE_CREATION_SIGNALS)
        assert score > 0
        assert len(matched) >= 1

    def test_case_insensitive(self):
        score1, _ = classify_task.score_signals("COMPARE X AND Y", classify_task.MULTI_TOPIC_SIGNALS)
        score2, _ = classify_task.score_signals("compare x and y", classify_task.MULTI_TOPIC_SIGNALS)
        assert score1 == score2


class TestClassify:

    # ── note_creation ────────────────────────────────────────────────────────

    def test_note_creation_explicit_create(self):
        result = classify_task.classify("create a note on osmosis")
        assert result["original_task_type"] == "note_creation"

    def test_note_creation_write_note(self):
        result = classify_task.classify("write a note summarising chapter 3")
        assert result["original_task_type"] == "note_creation"

    def test_note_creation_add_to_vault(self):
        result = classify_task.classify("add this to the vault")
        assert result["original_task_type"] == "note_creation"

    def test_note_creation_no_escalation(self):
        """note_creation must never be escalated even with low confidence."""
        result = classify_task.classify("create a note")
        assert result["task_type"] == "note_creation"
        assert result["escalated"] is False

    # ── vault_only ───────────────────────────────────────────────────────────

    def test_vault_only_my_notes(self):
        result = classify_task.classify("what do my notes say about Newton's laws?")
        assert result["original_task_type"] == "vault_only"

    def test_vault_only_in_vault(self):
        result = classify_task.classify("what's in the vault about photosynthesis?")
        assert result["original_task_type"] == "vault_only"

    # ── multi_topic_research ─────────────────────────────────────────────────

    def test_multi_topic_compare(self):
        result = classify_task.classify("compare mitosis and meiosis")
        assert result["original_task_type"] == "multi_topic_research"

    def test_multi_topic_versus(self):
        result = classify_task.classify("TCP versus UDP — differences")
        assert result["original_task_type"] == "multi_topic_research"

    def test_multi_topic_difference_between(self):
        result = classify_task.classify("what is the difference between debt and equity?")
        assert result["original_task_type"] == "multi_topic_research"

    # ── verified_research ────────────────────────────────────────────────────

    def test_verified_research_benchmark(self):
        result = classify_task.classify("benchmark performance of this algorithm")
        assert result["original_task_type"] == "verified_research"

    def test_verified_research_specification(self):
        result = classify_task.classify("verify this specification claim")
        assert result["original_task_type"] == "verified_research"

    def test_verified_research_fact_check(self):
        result = classify_task.classify("fact-check this claim about photosynthesis")
        assert result["original_task_type"] == "verified_research"

    # ── simple_lookup ────────────────────────────────────────────────────────

    def test_simple_lookup_default(self):
        result = classify_task.classify("what is photosynthesis")
        assert result["original_task_type"] == "simple_lookup"

    def test_simple_lookup_escalated(self):
        """simple_lookup confidence is 0.6 → should escalate to vault_only."""
        result = classify_task.classify("what is photosynthesis")
        assert result["escalated"] is True
        assert result["task_type"] == "vault_only"

    # ── output schema ────────────────────────────────────────────────────────

    def test_output_has_required_keys(self):
        result = classify_task.classify("explain gravity")
        for key in ("task_type", "original_task_type", "confidence", "escalated", "signals_matched", "signal_count"):
            assert key in result, f"Missing key: {key}"

    def test_confidence_in_range(self):
        result = classify_task.classify("create a note on gravity")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_signal_count_matches_list(self):
        result = classify_task.classify("create a note on gravity")
        assert result["signal_count"] == len(result["signals_matched"])

    # ── escalation ───────────────────────────────────────────────────────────

    def test_escalation_map_coverage(self):
        """Every task type in TASK_ORDER must appear in ESCALATION_MAP."""
        for t in classify_task.TASK_ORDER:
            assert t in classify_task.ESCALATION_MAP

    def test_multi_plus_verified_gives_verified_research(self):
        """Query with both multi and verified signals → verified_research."""
        result = classify_task.classify("compare the benchmark specs of X vs Y")
        assert result["original_task_type"] == "verified_research"
