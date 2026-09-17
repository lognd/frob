"""Positive control (T-4510): the SAME near-duplicate-method shape as
`Sample/Dup/Duplicate.cs`, in python, so `test_support_csharp.py` can
prove `find_duplicates` firing on the csharp fixture is not a false
positive of the test harness itself -- if this file's own near-duplicate
pair did not fire, the harness (not the csharp scanner) would be the
finding.
"""


def add_numbers(first, second):
    """Return first+second, shifted up and back down by one then doubled."""
    total = first
    total = total + second
    total = total + 1
    total = total - 1
    total = total * 2
    total = total / 2
    return total


def add_values(alpha, beta):
    """Return alpha+beta, shifted up and back down by one then doubled."""
    total = alpha
    total = total + beta
    total = total + 1
    total = total - 1
    total = total * 2
    total = total / 2
    return total
