"""Standalone unix-socket JSON-RPC daemon process (T-1092,
docs/modules/serve.md#socket-daemon-t-1092).

`frob serve` (`server.py`) only exists as a background thread inside a
LIVE MCP stdio client session -- there is no way to reach `frob.serve._tools`
from outside an MCP client, and every one-off caller (a CLI invocation, a
non-MCP editor integration) pays a full cold graph rebuild for every single
query. This module stands up a SECOND frontend over the exact same core: a
standalone OS process, reachable via a per-project-root unix domain socket
(`.frob/daemon.sock`), speaking a minimal newline-delimited JSON-RPC-shaped
protocol that dispatches straight into `frob.serve._tools`'s existing
`Result`-returning functions -- the identical warm-state-backed query logic
`server.py`'s MCP tools already call (T-0177's `frob.serve._warm`). Two
frontends, one core: this module adds NO parallel implementation of any
query, only a second transport.

Three pieces:

1. **Single-instance guard** (`acquire_singleton_lock`) -- an `flock(LOCK_EX
   | LOCK_NB)` held on `.frob/daemon.lock` for the daemon process's entire
   lifetime. `flock` is atomic at the kernel level: of any number of
   processes racing to acquire it over the same file, exactly one succeeds
   and every other call returns immediately with `EWOULDBLOCK` -- there is
   no window where two callers can both believe they hold it. A losing
   racer is not a failure state to surface loudly; it means someone else is
   already becoming (or already is) the daemon for this root, so it simply
   does not spawn a second one.
2. **JSON-RPC protocol** (`_JsonRpcRequest`/`_JsonRpcResponse`, `_TOOL_
   DISPATCH`, `dispatch_request`) -- one JSON object per line, `{"id":
   ..., "method": "frob_doable_tickets", "params": {...}}` in, `{"id":
   ..., "result": ...}` or `{"id": ..., "error": {"code": ..., "message":
   ...}}` out. `_TOOL_DISPATCH` maps each exposed method name directly to
   the matching `frob.serve._tools` function -- the same table `server.py`
   builds via `@server.tool()` decorators, just keyed by name instead of
   registered on a `FastMCP` instance.
3. **Idle-timeout server loop** (`SocketDaemonConfig`, `run_socket_daemon`)
   -- a `socketserver.ThreadingUnixStreamServer` that exits cleanly (socket
   file removed, lock released) once `idle_timeout_s` has elapsed since the
   last request, so a daemon nobody is using does not linger as an orphaned
   process forever.
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down disposition: this file's \
# exclusivity-vocabulary hits ('only', 'no parallel implementation') are source-level \
# design-rationale/scope-cut prose (describing already-implemented internal behavior, \
# verifiable by reading the code it annotates -- e.g. 'a second transport, not a \
# second query implementation') rather than a separate cross-module contract needing \
# its own tracked invariant; same calibration-batch disposition this repo already \
# applies to src/frob/serve/_daemon.py and src/frob/serve/_warm.py (T-0585)"

from __future__ import annotations

import errno
import fcntl
import json
import os
import queue
import socket
import socketserver
import threading
import time
from pathlib import Path
from typing import IO, Any, Callable

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.serve import _tools
from frob.serve._leases import DEFAULT_LEASE_CAPACITY, ResourceLeaseManager
from frob.serve._watch import WatchThread

_log = get_logger(__name__)

# frob:doc docs/modules/serve.md#socket-daemon-t-1092
DEFAULT_IDLE_TIMEOUT_S = 600.0
# How often the idle-monitor thread wakes up to check elapsed idle time --
# deliberately much smaller than DEFAULT_IDLE_TIMEOUT_S so the actual exit
# happens within one poll tick of the deadline, not up to a whole timeout
# late.
_IDLE_POLL_INTERVAL_S = 5.0

_LOCK_REL = Path(".frob") / "daemon.lock"
_SOCKET_REL = Path(".frob") / "daemon.sock"


# frob:doc docs/modules/serve.md#version-handshake-t-1105
def daemon_version() -> str:
    """This process's installed `frob` version, or 'unknown' from a raw
    source checkout with no registered distribution -- the daemon's own
    self-reported version for the `frob_version` RPC (T-1105). Duplicated
    (rather than imported) from `frob.app._daemon_proxy._client_version`'s
    identical shape: `frob.app` is a sibling-layer package this module must
    not import (`frob.serve` sits below `frob.app` in the dependency
    order), same disposition `_client_version`'s own docstring already
    notes for `frob.__main__._frob_version`."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("frob")
    except PackageNotFoundError:
        return "unknown"
    except Exception as exc:  # noqa: BLE001 -- best-effort version probe, never fatal
        _log.debug("serve: socketd: version lookup failed: %s", exc)
        return "unknown"


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
class DaemonError(ErrorSet):
    """Failure values `frob.serve._socketd`'s process-level operations can
    return."""

    AlreadyRunning = "another process already holds the single-instance lock"
    BindFailed = "the daemon unix socket could not be bound"
    UnknownMethod = "requested JSON-RPC method is not exposed by the daemon"
    MalformedRequest = "request line was not valid JSON-RPC-shaped JSON"
    RemoteError = "the daemon returned a JSON-RPC error response"
    Unreachable = "the daemon socket could not be connected to"
    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    Timeout = "no matching event arrived within the requested timeout"


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
class SocketDaemonConfig(BaseModel):
    """Process-entry configuration for `run_socket_daemon` -- the
    App/AppConfig-pattern config object for the standalone daemon process,
    all fields defaulted so a bare `SocketDaemonConfig(root=...)` is always
    valid."""

    model_config = {}

    root: Path
    idle_timeout_s: float = DEFAULT_IDLE_TIMEOUT_S


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
def lock_path(root: Path) -> Path:
    """The per-project-root single-instance lock file: `<root>/.frob/daemon.lock`."""
    return root / _LOCK_REL


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
# frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_serves_one_request_then_idle_exits kind="unit"  # noqa: E501
def socket_path(root: Path) -> Path:
    """The per-project-root unix domain socket: `<root>/.frob/daemon.sock`."""
    return root / _SOCKET_REL


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
# frob:tests tests/test_serve_socket.py::TestAcquireSingletonLock.test_first_caller_wins kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestAcquireSingletonLock.test_second_caller_loses_while_first_holds kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestAcquireSingletonLock.test_lock_released_on_close_allows_next_caller kind="unit"  # noqa: E501
def acquire_singleton_lock(root: Path) -> Result[IO[Any], DaemonError]:
    """Atomically acquire the per-`root` single-instance guard: an
    `flock(LOCK_EX | LOCK_NB)` on `lock_path(root)`, creating the file (and
    its parent `.frob/` directory) if needed. `flock` contention is
    resolved by the kernel, not by any check-then-act sequence this process
    performs itself -- of any number of processes calling this
    concurrently over the same `root`, exactly one receives `Ok` and every
    other one receives `Err(DaemonError.AlreadyRunning)` immediately, never
    both. The returned file object must be kept open (not garbage
    collected, not closed) for as long as this process wants to remain the
    singleton daemon -- closing it (or process exit) releases the lock."""
    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        if exc.errno not in (errno.EACCES, errno.EAGAIN):
            _log.error("serve: socketd: lock acquire failed unexpectedly: %s", exc)
            raise
        handle.close()
        _log.info("serve: socketd: lock contended at %s, another daemon owns it", path)
        return Err(DaemonError.AlreadyRunning)
    _log.info("serve: socketd: lock acquired at %s (pid=%d)", path, os.getpid())
    return Ok(handle)


