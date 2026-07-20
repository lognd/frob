"""Data models and error type for `frob.clean` (T-0457, docs/modules/clean.md)."""

from __future__ import annotations

import enum
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet


# frob:doc docs/modules/clean.md#public-api
class CleanTier(enum.IntEnum):
    """The three cumulative cleanup tiers `frob clean` operates at, each a
    superset of the one before it (SAFE subset of ALL subset of DEEP)."""

    SAFE = 1
    ALL = 2
    DEEP = 3


# frob:doc docs/modules/clean.md#public-api
class CleanError(ErrorSet):
    """Failure values `frob.clean.clean`/`scan` can return."""

    NotARepo = "root is not inside a git repository or worktree"
    RemoveFailed = "an OS-level error occurred while removing a matched artifact"


# frob:doc docs/modules/clean.md#public-api
class ArtifactEntry(BaseModel):
    """One matched cleanup candidate: its path, tier, the rule that matched it,
    and its reclaimable size in bytes (directories summed recursively)."""

    model_config = {}

    path: Path
    tier: CleanTier
    rule: str
    size_bytes: int
    is_dir: bool


# frob:doc docs/modules/clean.md#public-api
class CleanReport(BaseModel):
    """The result of a `scan`/`clean` call: what matched, what was actually
    removed (empty when `dry_run`), and what was skipped because it is
    git-tracked (the fail-safe path -- surfaced, never silently dropped)."""

    model_config = {}

    tier: CleanTier
    dry_run: bool
    entries: list[ArtifactEntry] = []
    skipped_tracked: list[Path] = []

    # frob:doc docs/modules/clean.md#public-api
    # frob:tests tests/test_clean.py::test_clean_execute_removes_matched
    @property
    def reclaimed_bytes(self) -> int:
        """Total bytes represented by every matched (not skipped) entry."""
        return sum(e.size_bytes for e in self.entries)

    # frob:doc docs/modules/clean.md#public-api
    # frob:tests tests/test_clean.py::test_scan_tier1_matches_expected
    @property
    def count(self) -> int:
        """Number of matched (not skipped) entries."""
        return len(self.entries)
