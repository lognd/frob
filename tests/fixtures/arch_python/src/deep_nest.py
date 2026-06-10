"""A module with deeply nested code to trigger nesting warnings."""

from __future__ import annotations


def process_matrix(matrix: list[list[list[list[list[int]]]]]) -> int:
    """Process a 5-dimensional matrix with deep nesting."""
    total = 0
    for level_a in matrix:
        for level_b in level_a:
            for level_c in level_b:
                for level_d in level_c:
                    for value in level_d:
                        if value > 0:
                            total += value
    return total