def _release_singleton_lock(handle: IO[Any]) -> None:
    """Release a lock `acquire_singleton_lock` returned: unlock then close
    the handle -- the mirror operation, always called on daemon shutdown."""
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()
    _log.info("serve: socketd: lock released (pid=%d)", os.getpid())


# The dispatch table both the JSON-RPC handler and tests use: every entry
# is the SAME `frob.serve._tools` function `server.py`'s MCP registration
# calls -- no parallel query implementation, only a second name -> callable
# mapping over the identical core. Documented via `dispatch_request`'s own
# doc anchor (its one real caller) rather than a private anchor here, per
# COV007's "anchor the public caller, not the private helper" convention.
_TOOL_DISPATCH: dict[str, Callable[..., Result[Any, _tools.ServeError]]] = {
    "frob_doable_tickets": _tools.frob_doable_tickets,
    "frob_stale_docs": _tools.frob_stale_docs,
    "frob_check_scope": _tools.frob_check_scope,
    "frob_graph_query": _tools.frob_graph_query,
    "frob_doc_for": _tools.frob_doc_for,
    "frob_affects": _tools.frob_affects,
    "frob_check_delta": _tools.frob_check_delta,
    "frob_run_touched_tests": _tools.frob_run_touched_tests,
    "frob_perf_hot": _tools.frob_perf_hot,
    "frob_daemon_status": _tools.frob_daemon_status,
    "frob_exports": _tools.frob_exports,
    "frob_stats": _tools.frob_stats,
}


