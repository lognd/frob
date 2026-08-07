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

T-1677/T-1672 ported the two pieces of Makefile-recipe resilience the
paragraph above used to disclose as deliberately deferred: a wall-clock
deadline + no-progress watchdog on every subprocess this module spawns
(`_spawn_with_watchdog`, killing the whole process GROUP on either trip
-- the 2026-08-06 field incident, a controller blocked forever in the
xdist scheduler with nothing anywhere timing it out), and the xdist
worker-crash serial-rerun recovery (`_pytest_outcome`'s
`_WORKER_CRASH_SIGNATURE_RE` match + one `-p no:xdist` retry, the other
2026-08-06 field incident: an OOM-killed worker's `INTERNALERROR>`
discarding 8622 already-passing tests' coverage). See
`docs/modules/testing.md`'s own T-1677 sections for the full design;
`FROB_COVERAGE_WALLCLOCK_DEADLINE_S`/`FROB_COVERAGE_NO_PROGRESS_
DEADLINE_S` are this module's own knobs, the direct successors to the
Makefile recipe's `COVERAGE_RERUN_DEADLINE`/`COVERAGE_XDIST_DEADLINE`.

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
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result
from typani.unit import Unit

from frob.logging import get_logger
from frob.process._guard import exec_enabled
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
# frob:ticket T-1677
# frob:doc docs/modules/testing.md#public-api
class CoverageRefreshError(ErrorSet):
    """Failure values `native_coverage_refresh` can return."""

    PytestRefused = "the pytest subprocess could not be spawned at all"
    CoverageXmlFailed = "`coverage xml` could not produce coverage.xml"
    StampFailed = "the post-run stamp_coverage call failed"
    # frob:ticket T-1677
    PytestWallClockExceeded = (
        "pytest exceeded its wall-clock deadline and was killed -- "
        "coverage is UNMEASURED, not partial or zero"
    )
    # frob:ticket T-1677
    PytestNoProgress = (
        "pytest produced no output for the no-progress deadline and was "
        "killed -- coverage is UNMEASURED, not partial or zero"
    )


# frob:ticket T-1677
#: Wall-clock deadline for one pytest subprocess pass, in seconds --
#: exceeding it means "kill the process group and report UNMEASURED",
#: never "wait forever" (the 2026-08-06 field incident this ticket exists
#: to close: a controller blocked in the xdist scheduler stayed alive and
#: idle for 5h04m with nothing anywhere ever timing it out). Overridable
#: via `FROB_COVERAGE_WALLCLOCK_DEADLINE_S` for a caller whose suite
#: genuinely needs longer (or, in a test, much shorter).
_DEFAULT_WALL_CLOCK_DEADLINE_S = 60.0 * 60.0
_WALL_CLOCK_DEADLINE_ENV = "FROB_COVERAGE_WALLCLOCK_DEADLINE_S"

# frob:ticket T-1677
#: No-progress deadline: if the pytest subprocess's own stdout/stderr
#: stream has not grown in this many seconds, treat it as HUNG regardless
#: of the wall-clock deadline above -- this is the signal that actually
#: distinguishes "hung" from "slow, but still working" (the field
#: incident's exact symptom: a normal-looking last log line, alive
#: process, pending exit code, nothing to tell an operator polling for
#: completion that it would never finish). Overridable via
#: `FROB_COVERAGE_NO_PROGRESS_DEADLINE_S`.
_DEFAULT_NO_PROGRESS_DEADLINE_S = 15.0 * 60.0
_NO_PROGRESS_DEADLINE_ENV = "FROB_COVERAGE_NO_PROGRESS_DEADLINE_S"

# frob:ticket T-1677
#: How often the watchdog polls the subprocess's liveness and its output
#: log's mtime. Small relative to either deadline above so a trip is
#: detected close to the deadline, not up to a whole poll interval late.
_WATCHDOG_POLL_INTERVAL_S = 5.0

# frob:ticket T-1677
#: Grace period between SIGTERM and SIGKILL when tearing down a killed
#: process group (POSIX) -- long enough for xdist workers to unwind their
#: own children on a clean signal, short enough to never itself become a
#: second hang.
_KILL_GRACE_PERIOD_S = 5.0

# frob:ticket T-1677
#: The xdist worker-crash signature this module knows how to detect and
#: retry serially (T-1672's "killed worker" incident, folded in here per
#: this ticket's own body: "fold T-1672 into this if one implementation
#: covers both"). `INTERNALERROR` is pytest's own marker for an
#: uncaught exception in its own machinery (xdist's scheduler raises
#: exactly this shape, `KeyError: <WorkerController gwNN>`, when a worker
#: process disappears out from under it); `gwNN` node-down report lines
#: are `execnet`'s. Matching either is enough to classify the abort as an
#: ENVIRONMENT failure (a worker got killed, most often OOM) rather than
#: a genuine test regression -- T-1672's item 3, "a resource kill and a
#: real suite failure both surface as exited 3; classify them
#: differently."
_WORKER_CRASH_SIGNATURE_RE = re.compile(
    r"INTERNALERROR>.*WorkerController|worker\s+gw\d+\s+crashed|"
    r"replacing crashed worker"
)


@dataclass(frozen=True)
class _WatchdogConfig:
    """The two independent deadlines `_spawn_with_watchdog` enforces
    (T-1677): `wall_clock_s` bounds the whole run regardless of output,
    `no_progress_s` bounds how long the run may go without producing any
    NEW output -- either one tripping is a hang, not a measurement."""

    wall_clock_s: float
    no_progress_s: float
    poll_interval_s: float = _WATCHDOG_POLL_INTERVAL_S


class _WatchdogAbortReason(ErrorSet):
    """Which of `_WatchdogConfig`'s two deadlines tripped (T-1677) -- kept
    separate from `CoverageRefreshError` so `_spawn_with_watchdog` (a
    low-level, `native_coverage_refresh`-agnostic primitive) does not need
    to know about that higher-level error type at all."""

    WallClockExceeded = "the wall-clock deadline was exceeded"
    NoProgress = "no new output for the no-progress deadline"


def _watchdog_config_from_env() -> _WatchdogConfig:
    """Build the active `_WatchdogConfig` from `_DEFAULT_*` constants,
    each overridable via its own env var (T-1677) -- the same "disclosed,
    configurable knob" precedent `COVERAGE_RERUN_DEADLINE`/
    `COVERAGE_XDIST_DEADLINE` set in the Makefile recipe this module
    otherwise deliberately does not shell out to. A malformed override
    (non-numeric) is logged and ignored rather than crashing the whole
    refresh over a bad env var."""

    def _read(env_name: str, default: float) -> float:
        raw = os.environ.get(env_name)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError:
            _log.warning(
                "coverage_refresh: %s=%r is not a number, using default %.0fs",
                env_name,
                raw,
                default,
            )
            return default

    return _WatchdogConfig(
        wall_clock_s=_read(_WALL_CLOCK_DEADLINE_ENV, _DEFAULT_WALL_CLOCK_DEADLINE_S),
        no_progress_s=_read(_NO_PROGRESS_DEADLINE_ENV, _DEFAULT_NO_PROGRESS_DEADLINE_S),
    )


def _kill_process_group(proc: subprocess.Popen, *, grace_s: float) -> None:
    """Kill `proc` AND every descendant it spawned (T-1677 item 4: "never
    leave zombies") -- a plain `proc.kill()` only kills the top-level
    `pytest` controller and leaves every xdist worker (its own child
    processes) running as orphans, which is exactly what a plain `kill`
    left behind in the field incident this ticket closes.

    POSIX: `proc` was spawned with `start_new_session=True`, making its
    pid also its process GROUP id -- `os.killpg` reaches the whole tree in
    one call. SIGTERM first (`grace_s` to unwind cleanly), SIGKILL if
    still alive after. Windows: `proc` was spawned with
    `CREATE_NEW_PROCESS_GROUP`; there is no killpg equivalent, so
    `taskkill /T /F` (kill the tree, force) is the documented substitute.

    Always reaps via `proc.wait()` at the end (best-effort, bounded) so
    the killed process never becomes a zombie under this process."""
    if sys.platform == "win32":
        try:
            subprocess.run(  # noqa: S603, S607
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                check=False,
                capture_output=True,
            )
        except OSError as exc:
            _log.warning(
                "coverage_refresh: taskkill failed for pid %d: %s", proc.pid, exc
            )
    else:
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            pgid = None
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=grace_s)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    try:
        proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        _log.error(
            "coverage_refresh: pid %d did not exit even after SIGKILL -- "
            "possible zombie, needs manual `kill -9 %d` / inspection",
            proc.pid,
            proc.pid,
        )


