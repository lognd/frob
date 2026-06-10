"""Alpha module with a function that has a duplicate in beta.py."""

from __future__ import annotations


def process_items(items: list[float], factor: float) -> float:
    """Accumulate scaled items and return total."""
    running = 0.0
    for item in items:
        running += item * factor
    if running < 0:
        running = 0.0
    if running > 1e9:
        running = 1e9
    return running
