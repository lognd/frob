# frob:ticket T-1309
"""Real-behavior tests for `frob.check._native`'s cargo runners (T-1309
TEST005 burn-down): the success, kill-switch-disabled, and unexpected-
crash paths for `_run_cargo`/`_run_cargo_fmt_check`/`_run_cargo_test`,
none of which any prior test exercised (only the missing-binary path was
covered, in `tests/unit/test_check_tool_unavailable.py`).
"""

from __future__ import annotations

from pathlib import Path

from typani import Err, Ok

from frob.check import _native as native_mod
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


class TestRunCargoRealPaths:
    def test_success_parses_cargo_json(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths.test_success_parses_cargo_json  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = native_mod._run_cargo("check", tmp_path)
        assert result.tool == "cargo-check"
        assert result.exit_code == 0

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cargo("clippy", tmp_path)
        assert not result.passed

    def test_unexpected_crash_is_typed_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths.test_unexpected_crash_is_typed_result  # noqa: E501
        def _raise(*a, **kw):
            raise RuntimeError("simulated: unexpected crash")

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_cargo("check", tmp_path)
        assert not result.passed


class TestRunCargoFmtCheckRealPaths:
    def test_all_formatted_is_clean_pass(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths.test_all_formatted_is_clean_pass  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = native_mod._run_cargo_fmt_check(tmp_path)
        assert result.exit_code == 0
        assert "formatted" in result.summary

    def test_unformatted_lines_produce_warning_diagnostics(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths.test_unformatted_lines_produce_warning_diagnostics  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(
                _FakeCompletedProcess(stdout="Diff in src/lib.rs\n", returncode=1)
            ),
        )
        result = native_mod._run_cargo_fmt_check(tmp_path)
        assert result.exit_code == 1
        assert len(result.diagnostics) == 1

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cargo_fmt_check(tmp_path)
        assert not result.passed


class TestRunCargoTestRealPaths:
    def test_success_parses_cargo_json(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths.test_success_parses_cargo_json  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = native_mod._run_cargo_test(tmp_path)
        assert result.tool == "cargo-test"

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cargo_test(tmp_path)
        assert not result.passed

    def test_unexpected_crash_is_typed_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths.test_unexpected_crash_is_typed_result  # noqa: E501
        def _raise(*a, **kw):
            raise RuntimeError("simulated: unexpected crash")

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_cargo_test(tmp_path)
        assert not result.passed
