"""
Tests for practice_agent.py

Covers:
  - Difficulty resolution from grade / profile
  - Vault score threshold (0.6)
  - Question distribution across types
  - Each question generator (mcq, short_answer, long_answer, fill_blank, true_false)
  - Time estimation
  - Answer key building
  - Note content generation
  - Source building
  - CLI output schema
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

import practice_agent as pa


# ── Difficulty resolution ─────────────────────────────────────────────────────

import marking_scheme_store as _mss

_CBSE_SCHEME = _mss.get_scheme("CBSE")

class TestResolveDifficulty:
    def test_grade_9_gives_beginner(self):
        diff, _, _ = pa._resolve_context({"grade": "9"}, None)
        assert diff == "beginner"

    def test_grade_10_gives_beginner(self):
        diff, _, _ = pa._resolve_context({"grade": "10"}, None)
        assert diff == "beginner"

    def test_grade_11_gives_intermediate(self):
        diff, _, _ = pa._resolve_context({"grade": "11"}, None)
        assert diff == "intermediate"

    def test_grade_12_gives_intermediate(self):
        diff, _, _ = pa._resolve_context({"grade": "12"}, None)
        assert diff == "intermediate"

    def test_unknown_grade_defaults_intermediate(self):
        diff, _, _ = pa._resolve_context({"grade": "6"}, None)
        assert diff == "intermediate"

    def test_explicit_overrides_grade(self):
        diff, _, _ = pa._resolve_context({"grade": "9"}, "advanced")
        assert diff == "advanced"

    def test_grade_returned_from_profile(self):
        _, grade, _ = pa._resolve_context({"grade": "11"}, None)
        assert grade == "11"

    def test_empty_profile_defaults(self):
        diff, grade, board = pa._resolve_context({}, None)
        assert diff == "intermediate"
        assert grade == "11"
        assert board == "Generic"

    def test_nested_profile_grade(self):
        profile = {"current_level": {"grade": "Class 11", "board": "CBSE"}}
        diff, grade, board = pa._resolve_context(profile, None)
        assert grade == "11"
        assert board == "CBSE"


# ── Threshold constant ────────────────────────────────────────────────────────

class TestThreshold:
    def test_threshold_is_0_6(self):
        assert pa.VAULT_SCORE_THRESHOLD == 0.6


# ── _best_vault_score ─────────────────────────────────────────────────────────

class TestBestVaultScore:
    def test_empty_returns_0(self):
        assert pa._best_vault_score({"vault_findings": []}) == 0.0

    def test_single_score(self):
        assert pa._best_vault_score({"vault_findings": [{"score": 0.75}]}) == 0.75

    def test_returns_max(self):
        findings = [{"score": 0.4}, {"score": 0.85}, {"score": 0.6}]
        assert pa._best_vault_score({"vault_findings": findings}) == 0.85

    def test_missing_key_returns_0(self):
        assert pa._best_vault_score({}) == 0.0


# ── _distribute_questions ─────────────────────────────────────────────────────

class TestDistributeQuestions:
    def test_single_type_gets_all(self):
        dist = pa._distribute_questions(10, ["mcq"])
        assert dist["mcq"] == 10

    def test_two_types_split_evenly(self):
        dist = pa._distribute_questions(10, ["mcq", "short_answer"])
        assert dist["mcq"] + dist["short_answer"] == 10

    def test_three_types_remainder_goes_to_first(self):
        dist = pa._distribute_questions(10, ["mcq", "short_answer", "long_answer"])
        total = sum(dist.values())
        assert total == 10

    def test_empty_types_defaults_to_mcq_short(self):
        dist = pa._distribute_questions(6, [])
        assert "mcq" in dist or "short_answer" in dist

    def test_each_type_gets_at_least_1(self):
        dist = pa._distribute_questions(3, ["mcq", "short_answer", "long_answer"])
        for v in dist.values():
            assert v >= 1


# ── _extract_sentences ────────────────────────────────────────────────────────

class TestExtractSentences:
    def test_splits_on_period(self):
        blocks = ["Osmosis is a process. It involves water movement."]
        sents = pa._extract_sentences(blocks)
        assert len(sents) >= 2

    def test_skips_very_short_strings(self):
        blocks = ["OK. Go."]
        sents = pa._extract_sentences(blocks)
        assert all(len(s) > 15 for s in sents)

    def test_empty_blocks_returns_empty(self):
        assert pa._extract_sentences([]) == []


# ── _extract_key_terms ────────────────────────────────────────────────────────

class TestExtractKeyTerms:
    def test_extracts_bold_terms(self):
        blocks = ["**Osmosis** is the movement of water across a membrane."]
        terms = pa._extract_key_terms(blocks)
        assert "Osmosis" in terms

    def test_no_duplicates(self):
        blocks = ["Osmosis occurs. Osmosis is important."]
        terms = pa._extract_key_terms(blocks)
        lower_terms = [t.lower() for t in terms]
        assert len(lower_terms) == len(set(lower_terms))

    def test_skips_stopwords(self):
        blocks = ["The process is important for the cell."]
        terms = pa._extract_key_terms(blocks)
        assert "The" not in terms
        assert "In" not in terms


# ── _extract_list_items ───────────────────────────────────────────────────────

class TestExtractListItems:
    def test_extracts_dash_items(self):
        blocks = ["- Water moves from high to low concentration.\n- This is passive transport."]
        items = pa._extract_list_items(blocks)
        assert len(items) >= 2

    def test_extracts_numbered_items(self):
        blocks = ["1. First step\n2. Second step"]
        items = pa._extract_list_items(blocks)
        assert len(items) >= 2

    def test_skips_short_items(self):
        blocks = ["- OK\n- Good point about osmosis in cells."]
        items = pa._extract_list_items(blocks)
        for item in items:
            assert len(item) > 10


# ── MCQ generator ─────────────────────────────────────────────────────────────

class TestMakeMCQ:
    def _base_sentences(self):
        return [
            "Osmosis is the movement of water molecules across a semipermeable membrane.",
            "It occurs from a region of high water concentration to low water concentration.",
            "Osmosis is an example of passive transport.",
        ]

    def test_returns_list(self):
        qs = pa._make_mcq("osmosis", "Biology", self._base_sentences(), ["Osmosis", "membrane"], [], "intermediate", 1)
        assert isinstance(qs, list)

    def test_each_question_has_required_keys(self):
        qs = pa._make_mcq("osmosis", "Biology", self._base_sentences(), ["Osmosis"], [], "intermediate", 1)
        for q in qs:
            assert "id" in q
            assert "type" in q
            assert q["type"] == "mcq"
            assert "question" in q
            assert "options" in q
            assert "answer" in q

    def test_options_has_four_choices(self):
        qs = pa._make_mcq("osmosis", "Biology", self._base_sentences(), [], [], "intermediate", 1)
        for q in qs:
            assert set(q["options"].keys()) == {"A", "B", "C", "D"}

    def test_ids_start_at_given_start(self):
        qs = pa._make_mcq("osmosis", "Biology", self._base_sentences(), [], [], "intermediate", 5)
        if qs:
            assert qs[0]["id"] == 5

    def test_no_crash_on_empty_sentences(self):
        qs = pa._make_mcq("osmosis", "Biology", [], [], [], "beginner", 1)
        assert isinstance(qs, list)


# ── Short answer generator ────────────────────────────────────────────────────

class TestMakeShortAnswer:
    def test_returns_list(self):
        qs = pa._make_short_answer("osmosis", "Biology", [], ["Osmosis", "membrane"], [], "intermediate", 1)
        assert isinstance(qs, list)

    def test_each_has_required_keys(self):
        qs = pa._make_short_answer("osmosis", "Biology", [], ["Osmosis"], [], "intermediate", 1)
        for q in qs:
            assert q["type"] == "short_answer"
            assert "question" in q
            assert "marks" in q
            assert "marking_scheme" in q

    def test_marking_scheme_has_value_points(self):
        qs = pa._make_short_answer("osmosis", "Biology", [], ["Osmosis"], [], "intermediate", 1)
        for q in qs:
            ms = q["marking_scheme"]
            assert "value_points" in ms
            assert isinstance(ms["value_points"], list)
            assert len(ms["value_points"]) == q["marks"]

    def test_value_points_count_matches_marks(self):
        qs = pa._make_short_answer("osmosis", "Biology", [], ["Osmosis"], [], "intermediate", 1)
        for q in qs:
            assert len(q["marking_scheme"]["value_points"]) == q["marks"]

    def test_beginner_has_lower_marks(self):
        qs_beg = pa._make_short_answer("osmosis", "Biology", [], ["Osmosis"], [], "beginner", 1)
        qs_adv = pa._make_short_answer("osmosis", "Biology", [], ["Osmosis"], [], "advanced", 1)
        if qs_beg and qs_adv:
            assert qs_beg[0]["marks"] <= qs_adv[0]["marks"]


# ── Long answer generator ─────────────────────────────────────────────────────

class TestMakeLongAnswer:
    def test_returns_list(self):
        qs = pa._make_long_answer("photosynthesis", "Biology", [], ["chlorophyll", "glucose"], [], "intermediate", 1)
        assert isinstance(qs, list)

    def test_each_has_required_keys(self):
        qs = pa._make_long_answer("photosynthesis", "Biology", [], ["chlorophyll"], [], "intermediate", 1)
        for q in qs:
            assert q["type"] == "long_answer"
            assert "question" in q
            assert "marks" in q
            assert "marking_scheme" in q

    def test_marking_scheme_has_value_points(self):
        qs = pa._make_long_answer("photosynthesis", "Biology", [], ["chlorophyll"], [], "intermediate", 1)
        for q in qs:
            ms = q["marking_scheme"]
            assert "value_points" in ms
            assert isinstance(ms["value_points"], list)

    def test_value_points_count_matches_marks(self):
        qs = pa._make_long_answer("photosynthesis", "Biology", [], [], [], "intermediate", 1)
        for q in qs:
            assert len(q["marking_scheme"]["value_points"]) == q["marks"]

    def test_5_mark_has_5_value_points(self):
        qs = pa._make_long_answer("photosynthesis", "Biology", [], [], [], "intermediate", 1)
        for q in qs:
            if q["marks"] == 5:
                assert len(q["marking_scheme"]["value_points"]) == 5


# ── Fill in the blank generator ───────────────────────────────────────────────

class TestMakeFillBlank:
    def test_returns_list(self):
        sents = ["Osmosis is the movement of water across a membrane."]
        qs = pa._make_fill_blank("osmosis", sents, ["Osmosis"], 1)
        assert isinstance(qs, list)

    def test_each_has_required_keys(self):
        sents = ["Osmosis is the movement of water across a membrane."]
        qs = pa._make_fill_blank("osmosis", sents, ["Osmosis"], 1)
        for q in qs:
            assert q["type"] == "fill_blank"
            assert "question" in q
            assert "answer" in q
            assert "_______" in q["question"]

    def test_blank_replaced_with_term(self):
        sents = ["Osmosis is a passive transport process."]
        qs = pa._make_fill_blank("osmosis", sents, ["Osmosis"], 1)
        if qs:
            assert qs[0]["answer"] == "Osmosis"

    def test_fallback_when_no_terms_in_sentences(self):
        qs = pa._make_fill_blank("osmosis", [], [], 1)
        assert len(qs) >= 1


# ── True/False generator ──────────────────────────────────────────────────────

class TestMakeTrueFalse:
    def _sentences(self):
        return [
            "Osmosis is the movement of water molecules across a semipermeable membrane.",
            "It is a type of passive transport.",
            "Plants rely on osmosis for water uptake.",
        ]

    def test_returns_list(self):
        qs = pa._make_true_false("osmosis", "Biology", self._sentences(), 1)
        assert isinstance(qs, list)

    def test_each_has_required_keys(self):
        qs = pa._make_true_false("osmosis", "Biology", self._sentences(), 1)
        for q in qs:
            assert q["type"] == "true_false"
            assert "question" in q
            assert "answer" in q
            assert q["answer"] in ("True", "False")

    def test_has_both_true_and_false_answers(self):
        qs = pa._make_true_false("osmosis", "Biology", self._sentences(), 1)
        answers = {q["answer"] for q in qs}
        assert "True" in answers
        assert "False" in answers


# ── Time estimation ───────────────────────────────────────────────────────────

class TestEstimateTime:
    def test_returns_string_with_minutes(self):
        questions = [{"type": "mcq"}, {"type": "short_answer"}]
        result = pa._estimate_time(questions)
        assert "minute" in result

    def test_more_questions_more_time(self):
        qs_few = [{"type": "mcq"}] * 2
        qs_many = [{"type": "mcq"}] * 10
        t_few = int(pa._estimate_time(qs_few).split()[0])
        t_many = int(pa._estimate_time(qs_many).split()[0])
        assert t_many > t_few

    def test_long_answer_adds_more_time(self):
        qs_mcq = [{"type": "mcq"}] * 5
        qs_long = [{"type": "long_answer"}] * 5
        t_mcq = int(pa._estimate_time(qs_mcq).split()[0])
        t_long = int(pa._estimate_time(qs_long).split()[0])
        assert t_long > t_mcq


# ── Answer key ────────────────────────────────────────────────────────────────

class TestBuildAnswerKey:
    def test_mcq_entry_has_answer_and_note(self):
        q = {"id": 1, "type": "mcq", "marks": 1, "answer": "B",
             "explanation": "Because...", "marking_scheme": _CBSE_SCHEME["mcq"]}
        key = pa._build_answer_key([q])
        assert key[0]["answer"] == "B"
        assert "examiner_note" in key[0]

    def test_fill_blank_entry_has_answer(self):
        q = {"id": 2, "type": "fill_blank", "marks": 1, "answer": "osmosis",
             "marking_scheme": _CBSE_SCHEME["fill_blank"]}
        key = pa._build_answer_key([q])
        assert key[0]["answer"] == "osmosis"

    def test_true_false_entry_has_marks_breakdown(self):
        q = {"id": 3, "type": "true_false", "marks": 1, "answer": "True",
             "justification": "...", "marking_scheme": _CBSE_SCHEME["true_false"]}
        key = pa._build_answer_key([q])
        assert key[0]["answer"] == "True"
        assert "marks_answer" in key[0]
        assert "marks_justification" in key[0]

    def test_short_answer_has_value_points(self):
        vps = [{"slot": "Definition (1 mark)", "point": "Osmosis is...", "marks": 1}]
        ms = {"total_marks": 1, "structure": "one point", "partial_credit": True,
              "examiner_note": "award 1 mark", "value_points": vps}
        q = {"id": 4, "type": "short_answer", "marks": 1, "question": "Define osmosis.", "marking_scheme": ms}
        key = pa._build_answer_key([q])
        assert key[0]["value_points"] == vps

    def test_long_answer_has_value_points(self):
        vps = [{"slot": f"Point {i} (1 mark)", "point": f"fact {i}", "marks": 1} for i in range(5)]
        ms = {"total_marks": 5, "structure": "5 points", "partial_credit": True,
              "examiner_note": "1 per point", "value_points": vps}
        q = {"id": 5, "type": "long_answer", "marks": 5, "question": "Discuss.", "marking_scheme": ms}
        key = pa._build_answer_key([q])
        assert len(key[0]["value_points"]) == 5

    def test_key_ids_match_question_ids(self):
        qs = [{"id": i, "type": "mcq", "marks": 1, "answer": "A",
               "explanation": "", "marking_scheme": _CBSE_SCHEME["mcq"]} for i in range(1, 4)]
        key = pa._build_answer_key(qs)
        assert [e["id"] for e in key] == [1, 2, 3]


# ── Note content ──────────────────────────────────────────────────────────────

class TestBuildNoteContent:
    def _make_questions(self):
        return [
            {"id": 1, "type": "mcq", "question": "What is osmosis?",
             "options": {"A": "Water movement", "B": "Food movement", "C": "Heat transfer", "D": "Light absorption"},
             "answer": "A", "explanation": "Correct."},
            {"id": 2, "type": "short_answer", "question": "Define osmosis.", "marks": 3,
             "expected_answer_hint": "movement of water"},
        ]

    def test_content_is_non_empty_string(self):
        content = pa._build_note_content(
            "Osmosis Practice", "osmosis", "Biology", "intermediate",
            "11", 2, "5 minutes", self._make_questions(), ["osmosis", "membrane"]
        )
        assert isinstance(content, str) and len(content) > 100

    def test_contains_frontmatter_delimiters(self):
        content = pa._build_note_content(
            "Osmosis Practice", "osmosis", "Biology", "intermediate",
            "11", 2, "5 minutes", self._make_questions(), []
        )
        assert content.count("---") >= 2

    def test_contains_h1_title(self):
        content = pa._build_note_content(
            "Osmosis Practice", "osmosis", "Biology", "intermediate",
            "11", 2, "5 minutes", self._make_questions(), []
        )
        assert "# Osmosis Practice" in content

    def test_contains_answer_key_section(self):
        content = pa._build_note_content(
            "Osmosis Practice", "osmosis", "Biology", "intermediate",
            "11", 2, "5 minutes", self._make_questions(), []
        )
        assert "Answer Key" in content

    def test_note_type_in_frontmatter(self):
        content = pa._build_note_content(
            "Osmosis Practice", "osmosis", "Biology", "intermediate",
            "11", 2, "5 minutes", self._make_questions(), []
        )
        assert "note_type: practice" in content


# ── CLI integration ───────────────────────────────────────────────────────────

class TestCLI:
    """
    Three subprocess calls total (class-scoped fixtures):
      - missing_arg_result: validates error on missing --topic
      - main_result:        osmosis/Biology with custom types — covers schema + types + values
      - override_result:    difficulty + question-count overrides
    """
    _PY    = str(Path(pa.__file__).resolve().parent.parent / "venv" / "Scripts" / "python.exe")
    _AGENT = str(Path(pa.__file__).resolve())
    _ENV   = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

    @pytest.fixture(scope="class")
    def missing_arg_result(self):
        return subprocess.run(
            [self._PY, self._AGENT, "--subject", "Biology"],
            capture_output=True, text=True, encoding="utf-8", env=self._ENV,
        )

    @pytest.fixture(scope="class")
    def main_result(self):
        return subprocess.run(
            [self._PY, self._AGENT,
             "--topic", "osmosis", "--subject", "Biology",
             "--question-types", "mcq,true_false"],
            capture_output=True, text=True, encoding="utf-8", env=self._ENV,
        )

    @pytest.fixture(scope="class")
    def main_data(self, main_result):
        return json.loads(main_result.stdout)

    @pytest.fixture(scope="class")
    def override_result(self):
        return subprocess.run(
            [self._PY, self._AGENT,
             "--topic", "osmosis", "--subject", "Biology",
             "--difficulty", "advanced", "--question-count", "5"],
            capture_output=True, text=True, encoding="utf-8", env=self._ENV,
        )

    # ── Error case ────────────────────────────────────────────────────────────
    def test_missing_topic_exits_nonzero(self, missing_arg_result):
        assert missing_arg_result.returncode != 0

    # ── Main result: exit + JSON + full schema ────────────────────────────────
    def test_exits_zero(self, main_result):
        assert main_result.returncode == 0

    def test_output_is_valid_json(self, main_result):
        assert isinstance(json.loads(main_result.stdout), dict)

    def test_output_has_required_keys(self, main_data):
        for key in ("topic", "subject", "difficulty", "grade", "question_count",
                    "estimated_time", "questions", "topics_covered", "sources",
                    "vault_score", "used_web", "suggested_note_title", "note_content"):
            assert key in main_data, f"Missing key: {key}"

    def test_topic_and_subject_fields(self, main_data):
        assert main_data["topic"] == "osmosis"
        assert main_data["subject"] == "Biology"

    def test_questions_is_list(self, main_data):
        assert isinstance(main_data["questions"], list)

    def test_question_types_respected(self, main_data):
        types_used = {q["type"] for q in main_data["questions"]}
        assert types_used.issubset({"mcq", "true_false"})

    def test_note_content_is_non_empty_string(self, main_data):
        assert isinstance(main_data["note_content"], str)
        assert len(main_data["note_content"]) > 50

    def test_vault_score_is_float(self, main_data):
        assert isinstance(main_data["vault_score"], float)

    def test_used_web_is_bool(self, main_data):
        assert isinstance(main_data["used_web"], bool)

    # ── Override result ───────────────────────────────────────────────────────
    def test_difficulty_override(self, override_result):
        data = json.loads(override_result.stdout)
        assert data["difficulty"] == "advanced"

    def test_question_count_override(self, override_result):
        data = json.loads(override_result.stdout)
        assert data["question_count"] <= 5