# frob:ticket T-1677
def _spawn_with_watchdog(
    argv: list[str], *, cwd: Path, config: _WatchdogConfig
) -> Result[subprocess.CompletedProcess, _WatchdogAbortReason]:
    """Run `argv` under BOTH a wall-clock deadline and a no-progress
    watchdog (T-1677), killing the whole process GROUP (not just the
    controller) on either trip.

    Cannot use `guarded_subprocess_run`/`subprocess.run` here: both block
    until the child exits with no way to observe it mid-run, which is
    exactly the field incident's shape (a controller blocked forever in
    the xdist scheduler, no timeout anywhere in the call stack). This
    spawns via `Popen` instead, redirecting stdout+stderr to a temp file
    this function itself polls -- the file's mtime is the no-progress
    signal (T-1677's explicit ask: "if the subprocess produces no output
    for N minutes, treat it as hung," the one signal that actually
    distinguishes hung from slow), and the returned `CompletedProcess`'s
    `.stdout` is that file's full content, so a caller reading it (the
    worker-crash signature scan) sees exactly what a blocking
    `subprocess.run(capture_output=True)` would have given it.

    The `FROB_DISABLE_EXEC` kill switch is checked by the CALLER
    (`_pytest_outcome`) before this is ever invoked -- the same guard
    `_spawn` performs internally -- so this function assumes exec is
    already permitted and never checks it itself."""
    log_fd, log_path_str = tempfile.mkstemp(
        prefix="frob-coverage-watchdog-", suffix=".log"
    )
    log_path = Path(log_path_str)

    _log.debug("coverage_refresh: spawning %r under watchdog (log=%s)", argv, log_path)
    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(  # noqa: S603
                argv,
                cwd=str(cwd),
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            proc = subprocess.Popen(  # noqa: S603
                argv,
                cwd=str(cwd),
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError as exc:
        os.close(log_fd)
        log_path.unlink(missing_ok=True)
        _log.error("coverage_refresh: watchdog spawn of %r failed: %s", argv, exc)
        return Err(_WatchdogAbortReason.WallClockExceeded)
    finally:
        # `Popen` duplicates the fd for the child; the parent's copy must
        # be closed here regardless of spawn success so tailing the file
        # below sees a live, not-still-open-for-write-by-us descriptor.
        try:
            os.close(log_fd)
        except OSError:
            pass

    start = time.monotonic()
    try:
        while True:
            code = proc.poll()
            if code is not None:
                content = log_path.read_text(encoding="utf-8", errors="replace")
                return Ok(subprocess.CompletedProcess(argv, code, stdout=content))

            elapsed = time.monotonic() - start
            if elapsed >= config.wall_clock_s:
                _log.error(
                    "coverage_refresh: %r exceeded its %.0fs wall-clock deadline "
                    "(pid %d) -- killing the process GROUP; coverage is "
                    "UNMEASURED for this run, not partial or zero",
                    argv,
                    config.wall_clock_s,
                    proc.pid,
                )
                _kill_process_group(proc, grace_s=_KILL_GRACE_PERIOD_S)
                return Err(_WatchdogAbortReason.WallClockExceeded)

            try:
                mtime = log_path.stat().st_mtime
            except OSError:
                mtime = start
            since_progress = time.time() - mtime
            if since_progress >= config.no_progress_s:
                _log.error(
                    "coverage_refresh: %r produced no output for %.0fs (pid %d, "
                    "%.0fs total elapsed) -- treating as HUNG and killing the "
                    "process GROUP; coverage is UNMEASURED for this run, not "
                    "partial or zero",
                    argv,
                    config.no_progress_s,
                    proc.pid,
                    elapsed,
                )
                _kill_process_group(proc, grace_s=_KILL_GRACE_PERIOD_S)
                return Err(_WatchdogAbortReason.NoProgress)

            remaining = config.wall_clock_s - elapsed
            time.sleep(min(config.poll_interval_s, remaining) if remaining > 0 else 0)
    finally:
        log_path.unlink(missing_ok=True)


#: Where `native_coverage_refresh` records the provenance of the run that
#: produced the current `coverage.xml` (T-1676) -- specifically whether the
#: suite was RED while it was measured. Consumers that need to know how far
#: to trust the artifact read this; nothing else in the tree records it.
# frob:ticket T-1676
_RUN_PROVENANCE_REL = ".frob/coverage-run.json"


# frob:ticket T-1676
# frob:ticket T-1677
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
    measurement the caller actually asked for.

    `worker_crash` (T-1677/T-1672): whether `_WORKER_CRASH_SIGNATURE_RE`
    matched this pass's output at ANY point (the original parallel attempt,
    even if a serial retry then succeeded) -- an ENVIRONMENT failure (a
    worker process got killed, most often OOM), classified distinctly from
    an ordinary red suite so a reader does not go hunting for a regression
    that does not exist (T-1672 item 3)."""

    ran: bool
    degraded: bool
    exit_code: int | None
    worker_crash: bool = False


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


# frob:ticket T-1677
class _SpawnError(ErrorSet):
    """Why `_spawn` did not return a completed process (T-1677) --
    distinguishes "never even started" from either watchdog deadline
    tripping, so a caller that cares (`_pytest_outcome`, wanting to report
    `CoverageRefreshError.PytestWallClockExceeded` vs `...NoProgress`
    rather than a generic failure) can. `_run` (coverage xml, which never
    needed the distinction even before this ticket) still collapses this
    to a plain `Unit` `Err`."""

    Refused = "exec disabled via FROB_DISABLE_EXEC"
    WallClockExceeded = "the wall-clock deadline was exceeded"
    NoProgress = "no new output for the no-progress deadline"


# frob:ticket T-1676
# frob:ticket T-1677
def _spawn(
    argv: list[str], *, cwd: Path
) -> Result[subprocess.CompletedProcess, _SpawnError]:
    """The one seam every subprocess in this module goes through (T-1676),
    now ALSO the one seam the T-1677 wall-clock/no-progress watchdog goes
    through -- every caller (pytest AND `coverage xml`) is covered by the
    same deadlines, not just the pytest call site, since a hang in either
    is the same class of "verification never returns an answer" defect.

    Still honors `FROB_DISABLE_EXEC` FIRST, before ever touching
    `_spawn_with_watchdog`'s `Popen` call (`exec_enabled()`, the same
    check `guarded_subprocess_run` itself performs) -- `Err(_SpawnError.
    Refused)` without spawning anything. Otherwise delegates to
    `_spawn_with_watchdog` under `_watchdog_config_from_env()`'s deadlines,
    translating its `_WatchdogAbortReason` into the matching `_SpawnError`
    variant.

    `_run` (below) is the pass/fail reading of this for callers where a
    non-zero exit genuinely means no usable output; `_pytest_outcome` is
    the reading for callers where it does not."""
    if not exec_enabled():
        _log.error("coverage_refresh: %s refused (exec disabled)", " ".join(argv))
        return Err(_SpawnError.Refused)
    spawned = _spawn_with_watchdog(argv, cwd=cwd, config=_watchdog_config_from_env())
    if spawned.is_err:
        reason = spawned.danger_err
        return Err(
            _SpawnError.WallClockExceeded
            if reason is _WatchdogAbortReason.WallClockExceeded
            else _SpawnError.NoProgress
        )
    return Ok(spawned.danger_ok)


# frob:ticket T-1516
def _run(argv: list[str], *, cwd: Path) -> Result[subprocess.CompletedProcess, Unit]:
    """`_spawn`, collapsed to a plain pass/fail `Result` (T-1516) -- for a
    subprocess whose non-zero exit genuinely means it produced nothing
    usable (`coverage xml`). Since T-1676 the pytest passes deliberately do
    NOT use this: a red suite still produces valid coverage data. T-1677's
    `_SpawnError` distinction (refused vs. either watchdog deadline) is
    collapsed back to `Unit` here -- `coverage xml` has no equivalent to
    `CoverageRefreshError`'s pytest-specific timeout variants, and its
    caller (`native_coverage_refresh`) already reports
    `CoverageXmlFailed` uniformly regardless of cause."""
    spawned = _spawn(argv, cwd=cwd)
    if spawned.is_err:
        return Err(Unit())
    proc = spawned.danger_ok
    if proc.returncode != 0:
        _log.error("coverage_refresh: %s exited %d", " ".join(argv), proc.returncode)
        return Err(Unit())
    return Ok(proc)


# frob:ticket T-1676
def _pytest_outcome(argv: list[str], *, cwd: Path) -> Result[_PytestPass, _SpawnError]:
    """Run one pytest pass and classify its exit (T-1676), now also
    detecting and recovering from an xdist worker crash (T-1677/T-1672).

    `Err(_SpawnError...)` means pytest never produced a usable exit at all
    -- either a refused spawn under `FROB_DISABLE_EXEC=1`, or one of
    T-1677's watchdog deadlines killed it. Those are the ONLY cases where
    there is genuinely no measurement to keep, and the only ones that
    still abort the refresh.

    A non-zero exit whose output matches `_WORKER_CRASH_SIGNATURE_RE`
    (T-1672's field incident: an OOM-killed xdist worker raises
    `INTERNALERROR> ... KeyError: <WorkerController gwNN>` and the run
    ends non-zero despite thousands of tests having already passed) gets
    ONE serial retry (`-p no:xdist`, disabling parallelism entirely so
    the same crash class structurally cannot recur) before being
    classified -- the Makefile recipe's xdist-crash serial-rerun recovery
    this module's own docstring originally disclosed as deferred. The
    retry's own outcome (whichever it is) is what gets returned;
    `worker_crash=True` either way, so `_write_run_provenance` can record
    "an environment failure happened here" even when the retry recovered
    a clean pass.

    Any OTHER non-zero exit is `Ok(_PytestPass(ran=True, degraded=True,
    ...))`: the tests that ran still wrote their coverage data, and that
    data is what the caller asked for. It is logged at ERROR so a red
    suite stays as visible as it was when it aborted the run -- it simply
    no longer vetoes the artifact."""
    spawned = _spawn(argv, cwd=cwd)
    if spawned.is_err:
        return Err(spawned.danger_err)
    proc = spawned.danger_ok
    code = proc.returncode
    output = proc.stdout or ""
    worker_crash = bool(code != 0 and _WORKER_CRASH_SIGNATURE_RE.search(output))

    if worker_crash:
        _log.error(
            "coverage_refresh: %s exited %d and matched the xdist "
            "worker-crash signature (T-1672: a worker process was killed, "
            "most often OOM) -- retrying ONCE serially (-p no:xdist) "
            "instead of discarding an already-mostly-passing run",
            " ".join(argv),
            code,
        )
        retry_argv = [*argv, "-p", "no:xdist"]
        respawned = _spawn(retry_argv, cwd=cwd)
        if respawned.is_err:
            _log.error(
                "coverage_refresh: serial retry after worker-crash also "
                "failed to complete (%s) -- keeping the original pass's "
                "data, still marked worker_crash",
                respawned.danger_err.value,
            )
        else:
            proc = respawned.danger_ok
            code = proc.returncode
            if code == 0:
                _log.info(
                    "coverage_refresh: serial retry after worker-crash "
                    "succeeded -- run is no longer degraded"
                )
            else:
                _log.error(
                    "coverage_refresh: serial retry after worker-crash "
                    "still exited %d -- this is a REAL failure, not the "
                    "worker-crash artifact",
                    code,
                )

    if code != 0 and not worker_crash:
        _log.error(
            "coverage_refresh: %s exited %d -- the suite was RED while coverage "
            "was measured; KEEPING the coverage data (T-1676) and marking this "
            "run degraded. Symbols whose tests failed early under-report; treat "
            "a NEW low-coverage finding from this run as suspect until the "
            "suite is green",
            " ".join(argv),
            code,
        )
    return Ok(
        _PytestPass(
            ran=True, degraded=code != 0, exit_code=code, worker_crash=worker_crash
        )
    )


# frob:ticket T-1677
_SPAWN_ERROR_TO_REFRESH_ERROR: dict[_SpawnError, CoverageRefreshError] = {
    _SpawnError.Refused: CoverageRefreshError.PytestRefused,
    _SpawnError.WallClockExceeded: CoverageRefreshError.PytestWallClockExceeded,
    _SpawnError.NoProgress: CoverageRefreshError.PytestNoProgress,
}


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
        return Err(_SPAWN_ERROR_TO_REFRESH_ERROR[ran.danger_err])
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
            return Err(_SPAWN_ERROR_TO_REFRESH_ERROR[ran.danger_err])
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
    property of the current artifact.

    T-1677/T-1672: `worker_crash` distinguishes an ENVIRONMENT abort (a
    killed xdist worker) from an ordinary red suite -- both set
    `degraded=True`, but only one of them means "go hunt for a real test
    regression." `aborted`/`abort_reason` are always `False`/`None` here:
    this function only ever runs on a pass that RAN to completion (a
    watchdog-killed pass never reaches this call at all -- see
    `native_coverage_refresh`'s own abort branch, which writes its own
    distinct provenance instead of calling this)."""
    record = {
        "degraded": outcome.degraded,
        "pytest_exit_code": outcome.exit_code,
        "pytest_ran": outcome.ran,
        "worker_crash": outcome.worker_crash,
        "aborted": False,
        "abort_reason": None,
    }
    path = root / _RUN_PROVENANCE_REL
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.warning("coverage_refresh: could not write %s: %s", path, exc)
        return
    if outcome.worker_crash:
        _log.warning(
            "coverage_refresh: coverage.xml recorded worker_crash=True in %s "
            "-- this run's degraded status (if still degraded after the "
            "T-1672 serial retry) is an ENVIRONMENT artifact (a killed "
            "xdist worker), not evidence of a real test regression",
            _RUN_PROVENANCE_REL,
        )
    elif outcome.degraded:
        _log.warning(
            "coverage_refresh: coverage.xml recorded as DEGRADED in %s "
            "(pytest exit %s) -- the artifact is usable but was measured "
            "against a red suite",
            _RUN_PROVENANCE_REL,
            outcome.exit_code,
        )


