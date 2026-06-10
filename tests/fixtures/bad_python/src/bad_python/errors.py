"""Python file with intentional errors for testing parsers."""

from __future__ import annotations

import os  # noqa: F401 -- intentional unused import for ruff F401 test


def returns_wrong_type(x: int) -> int:
    """Declared to return int but actually returns str -- triggers ty error."""
    return "not an int"  # type: ignore[return-value] marker is absent intentionally


def has_long_line() -> None:
    """Function containing a line that exceeds 88 characters to trigger ruff E501."""
    very_long_variable_name_that_makes_this_line_exceed_the_limit = (
        "this string makes the line go well past eighty-eight characters total"
    )


def clean_function(items: list[int]) -> int:
    """A valid function with no issues."""
    total = 0
    for item in items:
        total += item
    return total
