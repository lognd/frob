"""Beta module with a function that duplicates logic from alpha.py."""

from __future__ import annotations


def handle_entries(entries: list[float], multiplier: float) -> float:
    """Accumulate scaled entries and return total."""
    running = 0.0
    for entry in entries:
        running += entry * multiplier
    if running < 0:
        running = 0.0
    if running > 1e9:
        running = 1e9
    return running
