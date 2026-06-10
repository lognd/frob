"""Gamma module with a clearly different function."""

from __future__ import annotations


def format_report(title: str, lines: list[str]) -> str:
    """Build a simple text report from a title and body lines."""
    header = f"=== {title} ==="
    separator = "-" * len(header)
    body = "\n".join(f"  {line}" for line in lines)
    return f"{header}\n{separator}\n{body}"
