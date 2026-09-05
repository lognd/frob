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
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from frob.process._guard import (
    EXEC_KILL_SWITCH_ENV,
    FROB_DISABLE_POOL_PRELOAD_ENV,
    FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV,
    NET_KILL_SWITCH_ENV,
    ProcessGuardError,
    _default_text_encoding,
    _win32_isolate_console_group,
    exec_enabled,
    guarded_subprocess_run,
    net_enabled,
    pool_preload_enabled,
    win32_console_ctrl_ignore_scope,
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


# frob:ticket T-3670
class TestPoolPreloadEnabled:
    """T-3670 round 16: FROB_DISABLE_POOL_PRELOAD is frob.gates's own
    internal ProcessPoolExecutor kill switch -- a different spawn family
    from EXEC_KILL_SWITCH_ENV/NET_KILL_SWITCH_ENV above, which only ever
    gate guarded_subprocess_run's EXTERNAL tool spawns."""

    def test_unset_env_is_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/process/_guard.py::pool_preload_enabled kind="unit"
        monkeypatch.delenv(FROB_DISABLE_POOL_PRELOAD_ENV, raising=False)
        assert pool_preload_enabled() is True

    def test_truthy_value_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/process/_guard.py::pool_preload_enabled kind="unit"
        monkeypatch.setenv(FROB_DISABLE_POOL_PRELOAD_ENV, "1")
        assert pool_preload_enabled() is False

    def test_falsy_value_stays_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # frob:tests src/frob/process/_guard.py::pool_preload_enabled kind="unit"
        monkeypatch.setenv(FROB_DISABLE_POOL_PRELOAD_ENV, "0")
        assert pool_preload_enabled() is True


# frob:ticket T-0200
class TestGuardedSubprocessRun:
    # invariant spec: [INV-019](invariants/INV-019.md)
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

    # frob:ticket T-3015
    def test_timeout_returns_err_never_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3015: a command that outlives its `timeout=` budget must come
        back as `Err(ProcessGuardError.Timeout)`, never a raised
        `subprocess.TimeoutExpired` escaping this function -- the exact
        crash that took down `move-module`'s own Verify phase mid-
        transaction (T-2990/T-2989)."""
        # frob:tests src/frob/process/_guard.py::guarded_subprocess_run kind="unit"
        monkeypatch.delenv(EXEC_KILL_SWITCH_ENV, raising=False)
        result = guarded_subprocess_run(
            ["python3", "-c", "import time; time.sleep(5)"],
            capture_output=True,
            text=True,
            timeout=0.1,
        )
        assert result.is_err
        assert result.danger_err is ProcessGuardError.Timeout

    # frob:ticket T-3015
    def test_healthy_path_unchanged_when_timeout_kwarg_given(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3015 must-still-work fixture: a `timeout=` kwarg that the
        command comfortably beats behaves exactly as before -- `Ok` with
        the real `CompletedProcess`, not a new code path introduced by the
        try/except wrapping."""
        # frob:tests src/frob/process/_guard.py::guarded_subprocess_run kind="unit"
        monkeypatch.delenv(EXEC_KILL_SWITCH_ENV, raising=False)
        result = guarded_subprocess_run(
            ["python3", "-c", "print('hi')"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.is_ok
        assert result.danger_ok.stdout.strip() == "hi"

    # frob:ticket T-3797
    def test_missing_binary_returns_err_spawn_failed_never_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3797: an executable that cannot be spawned at all (missing
        binary) must come back as `Err(ProcessGuardError.SpawnFailed)`,
        never a raised `FileNotFoundError`/`OSError` escaping this
        function -- on win32 this same case surfaces as `FileNotFoundError:
        [WinError 2]` from `CreateProcess` and crashed `frob doctor`
        (`doctor.py::scan_external_tools` -> `_probe_binary_version` ->
        `guarded_subprocess_run`), which documents "never raises (missing
        binary...)" and relied on this function actually honoring that."""
        # frob:tests src/frob/process/_guard.py::guarded_subprocess_run kind="unit"
        monkeypatch.delenv(EXEC_KILL_SWITCH_ENV, raising=False)
        result = guarded_subprocess_run(
            ["a-binary-that-does-not-exist-xyz123", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.is_err
        assert result.danger_err is ProcessGuardError.SpawnFailed


# frob:ticket T-3651
class TestWin32IsolateConsoleGroup:
    """T-3648/T-3651: win32 frob check saga -- a spawned child inheriting
    frob's own console process group lets a console ctrl event delivered
    to that group reach frob's own main process too, not just the child,
    matching the spuriously-injected `KeyboardInterrupt` T-3648's diag
    caught with no visible external Ctrl-C. T-3648's
    `CREATE_NEW_PROCESS_GROUP`-only fix was NOT enough (run 33513484322
    caught the real SIGINT immediately after a tool spawn) because a new
    process group still SHARES THE CONSOLE with its parent -- any
    console-attached child can signal every process on that console
    regardless of group. `guarded_subprocess_run` now defaults every
    win32 spawn into its own process group AND off any console entirely
    (`CREATE_NO_WINDOW`), unless a caller already set an explicit
    `creationflags`."""

    # frob:tests src/frob/process/_guard.py::_win32_isolate_console_group
    def test_no_op_on_non_win32(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "linux")
        result = _win32_isolate_console_group({"capture_output": True})
        assert "creationflags" not in result

    # frob:tests src/frob/process/_guard.py::_win32_isolate_console_group
    def test_sets_new_process_group_on_win32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "win32")
        monkeypatch.setattr(
            "frob.process._guard.subprocess.CREATE_NEW_PROCESS_GROUP",
            0x00000200,
            raising=False,
        )
        monkeypatch.setattr(
            "frob.process._guard.subprocess.CREATE_NO_WINDOW",
            0x08000000,
            raising=False,
        )
        result = _win32_isolate_console_group({"capture_output": True})
        assert result["creationflags"] == 0x00000200 | 0x08000000

    # frob:tests src/frob/process/_guard.py::_win32_isolate_console_group
    def test_sets_create_no_window_on_win32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "win32")
        monkeypatch.setattr(
            "frob.process._guard.subprocess.CREATE_NEW_PROCESS_GROUP",
            0x00000200,
            raising=False,
        )
        monkeypatch.setattr(
            "frob.process._guard.subprocess.CREATE_NO_WINDOW",
            0x08000000,
            raising=False,
        )
        result = _win32_isolate_console_group({})
        flags = result["creationflags"]
        assert isinstance(flags, int)
        assert flags & 0x08000000

    # frob:tests src/frob/process/_guard.py::_win32_isolate_console_group
    def test_never_overrides_an_explicit_creationflags(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "win32")
        result = _win32_isolate_console_group({"creationflags": 42})
        assert result["creationflags"] == 42


class _FakeKernel32:
    """Records `SetConsoleCtrlHandler` calls in place of the real win32
    API (T-3657) -- lets `TestWin32ConsoleCtrlIgnoreScope` exercise the
    install/remove/callback contract on any host platform, not only
    win32."""

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls: list[tuple[Callable[[int], bool], bool]] = []

    def SetConsoleCtrlHandler(  # noqa: N802
        self, handler: Callable[[int], bool], add: bool
    ) -> bool:
        """Record `(handler, add)` and report success, mirroring the real
        `kernel32.SetConsoleCtrlHandler`'s boolean return."""
        self.calls.append((handler, add))
        return True


class _FakeWindll:
    """Stand-in for `ctypes.windll` exposing only `.kernel32` (T-3657)."""

    def __init__(self, kernel32: _FakeKernel32) -> None:
        """Wrap the given fake kernel32."""
        self.kernel32 = kernel32


class _FakeCtypes:
    """Stand-in for the `ctypes` module used inside
    `win32_console_ctrl_ignore_scope` (T-3657): real `WINFUNCTYPE`/
    `c_bool`/`c_ulong` don't exist off win32, so the scope's own `ctypes`
    reference is monkeypatched to this fake for non-win32 test hosts."""

    def __init__(self) -> None:
        """Build a fresh fake kernel32/windll pair for this instance."""
        self.kernel32 = _FakeKernel32()
        self.windll = _FakeWindll(self.kernel32)

    def WINFUNCTYPE(self, *_args: object, **_kwargs: object):  # noqa: N802
        """Return an identity factory: wrapping a plain Python callable
        with it just returns that callable, since the fake kernel32 never
        actually crosses the ctypes FFI boundary."""
        return lambda fn: fn

    c_bool = bool
    c_ulong = int


# frob:ticket T-3657
class TestWin32ConsoleCtrlIgnoreScope:
    """T-3657 round 15: `win32_console_ctrl_ignore_scope` is the prepared
    (env-gated, off-by-default) mitigation for the sender T-3651 (round
    14) proved is NOT one of the four guarded tool children -- see
    `FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV`'s docstring for the falsified
    round-14 hypothesis and this ticket's full evidence chain."""

    # frob:tests src/frob/process/_guard.py::win32_console_ctrl_ignore_scope
    def test_no_op_on_non_win32(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "linux")
        monkeypatch.setenv(FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV, "1")
        entered = False
        with win32_console_ctrl_ignore_scope():
            entered = True
        assert entered

    # frob:tests src/frob/process/_guard.py::win32_console_ctrl_ignore_scope
    def test_no_op_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "win32")
        monkeypatch.delenv(FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV, raising=False)
        fake_ctypes = _FakeCtypes()
        monkeypatch.setattr("frob.process._guard.ctypes", fake_ctypes)
        with win32_console_ctrl_ignore_scope():
            pass
        assert fake_ctypes.kernel32.calls == []

    # frob:tests src/frob/process/_guard.py::win32_console_ctrl_ignore_scope
    def test_installs_and_removes_handler_when_requested(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "win32")
        monkeypatch.setenv(FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV, "1")
        fake_ctypes = _FakeCtypes()
        monkeypatch.setattr("frob.process._guard.ctypes", fake_ctypes)
        with win32_console_ctrl_ignore_scope():
            assert fake_ctypes.kernel32.calls == [
                (fake_ctypes.kernel32.calls[0][0], True)
            ]
        assert fake_ctypes.kernel32.calls == [
            (fake_ctypes.kernel32.calls[0][0], True),
            (fake_ctypes.kernel32.calls[0][0], False),
        ]

    # frob:tests src/frob/process/_guard.py::win32_console_ctrl_ignore_scope
    def test_handler_swallows_ctrl_c_and_ctrl_break(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "win32")
        monkeypatch.setenv(FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV, "1")
        fake_ctypes = _FakeCtypes()
        monkeypatch.setattr("frob.process._guard.ctypes", fake_ctypes)
        with win32_console_ctrl_ignore_scope():
            handler = fake_ctypes.kernel32.calls[0][0]
            assert handler(0) is True  # CTRL_C_EVENT
            assert handler(1) is True  # CTRL_BREAK_EVENT

    # frob:tests src/frob/process/_guard.py::win32_console_ctrl_ignore_scope
    def test_handler_passes_through_other_events(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("frob.process._guard.sys.platform", "win32")
        monkeypatch.setenv(FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV, "1")
        fake_ctypes = _FakeCtypes()
        monkeypatch.setattr("frob.process._guard.ctypes", fake_ctypes)
        with win32_console_ctrl_ignore_scope():
            handler = fake_ctypes.kernel32.calls[0][0]
            assert handler(2) is False  # CTRL_CLOSE_EVENT, not ours to swallow


class TestDefaultTextEncoding:
    """T-2953: `subprocess.run(text=True, ...)` with no explicit
    `encoding=` falls back to the platform's default locale codec --
    UTF-8 on Linux/macOS, but cp1252 (or another Windows code page) on
    Windows -- so a byte a third-party tool (maturin/cargo/git/ty) can
    legitimately emit crashes the read with an uncatchable
    UnicodeDecodeError deep inside subprocess's own reader thread. This
    crashed `frob natives build`'s maturin call on windows-latest CI
    before the native extension was even built."""

    def test_injects_utf8_replace_when_text_true_and_no_encoding(self) -> None:
        result = _default_text_encoding({"text": True, "capture_output": True})
        assert result["encoding"] == "utf-8"
        assert result["errors"] == "replace"

    def test_injects_when_universal_newlines_true(self) -> None:
        result = _default_text_encoding({"universal_newlines": True})
        assert result["encoding"] == "utf-8"
        assert result["errors"] == "replace"

    def test_never_overrides_explicit_encoding(self) -> None:
        result = _default_text_encoding({"text": True, "encoding": "latin-1"})
        assert result["encoding"] == "latin-1"
        assert "errors" not in result

    def test_never_overrides_explicit_errors(self) -> None:
        result = _default_text_encoding({"text": True, "errors": "strict"})
        assert result["encoding"] == "utf-8"
        assert result["errors"] == "strict"

    def test_no_op_without_text_mode(self) -> None:
        result = _default_text_encoding({"capture_output": True})
        assert "encoding" not in result
        assert "errors" not in result

    def test_guarded_subprocess_run_survives_the_reported_crash_byte(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end regression for the exact byte
        (`UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f`)
        windows-latest CI reported: a real subprocess emitting that byte
        on stdout must not raise, and the captured text must be a real
        `str` (never `None`, which is what crashed the pydantic
        `CrateBuildResult` model downstream in `frob.natives._build`)."""
        monkeypatch.delenv(EXEC_KILL_SWITCH_ENV, raising=False)
        result = guarded_subprocess_run(
            [
                "python3",
                "-c",
                "import sys; sys.stdout.buffer.write(bytes([0x8f]))",
            ],
            capture_output=True,
            text=True,
        )
        assert result.is_ok
        proc = result.danger_ok
        assert isinstance(proc.stdout, str)
        assert proc.stdout != ""


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
