"""Frob-native, cross-platform coverage refresh orchestration (T-1516).

`make coverage`/`make coverage-fast` (T-1397/T-0484) already implement this
recipe -- subprocess rc generation, `pytest --cov`, `coverage combine`,
`coverage xml`, `frob check --stamp-coverage` -- but as ~300 lines of shell
inside `Makefile`, Linux-only (`make` is not a first-class citizen on
Windows, and the recipe's own comments document real xdist-crash-recovery
and rerun-deadline shell logic this module deliberately does NOT re-derive
line for line -- see this module's own docstring note below on what is and
is not ported). `native_coverage_refresh` is the missing frob-native
equivalent for the COMMON path (touched-set incremental refresh, or a
cold-start full run): pure Python + `subprocess`, works identically on
Linux/macOS/Windows, no shell/Makefile dependency (T-1205 acceptance[3]).

T-1517's per-file content-hash cache does the heavy lifting for "never
recompute an unchanged file": `python_coverage_targets` (T-0484) already
narrows which tests a touched-set run executes, `--cov-append` preserves
untouched files' PROCESS-level coverage data across that narrower run, and
`frob.gates._coverage.stamp_coverage` (wired in T-1517) backfills any file
this run did not measure at all from the persisted cache before writing
the lock -- this module's own job is narrower: decide whether a refresh is
needed at all, and if so, drive the actual `pytest`/`coverage` subprocess
calls and the final stamp, all from one Python entry point instead of a
Makefile target.

Deliberately deferred, not ported here (disclosed rather than silently
dropped, T-1205's own Done report and this ticket's follow-up residue):
the Makefile recipe's xdist-crash serial-rerun recovery
(`docs/guides/testing.md`, `tests/unit/test_makefile_coverage.py`'s
`TestCombineRecoversDisjointSessions`) and its configurable rerun-deadline
knobs (`COVERAGE_RERUN_DEADLINE`/`COVERAGE_XDIST_DEADLINE`) -- real,
already-hardened resilience against a specific parallel-run flake class
that would take a dedicated ticket of its own to re-derive faithfully in
Python rather than risk a subtly wrong port (that ticket is T-1672). A
caller that needs the full Makefile recipe's resilience still has it via
`make coverage`/`make coverage-fast` directly, unaffected by this module.

T-1676 removed the all-passing-tests requirement this module used to
impose: a non-zero pytest exit no longer discards the run. The suite
VERDICT and the coverage ARTIFACT are independent results, and a failing
test does not invalidate the coverage recorded for the thousands that
passed -- the field incident was a 7m32s full run, 8622 of 8654 tests
green, that produced no `coverage.xml` at all because one xdist worker was
OOM-killed. Such a run is now stamped, marked degraded in
`.frob/coverage-run.json`, and reported loudly. Accepting it is safe
because `stamp_coverage`'s independent `module_join_fraction` deflation
floor still refuses a coverage.xml that was genuinely truncated, and
`write_coverage_lock`'s ratchet still refuses to lower a committed floor.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result
from typani.unit import Unit

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.testing._incremental_coverage import python_coverage_targets

if TYPE_CHECKING:
    from frob.graph import GraphSnapshot

_log = get_logger(__name__)

#: The package this repo's own coverage recipe measures (mirrors
#: `Makefile`'s `--cov=src/frob`) -- the one repo-specific constant this
#: module hardcodes; a caller measuring a different package passes its own
#: `cov_target`.
# frob:ticket T-1516
_DEFAULT_COV_TARGET = "src/frob"


# frob:ticket T-1516
# frob:doc docs/modules/testing.md#public-api
class CoverageRefreshError(ErrorSet):
    """Failure values `native_coverage_refresh` can return."""

    PytestRefused = "the pytest subprocess could not be spawned at all"
    CoverageXmlFailed = "`coverage xml` could not produce coverage.xml"
    StampFailed = "the post-run stamp_coverage call failed"


#: Where `native_coverage_refresh` records the provenance of the run that
#: produced the current `coverage.xml` (T-1676) -- specifically whether the
#: suite was RED while it was measured. Consumers that need to know how far
#: to trust the artifact read this; nothing else in the tree records it.
# frob:ticket T-1676
_RUN_PROVENANCE_REL = ".frob/coverage-run.json"


# frob:ticket T-1676
@dataclass(frozen=True)
class _PytestPass:
    """The outcome of one pytest pass (T-1676).

    `ran` is whether pytest executed at all (False = the "nothing touched,
    only restamp" path). `exit_code` is its status, `None` when it did not
    run. `degraded` means it ran and exited non-zero -- the coverage data it
    produced is real but was measured against a RED suite, so a symbol whose
    test failed early under-reports.

    The whole point of the type (T-1676) is that a non-zero pytest exit is
    no longer conflated with "this pass produced nothing": the suite VERDICT
    and the coverage ARTIFACT are independent results, and discarding 8622
    passing tests' coverage because one test failed threw away the
    measurement the caller actually asked for."""

    ran: bool
    degraded: bool
    exit_code: int | None


# frob:ticket T-1516
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_full_run_when_no_stamp_exists  # noqa: E501
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_incremental_run_uses_touched_set_targets  # noqa: E501
def _pytest_argv(
    *,
    targets: tuple[str, ...],
    cov_target: str,
    append: bool,
) -> list[str]:
    """The `pytest` argv for one refresh pass (T-1516).

    `append=True` (an incremental, touched-set-restricted pass) adds
    `--cov-append` so a PRIOR full run's per-file data for every file this
    pass does not itself re-execute stays intact -- the same contract
    `make coverage-fast` already relies on (`_incremental_coverage.py`'s
    own module docstring). `targets` empty with `append=False` means a
    full, unrestricted suite run (cold start or `--full`)."""
    argv = [
        "pytest",
        f"--cov={cov_target}",
        "--cov-report=",
    ]
    if append:
        argv.append("--cov-append")
    argv.extend(targets)
    return argv


# frob:ticket T-1676
def _spawn(argv: list[str], *, cwd: Path) -> Result[subprocess.CompletedProcess, Unit]:
    """`guarded_subprocess_run` with the refused-spawn case collapsed to
    `Err` (T-1676) -- the one seam every subprocess in this module goes
    through, so "did not run at all" is distinguishable from "ran and
    exited non-zero" by every caller that cares about the difference.

    `_run` (below) is the pass/fail reading of this for callers where a
    non-zero exit really does mean no usable output; `_pytest_outcome` is
    the reading for callers where it does not."""
    guarded = guarded_subprocess_run(argv, cwd=str(cwd), check=False)
    if guarded.is_err:
        _log.error("coverage_refresh: %s refused (exec disabled)", " ".join(argv))
        return Err(Unit())
    return Ok(guarded.danger_ok)


# frob:ticket T-1516
def _run(argv: list[str], *, cwd: Path) -> Result[subprocess.CompletedProcess, Unit]:
    """`_spawn`, collapsed to a plain pass/fail `Result` (T-1516) -- for a
    subprocess whose non-zero exit genuinely means it produced nothing
    usable (`coverage xml`). Since T-1676 the pytest passes deliberately do
    NOT use this: a red suite still produces valid coverage data."""
    spawned = _spawn(argv, cwd=cwd)
    if spawned.is_err:
        return Err(Unit())
    proc = spawned.danger_ok
    if proc.returncode != 0:
        _log.error("coverage_refresh: %s exited %d", " ".join(argv), proc.returncode)
        return Err(Unit())
    return Ok(proc)


# frob:ticket T-1676
def _pytest_outcome(argv: list[str], *, cwd: Path) -> Result[_PytestPass, Unit]:
    """Run one pytest pass and classify its exit (T-1676).

    `Err(Unit())` means pytest never ran -- a refused spawn under
    `FROB_DISABLE_EXEC=1`. That is the ONLY case where there is genuinely no
    measurement to keep, and the only one that still aborts the refresh.

    A non-zero exit is `Ok(_PytestPass(ran=True, degraded=True, ...))`: the
    tests that ran still wrote their coverage data, and that data is what
    the caller asked for. It is logged at ERROR so a red suite stays as
    visible as it was when it aborted the run -- it simply no longer
    vetoes the artifact."""
    spawned = _spawn(argv, cwd=cwd)
    if spawned.is_err:
        return Err(Unit())
    code = spawned.danger_ok.returncode
    if code != 0:
        _log.error(
            "coverage_refresh: %s exited %d -- the suite was RED while coverage "
            "was measured; KEEPING the coverage data (T-1676) and marking this "
            "run degraded. Symbols whose tests failed early under-report; treat "
            "a NEW low-coverage finding from this run as suspect until the "
            "suite is green",
            " ".join(argv),
            code,
        )
    return Ok(_PytestPass(ran=True, degraded=code != 0, exit_code=code))


# frob:ticket T-1516
def _run_full_suite(
    root: Path, *, cov_target: str, reason: str
) -> Result[_PytestPass, CoverageRefreshError]:
    """Run the WHOLE suite under coverage, no target restriction (T-1516) --
    the `full=True`/cold-start branch of `native_coverage_refresh`, split out
    to keep that function under the ARCH001 line threshold. `reason` is a
    human-readable log label only (e.g. "explicit --full")."""
    _log.info("coverage_refresh: %s -- running the full suite", reason)
    argv = _pytest_argv(targets=(), cov_target=cov_target, append=False)
    ran = _pytest_outcome(argv, cwd=root)
    if ran.is_err:
        return Err(CoverageRefreshError.PytestRefused)
    return Ok(ran.danger_ok)


# frob:ticket T-1516
def _run_incremental_or_restamp(
    root: Path,
    snapshot: GraphSnapshot,
    *,
    base: str,
    cov_target: str,
    xml_path: Path,
) -> Result[_PytestPass, CoverageRefreshError]:
    """The non-cold-start branch of `native_coverage_refresh` (T-1516),
    split out to keep that function under the ARCH001 line threshold.

    Restricts the pytest run to `python_coverage_targets`'s touched-set
    selection (T-0484) with `--cov-append` when there is one; an empty
    selection either falls back to a full run (no `coverage.xml` yet -- true
    cold start in disguise) or skips pytest entirely and only re-stamps.
    Returns whether pytest actually ran, so the caller knows whether to run
    `coverage xml` afterward."""
    targets = python_coverage_targets(root, snapshot, base)
    if targets:
        _log.info("coverage_refresh: incremental run, %d target(s)", len(targets))
        argv = _pytest_argv(targets=targets, cov_target=cov_target, append=True)
        ran = _pytest_outcome(argv, cwd=root)
        if ran.is_err:
            return Err(CoverageRefreshError.PytestRefused)
        return Ok(ran.danger_ok)
    if not xml_path.exists():
        return _run_full_suite(
            root,
            cov_target=cov_target,
            reason="nothing touched and no coverage.xml yet",
        )
    _log.info(
        "coverage_refresh: nothing touched selects a python test -- "
        "restamping existing coverage.xml only"
    )
    return Ok(_PytestPass(ran=False, degraded=False, exit_code=None))


# frob:ticket T-1516
def _run_pytest_pass(
    root: Path,
    snapshot: GraphSnapshot,
    *,
    base: str,
    full: bool,
    cold_start: bool,
    cov_target: str,
    xml_path: Path,
) -> Result[_PytestPass, CoverageRefreshError]:
    """Dispatch to `_run_full_suite` or `_run_incremental_or_restamp` (T-1516),
    split out of `native_coverage_refresh` to keep it under the ARCH001
    line threshold. Returns the pass outcome (whether pytest ran, and
    whether it ran against a red suite)."""
    if full or cold_start:
        return _run_full_suite(
            root,
            cov_target=cov_target,
            reason=(
                "explicit --full" if full else "cold start (no coverage-stamp yet)"
            ),
        )
    return _run_incremental_or_restamp(
        root, snapshot, base=base, cov_target=cov_target, xml_path=xml_path
    )


# frob:ticket T-1676
def _write_run_provenance(root: Path, outcome: _PytestPass) -> None:
    """Record whether the run that produced the current `coverage.xml` was
    measured against a red suite (T-1676).

    Deliberately best-effort and side-effect-only: the coverage data itself
    is already written and stamped by the time this runs, and losing the
    provenance note must never turn a successful refresh into a failure.
    A failed write is logged, not returned -- there is nothing the caller
    could usefully do about it.

    Writing this on EVERY run, degraded or not, is the point: a stale
    "degraded" note left over from a previous run would be read as a
    property of the current artifact."""
    record = {
        "degraded": outcome.degraded,
        "pytest_exit_code": outcome.exit_code,
        "pytest_ran": outcome.ran,
    }
    path = root / _RUN_PROVENANCE_REL
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.warning("coverage_refresh: could not write %s: %s", path, exc)
        return
    if outcome.degraded:
        _log.warning(
            "coverage_refresh: coverage.xml recorded as DEGRADED in %s "
            "(pytest exit %s) -- the artifact is usable but was measured "
            "against a red suite",
            _RUN_PROVENANCE_REL,
            outcome.exit_code,
        )


# frob:ticket T-1516
# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_full_run_when_no_stamp_exists  # noqa: E501
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_incremental_run_uses_touched_set_targets  # noqa: E501
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_nothing_touched_only_restamps  # noqa: E501
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_red_suite_keeps_coverage_data  # noqa: E501
def native_coverage_refresh(
    root: Path,
    snapshot: GraphSnapshot,
    *,
    base: str = "HEAD",
    full: bool = False,
    cov_target: str = _DEFAULT_COV_TARGET,
) -> Result[Unit, CoverageRefreshError]:
    """Refresh `root`'s coverage data and stamp, in pure Python (T-1516,
    T-1205 acceptance[3]/[4]) -- `subprocess` calls to `pytest`/`coverage`
    plus a final `stamp_coverage`, no `Makefile`/shell dependency.

    `full=True` (or no `.frob/coverage-stamp` yet -- a genuine cold start,
    since there is nothing to diff an incremental run against) runs the
    WHOLE suite under coverage; otherwise this restricts the pytest run to
    `python_coverage_targets(root, snapshot, base)`'s touched-set
    selection (T-0484) with `--cov-append`, so an unrelated file's
    coverage data is never re-executed to produce it (T-1517's cache
    backfills it into the merged `CoverageData` at stamp time regardless).
    An empty touched-set selection with an existing `coverage.xml` skips
    the pytest run entirely and only re-stamps (nothing python-related
    changed, but the stamp's own file-hash record may still need
    refreshing for non-python or non-source changes) -- the cheapest
    possible "nothing to run" path.

    Always ends with `frob.gates._coverage.stamp_coverage(root, snapshot)`
    (deferred import: `frob.gates.__init__` imports `frob.testing`
    indirectly via `_coverage_wait`, so a module-level import here would
    close the same cycle T-1517's `stamp_coverage` wiring already works
    around) -- a caller never has to remember the separate stamp step.
    """
    from frob.gates._coverage import load_stamp, stamp_coverage

    cold_start = load_stamp(root) is None
    xml_path = root / "coverage.xml"

    pass_result = _run_pytest_pass(
        root,
        snapshot,
        base=base,
        full=full,
        cold_start=cold_start,
        cov_target=cov_target,
        xml_path=xml_path,
    )
    if pass_result.is_err:
        return Err(pass_result.danger_err)
    outcome = pass_result.danger_ok

    if outcome.ran:
        # `--cov-report=` above deliberately disables pytest-cov's own
        # report generation (mirrors the Makefile recipe's own separate
        # `coverage xml` step) so both the full and incremental branches
        # converge on one shared `coverage xml -i` call here -- `-i`
        # (ignore-errors) matches the Makefile's own flag, tolerating a
        # source file coverage.py traced mid-run but that no longer
        # exists by the time `xml` runs (T-1320).
        xml_ran = _run(["coverage", "xml", "-i"], cwd=root)
        if xml_ran.is_err:
            return Err(CoverageRefreshError.CoverageXmlFailed)

    stamped = stamp_coverage(root, snapshot)
    if stamped.is_err:
        _log.error("coverage_refresh: stamp_coverage failed: %s", stamped.danger_err)
        return Err(CoverageRefreshError.StampFailed)
    _write_run_provenance(root, outcome)
    return Ok(Unit())


__all__ = [
    "CoverageRefreshError",
    "native_coverage_refresh",
]
