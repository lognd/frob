"""Tests for `frob.serve._leases` (T-1097): the daemon-owned named
resource lease/semaphore primitive -- pure `ResourceLeaseManager` unit
tests, plus real-socket tests for the `frob_lease_acquire`/`frob_lease_
release` RPC layer and connection-crash auto-release.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import pytest

from frob.serve._leases import ResourceLeaseManager
from frob.serve._socketd import socket_path

# DUP001: reuse tests/test_app_daemon_proxy.py's own `_start_daemon` rather
# than duplicating it -- identical shape (spawn run_socket_daemon in a
# background thread, poll for the socket file).
from tests.test_app_daemon_proxy import _start_daemon


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A bare project root with `.frob/` already present."""
    (tmp_path / ".frob").mkdir()
    return tmp_path


class TestResourceLeaseManager:
    def test_second_acquire_blocks_until_first_releases(self) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestResourceLeaseManager.test_second_acquire_blocks_until_first_releases
        mgr = ResourceLeaseManager()
        assert mgr.acquire("coverage", "a", timeout_s=1.0) is True

        second_acquired: list[bool] = []

        def _second() -> None:
            second_acquired.append(mgr.acquire("coverage", "b", timeout_s=5.0))

        thread = threading.Thread(target=_second)
        thread.start()
        time.sleep(0.1)
        # "b" must still be blocked -- "a" holds the only slot.
        assert second_acquired == []
        assert mgr.release("coverage", "a") is True
        thread.join(timeout=5)
        assert second_acquired == [True]

    def test_acquire_times_out_if_never_freed(self) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestResourceLeaseManager.test_acquire_times_out_if_never_freed
        mgr = ResourceLeaseManager()
        assert mgr.acquire("coverage", "a", timeout_s=1.0) is True
        start = time.monotonic()
        got = mgr.acquire("coverage", "b", timeout_s=0.2)
        elapsed = time.monotonic() - start
        assert got is False
        assert elapsed < 2.0

    def test_release_holder_frees_every_resource_that_holder_held(self) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestResourceLeaseManager.test_release_holder_frees_every_resource_that_holder_held
        mgr = ResourceLeaseManager()
        assert mgr.acquire("coverage", "a", timeout_s=1.0) is True
        assert mgr.acquire("collection", "a", timeout_s=1.0) is True
        freed = mgr.release_holder("a")
        assert sorted(freed) == ["collection", "coverage"]
        # Both slots are free again for a new holder.
        assert mgr.acquire("coverage", "b", timeout_s=1.0) is True
        assert mgr.acquire("collection", "b", timeout_s=1.0) is True

    def test_distinct_resources_do_not_contend(self) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestResourceLeaseManager.test_distinct_resources_do_not_contend
        mgr = ResourceLeaseManager()
        assert mgr.acquire("coverage", "a", timeout_s=1.0) is True
        # A different resource name is a completely separate slot pool --
        # "b" must not block on "a" holding "coverage".
        assert mgr.acquire("collection", "b", timeout_s=1.0) is True

    def test_reentrant_acquire_by_same_holder_does_not_deadlock(self) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestResourceLeaseManager.test_reentrant_acquire_by_same_holder_does_not_deadlock
        mgr = ResourceLeaseManager()
        assert mgr.acquire("coverage", "a", timeout_s=1.0) is True
        assert mgr.acquire("coverage", "a", timeout_s=1.0) is True
        # Releasing once fully frees it (re-entrant acquire never
        # incremented the held count a second time).
        assert mgr.release("coverage", "a") is True
        assert mgr.acquire("coverage", "b", timeout_s=1.0) is True

    def test_release_of_unheld_resource_is_a_noop(self) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestResourceLeaseManager.test_release_of_unheld_resource_is_a_noop
        mgr = ResourceLeaseManager()
        assert mgr.release("coverage", "nobody") is False


