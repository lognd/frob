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
Python rather than risk a subtly wrong port. `native_coverage_refresh`
surfaces any pytest/coverage subprocess failure as a plain `Err` instead;
a caller that needs the full Makefile recipe's resilience still has it via
`make coverage`/`make coverage-fast` directly, unaffected by this module.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import subprocess
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
# frob:waive WIRE001 reason="a typani ErrorSet class is never referenced call-shaped (ClassName(...)) -- callers spell it ClassName.Member (bare attribute access) and the class only otherwise appears in a Result[..., ClassName] annotation, also paren-free; WIRE001's text scan structurally cannot see either shape (src/frob/gates/_wire.py's _is_reached_outside_diff_tests). The function that actually returns this error (native_coverage_refresh) IS wired: called from _coverage_wait.py's _run_native_refresh. Gate follow-up filed as T-1527." follow_up="T-1527"  # noqa: E501
class CoverageRefreshError(ErrorSet):
    """Failure values `native_coverage_refresh` can return."""

    PytestFailed = "the pytest subprocess exited non-zero"
    CoverageXmlFailed = "`coverage xml` could not produce coverage.xml"
    StampFailed = "the post-run stamp_coverage call failed"


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


# frob:ticket T-1516
def _run(argv: list[str], *, cwd: Path) -> Result[subprocess.CompletedProcess, Unit]:
    """`guarded_subprocess_run`, collapsed to a plain pass/fail `Result`
    (T-1516) -- a refused spawn (`FROB_DISABLE_EXEC=1`) and a real nonzero
    exit are both "this subprocess did not succeed" from this module's own
    callers' point of view; only the log line distinguishes them."""
    guarded = guarded_subprocess_run(argv, cwd=str(cwd), check=False)
    if guarded.is_err:
        _log.error("coverage_refresh: %s refused (exec disabled)", " ".join(argv))
        return Err(Unit())
    proc = guarded.danger_ok
    if proc.returncode != 0:
        _log.error("coverage_refresh: %s exited %d", " ".join(argv), proc.returncode)
        return Err(Unit())
    return Ok(proc)


# frob:ticket T-1516
def _run_full_suite(
    root: Path, *, cov_target: str, reason: str
) -> Result[Unit, CoverageRefreshError]:
    """Run the WHOLE suite under coverage, no target restriction (T-1516) --
    the `full=True`/cold-start branch of `native_coverage_refresh`, split out
    to keep that function under the ARCH001 line threshold. `reason` is a
    human-readable log label only (e.g. "explicit --full")."""
    _log.info("coverage_refresh: %s -- running the full suite", reason)
    argv = _pytest_argv(targets=(), cov_target=cov_target, append=False)
    ran = _run(argv, cwd=root)
    if ran.is_err:
        return Err(CoverageRefreshError.PytestFailed)
    return Ok(Unit())


# frob:ticket T-1516
def _run_incremental_or_restamp(
    root: Path,
    snapshot: GraphSnapshot,
    *,
    base: str,
    cov_target: str,
    xml_path: Path,
) -> Result[bool, CoverageRefreshError]:
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
        ran = _run(argv, cwd=root)
        if ran.is_err:
            return Err(CoverageRefreshError.PytestFailed)
        return Ok(True)
    if not xml_path.exists():
        return (
            _run_full_suite(
                root,
                cov_target=cov_target,
                reason="nothing touched and no coverage.xml yet",
            )
            | (lambda _: True)
        )
    _log.info(
        "coverage_refresh: nothing touched selects a python test -- "
        "restamping existing coverage.xml only"
    )
    return Ok(False)


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
) -> Result[bool, CoverageRefreshError]:
    """Dispatch to `_run_full_suite` or `_run_incremental_or_restamp` (T-1516),
    split out of `native_coverage_refresh` to keep it under the ARCH001
    line threshold. Returns whether pytest actually ran."""
    if full or cold_start:
        return (
            _run_full_suite(
                root,
                cov_target=cov_target,
                reason=(
                    "explicit --full"
                    if full
                    else "cold start (no coverage-stamp yet)"
                ),
            )
            | (lambda _: True)
        )
    return _run_incremental_or_restamp(
        root, snapshot, base=base, cov_target=cov_target, xml_path=xml_path
    )


# frob:ticket T-1516
# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_full_run_when_no_stamp_exists  # noqa: E501
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_incremental_run_uses_touched_set_targets  # noqa: E501
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_nothing_touched_only_restamps  # noqa: E501
# frob:tests tests/test_coverage.py::TestNativeCoverageRefresh.test_pytest_failure_is_err  # noqa: E501
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
    ran_pytest = pass_result.danger_ok

    if ran_pytest:
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
    return Ok(Unit())


__all__ = [
    "CoverageRefreshError",
    "native_coverage_refresh",
]