class _JsonRpcRequest(BaseModel):
    """One decoded request line: an opaque `id` echoed back verbatim in the
    response, the `frob.serve._tools` function name to call, and its
    keyword arguments."""

    model_config = {}

    id: int | str | None = None
    method: str
    params: dict[str, Any] = {}


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
# frob:tests tests/test_serve_socket.py::TestDispatchRequest.test_known_method_ok kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestDispatchRequest.test_unknown_method_is_error kind="unit"  # noqa: E501
def dispatch_request(root: Path, request: _JsonRpcRequest) -> dict[str, Any]:
    """Look `request.method` up in `_TOOL_DISPATCH` and call it with `root`
    plus `request.params` as keyword arguments, returning a JSON-RPC-shaped
    response dict (`{"id", "result"}` or `{"id", "error"}`) -- never
    raises: an unknown method, a bad-params `TypeError`, or a tool-level
    `Err` all become a JSON-RPC error object instead of an exception
    escaping to the connection handler."""
    fn = _TOOL_DISPATCH.get(request.method)
    if fn is None:
        _log.warning("serve: socketd: unknown method %r", request.method)
        return {
            "id": request.id,
            "error": {"code": "unknown_method", "message": request.method},
        }
    try:
        result = fn(root, **request.params)
    except TypeError as exc:
        _log.warning("serve: socketd: bad params for %s: %s", request.method, exc)
        return {
            "id": request.id,
            "error": {"code": "bad_params", "message": str(exc)},
        }
    if result.is_err:
        _log.info("serve: socketd: %s -> error: %s", request.method, result.danger_err)
        return {
            "id": request.id,
            "error": {
                "code": "tool_error",
                "message": str(result.danger_err.value),
            },
        }
    _log.info("serve: socketd: %s -> ok", request.method)
    return {"id": request.id, "result": result.danger_ok}


class _IdleTracker:
    """Tracks the monotonic timestamp of the last dispatched request, under
    a lock (the connection-handling threads and the idle-monitor thread
    both touch it concurrently)."""

    def __init__(self) -> None:
        """Start the clock at construction time -- an idle daemon that
        never receives a single request still ages normally from launch."""
        self._lock = threading.Lock()
        self._last_activity = time.monotonic()

    # frob:doc docs/modules/serve.md#idle-timeout
    def touch(self) -> None:
        """Record that a request was just handled -- resets the idle clock."""
        with self._lock:
            self._last_activity = time.monotonic()

    # frob:doc docs/modules/serve.md#idle-timeout
    # frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_serves_one_request_then_idle_exits kind="unit"  # noqa: E501
    def idle_for_s(self) -> float:
        """Seconds elapsed since the last `touch()` (or construction, if
        `touch()` was never called)."""
        with self._lock:
            return time.monotonic() - self._last_activity


