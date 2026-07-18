"""Damerau-Levenshtein typosquat distance check (docs/modules/vet.md VET-JS003,
generalized across ecosystems)."""

from __future__ import annotations

from frob.logging import get_logger
from frob.vet._popular import ECOSYSTEM_POPULAR

_log = get_logger(__name__)

_MAX_DISTANCE = 1


# frob:doc docs/modules/vet.md#public-api
def damerau_levenshtein(a: str, b: str) -> int:
    """Edit distance allowing insert/delete/substitute/transpose (OSA variant)."""
    # frob:waive PERF003 reason="algorithm-inherent edit-distance DP nested scan"
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost,
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="find_typosquat 85.7% branch cover, debt T-0160"
def find_typosquat(ecosystem: str, name: str) -> str | None:
    """The popular-list name `name` is a likely typosquat of, or `None`."""
    popular = ECOSYSTEM_POPULAR.get(ecosystem)
    if not popular:
        return None
    if name in popular:
        return None
    lowered = name.lower()
    for candidate in popular:
        if lowered == candidate:
            continue
        if abs(len(lowered) - len(candidate)) > _MAX_DISTANCE:
            continue
        if damerau_levenshtein(lowered, candidate) <= _MAX_DISTANCE:
            _log.info(
                "vet: %s/%s is distance<=%d from popular package %s",
                ecosystem,
                name,
                _MAX_DISTANCE,
                candidate,
            )
            return candidate
    return None


__all__ = ["damerau_levenshtein", "find_typosquat"]