# frob:ticket T-1677
def _write_abort_provenance(root: Path, error: CoverageRefreshError) -> None:
    """Record that the LAST coverage refresh attempt was ABORTED by a
    T-1677 watchdog deadline before `coverage.xml`/`stamp_coverage` ever
    ran (never a partial or zero measurement -- there IS no measurement).

    Same schema as `_write_run_provenance`, same best-effort posture (a
    failed write here must never turn an already-reported abort into a
    second, different-looking failure), written to the SAME file so a
    consumer only ever has one place to check -- the point is that
    `coverage.xml` on disk (if any) now predates this record and MUST be
    read as stale, not that there are two competing provenance files to
    reconcile. `degraded`/`worker_crash` are `False`/`False` here (there
    is no run to classify as red or crashed; it never got that far)."""
    record = {
        "degraded": False,
        "pytest_exit_code": None,
        "pytest_ran": False,
        "worker_crash": False,
        "aborted": True,
        "abort_reason": error.value,
    }
    path = root / _RUN_PROVENANCE_REL
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.warning(
            "coverage_refresh: could not write abort record to %s: %s", path, exc
        )
        return
    _log.error(
        "coverage_refresh: ABORTED (%s) -- recorded in %s; any existing "
        "coverage.xml is now STALE and must NOT be read as measuring the "
        "current tree",
        error.value,
        _RUN_PROVENANCE_REL,
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
        error = pass_result.danger_err
        # T-1677: a watchdog abort (wall-clock or no-progress) means
        # pytest never produced a trustworthy result -- `coverage xml`/
        # `stamp_coverage` MUST NOT run, or a stale-but-present
        # `coverage.xml` would silently read as current (the exact
        # "derived artifact goes stale and everything downstream reads it
        # as fresh" trap this ticket was filed to design against, same
        # family as T-1672). `_write_abort_provenance` records the abort
        # explicitly so `.frob/coverage-run.json` reflects the truth of
        # the LAST attempt even though `coverage.xml` itself, if one
        # exists, is untouched and now KNOWN-STALE.
        if error in (
            CoverageRefreshError.PytestWallClockExceeded,
            CoverageRefreshError.PytestNoProgress,
        ):
            _write_abort_provenance(root, error)
        return Err(error)
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
