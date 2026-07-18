"""Data shapes for frob.gates (docs/modules/gates.md is authoritative).

Every model is a frozen pydantic ``BaseModel`` so a `GateReport` can be
compared, cached, and serialized by identity-of-value -- the same posture
`frob.graph._models` and `frob.tickets._models` take.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

__all__ = [
    "CoverageData",
    "CoverageError",
    "GateConfig",
    "GateError",
    "GateReport",
    "GateStats",
    "PreworkSweep",
    "Severity",
    "SystemSpec",
    "TestPolicy",
    "Violation",
    "WaiverRef",
]


# frob:doc docs/modules/gates.md#data-models
class Severity(StrEnum):
    """A violation's exit-code weight: `error` fails `frob check`, `warn` does not."""

    ERROR = "error"
    WARN = "warn"


# frob:doc docs/modules/gates.md#data-models
class WaiverRef(BaseModel):
    """The `frob:waive` edge that suppressed a violation, kept for the report."""

    model_config = ConfigDict(frozen=True)

    site: str
    reason: str


# frob:doc docs/modules/gates.md#data-models
class Violation(BaseModel):
    """One gate finding: rule, site, and a message that embeds its own remedy."""

    model_config = ConfigDict(frozen=True)

    rule: str
    severity: Severity
    file: str
    line: int
    message: str
    waived: WaiverRef | None = None
    # frob:ticket T-0148
    # Set only where a violation is precisely about ONE symbol (currently
    # TEST005's per-symbol branch-coverage check) so `_match_waiver` can
    # require an exact `path::qualname` waiver match instead of the
    # file-wide match every other rule still uses -- without this,
    # `frob:waive` placement above a specific symbol is cosmetic: the
    # match still falls back to file-only equality and one directive
    # waives every violation of that rule anywhere in the file (the
    # blanket-waiver bug T-0148's review caught). Left None for rules
    # that are inherently file/module-scoped (module-line TEST005,
    # PERF, TEST006, ...), where a file-level waiver is the correct and
    # intentional precision, not a shortcut.
    symref: str | None = None


# frob:doc docs/modules/gates.md#data-models
class GateStats(BaseModel):
    """Per-gate counters: how many violations, how long, and whether it ran."""

    model_config = ConfigDict(frozen=True)

    counts: Mapping[str, int] = {}
    timing_s: Mapping[str, float] = {}
    skipped: tuple[str, ...] = ()


# frob:doc docs/modules/gates.md#data-models
class GateReport(BaseModel):
    """The merged result of `run_gates`: kept violations, waived ones, and stats."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[Violation, ...]
    waived: tuple[Violation, ...]
    stats: GateStats


# frob:doc docs/modules/gates.md#data-models
# frob:doc docs/guides/extending/gate-rule-families.md#gate-rule-families
class GateConfig(BaseModel):
    """Everything `run_gates` needs to load state and select which gates run."""

    model_config = ConfigDict(frozen=True)

    root: str
    base: str = "main"
    ticket: str | None = None
    gates: frozenset[str] = frozenset()


# frob:doc docs/modules/gates.md#data-models
class PreworkSweep(BaseModel):
    """A recorded dup+xref sweep over a ticket's scope at `frob ticket start` time."""

    model_config = ConfigDict(frozen=True)

    date: date
    dup_findings: int
    xref_hits: tuple[str, ...]
    digest: str


# frob:doc docs/modules/gates.md#data-models
class SystemSpec(BaseModel):
    """One `[[system]]` entry: an e2e-tested surface and its coverage scope."""

    model_config = ConfigDict(frozen=True)

    id: str
    entrypoint: str
    min_e2e: int = 1
    paths: tuple[str, ...] = ()


# frob:doc docs/modules/gates.md#data-models
class TestPolicy(BaseModel):
    """The `[testing]` table: all test-obligation floors, each overridable."""

    __test__: bool = False

    model_config = ConfigDict(frozen=True)

    min_unit_cases: int = 3
    min_integration: int = 1
    unit_branch_cov: int = 90
    module_line_cov: int = 85
    system_line_cov: int = 80
    # TEST007: require a pairwise integration test per cross-package
    # uses-contract dependency (opt-in; off by default). (T-0017)
    pair_integration: bool = False


# frob:doc docs/modules/gates.md#data-models
class CoverageData(BaseModel):
    """Parsed `coverage.xml` mapped onto the snapshot: per-symbol and per-module."""

    model_config = ConfigDict(frozen=True)

    source_sha: str
    symbol_branch: Mapping[str, float] = {}
    module_line: Mapping[str, float] = {}
    # frob:ticket T-0148
    # False only when coverage.xml had classes AND the repo had known source
    # paths to join against, but every re-rooting strategy _parse_classes
    # tried (every <sources><source> entry, then the bare filename fallback)
    # matched zero of them -- the "silent zero-match" failure mode this
    # ticket exists to make loud instead of quiet. True is also the
    # trivially-correct value when there was nothing to join (no classes,
    # or no known paths to check against).
    root_join_ok: bool = True
    # The exact roots `_parse_classes` tried, in order, for diagnostics.
    attempted_roots: tuple[str, ...] = ()


# frob:doc docs/modules/gates.md#error-types
class GateError(ErrorSet):
    """Failure values `run_gates` and its loading steps can return."""

    GraphUnavailable = "Graph build failed; gates cannot run"
    GitFailed = "git diff/merge-base failed"
    NoTicketContext = "Scope gate requested but no active ticket resolved"
    QueueUnavailable = "Ticket queue failed to load"
    ConfigMalformed = "frob.toml [testing]/[[system]]/[gates] table is malformed"
    WriteFailed = "Could not write gate state to disk"


# frob:doc docs/modules/gates.md#error-types
class CoverageError(ErrorSet):
    """Failure values `load_coverage`/`stamp_coverage` can return."""

    Missing = "No coverage.xml/stamp found; run make coverage"
    Malformed = "coverage.xml could not be parsed"
