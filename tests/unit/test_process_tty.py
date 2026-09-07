"""T-4255: `frob.process._tty.is_interactive_stdin` -- the single
cross-platform "is stdin a real terminal" check that replaced the bare
`sys.stdin.isatty()` calls in `frob ticket attach`'s TTY fast-fail and
`frob ticket new`'s clipboard-image offer. See the module's own docstring
for the measured win32 defect (`sys.stdin.isatty()` returns `True` for
`NUL`) this exists to fix."""

from __future__ import annotations

import sys

import pytest

from frob.process._tty import _win32_stdin_has_console, is_interactive_stdin


# frob:ticket T-4255
class TestIsInteractiveStdin:
    def test_non_tty_stdin_is_never_interactive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_non_tty_stdin_is_\
        # never_interactive
        """`sys.stdin.isatty() == False` short-circuits to `False` on every
        platform -- the win32-only `GetConsoleMode` follow-up check never
        even needs to run when this primitive already says no."""
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        assert is_interactive_stdin() is False

    def test_posix_tty_stdin_is_interactive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_posix_tty_stdin_i\
        # s_interactive
        """Off win32, `sys.stdin.isatty() == True` is the whole answer --
        no `GetConsoleMode` follow-up is attempted (there is nothing to
        call it on)."""
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        assert is_interactive_stdin() is True

    def test_win32_tty_isatty_but_no_console_is_not_interactive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_win32_tty_isatty_\
        # but_no_console_is_not_interactive
        """The exact regression this module fixes (T-4255, measured on
        real Windows via `winrun`): `isatty() == True` (Windows CRT's
        NUL-is-a-character-device quirk) but `GetConsoleMode` says there
        is no real console attached -- must resolve to `False`, not
        `True`."""
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr(
            "frob.process._tty._win32_stdin_has_console", lambda: False
        )
        assert is_interactive_stdin() is False

    def test_win32_tty_isatty_and_real_console_is_interactive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_process_tty.py::TestIsInteractiveStdin.test_win32_tty_isatty_\
        # and_real_console_is_interactive
        """A genuine win32 console (both `isatty()` and `GetConsoleMode`
        agree) is interactive."""
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr(
            "frob.process._tty._win32_stdin_has_console", lambda: True
        )
        assert is_interactive_stdin() is True


# frob:ticket T-4255
class TestWin32StdinHasConsole:
    def test_never_raises_when_ctypes_windll_is_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_process_tty.py::TestWin32StdinHasConsole.test_never_raises_wh\
        # en_ctypes_windll_is_unavailable
        """Off win32 (or any environment where `ctypes.windll` doesn't
        exist), `_win32_stdin_has_console` degrades to `False` -- the
        fail-safe direction for a TTY-gated fast-fail -- rather than
        raising `AttributeError` out of a plain interactive-check call."""
        assert _win32_stdin_has_console() is False
