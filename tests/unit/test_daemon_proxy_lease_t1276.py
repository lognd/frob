"""Direct-call coverage for `frob.app._daemon_proxy`'s lease surface and
liveness branches (T-1276).

`_LeaseConnection.call`/`.close`, `try_daemon_lease`, and
`release_daemon_lease` are only exercised today indirectly, through
`frob.testing._coverage_wait.run_coverage_wait`'s own daemon-lease path
(`tests/test_coverage_wait_shared.py`), which never asserts the
connection object's own methods or the lease-unreachable/disabled Err
paths directly -- hence their 0.0%-branch TEST005 findings despite the
module being exercised end to end elsewhere. These tests call
`try_daemon_lease`/`release_daemon_lease`/`_LeaseConnection` directly
against a real `run_socket_daemon` (mirroring
`tests/test_app_daemon_proxy.py`'s own `_start_daemon`/`_shutdown`
pattern -- a real daemon, not a mock, is the only thing that proves the
RPC round trip), plus `ensure_daemon`'s `Wedged`/`Orphaned` liveness
branches, which the existing `TestEnsureDaemon` class covers for
`NoSocket`/`Live`/`VersionSkew` but not these two.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from frob.app import _daemon_proxy
from frob.app._daemon_proxy import (
    ProxyReason,
    _LeaseConnection,
    ensure_daemon,
    release_daemon_lease,
    try_daemon_lease,
)
from frob.serve import SocketDaemonConfig, run_socket_daemon
from frob.serve._socketd import lock_path, socket_path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A bare project root with `.frob/` already present."""
    (tmp_path / ".frob").mkdir()
    return tmp_path


def _start_daemon(root: Path, idle_timeout_s: float = 5.0) -> threading.Thread:
    """Start a real `run_socket_daemon` in a background thread and block
    until its socket file exists -- mirrors `tests/test_app_daemon_proxy.
    py`'s own helper of the same name."""
    cfg = SocketDaemonConfig(root=root, idle_timeout_s=idle_timeout_s)
    thread = threading.Thread(target=lambda: run_socket_daemon(cfg), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not socket_path(root).exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert socket_path(root).exists()
    return thread


def _shutdown(root: Path, thread: threading.Thread) -> None:
    """Force the idle-timeout daemon down promptly rather than waiting out
    its full `idle_timeout_s` at teardown."""
    deadline = time.monotonic() + 5
    while (
        lock_path(root).exists() and time.monotonic() < deadline and thread.is_alive()
    ):
        time.sleep(0.05)
        if not socket_path(root).exists():
            break
    thread.join(timeout=1)


class TestDaemonLease:
    """T-1097/T-1126: `try_daemon_lease`/`release_daemon_lease`/
    `_LeaseConnection` -- the persistent-connection lease surface a real
    daemon must actually answer over the wire."""

    @pytest.fixture(autouse=True)
    def _opt_in(self, monkeypatch):
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease._opt_in
        monkeypatch.setenv("FROB_DAEMON", "1")

    def test_round_trip_acquire_call_release_close(
        self, root: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_round_trip_\
        # acquire_call_release_close
        thread = _start_daemon(root)
        try:
            acquired = try_daemon_lease(root, "t1276-resource", capacity=1)
            assert acquired.is_ok
            conn = acquired.danger_ok
            assert isinstance(conn, _LeaseConnection)

            # A second connection trying the same, now-exhausted (capacity=1)
            # resource must be told the lease is unavailable -- proves
            # `_LeaseConnection.call` really round-trips over the live
            # socket and that acquisition actually took effect server-side.
            second = try_daemon_lease(root, "t1276-resource", capacity=1, timeout_s=0.2)
            assert second.is_err
            assert second.danger_err is ProxyReason.Unreachable

            release_daemon_lease(conn, "t1276-resource")

            # Released -- capacity is free again for a fresh connection.
            third = try_daemon_lease(root, "t1276-resource", capacity=1)
            assert third.is_ok
            release_daemon_lease(third.danger_ok, "t1276-resource")
        finally:
            _shutdown(root, thread)

    def test_disabled_env_bypasses_lease(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_disabled_en\
        # v_bypasses_lease
        monkeypatch.setenv("FROB_NO_DAEMON", "1")
        result = try_daemon_lease(root, "t1276-resource")
        assert result.is_err
        assert result.danger_err is ProxyReason.Disabled

    def test_no_daemon_falls_back_unreachable(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_no_daemon_f\
        # alls_back_unreachable
        # Nothing is listening and spawning is disabled (nonexistent
        # interpreter path, same trick `test_no_daemon_no_socket_falls_back`
        # in tests/test_app_daemon_proxy.py uses) -- `_LeaseConnection.
        # __init__`'s own `connect()` must raise and be turned into
        # `Err(Unreachable)`, never propagate a raw `OSError`.
        monkeypatch.setattr(_daemon_proxy.sys, "executable", "/nonexistent/python")
        result = try_daemon_lease(root, "t1276-resource")
        assert result.is_err
        assert result.danger_err is ProxyReason.Unreachable


class TestEnsureDaemonLivenessBranches:
    """`ensure_daemon`'s `Wedged`/`Orphaned` liveness branches -- the
    existing `TestEnsureDaemon` class in tests/test_app_daemon_proxy.py
    covers `NoSocket`/`Live`/`VersionSkew` but not these two."""

    def test_wedged_does_not_spawn_a_rival(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py.TestEnsureDaemonLivenessBranches.\
        # test_wedged_does_not_spawn_a_rival
        monkeypatch.setattr(
            _daemon_proxy,
            "probe_daemon",
            lambda r, **k: (_daemon_proxy.DaemonLiveness.Wedged, None),
        )
        spawned = []
        monkeypatch.setattr(_daemon_proxy, "_spawn_daemon", lambda r: spawned.append(r))
        ensure_daemon(root)
        assert spawned == [], (
            "a Wedged daemon is already holding the socket -- spawning a "
            "rival is exactly wrong (acquire_singleton_lock would just "
            "refuse it), so ensure_daemon must bypass for this run instead"
        )

    def test_orphaned_clears_socket_then_spawns(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py.TestEnsureDaemonLivenessBranches.\
        # test_orphaned_clears_socket_then_spawns
        monkeypatch.setattr(
            _daemon_proxy,
            "probe_daemon",
            lambda r, **k: (_daemon_proxy.DaemonLiveness.Orphaned, None),
        )
        cleared = []
        spawned = []
        monkeypatch.setattr(
            _daemon_proxy, "_clear_orphaned_socket", lambda r: cleared.append(r)
        )
        monkeypatch.setattr(_daemon_proxy, "_spawn_daemon", lambda r: spawned.append(r))
        ensure_daemon(root)
        assert cleared == [root]
        assert spawned == [root]
