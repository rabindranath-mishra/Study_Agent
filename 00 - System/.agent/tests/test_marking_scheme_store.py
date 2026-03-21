"""
Tests for marking_scheme_store.py

Covers:
  - normalise_board: all aliases + unknown fallback
  - get_scheme: returns correct board + keys present
  - get_q_scheme: exact match + nearest-band fallback
  - get_q_scheme_by_marks: same logic with pre-fetched dict
  - get_board_from_profile: nested (current_level.board) + flat (board) shapes
  - list_supported_boards: completeness
  - board_display fields are non-empty strings
  - All boards have mcq / fill_blank / true_false entries
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import marking_scheme_store as mss


# ── normalise_board ────────────────────────────────────────────────────────────

class TestNormaliseBoard:
    def test_cbse_lowercase(self):
        assert mss.normalise_board("cbse") == "CBSE"

    def test_cbse_mixed_case(self):
        assert mss.normalise_board("CBSE") == "CBSE"

    def test_icse(self):
        assert mss.normalise_board("ICSE") == "ICSE"

    def test_isc_maps_to_icse(self):
        assert mss.normalise_board("ISC") == "ICSE"

    def test_ib_uppercase(self):
        assert mss.normalise_board("IB") == "IB"

    def test_cambridge(self):
        assert mss.normalise_board("Cambridge") == "Cambridge"

    def test_igcse_maps_to_cambridge(self):
        assert mss.normalise_board("IGCSE") == "Cambridge"

    def test_cie_maps_to_cambridge(self):
        assert mss.normalise_board("cie") == "Cambridge"

    def test_state_board(self):
        assert mss.normalise_board("state") == "State"

    def test_unknown_falls_back_to_generic(self):
        assert mss.normalise_board("MadeUpBoard") == "Generic"

    def test_empty_string_falls_back_to_generic(self):
        assert mss.normalise_board("") == "Generic"

    def test_whitespace_trimmed(self):
        assert mss.normalise_board("  cbse  ") == "CBSE"


# ── get_scheme ─────────────────────────────────────────────────────────────────

class TestGetScheme:
    _REQUIRED_KEYS = {"q_scheme", "mcq", "fill_blank", "true_false", "board_display"}

    @pytest.mark.parametrize("board", ["CBSE", "ICSE", "IB", "Cambridge", "State", "Generic"])
    def test_scheme_has_required_keys(self, board):
        scheme = mss.get_scheme(board)
        assert self._REQUIRED_KEYS.issubset(scheme.keys()), f"Missing keys in {board}: {self._REQUIRED_KEYS - scheme.keys()}"

    @pytest.mark.parametrize("board", ["CBSE", "ICSE", "IB", "Cambridge", "State", "Generic"])
    def test_board_display_is_non_empty_string(self, board):
        display = mss.get_scheme(board).get("board_display", "")
        assert isinstance(display, str) and len(display) > 0

    def test_unknown_board_returns_generic(self):
        scheme = mss.get_scheme("XYZ")
        assert scheme == mss.get_scheme("Generic")

    def test_cbse_q_scheme_has_mark_bands(self):
        q_scheme = mss.get_scheme("CBSE")["q_scheme"]
        assert 1 in q_scheme and 5 in q_scheme

    def test_icse_q_scheme_has_mark_bands(self):
        q_scheme = mss.get_scheme("ICSE")["q_scheme"]
        assert len(q_scheme) >= 4

    def test_ib_q_scheme_has_mark_bands(self):
        q_scheme = mss.get_scheme("IB")["q_scheme"]
        assert len(q_scheme) >= 3


# ── get_q_scheme ───────────────────────────────────────────────────────────────

class TestGetQScheme:
    def test_exact_match_cbse_3(self):
        entry = mss.get_q_scheme("CBSE", 3)
        assert entry is not None
        assert entry.get("value_point_count") == 3

    def test_exact_match_cbse_5(self):
        entry = mss.get_q_scheme("CBSE", 5)
        assert entry is not None
        assert entry.get("value_point_count") == 5

    def test_nearest_band_fallback_cbse_4_gives_3(self):
        # CBSE has 1,2,3,5,8 — marks=4 should return 3-band
        entry = mss.get_q_scheme("CBSE", 4)
        assert entry is not None
        assert entry.get("value_point_count") == 3

    def test_nearest_band_fallback_cbse_7_gives_5(self):
        entry = mss.get_q_scheme("CBSE", 7)
        assert entry is not None
        assert entry.get("value_point_count") == 5

    def test_marks_1_returns_1_point(self):
        entry = mss.get_q_scheme("CBSE", 1)
        assert entry["value_point_count"] == 1

    def test_marks_8_returns_8_points(self):
        entry = mss.get_q_scheme("CBSE", 8)
        assert entry["value_point_count"] == 8

    def test_entry_has_word_limit(self):
        entry = mss.get_q_scheme("CBSE", 3)
        assert "word_limit" in entry

    def test_entry_has_partial_credit(self):
        entry = mss.get_q_scheme("CBSE", 3)
        assert "partial_credit" in entry

    def test_entry_has_breakdown_list(self):
        entry = mss.get_q_scheme("CBSE", 3)
        assert isinstance(entry.get("breakdown"), list)
        assert len(entry["breakdown"]) == entry["value_point_count"]

    def test_cambridge_q_scheme_accessible(self):
        entry = mss.get_q_scheme("Cambridge", 4)
        assert entry is not None

    def test_ib_q_scheme_accessible(self):
        entry = mss.get_q_scheme("IB", 6)
        assert entry is not None


# ── get_q_scheme_by_marks ──────────────────────────────────────────────────────

class TestGetQSchemeByMarks:
    def test_exact_match(self):
        q_scheme = mss.get_scheme("CBSE")["q_scheme"]
        entry = mss.get_q_scheme_by_marks(q_scheme, 3)
        assert entry["value_point_count"] == 3

    def test_nearest_below(self):
        q_scheme = mss.get_scheme("CBSE")["q_scheme"]
        entry = mss.get_q_scheme_by_marks(q_scheme, 4)
        assert entry["value_point_count"] == 3

    def test_none_q_scheme_returns_none(self):
        assert mss.get_q_scheme_by_marks(None, 5) is None

    def test_empty_q_scheme_returns_none(self):
        assert mss.get_q_scheme_by_marks({}, 5) is None

    def test_marks_below_all_bands_returns_smallest(self):
        q_scheme = mss.get_scheme("CBSE")["q_scheme"]
        entry = mss.get_q_scheme_by_marks(q_scheme, 0)
        # Smallest band is 1
        assert entry is not None


# ── get_board_from_profile ─────────────────────────────────────────────────────

class TestGetBoardFromProfile:
    def test_nested_profile_cbse(self):
        profile = {"current_level": {"board": "CBSE", "grade": "Class 11"}}
        assert mss.get_board_from_profile(profile) == "CBSE"

    def test_nested_profile_icse(self):
        profile = {"current_level": {"board": "ISC"}}
        assert mss.get_board_from_profile(profile) == "ICSE"

    def test_flat_profile_board(self):
        profile = {"board": "IB"}
        assert mss.get_board_from_profile(profile) == "IB"

    def test_empty_profile_returns_generic(self):
        assert mss.get_board_from_profile({}) == "Generic"

    def test_unknown_board_returns_generic(self):
        profile = {"board": "RandomBoard"}
        assert mss.get_board_from_profile(profile) == "Generic"

    def test_nested_takes_precedence_over_flat(self):
        profile = {"current_level": {"board": "CBSE"}, "board": "IB"}
        assert mss.get_board_from_profile(profile) == "CBSE"


# ── list_supported_boards ──────────────────────────────────────────────────────

class TestListSupportedBoards:
    def test_includes_cbse(self):
        assert "CBSE" in mss.list_supported_boards()

    def test_includes_icse(self):
        assert "ICSE" in mss.list_supported_boards()

    def test_includes_ib(self):
        assert "IB" in mss.list_supported_boards()

    def test_includes_cambridge(self):
        assert "Cambridge" in mss.list_supported_boards()

    def test_generic_excluded(self):
        assert "Generic" not in mss.list_supported_boards()

    def test_returns_at_least_4_boards(self):
        assert len(mss.list_supported_boards()) >= 4


# ── MCQ / fill_blank / true_false scheme keys ─────────────────────────────────

class TestSimpleQuestionSchemes:
    @pytest.mark.parametrize("board", ["CBSE", "ICSE", "IB", "Cambridge", "Generic"])
    def test_mcq_has_note(self, board):
        mcq = mss.get_scheme(board)["mcq"]
        assert "note" in mcq

    @pytest.mark.parametrize("board", ["CBSE", "ICSE", "IB", "Cambridge", "Generic"])
    def test_fill_blank_has_note(self, board):
        fb = mss.get_scheme(board)["fill_blank"]
        assert "note" in fb

    @pytest.mark.parametrize("board", ["CBSE", "ICSE", "IB", "Cambridge", "Generic"])
    def test_true_false_has_marks_answer(self, board):
        tf = mss.get_scheme(board)["true_false"]
        assert "marks_answer" in tf

    @pytest.mark.parametrize("board", ["CBSE", "ICSE", "IB", "Cambridge", "Generic"])
    def test_true_false_has_marks_justification(self, board):
        tf = mss.get_scheme(board)["true_false"]
        assert "marks_justification" in tf
