"""Data shapes for `frob.perf` (docs/perf.md), frozen pydantic per project
convention so artifacts and reports compare/hash by value, not identity.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

__all__ = [
    "HeatEntry",
    "HeatReport",
    "PerfError",
    "ProfileArtifact",
]


# frob:ticket T-0021
class PerfError(ErrorSet):
    """Failure values every `frob.perf` function can return."""

    SpawnFailed = "Profiled command could not be started"
    NoArtifact = "No profile artifact found; run frob perf profile first"
    BadArtifact = "pstats artifact unreadable"


# frob:ticket T-0021
class ProfileArtifact(BaseModel):
    """One completed `frob perf profile` run: identity, argv, and totals.

    Content-addressed under `.frob/perf/<sha>.pstats`; this model is the
    meta sidecar written alongside the raw pstats file (`.frob/perf/<sha>.json`).
    """

    model_config = ConfigDict(frozen=True)

    sha: str
    argv: tuple[str, ...]
    created: datetime
    total_s: float

    @property
    # frob:ticket T-0021
    def pstats_name(self) -> str:
        """The pstats file's basename under `.frob/perf/`."""
        return f"{self.sha}.pstats"

    @property
    # frob:ticket T-0021
    def meta_name(self) -> str:
        """The meta sidecar's basename under `.frob/perf/`."""
        return f"{self.sha}.json"


# frob:ticket T-0021
class HeatEntry(BaseModel):
    """One symbol's profiled cost, ranked by cumulative time desc."""

    model_config = ConfigDict(frozen=True)

    ref: str
    cum_s: float
    self_s: float
    ncalls: int
    smells: tuple[str, ...] = ()


# frob:ticket T-0021
class HeatReport(BaseModel):
    """The full `frob perf heat` join result: ranked entries plus spillover."""

    model_config = ConfigDict(frozen=True)

    entries: tuple[HeatEntry, ...]
    unattributed_s: float
