"""Tests for `frob.serve._events` (T-1096): the subscribe/push event
stream layered over the T-1092 socket daemon.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from frob.serve._events import DaemonError, _EventBus, subscribe_and_wait
from frob.serve._socketd import SocketDaemonConfig, run_socket_daemon, send_request

# DUP001: reuse test_serve.py's own fixtures rather than duplicating them.
from tests.test_serve import _git_init, _write

_SAMPLE_PY = (
    '"""Module docstring."""\n\n\n'
    "def helper(x):\n"
    "    # frob:doc docs/x.md#helper\n"
    "    return x\n"
)


class TestEventBus:
    def test_publish_reaches_all_subscribers(self) -> None:
        # frob:tests \
        # tests/test_serve_events.py::TestEventBus.test_publish_reaches_all_subscribers
        bus = _EventBus()
        _, q1 = bus.subscribe()
        _, q2 = bus.subscribe()
        bus.publish("graph-changed", {"root": "x"})
        assert q1.get(timeout=2) == {"event": "graph-changed", "data": {"root": "x"}}
        assert q2.get(timeout=2) == {"event": "graph-changed", "data": {"root": "x"}}

    def test_publish_before_any_subscriber_is_a_noop(self) -> None:
        # frob:tests \
        # tests/test_serve_events.py::TestEventBus.test_publish_before_any_subscriber_i\
        # s_a_noop
        bus = _EventBus()
        bus.publish("graph-changed")  # must not raise
        sid, q = bus.subscribe()
        assert q.empty()
        bus.unsubscribe(sid)

    def test_unsubscribe_wakes_blocked_consumer(self) -> None:
        # frob:tests \
        # tests/test_serve_events.py::TestEventBus.test_unsubscribe_wakes_blocked_consu\
        # mer
        bus = _EventBus()
        sid, q = bus.subscribe()

        results: list = []

        def _consumer() -> None:
            results.append(q.get(timeout=5))

        t = threading.Thread(target=_consumer)
        t.start()
        bus.unsubscribe(sid)
        t.join(timeout=5)
        assert not t.is_alive()
        assert results == [None]


def _start_daemon(root: Path, idle_timeout_s: float = 5.0) -> threading.Thread:
    """Start `run_socket_daemon` on a background thread and block until it
    actually answers a request -- not just until the socket FILE exists
    (which can race ahead of `serve_forever()` actually accepting
    connections under CPU contention), mirroring
    `tests/test_serve_socket.py::TestRunSocketDaemon.
    test_stale_socket_file_is_replaced`'s own readiness-poll shape."""
    cfg = SocketDaemonConfig(root=root, idle_timeout_s=idle_timeout_s)
    thread = threading.Thread(target=lambda: run_socket_daemon(cfg), daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        response = send_request(root, "frob_doable_tickets", timeout_s=0.5)
        if response.is_ok:
            return thread
        time.sleep(0.1)
    raise AssertionError("daemon never became reachable")


class TestSubscribeAndWait:
    def test_receives_graph_changed_after_edit(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_events.py::TestSubscribeAndWait.test_receives_graph_changed_\
        # after_edit
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        thread = _start_daemon(tmp_path, idle_timeout_s=10.0)

        results: list = []

        def _wait() -> None:
            results.append(subscribe_and_wait(tmp_path, "graph-changed", timeout_s=8.0))

        waiter = threading.Thread(target=_wait)
        waiter.start()
        time.sleep(0.3)
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY + "\n# edited\n")
        waiter.join(timeout=10)
        assert not waiter.is_alive()
        assert len(results) == 1
        assert results[0].is_ok
        thread.join(timeout=15)

    def test_times_out_with_no_matching_event(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_events.py::TestSubscribeAndWait.test_times_out_with_no_match\
        # ing_event
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        thread = _start_daemon(tmp_path, idle_timeout_s=10.0)

        # A generous timeout (contended CI/parallel-worker CPU can delay
        # thread scheduling well past a tight bound) -- this test's point
        # is that no matching event ever arrives, not how fast that is
        # detected.
        result = subscribe_and_wait(tmp_path, "coverage-fresh", timeout_s=5.0)
        assert result.is_err
        assert result.danger_err == DaemonError.Timeout
        thread.join(timeout=15)

    def test_no_daemon_is_unreachable(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_events.py::TestSubscribeAndWait.test_no_daemon_is_unreachable
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        result = subscribe_and_wait(tmp_path, "graph-changed", timeout_s=1.0)
        assert result.is_err
        assert result.danger_err == DaemonError.Unreachable

    def test_receives_coverage_fresh_on_stamp_write(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_serve_events.py::TestSubscribeAndWait.test_receives_coverage_fresh\
        # _on_stamp_write
        _write(tmp_path, "src/pkg/a.py", _SAMPLE_PY)
        _git_init(tmp_path)
        thread = _start_daemon(tmp_path, idle_timeout_s=10.0)

        results: list = []

        def _wait() -> None:
            results.append(
                subscribe_and_wait(tmp_path, "coverage-fresh", timeout_s=8.0)
            )

        waiter = threading.Thread(target=_wait)
        waiter.start()
        time.sleep(0.3)
        stamp_path = tmp_path / ".frob" / "coverage-stamp"
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text('{"ok": true}')
        waiter.join(timeout=10)
        assert not waiter.is_alive()
        assert len(results) == 1
        assert results[0].is_ok
        thread.join(timeout=15)
