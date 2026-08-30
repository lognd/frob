"""T-3420: a coverage-instrumented pytest run deadlocks in its OWN SIGTERM
handler and survives `timeout` entirely if it receives a second SIGTERM
while the first is still running. `Collector.data_lock` (coverage's
internal lock, see `coverage/collector.py`) is a plain non-reentrant
`threading.Lock`; `_on_sigterm` (`coverage/control.py`) takes it while
saving partial data, and a SECOND SIGTERM re-entering that same handler on
the same thread blocks on the SAME lock forever -- matches the open,
unfixed upstream reports coveragepy#1101 and coveragepy#1340 (checked
2026-08-29 against coverage 7.14.1, this repo's installed version -- no
fix, no version floor available).

MEASURED single vs double SIGTERM, deliberately, before this fix:
  - a SINGLE SIGTERM to a coverage-instrumented run terminates cleanly
    every time (many trials) -- NOT the bug.
  - a SECOND SIGTERM landing while `Collector.pause()` holds `data_lock`
    deadlocks the process FOREVER (deterministic once the second signal
    lands inside that window; the window is normally brief, which is why
    this needs thousands of naive back-to-back signals to hit by luck, but
    disk-I/O-widened saves under real CI load make it reachable -- this is
    the likely mechanism behind the reported CI/macOS hangs).

THE FIX here is `sigterm = false` in `[tool.coverage.run]`
(pyproject.toml) -- coverage no longer installs a SIGTERM handler at all,
so `timeout` (and CI's own termination) goes back to being a reliable kill.
TRADEOFF, stated here and in pyproject.toml: a run that is actually killed
loses that run's coverage data outright, instead of coverage saving
whatever it collected so far. `parallel = true` already tolerates losing
individual data files (`coverage combine` merges whatever partial files
exist), and a run that finishes normally is unaffected -- it saves via the
ordinary atexit path, never the signal path.

This file supplies the two fixtures the ticket requires:
  - test_repeated_sigterm_terminates_in_bounded_time (MUST-FIRE)
  - test_normal_run_writes_complete_coverage_data (MUST-STAY-QUIET)
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

_SLEEP_TEST_SRC = """
# Widen coverage's own SIGTERM-handler critical section deterministically
# instead of relying on luck to land a signal inside a normally-brief
# window (naive back-to-back SIGTERM spam was measured NOT to reproduce
# the deadlock reliably -- thousands of trials, zero hits -- because the
# real window is short under a trivial workload). This holds
# Collector.data_lock itself for a few seconds, mirroring the disk-I/O-
# widened window a real CI run's larger data flush produces, so the test
# is deterministic rather than a coin flip.
import time

try:
    from coverage.collector import Collector

    _orig_pause = Collector.pause

    def _slow_pause(self, *a, **kw):
        self.data_lock.acquire()
        try:
            time.sleep(4)
        finally:
            self.data_lock.release()
        return _orig_pause(self, *a, **kw)

    Collector.pause = _slow_pause
except ImportError:
    pass


def test_sleeps():
    time.sleep(30)
"""

_FAST_TEST_SRC = """
def test_adds():
    assert 1 + 1 == 2
