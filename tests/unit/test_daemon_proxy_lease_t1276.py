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

import sys
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
from frob.serve._socketd import lock_path, send_request, socket_path

# T-3699: bounded join/shutdown budget for the real-daemon fixture below --
# named the same way T-1635/T-4356's own `_JOIN_BUDGET_S` is, so a daemon
# that is merely slow (not dead) under xdist CI contention gets the same
# load-slack `send_request`'s own timeout_s is given, instead of the two
# budgets silently disagreeing the way T-4356's root-cause hypothesis
# documented for the Linux-side shutdown-reap flake.
_JOIN_BUDGET_S = 5.0


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A bare project root with `.frob/` already present."""
    (tmp_path / ".frob").mkdir()
    return tmp_path


def _start_daemon(root: Path, idle_timeout_s: float = 5.0) -> threading.Thread:
    """Start a real `run_socket_daemon` in a background thread and block
    until its socket file exists -- mirrors `tests/test_app_daemon_proxy.
    py`'s own helper of the same name. Bounded by `_JOIN_BUDGET_S` (T-3699)
    rather than a bare literal, so the startup wait and the teardown wait
    below share one deliberately-chosen load-tolerance budget."""
    cfg = SocketDaemonConfig(root=root, idle_timeout_s=idle_timeout_s)
    thread = threading.Thread(target=lambda: run_socket_daemon(cfg), daemon=True)
    thread.start()
    deadline = time.monotonic() + _JOIN_BUDGET_S
    while not socket_path(root).exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert socket_path(root).exists(), (
        f"daemon socket for {root} did not appear within "
        f"{_JOIN_BUDGET_S}s -- server thread never reached listen()"
    )
    return thread


def _shutdown(root: Path, thread: threading.Thread) -> None:
    """T-3699: explicit, bounded daemon teardown -- send the real
    `frob_shutdown` RPC (same call T-4356 aligned to its own
    `_JOIN_BUDGET_S` on the Linux side) instead of only passively polling
    for `lock_path`/`socket_path` to disappear on their own. A daemon that
    never receives an explicit shutdown can keep its background thread
    (and its bound AF_UNIX socket) alive past this test's return, leaking
    into whatever test runs next on the same xdist worker -- exactly the
    kind of cross-test interference that can destabilize a worker rather
    than fail cleanly. `thread.join()`'s result is asserted, not just
    called, so a leak becomes a loud assertion failure here instead of a
    silent, later crash somewhere else."""
    if socket_path(root).exists():
        # Best-effort: a daemon that is merely slow (not dead) gets the
        # same explicit wait `send_request` already grants everywhere
        # else; failure here is harmless -- the idle-timeout poll below
        # is the real backstop.
        send_request(root, "frob_shutdown", timeout_s=_JOIN_BUDGET_S)
    deadline = time.monotonic() + _JOIN_BUDGET_S
    while (
        lock_path(root).exists() and time.monotonic() < deadline and thread.is_alive()
    ):
        time.sleep(0.05)
        if not socket_path(root).exists():
            break
    thread.join(timeout=_JOIN_BUDGET_S)
    assert not thread.is_alive(), (
        f"daemon thread for {root} did not exit within "
        f"{2 * _JOIN_BUDGET_S:.0f}s of frob_shutdown -- it would otherwise "
        "leak a live AF_UNIX socket into whatever test runs next on this "
        "worker"
    )


# frob:ticket T-1636
class TestDaemonLease:
    """T-1097/T-1126: `try_daemon_lease`/`release_daemon_lease`/
    `_LeaseConnection` -- the persistent-connection lease surface a real
    daemon must actually answer over the wire."""

    # frob:ticket T-1636
    @pytest.fixture(autouse=True)
    def _opt_in(self, monkeypatch):
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease._opt_in \
        # kind="integration"
        # T-1636: an autouse pytest fixture is reached via pytest's own
        # fixture-injection machinery for every test in this class, never a literal
        # call token a static call-graph can see -- same rationale as
        # test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths._opt_in.
        monkeypatch.setenv("FROB_DAEMON", "1")

    # frob:tests src/frob/app/_daemon_proxy.py::release_daemon_lease kind="unit"  # noqa: E501
    # frob:tests src/frob/app/_daemon_proxy.py::try_daemon_lease kind="unit"  # noqa: E501
    # frob:tests src/frob/app/_daemon_proxy.py::_LeaseConnection.close kind="unit"  # noqa: E501
    # frob:tests src/frob/app/_daemon_proxy.py::_LeaseConnection.call kind="unit"  # noqa: E501
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason=(
            "T-2961: the daemon's unix-socket transport (socketserver."
            "ThreadingUnixStreamServer) has no Windows equivalent -- "
            "run_socket_daemon refuses loudly rather than crashing, so this "
            "test's real-daemon assertions cannot hold on win32. See the "
            "Windows-native-daemon-transport epic filed alongside T-2961 "
            "for the tracked follow-up."
        ),
    )
    # reason: real socket daemon thread with a 0.2s Unreachable-timeout
    # expectation; nondeterministic under CI scheduler load, seen flaking
    # earlier.
    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_round_trip_acquire_call_release_close(
        self, root: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_round_trip_acquire_call_release_close  # noqa: E501
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

    # frob:tests src/frob/app/_daemon_proxy.py::try_daemon_lease kind="unit"  # noqa: E501
    def test_disabled_env_bypasses_lease(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_disabled_env_bypasses_lease  # noqa: E501
        monkeypatch.setenv("FROB_NO_DAEMON", "1")
        result = try_daemon_lease(root, "t1276-resource")
        assert result.is_err
        assert result.danger_err is ProxyReason.Disabled

    # frob:tests src/frob/app/_daemon_proxy.py::try_daemon_lease kind="unit"  # noqa: E501
    def test_no_daemon_falls_back_unreachable(self, root: Path, monkeypatch) -> None:
        # frob:waive BUG002 reason="win32-only skip; POSIX-primitive dependency not \
        # reproducible from a Linux parent-commit repro"
        if sys.platform == "win32":
            pytest.skip(
                "POSIX-only (T-3766): try_daemon_lease() returns "
                "Err(ProxyReason.PlatformUnsupported) before ever "
                "reaching the AF_UNIX connect on win32"
            )
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_no_daemon_falls_back_unreachable  # noqa: E501
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

    # frob:tests src/frob/app/_daemon_proxy.py::ensure_daemon kind="unit"  # noqa: E501
    def test_wedged_does_not_spawn_a_rival(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py.TestEnsureDaemonLivenessBranches.test_wedged_does_not_spawn_a_rival  # noqa: E501
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

    # frob:tests src/frob/app/_daemon_proxy.py::ensure_daemon kind="unit"  # noqa: E501
    def test_orphaned_clears_socket_then_spawns(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_lease_t1276.py.TestEnsureDaemonLivenessBranches.test_orphaned_clears_socket_then_spawns  # noqa: E501
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
