"""T-3675 (win32 round 18, Part 1): unit coverage for `tests/conftest.py`'s
session-teardown hard-exit escape hatch -- gated on `FROB_TEST_HARD_EXIT`,
env-gated OFF by default everywhere except the CI workflow's windows Test
step (see that step's own comment in `.github/workflows/ci.yml` and the
rationale in `docs/modules/process.md`). Round-17 evidence (T-3673, run
33556847222) showed the injected SIGINT this ticket family has chased was
MASKING a real session-teardown wedge -- this hatch documents what wedges
teardown (a one-line thread/child inventory) and hard-exits past it with
the session's own real exit code, the same `os._exit` pattern T-3608's
`_announce_stall_and_abort` already uses in this file.

Does NOT exercise a real `os._exit` call (that would kill the test
runner) -- `_maybe_hard_exit_after_session_finish` is tested via a
monkeypatched `os._exit` that records its argument instead of calling the
real one, mirroring how `test_process_guard.py`'s fake-ctypes tests avoid
touching a real win32 API.
"""

from __future__ import annotations

import threading

import pytest

from tests.unit._conftest_test_helpers import load_conftest_module


def _load_conftest():
    """Fresh standalone import of `tests/conftest.py` per test, same
    posture as `test_conftest_console_ctrl_guard.py`'s loader -- each
    test's monkeypatches and any module-level state never leak between
    call sites."""
    return load_conftest_module("_t3675_conftest_under_test")


class _FakeSession:
    """Minimal stand-in for `pytest.Session` -- only `.exitstatus` is
    read by `_maybe_hard_exit_after_session_finish`."""

    def __init__(self, exitstatus: object) -> None:
        """Store the given exitstatus verbatim (including a
        deliberately-wrong-typed value, for the fallback test)."""
        self.exitstatus = exitstatus


class TestHardExitRequested:
    """`_hard_exit_requested` -- the same-shaped gate as the T-3673
    console-ctrl guard's own `_test_console_ctrl_ignore_requested`, but
    with NO platform restriction (T-3675: a teardown wedge is not a
    win32-specific hazard, only win32 CI is what surfaced it)."""

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested.test_false_when_env_unset  # noqa: E501
    def test_false_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.delenv(module.FROB_TEST_HARD_EXIT_ENV, raising=False)
        assert module._hard_exit_requested() is False

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested.test_false_on_falsy_value  # noqa: E501
    def test_false_on_falsy_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_HARD_EXIT_ENV, "0")
        assert module._hard_exit_requested() is False

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested.test_true_on_truthy_value  # noqa: E501
    def test_true_on_truthy_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_HARD_EXIT_ENV, "1")
        assert module._hard_exit_requested() is True

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested.test_no_platform_restriction  # noqa: E501
    def test_no_platform_restriction(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unlike FROB_TEST_IGNORE_CONSOLE_CTRL/FROB_WIN32_IGNORE_CONSOLE_
        CTRL, this gate must NOT check sys.platform -- a teardown wedge
        is not win32-specific."""
        module = _load_conftest()
        monkeypatch.setattr(module.sys, "platform", "linux")
        monkeypatch.setenv(module.FROB_TEST_HARD_EXIT_ENV, "1")
        assert module._hard_exit_requested() is True


class TestDescribeTeardownBlockers:
    """`_describe_teardown_blockers` -- the one-line thread/child
    inventory printed right before the hard exit."""

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers.test_line_has_the_expected_marker_and_sections  # noqa: E501
    def test_line_has_the_expected_marker_and_sections(self) -> None:
        module = _load_conftest()
        line = module._describe_teardown_blockers()
        assert line.startswith("FROB-TEST-HARD-EXIT: threads=[")
        assert "children=[" in line

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers.test_includes_the_current_thread_with_its_daemon_flag  # noqa: E501
    def test_includes_the_current_thread_with_its_daemon_flag(self) -> None:
        module = _load_conftest()
        current = threading.current_thread()
        line = module._describe_teardown_blockers()
        assert f"{current.name!r}(daemon={current.daemon})" in line

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers.test_lists_an_extra_non_daemon_thread_by_name  # noqa: E501
    def test_lists_an_extra_non_daemon_thread_by_name(self) -> None:
        module = _load_conftest()
        stop = threading.Event()
        extra = threading.Thread(
            target=stop.wait, name="t3675-probe-thread", daemon=False
        )
        extra.start()
        try:
            line = module._describe_teardown_blockers()
            assert "'t3675-probe-thread'(daemon=False)" in line
        finally:
            stop.set()
            extra.join(timeout=5)

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers.test_empty_children_list_when_none_active  # noqa: E501
    def test_empty_children_list_when_none_active(self) -> None:
        module = _load_conftest()
        line = module._describe_teardown_blockers()
        assert "children=[]" in line


class TestMaybeHardExitAfterSessionFinish:
    """`_maybe_hard_exit_after_session_finish` -- the tail `pytest_
    sessionfinish` calls; a no-op unless requested, otherwise flushes
    and hard-exits with the session's real exit status. `os._exit` is
    monkeypatched to record its argument (never called for real)."""

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestMaybeHardExitAfterSessionFinish.test_no_op_when_not_requested  # noqa: E501
    def test_no_op_when_not_requested(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.delenv(module.FROB_TEST_HARD_EXIT_ENV, raising=False)
        calls: list[int] = []
        monkeypatch.setattr(module.os, "_exit", calls.append)
        module._maybe_hard_exit_after_session_finish(_FakeSession(0), 0)
        assert calls == []

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestMaybeHardExitAfterSessionFinish.test_hard_exits_with_the_sessions_real_exitstatus  # noqa: E501
    def test_hard_exits_with_the_sessions_real_exitstatus(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_HARD_EXIT_ENV, "1")
        calls: list[int] = []
        monkeypatch.setattr(module.os, "_exit", calls.append)
        module._maybe_hard_exit_after_session_finish(_FakeSession(1), 0)
        assert calls == [1]
        assert "FROB-TEST-HARD-EXIT:" in capsys.readouterr().out

    # frob:tests tests/unit/test_conftest_hard_exit_guard.py::TestMaybeHardExitAfterSessionFinish.test_falls_back_to_the_hook_exitstatus_when_session_exitstatus_is_not_an_int  # noqa: E501
    def test_falls_back_to_the_hook_exitstatus_when_session_exitstatus_is_not_an_int(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_HARD_EXIT_ENV, "1")
        calls: list[int] = []
        monkeypatch.setattr(module.os, "_exit", calls.append)
        module._maybe_hard_exit_after_session_finish(_FakeSession(None), 5)
        assert calls == [5]
