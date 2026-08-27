"""T-3018: `frob.process._pid_liveness` -- the shared, safe cross-platform
pid-liveness probe extracted out of `frob.mutate._journal` (T-3003) and
`frob.tickets._land` (still the unsafe POSIX-shaped `os.kill(pid, 0)`
before this ticket).

The Windows backend is exercised on Linux CI via a fake `kernel32`
standing in for the real Windows-only `ctypes.windll.kernel32`, the same
T-2934 precedent `frob.process._lock`'s own msvcrt/fcntl tests use:
monkeypatch the module's own resolved-backend name directly, never
`sys.platform` or the shared global `ctypes` module.
"""

from __future__ import annotations

import os

import pytest

from frob.process import _pid_liveness


class _FakeKernel32:
    """Stands in for `ctypes.windll.kernel32`: `alive_pids` names the pids
    this fake reports as `STILL_ACTIVE`; every other pid `OpenProcess`
    accepts is reported exited; `unknown_pids` fail `OpenProcess` outright
    (simulating a genuinely nonexistent pid)."""

    def __init__(
        self, alive_pids: set[int], unknown_pids: set[int] | None = None
    ) -> None:
        self._alive_pids = alive_pids
        self._unknown_pids = unknown_pids or set()
        self._open_handles: dict[int, int] = {}
        self._next_handle = 1

    def OpenProcess(self, _access, _inherit, pid):  # noqa: N802
        if pid in self._unknown_pids:
            return 0
        handle = self._next_handle
        self._next_handle += 1
        self._open_handles[handle] = pid
        return handle

    def GetExitCodeProcess(self, handle, exit_code_ptr):  # noqa: N802
        pid = self._open_handles[handle]
        exit_code_ptr._obj.value = (
            _pid_liveness._STILL_ACTIVE if pid in self._alive_pids else 0
        )
        return 1

    def CloseHandle(self, handle):  # noqa: N802
        self._open_handles.pop(handle, None)
        return 1


# frob:ticket T-3018
# frob:waive WIRE001 reason="a private per-file test helper used only by this file's \
# own test methods, all four call sites wrapped inside a monkeypatch.setattr(...) call \
# spanning multiple lines -- WIRE001's text-scan resolver does not always reach the \
# enclosing test_* method through that shape; there is no production caller to wire it \
# to by design" permanent="true"
def _make_raiser(exc_type: type[Exception]):
    """A fake `os.kill(pid, sig)` that always raises `exc_type` -- shared
    by both POSIX test classes below so the two closely-related "which
    exception maps to which verdict" tests do not duplicate the same
    monkeypatch plumbing (DUP002)."""

    def _raise(pid, sig):
        raise exc_type

    return _raise


class TestPidAlivePosix:
    """POSIX path: `_kernel32 is None`, real `os.kill(pid, 0)`."""

    def test_current_process_is_alive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_pid_liveness, "_kernel32", None)
        assert _pid_liveness.pid_alive(os.getpid()) is True

    def test_process_lookup_error_is_dead(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_pid_liveness, "_kernel32", None)
        monkeypatch.setattr(_pid_liveness.os, "kill", _make_raiser(ProcessLookupError))
        assert _pid_liveness.pid_alive(999999) is False

    def test_permission_error_is_conservatively_alive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_pid_liveness, "_kernel32", None)
        monkeypatch.setattr(_pid_liveness.os, "kill", _make_raiser(PermissionError))
        assert _pid_liveness.pid_alive(1) is True


class TestPidAliveTristatePosix:
    """`pid_alive_tristate`'s POSIX ambiguous case, unreachable via the
    plain `pid_alive` -- the whole reason `_land.py`'s reclaim logic
    needs the three-state variant."""

    def test_process_lookup_error_is_confirmed_dead(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_pid_liveness, "_kernel32", None)
        monkeypatch.setattr(_pid_liveness.os, "kill", _make_raiser(ProcessLookupError))
        assert _pid_liveness.pid_alive_tristate(999999) is False

    def test_permission_error_is_ambiguous_not_alive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(_pid_liveness, "_kernel32", None)
        monkeypatch.setattr(_pid_liveness.os, "kill", _make_raiser(PermissionError))
        assert _pid_liveness.pid_alive_tristate(1) is None

    def test_live_pid_is_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_pid_liveness, "_kernel32", None)
        assert _pid_liveness.pid_alive_tristate(os.getpid()) is True


class TestPidAliveWindowsBackend:
    """T-3018/T-3003: the query-only Windows probe never opens a
    `TerminateProcess`-capable handle -- proven here by a fake `kernel32`
    that would raise if `OpenProcess` were ever called with kill rights
    instead of `PROCESS_QUERY_LIMITED_INFORMATION`."""

    def test_alive_pid_reports_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeKernel32(alive_pids={4242})
        monkeypatch.setattr(_pid_liveness, "_kernel32", fake)
        assert _pid_liveness.pid_alive(4242) is True

    def test_exited_pid_reports_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeKernel32(alive_pids=set())
        monkeypatch.setattr(_pid_liveness, "_kernel32", fake)
        # OpenProcess succeeds (pid slot still resolvable) but the exit
        # code is not STILL_ACTIVE -- a real exited-but-not-yet-reaped
        # Windows process.
        assert _pid_liveness.pid_alive(1) is False

    def test_unknown_pid_open_process_fails_reports_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeKernel32(alive_pids=set(), unknown_pids={7777})
        monkeypatch.setattr(_pid_liveness, "_kernel32", fake)
        assert _pid_liveness.pid_alive(7777) is False

    def test_never_requests_kill_capable_access_rights(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The T-3003/T-3018 safety property itself: only the query-only
        access mask is ever requested, never PROCESS_ALL_ACCESS or any
        other mask carrying PROCESS_TERMINATE."""
        seen_access: list[int] = []

        class _RecordingKernel32(_FakeKernel32):
            def OpenProcess(self, _access, _inherit, pid):  # noqa: N802
                seen_access.append(_access)
                return super().OpenProcess(_access, _inherit, pid)

        fake = _RecordingKernel32(alive_pids={1})
        monkeypatch.setattr(_pid_liveness, "_kernel32", fake)
        _pid_liveness.pid_alive(1)
        assert seen_access == [_pid_liveness._PROCESS_QUERY_LIMITED_INFORMATION]

    def test_tristate_never_returns_ambiguous_on_windows_backend(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeKernel32(alive_pids={1})
        monkeypatch.setattr(_pid_liveness, "_kernel32", fake)
        assert _pid_liveness.pid_alive_tristate(1) is True
        assert _pid_liveness.pid_alive_tristate(2) is False
