"""T-3192 POSITIVE CONTROL: a timeout path that has never fired is not
known to work. This plants a deliberate hang and proves the exact
mechanism CI's Test steps use (`.github/workflows/ci.yml`'s
`PYTHONFAULTHANDLER=1` + a stack-dump-on-hang watcher) turns it into a
failure AND names where it was stuck, on this host, without needing an
actual CI run to find out.

T-3488: macOS has no GNU `timeout` (T-3250), so ci.yml's macOS Test step
uses a bash background watcher (`sleep budget; kill -ABRT $pid`) instead
of `timeout -s ABRT`. This test now uses that SAME bash watcher shape
(see `_WATCHER_SH` below, copied from the macOS Test step) rather than
the GNU `timeout` binary, so it is hermetic and runs the same recipe on
both Linux and macOS -- no `shutil.which("timeout")` skip needed.

Uses a short budget (a few seconds) against a real planted-hang pytest
file run as a genuine subprocess -- not a mock of `subprocess.run`, not
an assertion about the YAML alone (that's tests/test_ci_workflow_timeout.py's
job) -- so a regression in the ACTUAL mechanism (e.g. faulthandler not
actually installed the way `PYTHONFAULTHANDLER=1` promises, or the
watcher sending the wrong signal) fails this test, not just a static
check.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_PLANTED_HANG_SRC = """
import time

def test_deliberately_hangs_forever():
    time.sleep(600)
"""

# Mirrors .github/workflows/ci.yml's macOS "Test (macos, timed with
# stack-dump-on-hang)" step: launch the target in the background, race a
# `sleep budget` watcher against it, SIGABRT (for the PYTHONFAULTHANDLER
# stack dump) then SIGKILL if the watcher wins, and propagate the
# target's own exit status otherwise. Uses only bash/kill/sleep builtins
# -- no GNU `timeout` -- so it runs identically on Linux and macOS.
_WATCHER_SH = """
set -uo pipefail
budget="$1"
shift
"$@" &
pid=$!
(
  sleep "$budget"
  if kill -0 "$pid" 2>/dev/null; then
    kill -ABRT "$pid" 2>/dev/null || true
    sleep 2
    kill -KILL "$pid" 2>/dev/null || true
  fi
) &
watcher=$!
wait "$pid"
status=$?
kill "$watcher" 2>/dev/null || true
exit "$status"
"""


def _write_planted_hang(tmp_path: Path) -> Path:
    """One throwaway pytest file whose only test sleeps far longer than
    the budget below -- the wedge this whole guard exists to catch."""
    hang_file = tmp_path / "test_planted_hang.py"
    hang_file.write_text(_PLANTED_HANG_SRC, encoding="utf-8")
    return hang_file


def _run_under_watcher(
    budget_s: int, target_args: list[str], env: dict[str, str], harness_cap_s: float
) -> subprocess.CompletedProcess[str]:
    """Runs `target_args` under the `_WATCHER_SH` bash watcher, the same
    stack-dump-on-hang recipe ci.yml's macOS Test step uses in place of
    GNU `timeout` (T-3488/T-3250)."""
    return subprocess.run(
        ["bash", "-c", _WATCHER_SH, "watcher", str(budget_s), *target_args],
        capture_output=True,
        text=True,
        env=env,
        timeout=harness_cap_s,
    )


# frob:ticket T-3488
# frob:ticket T-3192
class TestCiHangGuardPositiveControl:
    """Mirrors CI's own stack-dump-on-hang watcher + `PYTHONFAULTHANDLER=1`
    recipe exactly, against a real planted hang, on a short budget so this
    stays fast as a normal suite member."""

    # PLATFORM001 declared boundary: the watcher script is bash + POSIX
    # kill/sleep, which Windows (win32) does not provide; this test never
    # claims Windows coverage. ci.yml's Windows Test step is already
    # advisory-only for the same reason (T-3425).
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="PLATFORM001: the bash kill -ABRT watcher this test proves "
        "is POSIX-only (bash/kill/sleep), same boundary as ci.yml's "
        "Windows Test step (advisory-only, T-3425)",
    )
    def test_planted_hang_is_killed_and_stack_named(self, tmp_path: Path) -> None:
        # frob:tests tests/system/test_ci_hang_guard_positive_control.py::TestCiHangGuardPositiveControl.test_planted_hang_is_killed_and_stack_named  # noqa: E501
        hang_file = _write_planted_hang(tmp_path)
        budget_s = 3
        env = os.environ | {"PYTHONFAULTHANDLER": "1"}
        # A generous WALL-CLOCK cap on the harness's own subprocess.run
        # call (never None -- T-2980's own DEFAULT_RUN_TIMEOUT_S doctrine)
        # so a regression that breaks the watcher itself fails this test
        # loudly instead of hanging the suite that is supposed to prove
        # hangs get caught.
        harness_cap_s = budget_s + 30
        proc = _run_under_watcher(
            budget_s,
            [sys.executable, "-m", "pytest", "-q", str(hang_file)],
            env,
            harness_cap_s,
        )

        # MUST-FIRE: the hang is a FAILURE, never a silent pass and never
        # an indefinite wait -- this is the T-3192 acceptance criterion
        # itself, reproduced locally instead of trusted from CI history.
        assert proc.returncode != 0, (
            "planted hang exited 0 -- the timeout guard did not fire at all"
        )

        # MUST-FIRE: the failure output NAMES where it was stuck (a stack
        # dump), not just a bare timeout message -- the whole point of
        # PYTHONFAULTHANDLER over a plain kill with no signal choice.
        combined = proc.stdout + proc.stderr
        assert "test_deliberately_hangs_forever" in combined, (
            "no frame naming the wedged test function in the output -- "
            "the fault handler did not dump a stack:\n" + combined
        )
        assert "test_planted_hang.py" in combined

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="PLATFORM001: same bash-watcher boundary as "
        "test_planted_hang_is_killed_and_stack_named above",
    )
    def test_ordinary_fast_test_is_unaffected(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: the same recipe, against a test that finishes
        immediately, passes cleanly with no stray dump/timeout noise --
        the guard must not manufacture false failures for healthy runs."""
        # frob:tests tests/system/test_ci_hang_guard_positive_control.py::TestCiHangGuardPositiveControl.test_ordinary_fast_test_is_unaffected  # noqa: E501
        fast_file = tmp_path / "test_fast.py"
        fast_file.write_text("def test_trivially_passes():\n    assert True\n")
        env = os.environ | {"PYTHONFAULTHANDLER": "1"}
        proc = _run_under_watcher(
            20,
            [sys.executable, "-m", "pytest", "-q", str(fast_file)],
            env,
            30,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "Fatal Python error" not in (proc.stdout + proc.stderr)
