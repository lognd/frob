"""Data shapes for the smart-dup pipeline (docs/modules/dup.md's Public API section).

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


# frob:doc docs/modules/dup.md#dup-error
class DupError(ErrorSet):
    """Failure values `find_clones`/`probe_equivalence` can return.

    `CoreUnavailable` is the no-silent-fallback rule (docs/modules/dup.md's Rust
    core section): rungs R3+ need `frob_core`; when it is not importable,
    callers get this error rather than a quietly degraded result.
    """

    CoreUnavailable = "frob-core native extension is not installed"
    NotPure = "Probe target has effects; observational probing refused"
    CacheCorrupt = "dup cache unreadable; delete .frob/dup.db to rebuild"
    NoGenerator = "no frob.fuzz Arbitrary generator for a probe parameter"
    SmtUnavailable = "z3-solver not installed; install with: uv pip install frob[smt]"
    SmtUnsupported = "function body is outside R7's bounded int/bool subset"


# frob:doc docs/modules/dup.md#clone-region
class CloneRegion(BaseModel):
    """A symbol, or a contiguous statement slice inside one, in match output."""

    model_config = ConfigDict(frozen=True)

    ref: str
    span: tuple[int, int]


# frob:doc docs/modules/dup.md#clone-pair
class ClonePair(BaseModel):
    """One region-to-region match at a given rung, with line alignment."""

    model_config = ConfigDict(frozen=True)

    left: CloneRegion
    right: CloneRegion
    similarity: float
    rung: str
    alignment: tuple[tuple[int, int], ...] = ()


# frob:doc docs/modules/dup.md#dup-stats
class DupStats(BaseModel):
    """Per-`find_clones` counters: how much work ran and how much was cached."""

    model_config = ConfigDict(frozen=True)

    fingerprinted: int = 0
    cache_hits: int = 0
    pairs_verified: int = 0


# frob:doc docs/modules/dup.md#clone-report
class CloneReport(BaseModel):
    """The whole result of one `find_clones` call: grouped pairs plus stats."""

    model_config = ConfigDict(frozen=True)

    groups: tuple[tuple[ClonePair, ...], ...] = ()
    stats: DupStats = DupStats()


# frob:doc docs/modules/dup.md#dup-config
class DupConfig(BaseModel):
    """The `[dup]` table in frob.toml (docs/modules/dup.md's config block).

    `region_kernel_enabled` gates the R1.5 exact-region kernel
    independently of the whole-symbol rungs (R1-R5): it is `False` by
    default so a default `frob check` never pays the extra suffix-array
    pass, even when `[dup].enforce` is already on. Set `[dup].region_kernel
    = true` in frob.toml to opt in.
    """

    model_config = ConfigDict(frozen=True)

    threshold: float = 0.85
    min_tokens: int = 40
    cache_entries: int = 200_000
    region_kernel_enabled: bool = False
    region_min_tokens: int = 15


# frob:doc docs/modules/dup.md#probe-verdict
class ProbeVerdict(BaseModel):
    """R6 result: whether two effect-free candidates behaved identically."""

    model_config = ConfigDict(frozen=True)

    left: str
    right: str
    equivalent: bool
    cases_run: int
    counterexample: Mapping[str, str] | None = None
