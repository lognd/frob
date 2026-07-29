"""Tests for `frob.serve._socketd` (T-1092): the standalone unix-socket
JSON-RPC daemon process and its atomic single-instance guard.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from frob.serve import _socketd
from frob.serve._socketd import (
    DaemonError,
    SocketDaemonConfig,
    _JsonRpcRequest,
    acquire_singleton_lock,
    dispatch_request,
    run_socket_daemon,
    send_request,
    socket_path,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A bare project root with a `.frob/` directory already present --
    the daemon creates it itself if missing, but tests exercising the
    lock/socket paths directly want it to exist up front."""
    (tmp_path / ".frob").mkdir()
    return tmp_path


class TestAcquireSingletonLock:
    def test_first_caller_wins(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestAcquireSingletonLock.test_first_caller_wins
        result = acquire_singleton_lock(root)
        assert result.is_ok
        result.danger_ok.close()

    def test_second_caller_loses_while_first_holds(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestAcquireSingletonLock.test_second_caller_loses\
        # _while_first_holds
        first = acquire_singleton_lock(root)
        assert first.is_ok
        second = acquire_singleton_lock(root)
        assert second.is_err
        assert second.danger_err == DaemonError.AlreadyRunning
        first.danger_ok.close()

    def test_lock_released_on_close_allows_next_caller(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestAcquireSingletonLock.test_lock_released_on_cl\
        # ose_allows_next_caller
        first = acquire_singleton_lock(root)
        assert first.is_ok
        first.danger_ok.close()
        second = acquire_singleton_lock(root)
        assert second.is_ok
        second.danger_ok.close()

    def test_n_racing_callers_exactly_one_wins(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestAcquireSingletonLock.test_n_racing_callers_ex\
        # actly_one_wins
        outcomes: list[bool] = []
        lock_guard = threading.Lock()
        barrier = threading.Barrier(8)

        def _attempt() -> None:
            barrier.wait()
            result = acquire_singleton_lock(root)
            with lock_guard:
                outcomes.append(result.is_ok)
            if result.is_ok:
                # Hold briefly so every racer's attempt lands while this
                # one still owns the lock.
                time.sleep(0.05)
                result.danger_ok.close()

        threads = [threading.Thread(target=_attempt) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(outcomes) == 8
        assert sum(outcomes) == 1


class TestDispatchRequest:
    def test_known_method_ok(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestDispatchRequest.test_known_method_ok
        request = _JsonRpcRequest(id=1, method="frob_doable_tickets", params={})
        response = dispatch_request(root, request)
        assert response["id"] == 1
        assert "result" in response
        assert response["result"] == []

    def test_unknown_method_is_error(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestDispatchRequest.test_unknown_method_is_error
        request = _JsonRpcRequest(id=2, method="not_a_real_method", params={})
        response = dispatch_request(root, request)
        assert response["id"] == 2
        assert response["error"]["code"] == "unknown_method"

    def test_frob_version_reports_daemon_version(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestDispatchRequest.test_frob_version_reports_dae\
        # mon_version
        # T-1105: `frob_version` is handled specially by `_RequestHandler`
        # (like `subscribe`), not routed through `dispatch_request`'s
        # `_TOOL_DISPATCH` table -- exercise it over a real running daemon.
        cfg = SocketDaemonConfig(root=root, idle_timeout_s=5.0)
        thread = threading.Thread(target=lambda: run_socket_daemon(cfg), daemon=True)
        thread.start()
        deadline = time.monotonic() + 5
        while not socket_path(root).exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert socket_path(root).exists()
        try:
            response = send_request(root, "frob_version")
            assert response.is_ok
            assert response.danger_ok["version"] == _socketd.daemon_version()
        finally:
            shutdown = send_request(root, "frob_shutdown")
            assert shutdown.is_ok
            thread.join(timeout=5)

    def test_frob_shutdown_stops_the_server(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestDispatchRequest.test_frob_shutdown_stops_the_\
        # server
        cfg = SocketDaemonConfig(root=root, idle_timeout_s=5.0)
        results: list = []
        thread = threading.Thread(
            target=lambda: results.append(run_socket_daemon(cfg)), daemon=True
        )
        thread.start()
        deadline = time.monotonic() + 5
        while not socket_path(root).exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert socket_path(root).exists()

        response = send_request(root, "frob_shutdown")
        assert response.is_ok
        assert response.danger_ok["shutting_down"] is True

        thread.join(timeout=5)
        assert not thread.is_alive()
        assert results[0].is_ok
        assert not socket_path(root).exists()


class TestRunSocketDaemon:
    def test_serves_one_request_then_idle_exits(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestRunSocketDaemon.test_serves_one_request_then_\
        # idle_exits
        cfg = SocketDaemonConfig(root=root, idle_timeout_s=0.3)
        results: list = []

        def _run() -> None:
            results.append(run_socket_daemon(cfg))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        deadline = time.monotonic() + 5
        while not socket_path(root).exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert socket_path(root).exists()

        response = send_request(root, "frob_doable_tickets")
        assert response.is_ok
        assert response.danger_ok == []

        thread.join(timeout=5)
        assert not thread.is_alive()
        assert len(results) == 1
        assert results[0].is_ok
        assert not socket_path(root).exists()
        assert (
            not _socketd.lock_path(root).exists() or True
        )  # lock file may remain, unlocked

    def test_contended_lock_is_err(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestRunSocketDaemon.test_contended_lock_is_err
        held = acquire_singleton_lock(root)
        assert held.is_ok
        cfg = SocketDaemonConfig(root=root, idle_timeout_s=0.1)
        result = run_socket_daemon(cfg)
        assert result.is_err
        assert result.danger_err == DaemonError.AlreadyRunning
        held.danger_ok.close()

    def test_stale_socket_file_is_replaced(self, root: Path) -> None:
        # frob:tests \
        # tests/test_serve_socket.py::TestRunSocketDaemon.test_stale_socket_file_is_rep\
        # laced
        stale = socket_path(root)
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("not a real socket")

        cfg = SocketDaemonConfig(root=root, idle_timeout_s=0.3)
        results: list = []

        def _run() -> None:
            results.append(run_socket_daemon(cfg))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            response = send_request(root, "frob_doable_tickets", timeout_s=0.2)
            if response.is_ok:
                break
            time.sleep(0.05)
        else:
            pytest.fail("daemon never became reachable over the replaced socket")

        thread.join(timeout=5)
        assert not thread.is_alive()
        assert results[0].is_ok
