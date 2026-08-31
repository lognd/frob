"""T-3531: CI output hygiene -- `faulthandler_timeout`/`log_level`
regression coverage.

Two things are tested:

1. The pinned config values in `pyproject.toml` (`faulthandler_timeout =
   600`, `log_level = "WARNING"`) do not silently regress back toward
   the noisy defaults T-3531 measured (100 / unset-DEBUG).
2. The underlying MECHANISM `faulthandler_timeout` exercises -- a test
   running past the threshold gets a full all-threads stack dump, one
   that finishes under it does not -- proven with a real subprocess
   pytest invocation, but at SCALED-DOWN timing (a fraction of a second,
   not the real 600s) so this stays a fast regression test rather than
   reproducing the 10-minute CI wait itself. The scaled proof is what
   MUST-FIRE/MUST-STAY-QUIET actually need: that raising the threshold
   number continues to gate the dump correctly, not that 600 specifically
   is the right number (a config constant, already covered by test 1).
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


class TestPinnedConfigValues:
    """T-3531's own config changes stay pinned -- a regression test for
    the two literal values, not the behavior (covered separately below)."""

    def test_faulthandler_timeout_is_raised_above_the_old_noisy_value(self) -> None:
        # frob:tests tests/system/test_faulthandler_ci_hygiene.py::TestPinnedConfigValues.test_faulthandler_timeout_is_raised_above_the_old_noisy_value  # noqa: E501
        with (_REPO_ROOT / "pyproject.toml").open("rb") as f:
            cfg = tomllib.load(f)
        pytest_cfg = cfg["tool"]["pytest"]["ini_options"]
        # T-3531: 100 sprayed a full-thread dump on every HEALTHY test past
        # 100s (the frob_self_scan_heavy group's own @pytest.mark.
        # timeout(1200) legitimately runs longer); must stay above that,
        # and below the heavy group's own 1200s kill so a genuine hang in
        # that group still dumps before it is killed.
        assert 100 < pytest_cfg["faulthandler_timeout"] < 1200

    def test_captured_log_level_is_bounded_to_warning(self) -> None:
        # frob:tests tests/system/test_faulthandler_ci_hygiene.py::TestPinnedConfigValues.test_captured_log_level_is_bounded_to_warning  # noqa: E501
        with (_REPO_ROOT / "pyproject.toml").open("rb") as f:
            cfg = tomllib.load(f)
        pytest_cfg = cfg["tool"]["pytest"]["ini_options"]
        assert pytest_cfg["log_level"] == "WARNING"


class TestFaulthandlerTimeoutMechanism:
    """T-3531 MUST-FIRE/MUST-STAY-QUIET: a real subprocess pytest run,
    scaled-down timing, proving the threshold itself (not just its
    current numeric value) correctly gates the dump."""

    @staticmethod
    def _run_scaled(tmp_path: Path, sleep_s: float, threshold_s: float) -> str:
        """Runs ONE synthetic test that sleeps `sleep_s`, under a
        `faulthandler_timeout` of `threshold_s`, and returns combined
        stdout+stderr. `--timeout` is set generously above `sleep_s` so
        the test always completes normally (pytest-timeout's own kill is
        not what this test is proving -- `faulthandler_timeout`'s
        independent dump-before-any-kill behavior is)."""
        test_file = tmp_path / "test_sleeper.py"
        test_file.write_text(
            "import time\n\n\ndef test_sleeper():\n    time.sleep(%r)\n" % sleep_s
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-o",
                f"faulthandler_timeout={threshold_s}",
                "-o",
                "addopts=",
                "--timeout",
                str(sleep_s + 30),
                "--timeout-method=thread",
                str(test_file),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=sleep_s + 60,
        )
        return result.stdout + result.stderr

    # frob:tests tests/system/test_faulthandler_ci_hygiene.py::TestFaulthandlerTimeoutMechanism.test_healthy_run_under_threshold_produces_no_dump  # noqa: E501
    def test_healthy_run_under_threshold_produces_no_dump(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: a test that finishes well before
        `faulthandler_timeout` produces zero stack-dump lines -- the
        scaled-down analog of the ticket's own '150s sleep, 300s
        threshold, zero dump lines' acceptance case."""
        output = self._run_scaled(tmp_path, sleep_s=0.3, threshold_s=5)
        assert "Stack of" not in output
        assert "Timeout (0:" not in output

    # frob:tests tests/system/test_faulthandler_ci_hygiene.py::TestFaulthandlerTimeoutMechanism.test_run_past_threshold_still_dumps  # noqa: E501
    def test_run_past_threshold_still_dumps(self, tmp_path: Path) -> None:
        """MUST-FIRE: a test that runs PAST `faulthandler_timeout` still
        gets the full all-threads dump -- raising the threshold narrows
        WHEN it fires, it must never silence it outright."""
        output = self._run_scaled(tmp_path, sleep_s=3, threshold_s=1)
        assert "Stack of" in output or "Timeout (0:" in output