class _RequestHandler(socketserver.StreamRequestHandler):
    """One unix-socket connection: read newline-delimited JSON-RPC request
    lines until the client closes, dispatching each through `dispatch_
    request` and writing back one JSON response line per request. A
    `subscribe` request (T-1096) additionally starts a per-connection
    writer thread that pumps push event frames from the server's
    `event_bus` onto this same connection for as long as it stays open."""

    server: _DaemonServer

    # T-1096: guards self.wfile between the main handle() loop's own
    # response writes and _pump_events' async event writes on the same
    # connection -- two threads can otherwise interleave partial JSON
    # lines onto the wire.
    _write_lock: threading.Lock
    _sub_id: int | None
    _events_thread: threading.Thread | None
    # T-1097: this connection's identity in `server.lease_manager` --
    # every resource lease this connection acquires is tracked under this
    # one id, so `release_holder(self._lease_holder_id)` in `handle`'s
    # `finally` frees all of them in one call on disconnect/crash.
    _lease_holder_id: str

    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    def setup(self) -> None:  # noqa: ANN201
        """Per-connection state `handle()` needs -- `StreamRequestHandler`
        constructs a fresh handler instance per connection, so this is the
        correct place to initialize instance state, not `__init__`."""
        super().setup()
        self._write_lock = threading.Lock()
        self._sub_id = None
        self._events_thread = None
        self._lease_holder_id = f"{id(self)}-{time.monotonic_ns()}"

    # frob:doc docs/modules/serve.md#protocol
    # frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_serves_one_request_then_idle_exits kind="unit"  # noqa: E501
    # frob:waive ARCH103 reason="T-1092: the connection loop -- read a line, parse it, \
    # dispatch it, write the response -- is the entire, inherently sequential job of a \
    # socketserver.StreamRequestHandler.handle() override; splitting the \
    # parse/dispatch/write steps into separate functions would not reduce real \
    # complexity, only relocate it behind an extra call boundary for a single caller"
    def handle(self) -> None:  # noqa: ANN201
        """Serve every request line on this connection until EOF or a
        malformed line -- one connection may carry many sequential
        requests (a persistent client), not just one. Always unsubscribes
        (T-1096) on the way out, even on an abrupt disconnect."""
        try:
            for raw_line in self.rfile:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                self.server.idle_tracker.touch()
                try:
                    payload = json.loads(line)
                    request = _JsonRpcRequest.model_validate(payload)
                except Exception as exc:  # noqa: BLE001
                    _log.warning("serve: socketd: malformed request line: %s", exc)
                    response = {
                        "id": None,
                        "error": {
                            "code": "malformed_request",
                            "message": str(exc),
                        },
                    }
                else:
                    if request.method == "subscribe":
                        response = self._handle_subscribe(request)
                    elif request.method == "frob_version":
                        response = self._handle_version(request)
                    elif request.method == "frob_shutdown":
                        response = self._handle_shutdown(request)
                    elif request.method == "frob_lease_acquire":
                        response = self._handle_lease_acquire(request)
                    elif request.method == "frob_lease_release":
                        response = self._handle_lease_release(request)
                    else:
                        response = dispatch_request(self.server.root, request)
                self._write_line(response)
        finally:
            if self._sub_id is not None:
                self.server.event_bus.unsubscribe(self._sub_id)
            # T-1097 acceptance [1]: a crashed/disconnected client's
            # leases are freed HERE, unconditionally, regardless of
            # whether it ever sent an explicit frob_lease_release.
            self.server.lease_manager.release_holder(self._lease_holder_id)

    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    # frob:waive COV007 reason="docs/modules/serve.md individually names \
    # _RequestHandler._handle_subscribe (T-0529 precedent: a deliberate per-RPC-verb \
    # architecture doc, not accidental drift onto a private helper)"
    # frob:tests tests/test_serve_events.py::TestSubscribeAndWait.test_receives_graph_changed_after_edit kind="unit"  # noqa: E501
    def _handle_subscribe(self, request: _JsonRpcRequest) -> dict[str, Any]:
        """Register this connection with `server.event_bus` and start its
        dedicated event-pump thread -- called once per `subscribe`
        request; a second `subscribe` on the same connection just
        re-subscribes (drops the old subscription id, starts a new one)
        rather than erroring, since nothing about this protocol forbids a
        client subscribing more than once."""
        if self._sub_id is not None:
            self.server.event_bus.unsubscribe(self._sub_id)
        sid, q = self.server.event_bus.subscribe()
        self._sub_id = sid
        thread = threading.Thread(
            target=self._pump_events, args=(q,), daemon=True, name="frob-socketd-pump"
        )
        self._events_thread = thread
        thread.start()
        _log.info("serve: socketd: connection subscribed (sub_id=%d)", sid)
        return {"id": request.id, "result": {"subscribed": True}}

    # frob:doc docs/modules/serve.md#version-handshake-t-1105
    # frob:waive COV007 reason="each _RequestHandler._handle_* method is a distinct \
    # wire-protocol RPC verb with its own dedicated doc anchor (T-0529 precedent: \
    # deliberate per-RPC-verb architecture doc, not accidental drift)"
    # frob:tests tests/test_serve_socket.py::TestDispatchRequest.test_frob_version_reports_daemon_version kind="unit"  # noqa: E501
    def _handle_version(self, request: _JsonRpcRequest) -> dict[str, Any]:
        """Answer the `frob_version` handshake RPC (T-1105) with this
        daemon process's own installed `frob` version -- the real,
        daemon-side replacement for the old client-written
        `.frob/daemon.meta.json` sidecar-file skew check (T-1093), which
        could go stale relative to whichever process actually happens to
        be running the daemon."""
        return {"id": request.id, "result": {"version": daemon_version()}}

    # frob:doc docs/modules/serve.md#version-handshake-t-1105
    # frob:waive COV007 reason="each _RequestHandler._handle_* method is a distinct \
    # wire-protocol RPC verb with its own dedicated doc anchor (T-0529 precedent: \
    # deliberate per-RPC-verb architecture doc, not accidental drift)"
    # frob:tests tests/test_serve_socket.py::TestDispatchRequest.test_frob_shutdown_stops_the_server kind="unit"  # noqa: E501
    def _handle_shutdown(self, request: _JsonRpcRequest) -> dict[str, Any]:
        """Answer `frob_shutdown` (T-1105) and asynchronously stop the
        server -- a graceful, protocol-level replacement for the old
        client-side `SIGTERM`-by-recorded-pid dance (T-1093's
        `_kill_stale_daemon`), which needed a pid sidecar file to exist and
        stay accurate. `server.shutdown()` blocks until `serve_forever`'s
        loop notices and returns, so it is invoked from a short-lived
        helper thread rather than this connection's own handler thread --
        calling it inline here would deadlock this exact thread against
        the loop it is asking to stop."""
        _log.info("serve: socketd: frob_shutdown requested, stopping server")
        threading.Thread(
            target=self.server.shutdown, name="frob-socketd-shutdown", daemon=True
        ).start()
        return {"id": request.id, "result": {"shutting_down": True}}

    # frob:doc docs/modules/serve.md#resource-leasessemaphores-t-1097
    # frob:waive COV007 reason="each _RequestHandler._handle_* method is a distinct \
    # wire-protocol RPC verb with its own dedicated doc anchor (T-0529 precedent: \
    # deliberate per-RPC-verb architecture doc, not accidental drift)"
    # frob:tests tests/test_serve_leases.py::TestLeaseRpc.test_second_client_blocks_until_first_releases kind="unit"  # noqa: E501
    def _handle_lease_acquire(self, request: _JsonRpcRequest) -> dict[str, Any]:
        """Answer `frob_lease_acquire` (T-1097): block THIS connection's
        handler thread (blocking here only blocks this one connection --
        every other connection has its own thread, T-1092's `Threading
        UnixStreamServer`) until `server.lease_manager` grants a slot of
        `params["resource"]` to this connection's `_lease_holder_id`, or
        `params["timeout_s"]` elapses first. `params["capacity"]` is only
        consulted the FIRST time a given resource name is ever acquired
        (`ResourceLeaseManager._state_for`'s create-on-first-mention
        rule)."""
        resource = request.params.get("resource")
        if not isinstance(resource, str) or not resource:
            return {
                "id": request.id,
                "error": {"code": "bad_params", "message": "resource must be a str"},
            }
        capacity = request.params.get("capacity", DEFAULT_LEASE_CAPACITY)
        timeout_s = request.params.get("timeout_s")
        acquired = self.server.lease_manager.acquire(
            resource,
            self._lease_holder_id,
            capacity=capacity,
            timeout_s=timeout_s,
        )
        return {"id": request.id, "result": {"acquired": acquired}}

    # frob:doc docs/modules/serve.md#resource-leasessemaphores-t-1097
    # frob:waive COV007 reason="each _RequestHandler._handle_* method is a distinct \
    # wire-protocol RPC verb with its own dedicated doc anchor (T-0529 precedent: \
    # deliberate per-RPC-verb architecture doc, not accidental drift)"
    # frob:tests tests/test_serve_leases.py::TestLeaseRpc.test_explicit_release_frees_the_slot_for_the_next_waiter kind="unit"  # noqa: E501
    def _handle_lease_release(self, request: _JsonRpcRequest) -> dict[str, Any]:
        """Answer `frob_lease_release` (T-1097): free THIS connection's
        slot of `params["resource"]`, if it holds one -- the explicit
        counterpart to the implicit `release_holder` teardown `handle`'s
        `finally` block always performs on disconnect, for a well-behaved
        client that wants to free a resource without closing the whole
        connection."""
        resource = request.params.get("resource")
        if not isinstance(resource, str) or not resource:
            return {
                "id": request.id,
                "error": {"code": "bad_params", "message": "resource must be a str"},
            }
        released = self.server.lease_manager.release(resource, self._lease_holder_id)
        return {"id": request.id, "result": {"released": released}}

    def _pump_events(self, q: queue.Queue[dict[str, Any] | None]) -> None:
        """Event-pump thread body: block on `q.get()` and write each frame
        out to this connection until a `None` sentinel (unsubscribed) or a
        write failure (the client went away) ends it. Both `OSError`
        (a broken pipe/reset connection) and `ValueError` (stdlib's
        `BufferedWriter` raises this, not `OSError`, for a write against
        an already-`close()`d file -- the race between this thread waking
        for a queued frame and `handle()`'s own connection teardown
        finishing first) are expected end-of-connection signals here, not
        bugs to propagate."""
        while True:
            frame = q.get()
            if frame is None:
                return
            try:
                self._write_line(frame)
            except (OSError, ValueError):
                return

    def _write_line(self, payload: dict[str, Any]) -> None:
        """Write one JSON line to `self.wfile`, serialized against
        concurrent writers on this same connection (the main handler
        thread and, once subscribed, the event-pump thread)."""
        with self._write_lock:
            self.wfile.write((json.dumps(payload) + "\n").encode("utf-8"))
            self.wfile.flush()


