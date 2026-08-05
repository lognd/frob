"""T-1350 TEST005 burn-down: `frob.perf._harness.main`'s remaining
uncovered branches -- the short-argv early return (line 98), the `-m
<module>` dispatch path (`is_module` True at lines 113/124), and the
`SystemExit` exit-code normalization's non-int/None branches (line 122's
surrounding `isinstance`/`None` checks). `test_harness_sampling.py`
already covers the script-argv, sampled, and `FROB_PERF_SERIAL_POOLS`
branches; this file fills in the remainder without duplicating that
coverage.
"""

from __future__ import annotations

import sys
from pathlib import Path

from frob.perf import _harness

_MODULE_FIXTURE = """
def hot_loop():
    total = 0
    for i in range(5):
        total += i
    return total


if __name__ == "__main__":
    hot_loop()
"""


class TestHarnessMainShortArgv:
    """Line 98's `len(sys.argv) < 3` True branch: too few argv tokens
    returns 2 immediately, never touching cProfile/runpy at all."""

    def test_missing_target_returns_2(self, monkeypatch) -> None:
        # frob:tests tests/unit/perf/test_harness_main_branches.py::TestHarnessMainShortArgv.test_missing_target_returns_2  # noqa: E501
        monkeypatch.setattr(sys, "argv", ["_harness.py", "out.pstats"])
        assert _harness.main() == 2

    def test_no_argv_at_all_returns_2(self, monkeypatch) -> None:
        # frob:tests tests/unit/perf/test_harness_main_branches.py::TestHarnessMainShortArgv.test_no_argv_at_all_returns_2  # noqa: E501
        monkeypatch.setattr(sys, "argv", ["_harness.py"])
        assert _harness.main() == 2


class TestHarnessMainModuleDispatch:
    """`is_module` True branch (lines 113/124): `-m <module>` argv form
    runs via `runpy.run_module`, not `runpy.run_path`, and rewrites
    `sys.argv` to `[modname, ...]` rather than the raw target list."""

    def test_dash_m_runs_module_and_exits_clean(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/perf/test_harness_main_branches.py::TestHarnessMainModuleDispatch.test_dash_m_runs_module_and_exits_clean  # noqa: E501
        modname = "_t1350_hot_loop_mod"
        script = tmp_path / f"{modname}.py"
        script.write_text(_MODULE_FIXTURE, encoding="utf-8")
        pstats_path = tmp_path / "out.pstats"

        monkeypatch.setenv("FROB_PERF_SERIAL_POOLS", "0")
        monkeypatch.delenv("FROB_PERF_SAMPLE", raising=False)
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.setattr(
            sys, "argv", ["_harness.py", str(pstats_path), "-m", modname]
        )
        code = _harness.main()
        assert code == 0
        assert pstats_path.is_file()


class TestHarnessMainExitCodeNormalization:
    """`SystemExit.code`'s three shapes (line 122's ternary): a plain int
    code, `None` (bare `sys.exit()`), and a non-int code (e.g. a string
    message) each normalize differently -- int passes through, `None`
    means clean (0), anything else means failure (1)."""

    def _run(self, tmp_path: Path, monkeypatch, body: str) -> int:
        script = tmp_path / "workload.py"
        script.write_text(body, encoding="utf-8")
        pstats_path = tmp_path / "out.pstats"
        monkeypatch.setenv("FROB_PERF_SERIAL_POOLS", "0")
        monkeypatch.delenv("FROB_PERF_SAMPLE", raising=False)
        monkeypatch.setattr(
            sys, "argv", ["_harness.py", str(pstats_path), str(script)]
        )
        return _harness.main()

    def test_int_exit_code_passes_through(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization.test_int_exit_code_passes_through  # noqa: E501
        code = self._run(tmp_path, monkeypatch, "raise SystemExit(7)\n")
        assert code == 7

    def test_none_exit_code_normalizes_to_zero(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization.test_none_exit_code_normalizes_to_zero  # noqa: E501
        code = self._run(tmp_path, monkeypatch, "raise SystemExit()\n")
        assert code == 0

    def test_non_int_exit_code_normalizes_to_one(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization.test_non_int_exit_code_normalizes_to_one  # noqa: E501
        code = self._run(tmp_path, monkeypatch, "raise SystemExit('boom')\n")
        assert code == 1

    def test_clean_run_returns_zero_without_exit(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/perf/test_harness_main_branches.py::TestHarnessMainExitCodeNormalization.test_clean_run_returns_zero_without_exit  # noqa: E501
        code = self._run(tmp_path, monkeypatch, "x = 1 + 1\n")
        assert code == 0
