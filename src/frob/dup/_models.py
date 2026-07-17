"""Data shapes for the smart-dup pipeline (docs/dup.md's Public API section).

Every model is a frozen pydantic `BaseModel`, matching `frob.graph._models`'
posture: a `CloneReport` must compare and cache by identity-of-value, not
identity-of-object, so the DUP001/DUP002 gate rules can be pure functions
over it.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict
from typani import ErrorSet

__all__ = [
    "CloneRegion",
    "ClonePair",
    "CloneReport",
    "DupConfig",
    "DupError",
    "DupStats",
    "ProbeVerdict",
]


class DupError(ErrorSet):
    """Failure values `find_clones`/`probe_equivalence` can return.

    `CoreUnavailable` is the no-silent-fallback rule (docs/dup.md's Rust
    core section): rungs R3+ need `frob_core`; when it is not importable,
    callers get this error rather than a quietly degraded result.
    """

    CoreUnavailable = "frob-core native extension is not installed"
    NotPure = "Probe target has effects; observational probing refused"
    CacheCorrupt = "dup cache unreadable; delete .frob/dup.db to rebuild"
    NoGenerator = "no frob.fuzz Arbitrary generator for a probe parameter"


class CloneRegion(BaseModel):
    """A symbol, or a contiguous statement slice inside one, in match output."""

    model_config = ConfigDict(frozen=True)

    ref: str
    span: tuple[int, int]


class ClonePair(BaseModel):
    """One region-to-region match at a given rung, with line alignment."""

    model_config = ConfigDict(frozen=True)

    left: CloneRegion
    right: CloneRegion
    similarity: float
    rung: str
    alignment: tuple[tuple[int, int], ...] = ()


class DupStats(BaseModel):
    """Per-`find_clones` counters: how much work ran and how much was cached."""

    model_config = ConfigDict(frozen=True)

    fingerprinted: int = 0
    cache_hits: int = 0
    pairs_verified: int = 0


class CloneReport(BaseModel):
    """The whole result of one `find_clones` call: grouped pairs plus stats."""

    model_config = ConfigDict(frozen=True)

    groups: tuple[tuple[ClonePair, ...], ...] = ()
    stats: DupStats = DupStats()


class DupConfig(BaseModel):
    """The `[dup]` table in frob.toml (docs/dup.md's config block)."""

    model_config = ConfigDict(frozen=True)

    threshold: float = 0.85
    min_tokens: int = 40
    cache_entries: int = 200_000


class ProbeVerdict(BaseModel):
    """R6 result: whether two effect-free candidates behaved identically."""

    model_config = ConfigDict(frozen=True)

    left: str
    right: str
    equivalent: bool
    cases_run: int
    counterexample: Mapping[str, str] | None = None
