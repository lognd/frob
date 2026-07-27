"""Data shapes for frob.gates (docs/modules/gates.md is authoritative).

Every model is a frozen pydantic ``BaseModel`` so a `GateReport` can be
compared, cached, and serialized by identity-of-value -- the same posture
`frob.graph._models` and `frob.tickets._models` take.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_models.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

__all__ = [
    "CoverageData",
    "CoverageError",
    "DebtEntry",
    "DeprecatedEntry",
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


# frob:doc docs/modules/gates.md#debt-gate-t-0412
class DebtEntry(BaseModel):
    """One outstanding `frob:debt` entry, as `frob debt` lists it (T-0412):
    the rule it suppresses, where it lives, the ticket that owns it, its
    expiry (if any), and whether it has already expired."""

    model_config = ConfigDict(frozen=True)

    rule: str
    site: str
    ticket: str
    until: str
    expired: bool


# frob:doc docs/modules/gates.md#deprecated-gate-t-0576
class DeprecatedEntry(BaseModel):
    """One outstanding `frob:deprecated` entry, as `frob.gates.list_deprecated`
    reports it (T-0576): the symbol carrying the sunset, its owning ticket,
    the sunset date, and whether that date has already passed."""

    model_config = ConfigDict(frozen=True)

    symref: str
    since: str
    sunset: str
    ticket: str
    expired: bool


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
    # T-0289: the raw measured value the violation is about (currently only
    # ARCH001's function line count). Lets `_match_waiver` honor a waiver's
    # `ceiling=N` attribute -- a `frob:waive ARCH001 reason="..." ceiling=50`
    # only suppresses while `metric <= 50`; grow the function past 50 lines
    # and the waiver stops matching, so the exception can't silently rot.
    metric: int | None = None


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
    """A recorded dup+xref sweep over a ticket's scope at `frob ticket start` time.

    T-0584: `partial`/`pending_patterns` support a bounded, resumable sweep on
    slow mounts (see `gates/_prework.py::sweep_ticket`'s budget_seconds). A
    sweep that ran out of budget mid-scan records `partial=True` and the
    scope patterns it did not get to in `pending_patterns`, instead of
    either blocking forever (the old fully-synchronous-only shape) or
    silently dropping the unfinished patterns. `prework_gate` treats a
    partial sweep whose `digest` still matches the ticket's current scope
    digest as provisionally clean (not a PRE001 violation) -- the whole
    point being that `frob ticket sweep` can never again be a catch-22 where
    finishing the sweep requires foreground time the sweep itself does not
    have.
    """

    model_config = ConfigDict(frozen=True)

    date: date
    dup_findings: int
    xref_hits: tuple[str, ...]
    digest: str
    partial: bool = False
    pending_patterns: tuple[str, ...] = ()


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
    # TEST009 (T-0225): min e2e edges owed per `.strata` design file -- the
    # design-artifact counterpart to `min_integration`, since design ids are
    # exempt from TEST003's package-level integration count.
    min_design_e2e: int = 1
    unit_branch_cov: int = 90
    module_line_cov: int = 85
    system_line_cov: int = 80
    # TEST007: require a pairwise integration test per cross-package
    # uses-contract dependency (opt-in; off by default). (T-0017)
    pair_integration: bool = False
    # T-0589: tie TEST001 credit to real per-symbol branch coverage, not
    # just a name/edge match -- when a symbol's `frob:tests` edge or
    # convention-named test satisfies TEST001 on its own, but coverage.xml
    # shows the symbol was MEASURED (its file is covered) and never
    # actually EXECUTED (symbol_branch == 0.0%, the T-0557 "no entry
    # despite a measured file" signal `_test005_symbols` already uses),
    # that is the def-myfunc-pass-shaped gap docs/audits/gates-accounting.md
    # B1 describes: a test bound by name/edge that never really calls the
    # function. Opt-in and off by default (a global flip would require the
    # compat survey T-0589's own body calls for, which needs a coverage
    # stamp this repo does not carry by default in an agent worktree, and
    # would immediately promote every one of T-0875's TEST005 warnings to
    # a TEST001 ERROR without that survey) -- flip once T-0875's TEST005
    # burn-down has cleared enough debt that a survey is cheap to run.
    require_branch_coverage_for_test001: bool = False


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
    # frob:ticket T-0464
    # `source_sha` above is only the sha of coverage.xml itself, not of the
    # source it measured -- neither field alone catches a coverage.xml that
    # is stale or deflated relative to the working tree it claims to
    # describe. `stale_by_mtime` is True when coverage.xml is older than the
    # newest known source file on disk. `module_join_fraction` is the share
    # of known python modules that actually show up in `module_line` --
    # a run that silently drops subprocess coverage (T-0464's root cause)
    # measures only the main pytest process, so most modules never appear
    # in coverage.xml at all even though `root_join_ok` is True (some data
    # did join). Both are advisory (TEST011, WARN) signals, not floors.
    stale_by_mtime: bool = False
    module_join_fraction: float = 1.0


# frob:doc docs/modules/gates.md#error-types
class GateError(ErrorSet):
    """Failure values `run_gates` and its loading steps can return."""

    GraphUnavailable = "Graph build failed; gates cannot run"
    GitFailed = "git diff/merge-base failed"
    NoTicketContext = "Scope gate requested but no active ticket resolved"
    QueueUnavailable = "Ticket queue failed to load"
    ConfigMalformed = "frob.toml [testing]/[[system]]/[gates] table is malformed"
    WriteFailed = "Could not write gate state to disk"
    # T-0431: FROB_WORKTREE is leased to a different worktree than the cwd
    # a stamping command (--stamp-baseline/--stamp-coverage) is running in.
    WorktreeLeaseViolation = (
        "FROB_WORKTREE is leased to a different worktree than this command's cwd"
    )


# frob:doc docs/modules/gates.md#error-types
class CoverageError(ErrorSet):
    """Failure values `load_coverage`/`stamp_coverage` can return."""

    Missing = "No coverage.xml/stamp found; run make coverage"
    Malformed = "coverage.xml could not be parsed"
