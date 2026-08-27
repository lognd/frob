"""Shared, safe process-liveness probe (T-3018): one `frob.process` home
for the pid-alive check that used to be duplicated between
`frob.mutate._journal` (fixed for Windows by T-3003) and
`frob.tickets._land` (still the unsafe POSIX-shaped shape T-3018 found).

On POSIX, `os.kill(pid, 0)` is a genuine side-effect-free liveness probe:
signal `0` sends nothing, so a `ProcessLookupError` means the pid is gone
and success (or `PermissionError`, meaning the pid exists but is owned by
someone else) means it is alive.

On Windows, `os.kill(pid, sig)` is NOT side-effect-free: CPython's
Windows `os.kill` opens the target with `PROCESS_ALL_ACCESS` and calls
`TerminateProcess(handle, sig)` -- a `sig` of `0` still terminates
whatever process currently holds that pid, exit code `0`. Combined with
Windows' fast PID reuse, a genuinely-dead pid probed shortly after exit
can be silently reassigned to an unrelated LIVE process by the time this
runs, and the POSIX-shaped probe would then actively kill it instead of
merely observing it. `pid_alive` therefore never calls `os.kill` when the
Windows backend is available: it opens a query-only handle
(`PROCESS_QUERY_LIMITED_INFORMATION`, no kill rights at all) and reads
`GetExitCodeProcess`/`STILL_ACTIVE`, which cannot terminate anything.
"""

from __future__ import annotations

import ctypes
import os
from typing import Any

from frob.logging import get_logger

# frob:ticket T-3018
_log = get_logger(__name__)

# frob:ticket T-3018
#: The Windows `kernel32` handle, or `None` on any platform where
#: `ctypes.windll` does not exist (every non-Windows platform). Resolved
#: once at import time, the same "optional backend probed once at import,
#: `None` everywhere it is unavailable" shape `frob.process._lock`'s own
#: `msvcrt`/`fcntl` pair uses (T-2934) -- a test fakes the Windows path on
#: Linux CI by monkeypatching THIS name directly (`monkeypatch.setattr(
#: _pid_liveness, "_kernel32", FakeKernel32())`), never by monkeypatching
#: `sys.platform` or the shared global `ctypes` module.
_kernel32: Any | None
try:
    _kernel32 = ctypes.windll.kernel32  # ty: ignore[unresolved-attribute]
except AttributeError:
    _kernel32 = None

# frob:ticket T-3018
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259


# frob:ticket T-3018
def _pid_alive_windows(pid: int) -> bool:
    """Windows-backend liveness probe: open `pid` with query-only rights
    and read its exit code -- never a `TerminateProcess`-capable handle,
    so (unlike a POSIX-shaped `os.kill(pid, 0)`) this cannot kill a live
    process even under a PID-reuse race. Callers reach this only when
    `_kernel32` is not `None` (a real Windows process, or a test's fake
    standing in for one)."""
    assert _kernel32 is not None
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # ERROR_INVALID_PARAMETER (and similar) -- no such pid: dead.
        return False
    try:
        exit_code = ctypes.c_ulong()
        if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            # Could not query for some other reason -- conservatively alive.
            return True
        return exit_code.value == _STILL_ACTIVE
    finally:
        _kernel32.CloseHandle(handle)


# frob:doc docs/modules/process.md#pid-liveness-t-3018
# frob:ticket T-3018
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAlivePosix.test_current_process_is_alive  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAlivePosix.test_process_lookup_error_is_dead  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAlivePosix.test_permission_error_is_conservatively_alive  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend.test_alive_pid_reports_true  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend.test_exited_pid_reports_false  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend.test_unknown_pid_open_process_fails_reports_false  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend.test_never_requests_kill_capable_access_rights  # noqa: E501
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to os.kill itself; every exception \
# os.kill can raise is an OSError subclass, and ProcessLookupError/ \
# PermissionError/OSError together already cover the full hierarchy"
def pid_alive(pid: int) -> bool:
    """Whether `pid` names a currently-running process, safely on every
    platform (T-3018/T-3003). On POSIX (`_kernel32 is None`), a signal-0
    probe (`os.kill(pid, 0)`, which sends no actual signal): a
    `ProcessLookupError` means the PID is gone (dead); a `PermissionError`
    means the PID exists but is owned by someone else (alive, just not
    ours to signal) -- treated as alive, the conservative choice. On
    Windows (`_kernel32` set), delegates to `_pid_alive_windows` instead
    -- see its docstring for why the POSIX-shaped probe is unsafe there."""
    if _kernel32 is not None:
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


# frob:doc docs/modules/process.md#pid-liveness-t-3018
# frob:ticket T-3018
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to os.kill itself; every exception \
# os.kill can raise is an OSError subclass, and ProcessLookupError/ \
# PermissionError/OSError together already cover the full hierarchy"
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveTristatePosix.test_process_lookup_error_is_confirmed_dead  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveTristatePosix.test_permission_error_is_ambiguous_not_alive  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveTristatePosix.test_live_pid_is_true  # noqa: E501
# frob:tests tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend.test_tristate_never_returns_ambiguous_on_windows_backend  # noqa: E501
def pid_alive_tristate(pid: int) -> bool | None:
    """Three-state variant of `pid_alive` for a caller that must never
    treat "cannot tell" as license to act (e.g. `frob.tickets._land`'s
    land-lock-holder reclaim logic: only a CONFIRMED-dead holder is ever
    safe to reclaim automatically). `True` (alive), `False` (CONFIRMED
    dead), or `None` (ambiguous -- ONLY reachable on POSIX, where a
    `PermissionError`/other non-`ProcessLookupError` `OSError` means "pid
    exists but we cannot fully probe it" or "transient probe failure",
    never a trustworthy dead/alive verdict either way). On Windows
    (`_kernel32` set), `_pid_alive_windows`'s query-only probe is
    definitive by construction (an inaccessible-but-real handle still
    yields a `GetExitCodeProcess` verdict or the documented conservative
    `True` fallback) -- `None` never occurs there."""
    if _kernel32 is not None:
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return None
    return True