class _RawClient:
    """A persistent raw JSON-RPC connection to the daemon (unlike
    `send_request`, which opens-sends-recvs-closes per call) -- needed
    here because a lease must be acquired and released (or NOT released,
    to simulate a crash) across multiple request lines on the SAME
    connection, which is exactly the property a lease-per-connection
    primitive is meant to test."""

    def __init__(self, root: Path) -> None:
        """Connect once; every `call()` reuses the same socket."""
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.settimeout(10.0)
        self._sock.connect(str(socket_path(root)))
        self._buf = b""

    def call(self, method: str, params: dict | None = None) -> dict:
        """Send one JSON-RPC request line and read one response line back."""
        self._sock.sendall(
            (
                json.dumps({"id": 1, "method": method, "params": params or {}}) + "\n"
            ).encode("utf-8")
        )
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                break
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        return json.loads(line.decode("utf-8"))

    def close(self) -> None:
        """Close the connection WITHOUT sending any release -- this is
        exactly what a crashed/killed client looks like from the daemon's
        side."""
        self._sock.close()


def _shutdown(root: Path, thread: threading.Thread) -> None:
    """Ask the daemon to stop and wait for its thread to exit."""
    try:
        client = _RawClient(root)
        client.call("frob_shutdown")
        client.close()
    except OSError:
        pass
    thread.join(timeout=5)


class TestLeaseRpc:
    """T-1097 acceptance [0]: real socket clients serialize on a lease."""

    def test_second_client_blocks_until_first_releases(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestLeaseRpc.test_second_client_blocks_until_first_releases
        thread = _start_daemon(root)
        try:
            first = _RawClient(root)
            second = _RawClient(root)

            resp1 = first.call("frob_lease_acquire", {"resource": "coverage"})
            assert resp1["result"]["acquired"] is True

            second_result: list[dict] = []

            def _second_acquire() -> None:
                second_result.append(
                    second.call(
                        "frob_lease_acquire",
                        {"resource": "coverage", "timeout_s": 5.0},
                    )
                )

            t = threading.Thread(target=_second_acquire)
            t.start()
            time.sleep(0.2)
            # Second connection must still be blocked -- exactly one
            # writer at a time, no two concurrent holders.
            assert second_result == []

            release_resp = first.call("frob_lease_release", {"resource": "coverage"})
            assert release_resp["result"]["released"] is True

            t.join(timeout=5)
            assert second_result == [{"id": 1, "result": {"acquired": True}}]

            first.close()
            second.close()
        finally:
            _shutdown(root, thread)

    def test_explicit_release_frees_the_slot_for_the_next_waiter(
        self, root: Path
    ) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestLeaseRpc.test_explicit_release_frees_the_slot_for_the_next_waiter
        thread = _start_daemon(root)
        try:
            client = _RawClient(root)
            resp = client.call("frob_lease_acquire", {"resource": "coverage"})
            assert resp["result"]["acquired"] is True
            resp = client.call("frob_lease_release", {"resource": "coverage"})
            assert resp["result"]["released"] is True
            # A fresh client can now acquire immediately, no blocking.
            other = _RawClient(root)
            resp = other.call(
                "frob_lease_acquire", {"resource": "coverage", "timeout_s": 1.0}
            )
            assert resp["result"]["acquired"] is True
            client.close()
            other.close()
        finally:
            _shutdown(root, thread)


class TestConnectionCrashReleasesLease:
    """T-1097 acceptance [1]: a crashed/disconnected client's lease is
    released automatically, with no daemon restart needed."""

    def test_closing_connection_without_explicit_release_frees_the_lease(
        self, root: Path
    ) -> None:
        # frob:tests \
        # tests/test_serve_leases.py::TestConnectionCrashReleasesLease.test_closing_connection_without_explicit_release_frees_the_lease
        thread = _start_daemon(root)
        try:
            first = _RawClient(root)
            resp = first.call("frob_lease_acquire", {"resource": "coverage"})
            assert resp["result"]["acquired"] is True

            # Simulate a crash: close the raw socket with NO
            # frob_lease_release sent first.
            first.close()

            # Give the daemon's connection-handling thread a moment to
            # notice EOF and run handle()'s finally block.
            deadline = time.monotonic() + 5
            second = _RawClient(root)
            acquired = False
            while time.monotonic() < deadline:
                resp = second.call(
                    "frob_lease_acquire", {"resource": "coverage", "timeout_s": 0.2}
                )
                if resp["result"]["acquired"]:
                    acquired = True
                    break
            assert acquired, (
                "a crashed connection's lease must be released without an "
                "explicit frob_lease_release or a daemon restart"
            )
            second.close()
        finally:
            _shutdown(root, thread)
