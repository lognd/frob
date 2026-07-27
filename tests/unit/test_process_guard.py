"""T-0200: `frob.process._guard`'s real exec/net kill-switch mechanism, and
its wiring into every `frob.check` tool runner
(`_python.py`/`_native.py`/`_ts.py`) that spawns a subprocess. `design/
frob.strata`'s `checker` node LINT004 finding (T-0155) claimed "no real
kill switch around subprocess spawning yet" -- these tests are the
evidence that claim is no longer true: `FROB_DISABLE_EXEC=1` genuinely
stops every check-stage tool invocation without a redeploy.
"""

from __future__ import annotations

import subprocess

import pytest

from frob.process._guard import (
    EXEC_KILL_SWITCH_ENV,
    NET_KILL_SWITCH_ENV,
    ProcessGuardError,
    exec_enabled,
    guarded_subprocess_run,
    net_enabled,
)


# frob:ticket T-0200
class TestExecEnabled:
    def test_unset_env_is_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/process/_guard.py::exec_enabled kind="unit"
        monkeypatch.delenv(EXEC_KILL_SWITCH_ENV, raising=False)
        assert exec_enabled() is True

    @pytest.mark.parametrize("value", ["1", "true", "True", "YES", "on"])
    def test_truthy_values_disable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        # frob:tests src/frob/process/_guard.py::exec_enabled kind="unit"
        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, value)
        assert exec_enabled() is False

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
    def test_falsy_values_stay_enabled(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        # frob:tests src/frob/process/_guard.py::exec_enabled kind="unit"
        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, value)
        assert exec_enabled() is True


# frob:ticket T-0200
class TestNetEnabled:
    def test_unset_env_is_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/process/_guard.py::net_enabled kind="unit"
        monkeypatch.delenv(NET_KILL_SWITCH_ENV, raising=False)
        assert net_enabled() is True

    def test_truthy_value_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/process/_guard.py::net_enabled kind="unit"
        monkeypatch.setenv(NET_KILL_SWITCH_ENV, "1")
        assert net_enabled() is False


# frob:ticket T-0200
class TestGuardedSubprocessRun:
    def test_disabled_returns_err_without_spawning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/process/_guard.py::guarded_subprocess_run kind="unit"
        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, "1")

        def _fail_if_called(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise AssertionError("subprocess.run must not be called while disabled")

        monkeypatch.setattr(subprocess, "run", _fail_if_called)
        result = guarded_subprocess_run(["true"])
        assert result.is_err
        assert result.danger_err is ProcessGuardError.ExecDisabled

    def test_enabled_spawns_and_returns_ok(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/process/_guard.py::guarded_subprocess_run kind="unit"
        monkeypatch.delenv(EXEC_KILL_SWITCH_ENV, raising=False)
        result = guarded_subprocess_run(
            ["python3", "-c", "print('hi')"], capture_output=True, text=True
        )
        assert result.is_ok
        assert result.danger_ok.stdout.strip() == "hi"


# frob:ticket T-0200
class TestCheckStagesHonorExecKillSwitch:
    """Every tool runner that shells out spawns nothing while
    `FROB_DISABLE_EXEC` is set -- the real, wired mechanism behind
    `checker`'s `design/frob.strata` `attr flag="FROB_DISABLE_EXEC";`."""

    def test_run_ruff_disabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        # frob:tests src/frob/check/_python.py::_run_ruff kind="unit"
        # frob:tests src/frob/process/parsers/common.py::tool_disabled_result \
        # kind="unit"
        from frob.check._python import _run_ruff

        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, "1")
        results = _run_ruff(tmp_path, None)
        assert len(results) == 2
        for r in results:
            assert not r.passed
            assert EXEC_KILL_SWITCH_ENV in r.summary

    def test_run_ty_disabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        # frob:tests src/frob/check/_python.py::_run_ty kind="unit"
        from frob.check._python import _run_ty

        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, "1")
        r = _run_ty(tmp_path)
        assert not r.passed
        assert EXEC_KILL_SWITCH_ENV in r.summary

    def test_run_cmake_build_disabled(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        # frob:tests src/frob/check/_native.py::_cmake_configure kind="unit"
        from frob.check._native import _cmake_configure

        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, "1")
        r = _cmake_configure(tmp_path, tmp_path / "build")
        assert r is not None
        assert not r.passed
        assert EXEC_KILL_SWITCH_ENV in r.summary

    def test_run_cargo_disabled(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        # frob:tests src/frob/check/_native.py::_run_cargo kind="unit"
        from frob.check._native import _run_cargo

        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, "1")
        r = _run_cargo("build", tmp_path)
        assert r is not None
        assert not r.passed
        assert EXEC_KILL_SWITCH_ENV in r.summary

    def test_run_tsc_disabled(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        # frob:tests src/frob/check/_ts.py::_run_tsc kind="unit"
        import shutil

        from frob.check._ts import _run_tsc

        if shutil.which("npx") is None:
            pytest.skip("npx not on PATH in this environment")
        monkeypatch.setenv(EXEC_KILL_SWITCH_ENV, "1")
        r = _run_tsc(tmp_path)
        assert not r.passed
        assert EXEC_KILL_SWITCH_ENV in r.summary
