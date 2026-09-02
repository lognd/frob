"""T-3673 (win32 round 17): unit coverage for `tests/conftest.py`'s
session-lifetime win32 console-ctrl-ignore guard -- gated on
`FROB_TEST_IGNORE_CONSOLE_CTRL`, env-gated OFF by default everywhere
except the CI workflow's windows Test step (see that step's own
comment in `.github/workflows/ci.yml` and the rationale in
`docs/modules/process.md`). Mirrors the fake-ctypes pattern
`tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope`
already uses for the check-pipeline mitigation this one is modeled on
(T-3657), since real `ctypes.windll` doesn't exist off win32.
"""

from __future__ import annotations

import sys
from typing import Callable, cast

import pytest

from tests.unit._conftest_test_helpers import load_conftest_module


def _load_conftest():
    """Fresh standalone import of `tests/conftest.py` per test (not
    pytest's own already-loaded plugin instance) so each test's
    monkeypatches and module-level `_test_console_ctrl_handler_holder`
    state never leak between call sites."""
    return load_conftest_module("_t3673_conftest_under_test")


class _FakeKernel32:
    """Records every `SetConsoleCtrlHandler(handler, enable)` call."""

    def __init__(self) -> None:
        """Start with an empty call log."""
        self.calls: list[tuple[object, bool]] = []

    def SetConsoleCtrlHandler(self, handler: object, enable: bool) -> None:  # noqa: N802
        """Log the call instead of touching any real win32 API."""
        self.calls.append((handler, enable))


class _FakeWindll:
    """Stand-in for `ctypes.windll` exposing only `.kernel32`."""

    def __init__(self, kernel32: _FakeKernel32) -> None:
        """Wrap the given fake kernel32 instance."""
        self.kernel32 = kernel32


class _FakeCtypes:
    """Stand-in for the `ctypes` module referenced inside `tests/
    conftest.py`'s guard functions -- same shape as `test_process_guard.
    py`'s `_FakeCtypes`, duplicated here (not imported) because the two
    live in different subsystems (suite guard vs. check-pipeline guard)
    with no shared home to extract a third copy into without widening
    this ticket's scope beyond `tests/conftest.py`."""

    def __init__(self) -> None:
        """Build a fresh fake kernel32/windll pair for this instance."""
        self.kernel32 = _FakeKernel32()
        self.windll = _FakeWindll(self.kernel32)

    def WINFUNCTYPE(self, *_args: object, **_kwargs: object):  # noqa: N802
        """Identity factory: the fake kernel32 never crosses the real
        ctypes FFI boundary, so wrapping just returns the callable."""
        return lambda fn: fn

    c_bool = bool
    c_ulong = int


class TestTestConsoleCtrlIgnoreRequested:
    """`_test_console_ctrl_ignore_requested` -- the same-shaped gate as
    `src/frob/process/_guard.py::_win32_ignore_console_ctrl_requested`,
    checked once, fresh, before any win32 API is touched."""

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested.test_false_on_non_win32_even_when_env_set  # noqa: E501
    def test_false_on_non_win32_even_when_env_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "linux")
        monkeypatch.setenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "1")
        assert module._test_console_ctrl_ignore_requested() is False

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested.test_false_on_win32_when_env_unset  # noqa: E501
    def test_false_on_win32_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "win32")
        monkeypatch.delenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, raising=False)
        assert module._test_console_ctrl_ignore_requested() is False

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested.test_false_on_falsy_value  # noqa: E501
    def test_false_on_falsy_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "win32")
        monkeypatch.setenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "0")
        assert module._test_console_ctrl_ignore_requested() is False

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested.test_true_on_win32_when_truthy  # noqa: E501
    def test_true_on_win32_when_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "win32")
        monkeypatch.setenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "1")
        assert module._test_console_ctrl_ignore_requested() is True


class TestInstallAndUninstallTestConsoleCtrlIgnoreGuard:
    """`_install_test_console_ctrl_ignore_guard`/`_uninstall_test_
    console_ctrl_ignore_guard` -- the pair `pytest_configure`/`pytest_
    unconfigure` call, install/remove exactly one handler when
    requested and are a no-op otherwise."""

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard.test_no_op_when_not_requested  # noqa: E501
    def test_no_op_when_not_requested(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "linux")
        monkeypatch.setenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "1")
        fake_ctypes = _FakeCtypes()
        monkeypatch.setattr(module, "ctypes", fake_ctypes)
        module._install_test_console_ctrl_ignore_guard()
        assert fake_ctypes.kernel32.calls == []
        assert module._test_console_ctrl_handler_holder == []
        module._uninstall_test_console_ctrl_ignore_guard()
        assert fake_ctypes.kernel32.calls == []

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard.test_installs_and_removes_exactly_one_handler  # noqa: E501
    def test_installs_and_removes_exactly_one_handler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "win32")
        monkeypatch.setenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "1")
        fake_ctypes = _FakeCtypes()
        monkeypatch.setattr(module, "ctypes", fake_ctypes)

        module._install_test_console_ctrl_ignore_guard()
        assert len(module._test_console_ctrl_handler_holder) == 1
        assert fake_ctypes.kernel32.calls == [(fake_ctypes.kernel32.calls[0][0], True)]

        module._uninstall_test_console_ctrl_ignore_guard()
        assert module._test_console_ctrl_handler_holder == []
        assert fake_ctypes.kernel32.calls == [
            (fake_ctypes.kernel32.calls[0][0], True),
            (fake_ctypes.kernel32.calls[0][0], False),
        ]

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard.test_handler_swallows_ctrl_c_and_ctrl_break_only  # noqa: E501
    def test_handler_swallows_ctrl_c_and_ctrl_break_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "win32")
        monkeypatch.setenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "1")
        fake_ctypes = _FakeCtypes()
        monkeypatch.setattr(module, "ctypes", fake_ctypes)

        module._install_test_console_ctrl_ignore_guard()
        handler = cast("Callable[[int], bool]", fake_ctypes.kernel32.calls[0][0])
        assert handler(0) is True  # CTRL_C_EVENT
        assert handler(1) is True  # CTRL_BREAK_EVENT
        assert handler(2) is False  # CTRL_CLOSE_EVENT -- must fall through
        module._uninstall_test_console_ctrl_ignore_guard()

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard.test_uninstall_without_install_is_a_no_op  # noqa: E501
    def test_uninstall_without_install_is_a_no_op(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _load_conftest()
        assert module._test_console_ctrl_handler_holder == []
        module._uninstall_test_console_ctrl_ignore_guard()
        assert module._test_console_ctrl_handler_holder == []


class TestRealPlatformNeverRequestsGuardByDefault:
    """Sanity check against the ACTUAL running platform/env, not a
    monkeypatched one -- catches an accidental default-on regression
    that only the mocked tests above would never see."""

    # frob:tests tests/unit/test_conftest_console_ctrl_guard.py::TestRealPlatformNeverRequestsGuardByDefault.test_unset_in_this_repos_own_default_env  # noqa: E501
    def test_unset_in_this_repos_own_default_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _load_conftest()
        monkeypatch.delenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, raising=False)
        assert module._test_console_ctrl_ignore_requested() is False
        if sys.platform != "win32":
            # Doubly true off win32: the platform check alone suffices
            # even if some ambient env var were set.
            monkeypatch.setenv(module.FROB_TEST_IGNORE_CONSOLE_CTRL_ENV, "1")
            assert module._test_console_ctrl_ignore_requested() is False
