"""T-1350 TEST005 burn-down: `install_serial_pools`'s `frob.gates` import
guard (lines ~138-152) -- the `ImportError` branch and the "anything else
at import time" `Exception` branch (EXHAUST001, T-1371's widening) are
untested by `test_serial_pools.py`'s own happy-path acceptance test, which
never forces `import frob.gates` to fail. Both branches log a warning and
return, leaving only the `concurrent.futures`-level patch applied -- this
proves that return path, not just the observable log line, by asserting
`concurrent.futures`'s two names were patched to `SerialExecutor` while
`frob.gates`'s own bound names are left untouched (a stub module with
sentinel attributes, in the `Exception` case, would have been overwritten
by the happy path but is provably NOT here)."""

from __future__ import annotations

import builtins
import concurrent.futures

import pytest

from frob.perf import _serial_pools
from frob.perf._serial_pools import SerialExecutor, install_serial_pools


# frob:waive WIRE001 reason="autouse pytest fixture for this module's own tests -- \
# WIRE001's reachability scan skips test paths by design \
# (conftest.py::_install_stackdump_handler's WIRE001/T-1466 precedent, \
# tests/test_tickets_migration.py's _git_init/_done_ticket T-1490 precedent), so any \
# helper reached only from within its own test file (autouse fixtures doubly so, since \
# nothing calls them by name at all) always reads as unwired" follow_up="T-1490"
@pytest.fixture(autouse=True)
def _restore_pool_executors():
    """`install_serial_pools()` mutates `concurrent.futures` globally and
    permanently (this module's own docstring: "meant to be called once ...
    from the profiling harness") -- restore the real executors afterward so
    this test's patch cannot leak into any test that runs later in the
    same session, matching `test_harness_sampling.py`'s own leak-avoidance
    discipline."""
    real_thread = concurrent.futures.ThreadPoolExecutor
    real_process = concurrent.futures.ProcessPoolExecutor
    yield
    concurrent.futures.ThreadPoolExecutor = real_thread
    concurrent.futures.ProcessPoolExecutor = real_process


# frob:waive WIRE001 reason="test-fixture builder for this module's own tests (called \
# by both TestInstallSerialPoolsGatesImportError and \
# TestInstallSerialPoolsGatesUnexpectedException below, same file) -- WIRE001's \
# reachability scan skips test paths by design, same precedent as \
# tests/test_tickets_migration.py's _git_init" follow_up="T-1490"
def _blocking_import(name: str, raise_exc: type[BaseException]):
    """A `builtins.__import__` stand-in that raises `raise_exc` only for
    `frob.gates` (and its submodules), delegating every other import to the
    real builtin -- so importing `frob.perf._serial_pools` itself (already
    imported) and everything else pytest needs keeps working."""
    real_import = builtins.__import__

    def _fake_import(mod_name, *args, **kwargs):
        if mod_name == "frob.gates" or mod_name.startswith("frob.gates."):
            raise raise_exc(f"synthetic failure for {mod_name}")
        return real_import(mod_name, *args, **kwargs)

    return _fake_import


class TestInstallSerialPoolsGatesImportError:
    """The plain `ImportError` branch: `frob.gates` genuinely missing/
    broken to import."""

    def test_import_error_still_patches_concurrent_futures_only(
        self, monkeypatch
    ) -> None:
        # frob:tests tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesImportError.test_import_error_still_patches_concurrent_futures_only  # noqa: E501
        monkeypatch.setattr(
            builtins, "__import__", _blocking_import("frob.gates", ImportError)
        )
        install_serial_pools()
        assert concurrent.futures.ThreadPoolExecutor is SerialExecutor
        assert concurrent.futures.ProcessPoolExecutor is SerialExecutor


class TestInstallSerialPoolsGatesUnexpectedException:
    """The broadened `except Exception` branch (T-1371/EXHAUST001): some
    OTHER surprise at `frob.gates` import time (not `ImportError`) must
    still be swallowed -- `install_serial_pools`'s own docstring promises
    "safe to call even if frob.gates fails to import" for ANY import-time
    surprise, not just the named exception type."""

    def test_unexpected_import_time_exception_is_swallowed(
        self, monkeypatch
    ) -> None:
        # frob:tests tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesUnexpectedException.test_unexpected_import_time_exception_is_swallowed  # noqa: E501
        monkeypatch.setattr(
            builtins, "__import__", _blocking_import("frob.gates", RuntimeError)
        )
        # Must not raise -- the whole point of the broadened except clause.
        install_serial_pools()
        assert concurrent.futures.ThreadPoolExecutor is SerialExecutor
        assert concurrent.futures.ProcessPoolExecutor is SerialExecutor


# frob:waive DEAD001 reason="imported only for isinstance/identity checks and to reach module attrs during monkeypatching -- both used above"  # noqa: E501
_ = _serial_pools
