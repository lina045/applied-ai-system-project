import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic_utils import reset_game
from app import parse_guess, check_guess, update_score


# --- reset_game tests (logic_utils) ---

def test_new_game_resets_status_to_playing():
    state = {"attempts": 5, "secret": 42, "status": "won", "history": [10, 20, 42]}
    reset_game(state, 1, 100)
    assert state["status"] == "playing"

def test_new_game_resets_attempts_to_zero():
    state = {"attempts": 5, "secret": 42, "status": "lost", "history": [1, 2, 3]}
    reset_game(state, 1, 100)
    assert state["attempts"] == 0

def test_new_game_clears_history():
    state = {"attempts": 3, "secret": 42, "status": "won", "history": [10, 20, 42]}
    reset_game(state, 1, 100)
    assert state["history"] == []

def test_new_game_secret_within_range():
    state = {"attempts": 0, "secret": 99, "status": "playing", "history": []}
    reset_game(state, 1, 20)
    assert 1 <= state["secret"] <= 20


# --- parse_guess tests ---
# These simulate what happens when the form is submitted (Enter key or button click).
# Before the fix, pressing Enter never reached this logic because submit was always False.

def test_parse_guess_valid_number():
    ok, value, err = parse_guess("42")
    assert ok is True
    assert value == 42
    assert err is None

def test_parse_guess_empty_string():
    # Pressing Enter with an empty field should return a helpful error, not crash
    ok, value, err = parse_guess("")
    assert ok is False
    assert value is None
    assert err == "Enter a guess."

def test_parse_guess_none():
    ok, value, err = parse_guess(None)
    assert ok is False
    assert value is None
    assert err == "Enter a guess."

def test_parse_guess_non_numeric():
    ok, value, err = parse_guess("abc")
    assert ok is False
    assert value is None
    assert err == "That is not a number."

def test_parse_guess_decimal_truncates():
    # "7.9" should be accepted and truncated to 7
    ok, value, _ = parse_guess("7.9")
    assert ok is True
    assert value == 7


# --- check_guess tests ---
# These verify the outcome logic that runs after a valid form submission.

def test_check_guess_correct():
    outcome, _ = check_guess(50, 50)
    assert outcome == "Win"

def test_check_guess_too_high():
    outcome, _ = check_guess(60, 50)
    assert outcome == "Too High"

def test_check_guess_too_low():
    outcome, _ = check_guess(40, 50)
    assert outcome == "Too Low"


# --- Full submit flow test ---
# Simulates exactly what happens at line 149 after the Enter-key fix:
# parse → check → update_score, all in sequence.

def test_full_submit_flow_win():
    ok, guess_int, _ = parse_guess("42")
    assert ok is True

    outcome, _ = check_guess(guess_int, 42)
    assert outcome == "Win"

    score = update_score(0, outcome, attempt_number=1)
    assert score > 0  # winning should add points

def test_full_submit_flow_wrong_guess():
    ok, guess_int, _ = parse_guess("30")
    assert ok is True

    outcome, _ = check_guess(guess_int, 42)
    assert outcome == "Too Low"

def test_full_submit_flow_invalid_input_does_not_reach_check_guess():
    # If Enter is pressed with bad input, parse_guess returns ok=False
    # and check_guess should never be called — game state stays unchanged.
    ok, guess_int, _ = parse_guess("")
    assert ok is False
    assert guess_int is None  # nothing to pass to check_guess
