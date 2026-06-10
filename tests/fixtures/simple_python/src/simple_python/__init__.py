"""Simple Python package with clean, typed functions."""
from __future__ import annotations


def add(x: int, y: int) -> int:
    """Return the sum of two integers."""
    return x + y


def greet(name: str) -> str:
    """Return a greeting string."""
    return f"Hello, {name}!"


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to the range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def is_palindrome(s: str) -> bool:
    """Return True if s reads the same forwards and backwards."""
    cleaned = s.lower().replace(" ", "")
    return cleaned == cleaned[::-1]
