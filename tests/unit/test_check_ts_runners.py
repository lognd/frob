# frob:ticket T-1309
"""Real-behavior tests for `frob.check._ts`'s tsc/eslint/prettier/vitest
runners (T-1309 TEST005 burn-down): the success and kill-switch-disabled
paths through `_run_npx`, which `tests/unit/test_check_tool_unavailable.py`
does not cover (that file only exercises the missing-binary path).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from typani import Err, Ok

from frob.check import _ts as ts_mod
from frob.process._guard import ProcessGuardError


# frob:waive WIRE001 reason="a private test-fixture stand-in used only by this file's \
# own tests below -- there is no production caller to wire it to by design, it exists \
# solely as a subprocess.CompletedProcess-shaped stub for monkeypatched \
# guarded_subprocess_run returns" follow_up="T-1511"
class _FakeCompletedProcess:
    """Minimal `subprocess.CompletedProcess`-shaped stand-in."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


# frob:waive WIRE001 reason="an autouse pytest fixture, wired in by pytest's own \
# fixture-injection machinery for every test in this file (not a direct-call \
# relationship WIRE001's static caller search can see) -- the standard pytest fixture \
# idiom, not dead code" follow_up="T-1510"
@pytest.fixture(autouse=True)
def _npx_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file simulates `npx` being on PATH."""
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/npx")


class TestRunTscRealPaths:
    def test_success_parses_clean_output(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunTscRealPaths.test_success_parses_clean_output  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = ts_mod._run_tsc(tmp_path)
        assert result.tool == "tsc"
        assert result.exit_code == 0

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunTscRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = ts_mod._run_tsc(tmp_path)
        assert not result.passed
        assert "disabled" in result.summary.lower()

    def test_timeout_is_missing_tool_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunTscRealPaths.test_timeout_is_missing_tool_result  # noqa: E501
        def _raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="npx", timeout=1)

        monkeypatch.setattr(ts_mod, "guarded_subprocess_run", _raise_timeout)
        result = ts_mod._run_tsc(tmp_path)
        assert not result.passed


class TestRunEslintRealPaths:
    def test_success_parses_json_output(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunEslintRealPaths.test_success_parses_json_output  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="[]", returncode=0)),
        )
        result = ts_mod._run_eslint(tmp_path)
        assert result.tool == "eslint"

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunEslintRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = ts_mod._run_eslint(tmp_path)
        assert not result.passed


class TestRunPrettierRealPaths:
    def test_all_formatted_is_clean_pass(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunPrettierRealPaths.test_all_formatted_is_clean_pass  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = ts_mod._run_prettier(tmp_path)
        assert result.exit_code == 0
        assert "formatted" in result.summary

    def test_unformatted_files_produce_warning_diagnostics(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunPrettierRealPaths.test_unformatted_files_produce_warning_diagnostics  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(
                _FakeCompletedProcess(stdout="src/a.ts\nsrc/b.ts\n", returncode=1)
            ),
        )
        result = ts_mod._run_prettier(tmp_path)
        assert result.exit_code == 1
        assert len(result.diagnostics) == 2
        assert "2 files" in result.summary

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunPrettierRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = ts_mod._run_prettier(tmp_path)
        assert not result.passed


class TestRunVitestRealPaths:
    def test_no_parseable_report_is_unverified_pass(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunVitestRealPaths.test_no_parseable_report_is_unverified_pass  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(
                _FakeCompletedProcess(stdout="not json", returncode=0)
            ),
        )
        result = ts_mod._run_vitest(tmp_path)
        assert "unverified" in result.summary
        assert len(result.diagnostics) == 1

    def test_nonzero_exit_no_report_is_failed(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunVitestRealPaths.test_nonzero_exit_no_report_is_failed  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(
                _FakeCompletedProcess(stdout="not json", returncode=1)
            ),
        )
        result = ts_mod._run_vitest(tmp_path)
        assert result.summary == "tests failed"

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_ts_runners.py::TestRunVitestRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            ts_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = ts_mod._run_vitest(tmp_path)
        assert not result.passed