class _DaemonServer(socketserver.ThreadingUnixStreamServer):
    """`ThreadingUnixStreamServer` bound to `socket_path(root)`, one
    connection handled per thread, tagged with the `root` it serves and an
    `_IdleTracker` every connection's requests feed."""

    daemon_threads = True
    # frob:waive PII012 reason="T-1092: stdlib socketserver.BaseServer's own \
    # reuse-addr flag (SO_REUSEADDR); no relation to a person's contact address -- a \
    # name-only false-positive match on 'address'"
    allow_reuse_address = True

    def __init__(self, root: Path, sock_path: Path) -> None:
        """Bind the unix socket at `sock_path` and stash `root` for
        `_RequestHandler.handle` to dispatch against. `event_bus` (T-1096)
        is imported locally, not at module level, to avoid a
        `_socketd`<->`_events` import cycle -- `_events.subscribe_and_wait`
        itself imports `DaemonError`/`socket_path` FROM this module, so
        this module cannot also import `_events` at module scope."""
        from frob.serve._events import _EventBus

        self.root = root
        self.idle_tracker = _IdleTracker()
        self.event_bus = _EventBus()
        # T-1097: one ResourceLeaseManager per daemon process, shared
        # across every connection-handling thread.
        self.lease_manager = ResourceLeaseManager()
        super().__init__(str(sock_path), _RequestHandler, bind_and_activate=True)


