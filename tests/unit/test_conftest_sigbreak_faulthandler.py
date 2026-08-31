"""T-3565: unit coverage for `tests/conftest.py`'s
`_install_sigbreak_faulthandler` (T-3560's TEMPORARY windows-latest
diagnostics) -- specifically the crash `faulthandler.register` not
existing on win32 caused (run 33370059331, `INTERNALERROR AttributeError:
module 'faulthandler' has no attribute 'register'` at `pytest_configure`
time, before a single test ran). Deliberately NOT gated by a win32-only
module skip (unlike `test_conftest_stackdump.py`'s `SIGUSR1` coverage) --
the whole point is to catch a Windows-only crash from a Linux/macOS CI
run, by faking the win32-shaped environment via monkeypatch rather than
requiring an actual Windows host."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.unit._conftest_test_helpers import load_conftest_module


def _load_conftest():
    """Fresh `tests/conftest.py` module instance -- see
    `_conftest_test_helpers.load_conftest_module`'s own docstring for why
    a standalone import (not pytest's own already-loaded conftest) is
    needed here."""
    return load_conftest_module("_t3565_conftest_under_test")


class TestSigbreakFaultHandlerCrossPlatformSafety:
    """`_install_sigbreak_faulthandler` must never raise, regardless of
    whether `faulthandler.register` exists on the host it runs on."""

    def test_succeeds_when_faulthandler_register_is_absent_on_simulated_win32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3565's own regression: simulate exactly the shape that
        crashed `pytest_configure` on real Windows -- `sys.platform ==
        "win32"`, `signal.SIGBREAK` present (as it genuinely is on real
        Windows), but `faulthandler.register` ABSENT (as it genuinely is
        on every win32 CPython build) -- and assert the function returns
        cleanly instead of raising `AttributeError`."""
        # frob:tests \
        # tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCr\
        # ossPlatformSafety.test_succeeds_when_faulthandler_register_is_absent_on_simul\
        # ated_win32
        conftest = _load_conftest()
        monkeypatch.setattr(conftest.sys, "platform", "win32")
        monkeypatch.setattr(conftest.signal, "SIGBREAK", 21, raising=False)
        monkeypatch.delattr(conftest.faulthandler, "register", raising=False)

        conftest._install_sigbreak_faulthandler()  # must not raise

    def test_installs_a_signal_handler_when_register_is_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The fallback path genuinely installs a `signal.signal` handler
        for `SIGBREAK` (not merely a silent no-op) when `faulthandler.
        register` is unavailable."""
        # frob:tests \
        # tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCr\
        # ossPlatformSafety.test_installs_a_signal_handler_when_register_is_absent
        conftest = _load_conftest()
        monkeypatch.setattr(conftest.sys, "platform", "win32")
        monkeypatch.setattr(conftest.signal, "SIGBREAK", 21, raising=False)
        monkeypatch.delattr(conftest.faulthandler, "register", raising=False)

        installed: list[tuple[int, object]] = []
        monkeypatch.setattr(
            conftest.signal,
            "signal",
            lambda sig, handler: installed.append((sig, handler)),
        )

        conftest._install_sigbreak_faulthandler()

        assert len(installed) == 1
        sig, handler = installed[0]
        assert sig == 21
        assert callable(handler)

    def test_dump_then_chain_calls_dump_traceback_then_previous_handler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The installed handler dumps every thread's stack THEN chains
        to whatever handler was previously registered -- the interrupt
        is still delivered exactly as it would have been without this
        diagnostic (T-3560's own "observation-only" contract)."""
        # frob:tests \
        # tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCr\
        # ossPlatformSafety.test_dump_then_chain_calls_dump_traceback_then_previous_han\
        # dler
        conftest = _load_conftest()
        monkeypatch.setattr(conftest.sys, "platform", "win32")
        monkeypatch.setattr(conftest.signal, "SIGBREAK", 21, raising=False)
        monkeypatch.delattr(conftest.faulthandler, "register", raising=False)

        calls: list[str] = []
        monkeypatch.setattr(
            conftest.faulthandler,
            "dump_traceback",
            lambda all_threads=False: calls.append("dump"),
        )
        previous_calls: list[tuple[int, object]] = []

        def _previous(signum: int, frame: object) -> None:
            previous_calls.append((signum, frame))

        monkeypatch.setattr(conftest.signal, "getsignal", lambda sig: _previous)
        installed: list[Callable[[int, object], None]] = []
        monkeypatch.setattr(
            conftest.signal,
            "signal",
            lambda sig, handler: installed.append(handler),
        )

        conftest._install_sigbreak_faulthandler()
        assert len(installed) == 1
        handler = installed[0]

        handler(21, None)
        assert calls == ["dump"]
        assert previous_calls == [(21, None)]

    def test_still_prefers_faulthandler_register_when_it_exists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When `faulthandler.register` IS available (never true on real
        win32 today, but this keeps the general-case path exercised and
        correct for any future platform where both `SIGBREAK`-like
        delivery and `faulthandler.register` coexist), it is used
        directly rather than the `signal.signal` fallback."""
        # frob:tests \
        # tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCr\
        # ossPlatformSafety.test_still_prefers_faulthandler_register_when_it_exists
        conftest = _load_conftest()
        monkeypatch.setattr(conftest.sys, "platform", "win32")
        monkeypatch.setattr(conftest.signal, "SIGBREAK", 21, raising=False)
        registered: list[object] = []
        monkeypatch.setattr(
            conftest.faulthandler,
            "register",
            lambda sig, all_threads=False: registered.append((sig, all_threads)),
            raising=False,
        )
        monkeypatch.setattr(
            conftest.signal,
            "signal",
            lambda sig, handler: (_ for _ in ()).throw(
                AssertionError("signal.signal must not be called on the register path")
            ),
        )

        conftest._install_sigbreak_faulthandler()

        assert registered == [(21, True)]

    def test_noop_off_win32(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unchanged off win32: `sys.platform != "win32"` still short-
        circuits before touching `signal`/`faulthandler` at all."""
        # frob:tests \
        # tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCr\
        # ossPlatformSafety.test_noop_off_win32
        conftest = _load_conftest()
        monkeypatch.setattr(conftest.sys, "platform", "linux")
        monkeypatch.setattr(conftest.signal, "SIGBREAK", 21, raising=False)
        monkeypatch.setattr(
            conftest.signal,
            "signal",
            lambda sig, handler: (_ for _ in ()).throw(
                AssertionError("signal.signal must not be called off win32")
            ),
        )

        conftest._install_sigbreak_faulthandler()  # must not raise, must not call

    def test_noop_when_no_sigbreak_attribute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unchanged when `signal.SIGBREAK` itself is absent (every real
        POSIX host) -- the existing guard this ticket did not touch."""
        # frob:tests \
        # tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCr\
        # ossPlatformSafety.test_noop_when_no_sigbreak_attribute
        conftest = _load_conftest()
        monkeypatch.setattr(conftest.sys, "platform", "win32")
        monkeypatch.delattr(conftest.signal, "SIGBREAK", raising=False)

        conftest._install_sigbreak_faulthandler()  # must not raise
