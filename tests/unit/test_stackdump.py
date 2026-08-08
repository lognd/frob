"""T-1466: unit coverage for `frob.testing._stackdump` -- the SIGUSR1
stack-dump handler extracted out of `tests/conftest.py` (T-1433) so it is
reachable from ANY frob process, not just pytest's own test-session
lifecycle (closing the WIRE001 finding both helpers used to carry, since
`tests/conftest.py` is itself a test-path the gate's text scan skips)."""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

import pytest

if sys.platform == "win32":  # pragma: no cover - POSIX-only feature
    pytest.skip("SIGUSR1 is POSIX-only", allow_module_level=True)

from frob.testing._stackdump import (
    STACKDUMP_ENV,
    dump_all_thread_stacks,
    install_stackdump_handler,
)


class TestStackdumpHandler:
    """`install_stackdump_handler`/`dump_all_thread_stacks`, independent of
    any pytest-specific wiring."""

    # frob:tests tests/unit/test_stackdump.py::TestStackdumpHandler.test_sigusr1_writes_all_thread_stacks_when_enabled  # noqa: E501
    def test_sigusr1_writes_all_thread_stacks_when_enabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With `FROB_COVERAGE_STACKDUMP=1` set, installing the handler and
        then raising `SIGUSR1` in-process writes a `.frob/stackdumps/
        pid-<pid>.txt` file containing a recognizable stack-dump marker --
        the same artifact any frob process (not just a pytest worker)
        produces once it opts in."""
        monkeypatch.setenv(STACKDUMP_ENV, "1")
        monkeypatch.chdir(tmp_path)
        previous = signal.getsignal(signal.SIGUSR1)
        try:
            install_stackdump_handler()
            os.kill(os.getpid(), signal.SIGUSR1)
            dump_path = tmp_path / ".frob" / "stackdumps" / f"pid-{os.getpid()}.txt"
            assert dump_path.is_file(), list((tmp_path / ".frob").rglob("*"))
            content = dump_path.read_text(encoding="utf-8")
            assert "SIGUSR1 stack dump" in content
            assert str(os.getpid()) in content
        finally:
            signal.signal(signal.SIGUSR1, previous)

    # frob:tests tests/unit/test_stackdump.py::TestStackdumpHandler.test_handler_not_installed_when_env_unset  # noqa: E501
    def test_handler_not_installed_when_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without `FROB_COVERAGE_STACKDUMP` set, installing must be a
        no-op -- the default handler (whatever it was before) stays in
        place, so an unrelated `SIGUSR1` sender is not silently
        intercepted by a debug-only feature, on ANY caller."""
        monkeypatch.delenv(STACKDUMP_ENV, raising=False)
        previous = signal.getsignal(signal.SIGUSR1)
        try:
            install_stackdump_handler()
            assert signal.getsignal(signal.SIGUSR1) is previous
        finally:
            signal.signal(signal.SIGUSR1, previous)

    # frob:tests tests/unit/test_stackdump.py::TestStackdumpHandler.test_reachable_via_frob_testing_public_surface  # noqa: E501
    def test_reachable_via_frob_testing_public_surface(self) -> None:
        """T-1466's own motivation: `install_stackdump_handler` must be
        importable from `frob.testing`'s public surface, not just its
        private submodule -- the structural fix for WIRE001 flagging this
        as reachable only from `tests/conftest.py`'s own tests."""
        import frob.testing as testing_pkg

        assert testing_pkg.install_stackdump_handler is install_stackdump_handler
        assert testing_pkg.dump_all_thread_stacks is dump_all_thread_stacks
        assert testing_pkg.STACKDUMP_ENV == STACKDUMP_ENV