def _remove_stale_socket(sock_path: Path) -> None:
    """Unlink a leftover socket file at `sock_path` if one exists -- safe
    to do unconditionally here because the caller only reaches this after
    winning `acquire_singleton_lock`, so no other live daemon can be bound
    to it; a stale file is left over only from a previous process that
    exited without cleaning up (crash, `SIGKILL`)."""
    try:
        sock_path.unlink()
        _log.info("serve: socketd: removed stale socket file at %s", sock_path)
    except FileNotFoundError:
        pass


def _idle_monitor(
    server: _DaemonServer, idle_timeout_s: float, stop: threading.Event
) -> None:
    """Background thread body: poll `server.idle_tracker` at an interval
    scaled to `idle_timeout_s` (never more than `_IDLE_POLL_INTERVAL_S`, so
    a short test-configured timeout is still observed promptly rather than
    waiting for a fixed multi-second tick); once `idle_timeout_s` has
    elapsed with no request, call `server.shutdown()` so `serve_forever()`
    returns and the process can exit cleanly. Also exits promptly if `stop`
    is set externally (tests tearing down without waiting a full
    timeout)."""
    poll_interval = min(_IDLE_POLL_INTERVAL_S, max(idle_timeout_s / 4, 0.01))
    while not stop.is_set():
        if server.idle_tracker.idle_for_s() >= idle_timeout_s:
            _log.info("serve: socketd: idle for >=%gs, shutting down", idle_timeout_s)
            server.shutdown()
            return
        stop.wait(poll_interval)


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
# frob:tests tests/test_serve_socket.py::TestDispatchRequest.test_known_method_ok kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestDispatchRequest.test_unknown_method_is_error kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_serves_one_request_then_idle_exits kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_contended_lock_is_err kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_stale_socket_file_is_replaced kind="unit"  # noqa: E501
def run_socket_daemon(cfg: SocketDaemonConfig) -> Result[None, DaemonError]:
    """The standalone daemon process entry point (T-1092): acquire the
    single-instance lock (`Err(DaemonError.AlreadyRunning)` if another
    process already holds it -- the caller should treat this as "a daemon
    is already up", not surface it as a user-facing failure), remove any
    stale socket file, bind `socket_path(cfg.root)`, start the idle-monitor
    thread, then block in `serve_forever()` until the idle timeout fires.
    On the way out (normal idle exit or an exception) the socket file is
    removed and the lock released, so the next caller finds a clean slate.
    """
    root = cfg.root.resolve()
    lock_result = acquire_singleton_lock(root)
    if lock_result.is_err:
        return Err(lock_result.danger_err)
    lock_handle = lock_result.danger_ok

    sock_path = socket_path(root)
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_stale_socket(sock_path)

    try:
        server = _DaemonServer(root, sock_path)
    except OSError as exc:
        _log.error("serve: socketd: bind failed at %s: %s", sock_path, exc)
        _release_singleton_lock(lock_handle)
        return Err(DaemonError.BindFailed)

    stop = threading.Event()
    monitor = threading.Thread(
        target=_idle_monitor,
        args=(server, cfg.idle_timeout_s, stop),
        name="frob-socketd-idle-monitor",
        daemon=True,
    )
    monitor.start()

    # T-1094: push-invalidate the warm state during idle time instead of
    # leaving every rebuild to whichever client query happens to arrive
    # next. `on_change` (T-1096) publishes a `graph-changed` event to any
    # subscribed client the moment a real on-disk change is observed.
    from frob.serve._events import CoverageWatcher

    watcher = WatchThread(
        root, on_change=lambda: server.event_bus.publish("graph-changed")
    )
    watcher.start()

    # T-1096: the `coverage-fresh` event source -- any write to
    # `.frob/coverage-stamp` (by run_coverage_wait, a bare `make coverage`,
    # or a future cross-worktree single-flight run, T-1095) is republished
    # as a push event so a subscribed client never has to poll for it.
    coverage_watcher = CoverageWatcher(
        root, on_fresh=lambda: server.event_bus.publish("coverage-fresh")
    )
    coverage_watcher.start()

    _log.info(
        "serve: socketd: listening at %s (pid=%d, idle_timeout=%gs)",
        sock_path,
        os.getpid(),
        cfg.idle_timeout_s,
    )
    try:
        server.serve_forever()
    finally:
        stop.set()
        watcher.stop()
        coverage_watcher.stop()
        server.server_close()
        _remove_stale_socket(sock_path)
        _release_singleton_lock(lock_handle)
        _log.info("serve: socketd: shut down cleanly at %s", sock_path)
    return Ok(None)


