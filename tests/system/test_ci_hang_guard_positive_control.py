"""T-3192 POSITIVE CONTROL: a timeout path that has never fired is not
known to work. This plants a deliberate hang and proves the exact
mechanism CI's ubuntu Test step now uses (`.github/workflows/ci.yml`'s
`timeout -s ABRT <budget> uv run pytest -q`, `PYTHONFAULTHANDLER=1`)
turns it into a failure AND names where it was stuck, on this host,
without needing an actual CI run to find out.

Uses a short budget (a few seconds) against a real planted-hang pytest
file run as a genuine subprocess -- not a mock of `subprocess.run`, not
an assertion about the YAML alone (that's tests/test_ci_workflow_timeout.py's
job) -- so a regression in the ACTUAL mechanism (e.g. faulthandler not
actually installed the way `PYTHONFAULTHANDLER=1` promises, or `timeout`
sending the wrong signal) fails this test, not just a static check.
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


def _write_planted_hang(tmp_path: Path) -> Path:
    """One throwaway pytest file whose only test sleeps far longer than
    the budget below -- the wedge this whole guard exists to catch."""
    hang_file = tmp_path / "test_planted_hang.py"
    hang_file.write_text(_PLANTED_HANG_SRC, encoding="utf-8")
    return hang_file


# frob:ticket T-3192
class TestCiHangGuardPositiveControl:
    """Mirrors CI's own `timeout -s ABRT <budget> uv run pytest -q` +
    `PYTHONFAULTHANDLER=1` recipe exactly, against a real planted hang, on
    a short budget so this stays fast as a normal suite member."""

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="timeout/SIGABRT is POSIX-only, same platform gate as the "
        "CI step this proves (see tests/test_ci_workflow_timeout.py)",
    )
    def test_planted_hang_is_killed_and_stack_named(self, tmp_path: Path) -> None:
        # frob:tests tests/system/test_ci_hang_guard_positive_control.py::TestCiHangGuardPositiveControl.test_planted_hang_is_killed_and_stack_named  # noqa: E501
        hang_file = _write_planted_hang(tmp_path)
        budget_s = 3
        env = os.environ | {"PYTHONFAULTHANDLER": "1"}
        # A generous WALL-CLOCK cap on the harness's own subprocess.run
        # call (never None -- T-2980's own DEFAULT_RUN_TIMEOUT_S doctrine)
        # so a regression that breaks `timeout` itself fails this test
        # loudly instead of hanging the suite that is supposed to prove
        # hangs get caught.
        harness_cap_s = budget_s + 30
        proc = subprocess.run(
            [
                "timeout",
                "-s",
                "ABRT",
                f"{budget_s}s",
                sys.executable,
                "-m",
                "pytest",
                "-q",
                str(hang_file),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=harness_cap_s,
        )

        # MUST-FIRE: the hang is a FAILURE, never a silent pass and never
        # an indefinite wait -- this is the T-3192 acceptance criterion
        # itself, reproduced locally instead of trusted from CI history.
        assert proc.returncode != 0, (
            "planted hang exited 0 -- the timeout guard did not fire at all"
        )

        # MUST-FIRE: the failure output NAMES where it was stuck (a stack
        # dump), not just a bare timeout message -- the whole point of
        # PYTHONFAULTHANDLER over a plain `timeout` with no signal choice.
        combined = proc.stdout + proc.stderr
        assert "test_deliberately_hangs_forever" in combined, (
            "no frame naming the wedged test function in the output -- "
            "the fault handler did not dump a stack:\n" + combined
        )
        assert "test_planted_hang.py" in combined

    def test_ordinary_fast_test_is_unaffected(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: the same recipe, against a test that finishes
        immediately, passes cleanly with no stray dump/timeout noise --
        the guard must not manufacture false failures for healthy runs."""
        # frob:tests tests/system/test_ci_hang_guard_positive_control.py::TestCiHangGuardPositiveControl.test_ordinary_fast_test_is_unaffected  # noqa: E501
        fast_file = tmp_path / "test_fast.py"
        fast_file.write_text("def test_trivially_passes():\n    assert True\n")
        env = os.environ | {"PYTHONFAULTHANDLER": "1"}
        proc = subprocess.run(
            [
                "timeout",
                "-s",
                "ABRT",
                "20s",
                sys.executable,
                "-m",
                "pytest",
                "-q",
                str(fast_file),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "Fatal Python error" not in (proc.stdout + proc.stderr)
