"""Single cross-platform "is stdin a real interactive terminal" decision
(T-4255), for callers that must fail fast rather than block/misbehave off
a TTY (`frob ticket attach`'s clipboard read, `frob ticket new`'s clipboard
offer).

`sys.stdin.isatty()` alone is NOT that check on win32: measured on real
Windows via `winrun` (T-4255), `sys.stdin.isatty()` returns `True` for a
child spawned with `stdin=subprocess.DEVNULL` -- the Windows CRT's
`_isatty()` reports `True` for ANY character device, and `NUL` is a
character device, not only a real console. The exact same call that
correctly signals "no TTY" on Linux/macOS (piping from `/dev/null`)
therefore lies on Windows, and a caller gating a fast-fail on it alone
takes the wrong branch there -- proven by `frob ticket attach`'s own T-3936
regression test failing on windows-latest with the clipboard path
attempted instead of the "no TTY" refusal.

`GetConsoleMode` (via `ctypes`) is the reliable win32-side check: it
succeeds only for a handle that is genuinely attached to a console,
returning `False`/failure for `NUL`, a pipe, or a redirected file --
confirmed by direct measurement (`GetConsoleMode` on a `DEVNULL`-redirected
stdin handle returns failure, while `sys.stdin.isatty()` on the very same
handle returns `True`)."""

from __future__ import annotations

import sys

__all__ = ["is_interactive_stdin"]


# frob:tests \
# tests/unit/test_process_tty.py::TestWin32StdinHasConsole.test_never_raises_when_ctype\
# s_windll_is_unavailable
def _win32_stdin_has_console() -> bool:
    """win32-only: whether the current process's stdin handle is genuinely
    attached to a console, via `GetConsoleMode` -- `False` for `NUL`, a
    pipe, or a redirected file, none of which `sys.stdin.isatty()` alone
    can tell apart from a real console on this platform (see module
    docstring). Never raises: any failure to even ask the question (no
    `ctypes.windll`, a missing/invalid handle) is treated as "not a
    console", the fail-safe direction for a TTY-gated fast-fail."""
    try:
        import ctypes

        std_input_handle = -10  # STD_INPUT_HANDLE, per the Win32 API
        # `ctypes.windll` is a win32-only stdlib member -- typeshed only
        # declares it under a win32 platform guard, so `getattr` sidesteps
        # static attribute resolution instead of chasing a suppression
        # comment that cannot be correct on every checked platform at
        # once (same rationale as `_guard.py`'s own win32 console-ctrl
        # scope, T-3657).
        kernel32 = getattr(ctypes, "windll").kernel32  # noqa: B009
        handle = kernel32.GetStdHandle(std_input_handle)
        mode = ctypes.c_uint32()
        return bool(kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
    except (AttributeError, OSError, ValueError):
        return False


# frob:tests \
# tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_non_tty_stdin_is_never_in\
# teractive
# frob:tests \
# tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_posix_tty_stdin_is_intera\
# ctive
# frob:tests \
# tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_win32_tty_isatty_but_no_c\
# onsole_is_not_interactive
# frob:tests \
# tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_win32_tty_isatty_and_real\
# _console_is_interactive
# frob:doc docs/modules/process.md#cross-platform-interactive-stdin-check-t-4255
def is_interactive_stdin() -> bool:
    """Whether stdin is a real interactive terminal a human could type
    into -- the single home for this check (T-4255) so `NUL`'s Windows
    CRT `isatty()` quirk (module docstring) is fixed once, not re-derived
    (and re-broken) at every call site. `sys.stdin.isatty()` is the whole
    answer on every POSIX platform; on win32 it is necessary but not
    sufficient, so it's followed by `GetConsoleMode` to rule out `NUL`
    and other non-console character devices doing the same on windows-
    latest CI (proven regression: T-4255's `frob ticket attach` TTY
    fast-fail test)."""
    if not sys.stdin.isatty():
        return False
    if sys.platform == "win32":
        return _win32_stdin_has_console()
    return True