# frob:doc docs/modules/serve.md#socket-daemon-t-1092
# frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_serves_one_request_then_idle_exits kind="unit"  # noqa: E501
# frob:tests tests/test_serve_socket.py::TestRunSocketDaemon.test_stale_socket_file_is_replaced kind="unit"  # noqa: E501
# frob:waive ARCH103 reason="T-1092: a minimal synchronous JSON-RPC client -- connect, \
# send one line, read one line back, unwrap into a Result -- is the entire, inherently \
# sequential job of this function; splitting the connect/send/recv/unwrap steps into \
# separate functions would not reduce real complexity, only relocate it behind an \
# extra call boundary for a single caller"
def send_request(
    root: Path,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    timeout_s: float = 10.0,
) -> Result[Any, DaemonError]:
    """A minimal synchronous client: connect to `socket_path(root)`, send
    one JSON-RPC request, read one JSON-RPC response line back, and unwrap
    it into a `Result` -- the shape a future CLI-side client (the next
    child ticket) will build on, and what `tests/test_serve_socket.py`
    uses to exercise `run_socket_daemon` end-to-end over a real socket."""
    sock_path = socket_path(root.resolve())
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout_s)
            sock.connect(str(sock_path))
            request_line = json.dumps(
                {"id": 1, "method": method, "params": params or {}}
            )
            sock.sendall((request_line + "\n").encode("utf-8"))
            buffer = b""
            while not buffer.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buffer += chunk
    except OSError as exc:
        _log.info("serve: socketd: client: could not reach %s: %s", sock_path, exc)
        return Err(DaemonError.Unreachable)
    response = json.loads(buffer.decode("utf-8"))
    if "error" in response:
        _log.warning(
            "serve: socketd: client: %s -> error: %s", method, response["error"]
        )
        return Err(DaemonError.RemoteError)
    return Ok(response.get("result"))


__all__ = [
    "DEFAULT_IDLE_TIMEOUT_S",
    "DaemonError",
    "SocketDaemonConfig",
    "acquire_singleton_lock",
    "daemon_version",
    "dispatch_request",
    "lock_path",
    "run_socket_daemon",
    "send_request",
    "socket_path",
]
