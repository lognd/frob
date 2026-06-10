"""Tests for simple_python package."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simple_python import add, clamp, greet, is_palindrome


def test_add_integers():
    assert add(2, 3) == 5


def test_greet_returns_string():
    result = greet("World")
    assert result == "Hello, World!"


def test_clamp_within_range():
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-1.0, 0.0, 10.0) == 0.0
    assert clamp(11.0, 0.0, 10.0) == 10.0


def test_is_palindrome():
    assert is_palindrome("racecar")
    assert is_palindrome("A man a plan a canal Panama".replace(" ", ""))
    assert not is_palindrome("hello")
