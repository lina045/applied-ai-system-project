import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_detective import validate_input, _extract_code, MAX_CODE_LENGTH


# --- validate_input ---

def test_validate_empty_string():
    assert validate_input("") is not None

def test_validate_whitespace_only():
    assert validate_input("   \n  ") is not None

def test_validate_valid_code():
    assert validate_input("def foo(): pass") is None

def test_validate_too_long():
    long_code = "x = 1\n" * (MAX_CODE_LENGTH // 6 + 1)
    assert validate_input(long_code) is not None

def test_validate_exactly_at_limit():
    # A string exactly at the limit should be accepted
    code = "a" * MAX_CODE_LENGTH
    assert validate_input(code) is None

def test_validate_one_over_limit():
    code = "a" * (MAX_CODE_LENGTH + 1)
    assert validate_input(code) is not None


# --- _extract_code ---

def test_extract_code_plain_fence():
    text = "```\nprint('hello')\n```"
    assert _extract_code(text) == "print('hello')"

def test_extract_code_python_fence():
    text = "```python\nreturn x + 1\n```"
    assert _extract_code(text) == "return x + 1"

def test_extract_code_no_fence():
    # Falls back to strip() when no fence is present
    text = "  def foo(): pass  "
    assert _extract_code(text) == "def foo(): pass"

def test_extract_code_multiline():
    text = "```python\ndef add(a, b):\n    return a + b\n```"
    assert _extract_code(text) == "def add(a, b):\n    return a + b"

def test_extract_code_ignores_prose_outside_fence():
    text = "Here is the fix:\n```python\nx = 1\n```\nHope that helps!"
    assert _extract_code(text) == "x = 1"