"""

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_test_file(tmp_path: Path, name: str, src: str) -> Path:
    """One throwaway pytest file used as the coverage-instrumented target."""
    test_file = tmp_path / name
    test_file.write_text(src, encoding="utf-8")
    return test_file


def _send_signal_to_group(pid: int, sig: int) -> None:
    """Send a signal to the process group led by pid. POSIX-only (os.killpg
    does not exist on win32); this whole test class is skipped there, but
    fetch through getattr so a multi-platform static check does not flag
    the win32 branch for a member that is genuinely absent there.

    T-3437 (MEASURED on macOS CI, run 33281416850): the child can already
    have exited (caught the first SIGTERM and died, or the widened-
    critical-section window closed faster than macOS's own scheduling)
    by the time the SECOND signal is sent, in which case `killpg` raises
    `ProcessLookupError` (errno ESRCH, "No such process"). A dead process
    group IS the must-fire outcome this fixture is proving (the process
    terminated, it did not deadlock) -- so ESRCH is swallowed here, never
    treated as a test failure or a reason to skip on macOS specifically."""
    killpg = getattr(os, "killpg")  # noqa: B009 -- deliberate, see docstring
    try:
        killpg(pid, sig)
    except ProcessLookupError:
        pass  # already exited -- the process group is gone, which is fine


def _spawn_coverage_run(test_file: Path, cwd: Path) -> subprocess.Popen:
    """Start a coverage-instrumented pytest subprocess against test_file,
    pointed at this repo's own pyproject.toml via --cov-config (so
    [tool.coverage.run]'s sigterm setting under test actually applies,
    regardless of the throwaway tmp_path cwd), in its own process group
    so a bad kill signal here cannot escape to the test runner."""
    env = os.environ | {"COVERAGE_FILE": str(cwd / ".coverage.t3420")}
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=.",
            f"--cov-config={_REPO_ROOT / 'pyproject.toml'}",
            "-p",
            "no:xdist",
            "-q",
            str(test_file),
        ],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


# frob:ticket T-3420
class TestCoverageSigtermDeadlock:
    """Proves the SIGTERM-handler re-entrancy deadlock is mitigated: a
    coverage run under repeated SIGTERM must die in bounded time, and an
    ordinary coverage run must still write complete data."""

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="SIGTERM/process-group signalling is POSIX-only",
    )
    def test_repeated_sigterm_terminates_in_bounded_time(self, tmp_path: Path) -> None:
        """MUST-FIRE: a coverage-instrumented run that receives repeated
        SIGTERM (mirroring `timeout`'s own escalation, or a CI runner
        retrying termination) must actually die within a bounded wall
        time -- not survive deadlocked in its own signal handler."""
        # frob:tests tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock.test_repeated_sigterm_terminates_in_bounded_time  # noqa: E501
        test_file = _write_test_file(tmp_path, "test_sleeps.py", _SLEEP_TEST_SRC)
        proc = _spawn_coverage_run(test_file, tmp_path)
        try:
            time.sleep(1.0)
            # First SIGTERM: if coverage's SIGTERM handler is installed
            # (sigterm=true), this enters it and (via the target file's
            # widened Collector.pause) acquires data_lock and holds it
            # for ~4s. Second SIGTERM, timed to land inside that window,
            # re-enters the same handler on the same thread and -- if the
            # handler is still installed -- deadlocks on the same lock.
            _send_signal_to_group(proc.pid, signal.SIGTERM)
            time.sleep(1.0)
            _send_signal_to_group(proc.pid, signal.SIGTERM)  # lands inside the window
            bounded_wait_s = 20
            try:
                proc.wait(timeout=bounded_wait_s)
            except subprocess.TimeoutExpired:
                pytest.fail(
                    f"process survived {bounded_wait_s}s after repeated "
                    "SIGTERM -- the signal-handler deadlock is back "
                    "(check [tool.coverage.run] sigterm in pyproject.toml)"
                )
            # A process that dies from SIGTERM (or exits after catching
            # it) is the point of this fixture -- either is a real death,
            # not a hang. Only a still-running process is a failure, and
            # that path is asserted above.
        finally:
            if proc.poll() is None:
                _send_signal_to_group(proc.pid, signal.SIGKILL)  # cleanup only
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass  # best-effort cleanup; the assertion above already ran

    def test_normal_run_writes_complete_coverage_data(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: with SIGTERM handling off, an ordinary
        (uninterrupted) coverage run must still finish normally and write
        a complete, readable data file -- the mitigation must not degrade
        the common case."""
        # frob:tests tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock.test_normal_run_writes_complete_coverage_data  # noqa: E501
        test_file = _write_test_file(tmp_path, "test_adds.py", _FAST_TEST_SRC)
        data_file = tmp_path / ".coverage.t3420"
        env = os.environ | {"COVERAGE_FILE": str(data_file)}
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=.",
                f"--cov-config={_REPO_ROOT / 'pyproject.toml'}",
                "-p",
                "no:xdist",
                "-q",
                str(test_file),
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert data_file.exists(), (
            "no coverage data file written by a normal, uninterrupted run:\n"
            + proc.stdout
            + proc.stderr
        )
        assert data_file.stat().st_size > 0, "coverage data file is empty"
