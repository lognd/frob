"""CLI-side auto-proxy to the T-1092 unix-socket daemon (T-1093,
docs/modules/serve.md#cli-daemon-proxy-t-1093).

`frob.serve._socketd` (T-1092) stands up a standalone daemon process and a
JSON-RPC protocol to talk to it, but nothing in the CLI dispatch path ever
calls it -- every invocation still recomputes cold, in-process. This module
is the missing client-side seam: `query()` is the one entry point a runner
calls instead of computing a proxyable answer itself. It always resolves to
one of two outcomes, transparently:

1. `Ok(result)` -- a live, version-matched daemon answered the query over
   the socket. The caller renders `result` exactly as it would have
   rendered its own in-process computation (T-1093's #1 safety invariant:
   the two must be byte-for-byte identical for every proxied query shape --
   see `tests/test_app_daemon_proxy.py`'s differential test).
2. `Err(ProxyReason)` -- for ANY reason (disabled, no daemon, daemon
   crashed/unreachable, stale-version daemon mid-restart, a JSON-RPC error
   from the daemon itself) -- the caller falls straight back to computing
   the answer in-process, exactly as it did before this module existed.
   None of these reasons are user-facing errors; every one is logged at
   this module's logger and swallowed here.

Self-healing version skew (T-1093 acceptance [1] / T-0321 HARD requirement
6, T-1105): `ensure_daemon` asks the daemon itself, over the socket, via
the `frob_version` RPC (T-1105, `frob.serve._socketd.daemon_version`) --
there is no sidecar meta-file to fall out of sync with whichever process
last spawned the daemon. A mismatch between the daemon's self-reported
version and this client's own (`_client_version`) means the daemon predates
(or postdates) this client's own `frob` install, most likely a stale daemon
left running across a `frob` upgrade -- it is asked to gracefully stop via
the `frob_shutdown` RPC and a fresh one is spawned in its place before the
query proceeds. This replaces T-1093's original `.frob/daemon.meta.json`
sidecar-file approach (a client-written `{"version", "pid"}` file compared
against, and a `SIGTERM`-by-recorded-pid teardown) with a real protocol-
level handshake, per the residual T-1093 disclosed (T-draft-8a56400c).

`FROB_NO_DAEMON=1` is an unconditional bypass (T-1093 acceptance [2]): with
it set, `query()` returns `Err(ProxyReason.Disabled)` immediately, before
ever touching the socket, lock, or meta file -- the differential test uses
this to produce the reference in-process answer to diff the daemon-served
one against.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from typani import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

# How long a fresh spawn is given to bind its socket before this call gives
# up and falls back for THIS query -- kept short (this runs on the CLI's hot
# path) since the payoff is warm state on the NEXT call, not necessarily
# this one.
_SPAWN_GRACE_S = 1.5
_SPAWN_POLL_INTERVAL_S = 0.05
# frob:waive DUP001 reason="T-1093/T-1105: this shutdown grace window mirrors \
# _SPAWN_GRACE_S's shape (a short bounded poll loop) but measures a distinct thing -- \
# an old daemon releasing its flock after a graceful frob_shutdown RPC, not a new one \
# binding a socket -- and the two callers (ensure_daemon's skew path vs query's \
# fresh-spawn path) would still need two constants even if the values matched"
_SHUTDOWN_GRACE_S = 1.0
# frob:ticket T-1377
# Liveness is a LOCAL unix-socket round trip -- sub-millisecond when
# healthy -- so half a second is already ~1000x headroom. It is deliberately
# NOT `send_request`'s 10s query timeout: budgeting a health check like a
# real query is what made an unhealthy daemon cost 10s on every single
# `frob` invocation that proxies.
_PROBE_TIMEOUT_S = 0.5


# frob:doc docs/modules/serve.md#daemon-liveness-t-1377-and-the-opt-in-switch-t-1379
class DaemonLiveness(ErrorSet):
    """What a bounded probe actually found, so each distinct state can get
    the distinct response it needs.

    The pre-T-1377 code collapsed all four onto `None` ("spawn a
    replacement"), which is right for exactly one of them and actively
    harmful for `Wedged`.
    """

    Live = "a version-matched daemon answered the probe"
    NoSocket = "no socket file exists for this root"
    Orphaned = "a socket file exists but nothing is listening on it"
    Wedged = "something is listening but did not answer a probe in budget"
    VersionSkew = "a daemon answered but reports a different frob version"


# frob:ticket T-1377
# frob:ticket T-1380
# frob:doc docs/modules/serve.md#daemon-liveness-t-1377-and-the-opt-in-switch-t-1379
# frob:tests tests/test_app_daemon_proxy.py::TestProbeDaemon.test_missing_socket_is_nosocket  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestProbeDaemon.test_dead_socket_file_is_orphaned  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestProbeDaemon.test_silent_listener_is_wedged  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket.test_connect_timeout_is_wedged  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket.test_connect_oserror_is_wedged  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket.test_hangup_before_newline_is_wedged  # noqa: E501
def probe_daemon(
    root: Path, *, timeout_s: float = _PROBE_TIMEOUT_S
) -> tuple[DaemonLiveness, str | None]:
    """Classify the daemon for `root` in BOUNDED time: `(liveness, version)`.

    Socket-file existence is not liveness -- a unix socket outlives the
    process that bound it, which is precisely how a dead daemon kept
    costing every caller a full 10s connect timeout. Only a real
    connect-plus-answer round trip proves a daemon is serving.

    Never raises: an unclassifiable failure reports `Wedged`, the
    conservative answer, because that is the one state where spawning a
    competing daemon makes things worse rather than better.
    """
    from frob.serve import socket_path

    path = socket_path(root.resolve())
    if not path.exists():
        return (DaemonLiveness.NoSocket, None)
    raw = _ask_version_over_socket(path, timeout_s)
    if isinstance(raw, DaemonLiveness):
        return (raw, None)
    return _classify_version_reply(raw)


# frob:ticket T-1380
# frob:waive ARCH103 reason="a socket health probe IS connect-send-recv plus the two \
# failure decisions those calls can produce; splitting the recv loop away from the \
# connect that must precede it would add indirection without separating a real \
# sub-concern, and the classification half is already extracted into \
# _classify_version_reply"
# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to socket.socket's own \
# connect/settimeout/sendall/recv calls, stdlib socket calls the resolver cannot \
# statically bound past the broad except (TimeoutError, OSError) wrapping the whole \
# with-block; every locally documented raise path (ConnectionRefusedError, \
# FileNotFoundError, TimeoutError, OSError) is caught explicitly"
def _ask_version_over_socket(path: Path, timeout_s: float) -> bytes | DaemonLiveness:
    """One bounded `frob_version` round trip: the raw reply bytes, or the
    `DaemonLiveness` that the transport failure itself already proves."""
    import socket as _socket

    try:
        with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout_s)
            try:
                sock.connect(str(path))
            except (ConnectionRefusedError, FileNotFoundError):
                # The file outlived its process: nothing is accepting on it.
                return DaemonLiveness.Orphaned
            except (TimeoutError, OSError):
                return DaemonLiveness.Wedged
            sock.sendall(b'{"id": 1, "method": "frob_version", "params": {}}\n')
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    # Accepted, then hung up without answering.
                    return DaemonLiveness.Wedged
                buf += chunk
    except (TimeoutError, OSError):
        return DaemonLiveness.Wedged
    return buf


# frob:ticket T-1380
# frob:waive EXHAUST003 reason="T-1371: leaked Unknown traces to \
# bytes.split/bytes.decode and dict.get chained twice, plain str/bytes/dict operations \
# the resolver cannot statically bound; the one real raise path (json.loads on \
# malformed input) is caught below"
# frob:waive EXHAUST002 reason="T-1371: same resolver artifact as EXHAUST003 above -- \
# the chained payload.get(...).get(...) is defensive against a non-dict 'result' \
# value, which raises AttributeError (already caught), not KeyError; dict.get never \
# raises KeyError by construction, so this is a false positive from the gate's \
# syntactic scan"
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.test_malformed_json_is_wedged  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.test_non_dict_result_is_wedged  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.test_non_str_version_is_wedged  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.test_bad_utf8_is_wedged  # noqa: E501
def _classify_version_reply(buf: bytes) -> tuple[DaemonLiveness, str | None]:
    """A well-formed reply -> `Live` or `VersionSkew`; anything unreadable
    -> `Wedged`, the conservative answer."""
    try:
        payload = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
        version = payload.get("result", {}).get("version")
    except (ValueError, AttributeError, UnicodeDecodeError):
        return (DaemonLiveness.Wedged, None)
    if not isinstance(version, str):
        return (DaemonLiveness.Wedged, None)
    if version != _client_version():
        return (DaemonLiveness.VersionSkew, version)
    return (DaemonLiveness.Live, version)


# frob:ticket T-1377
# frob:tests tests/test_app_daemon_proxy.py::TestProbeDaemon.test_orphaned_socket_is_unlinked  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClearOrphanedSocket.test_unlink_oserror_is_swallowed  # noqa: E501
def _clear_orphaned_socket(root: Path) -> None:
    """Unlink a socket file nothing is listening on, so the next probe is a
    clean `NoSocket` rather than another refused connect."""
    from frob.serve import socket_path

    try:
        socket_path(root.resolve()).unlink()
        _log.info("daemon_proxy: unlinked orphaned socket for %s", root)
    except OSError as exc:
        _log.info("daemon_proxy: could not unlink orphaned socket: %s", exc)


# frob:doc docs/modules/serve.md#cli-daemon-proxy-t-1093
class ProxyReason(ErrorSet):
    """Why a query was NOT served by the daemon. Every value means "fall
    back to in-process, silently" -- none is a user-facing failure."""

    Disabled = "the daemon is not enabled for this process (T-1379: opt-in)"
    Unreachable = "no live daemon socket answered for this root"
    RemoteError = "the daemon returned a JSON-RPC error for this query"


# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClientVersion.test_unexpected_exception_falls_back_to_unknown  # noqa: E501
def _client_version() -> str:
    """This process's installed `frob` version, or 'unknown' from a raw
    source checkout with no registered distribution -- mirrors
    `frob.__main__._frob_version`'s own fallback shape (duplicated rather
    than imported: `__main__.py` is a sibling-owned file this ticket must
    not import back into, per its declared scope)."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("frob")
    except PackageNotFoundError:
        return "unknown"
    except Exception as exc:  # noqa: BLE001 -- best-effort version probe, never fatal
        _log.debug("daemon_proxy: version lookup failed: %s", exc)
        return "unknown"


# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestSpawnDaemon.test_popen_oserror_is_swallowed  # noqa: E501
def _spawn_daemon(root: Path) -> None:
    """Best-effort, fire-and-forget spawn of the T-1092 socket daemon
    (`frob.serve.run_socket_daemon`) as a detached subprocess of the
    CURRENTLY RUNNING interpreter (`sys.executable`, so it inherits this
    exact `frob` install rather than whatever a bare `frob` on PATH would
    resolve to). Never raises: a spawn failure just means the next query
    stays `Unreachable` and falls back in-process, same as any other
    daemon-down case."""
    code = (
        "from pathlib import Path\n"
        "from frob.serve import SocketDaemonConfig, run_socket_daemon\n"
        f"run_socket_daemon(SocketDaemonConfig(root=Path({str(root)!r})))\n"
    )
    try:
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        _log.info("daemon_proxy: spawn failed for %s: %s", root, exc)
        return
    _log.info(
        "daemon_proxy: spawned daemon pid=%d for %s (client version=%s)",
        proc.pid,
        root,
        _client_version(),
    )


# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon.test_rpc_failure_is_logged_and_returns  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon.test_successful_shutdown_waits_for_lock_release  # noqa: E501
def _shutdown_stale_daemon(root: Path) -> None:
    """Ask the daemon already running for `root` to stop gracefully via the
    `frob_shutdown` RPC (T-1105) and wait (briefly, bounded by
    `_SHUTDOWN_GRACE_S`) for its lock file to be released, so a follow-up
    spawn does not race it for the still-held `flock`. The RPC itself
    failing (daemon gone between the version check and now) is not an
    error here -- either way the caller proceeds to spawn a replacement;
    `acquire_singleton_lock` is what actually guarantees exclusivity."""
    from frob.serve import send_request
    from frob.serve._socketd import lock_path

    result = send_request(root, "frob_shutdown")
    if result.is_err:
        _log.info(
            "daemon_proxy: version skew, frob_shutdown RPC failed for %s: %s",
            root,
            result.danger_err,
        )
        return
    _log.info("daemon_proxy: version skew, frob_shutdown accepted for %s", root)
    path = lock_path(root)
    deadline = time.monotonic() + _SHUTDOWN_GRACE_S
    while time.monotonic() < deadline:
        if not path.exists():
            return
        time.sleep(_SPAWN_POLL_INTERVAL_S)


# frob:doc docs/modules/serve.md#cli-daemon-proxy-t-1093
# frob:tests tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_spawns_when_nothing_recorded kind="unit"  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_version_handshake_end_to_end kind="unit"  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_restarts_on_version_skew kind="unit"  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_noop_when_version_matches kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches.test_wedged_does_not_spawn_a_rival kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches.test_orphaned_clears_socket_then_spawns kind="unit"  # noqa: E501
def ensure_daemon(root: Path) -> None:
    """Ensure a live, version-matched daemon is running (or freshly
    starting) for `root`, self-healing a version-skewed one first (T-1093
    acceptance [1], T-1105). Version skew is detected via the daemon's own
    `frob_version` RPC response (`probe_daemon`, T-1377), not a sidecar
    meta file -- there is nothing here to go stale relative to whichever
    process actually happens to be running the daemon. Best-effort only
    and never raises: a caller that cannot get a daemon up simply finds no
    socket to connect to on the next `query()` call and falls back
    in-process, same as any other `Unreachable` case."""
    # frob:ticket T-1377
    liveness, daemon_version = probe_daemon(root)
    if liveness is DaemonLiveness.Live:
        return
    if liveness is DaemonLiveness.Wedged:
        # Something IS holding the socket. Spawning a rival is exactly
        # wrong: `acquire_singleton_lock` refuses it, so every subsequent
        # invocation pays another failed spawn. Bypass for this run.
        _log.warning(
            "daemon_proxy: daemon for %s is listening but did not answer a "
            "%.2fs probe -- treating as wedged, NOT spawning a rival; this "
            "run falls back in-process",
            root,
            _PROBE_TIMEOUT_S,
        )
        return
    if liveness is DaemonLiveness.VersionSkew:
        _log.info(
            "daemon_proxy: version skew detected (daemon=%s, client=%s) for %s",
            daemon_version,
            _client_version(),
            root,
        )
        _shutdown_stale_daemon(root)
    elif liveness is DaemonLiveness.Orphaned:
        _clear_orphaned_socket(root)
    _spawn_daemon(root)


# frob:ticket T-1379
# frob:doc docs/modules/serve.md#daemon-liveness-t-1377-and-the-opt-in-switch-t-1379
# frob:tests tests/test_app_daemon_proxy.py::TestDaemonOptIn.test_unset_env_disables_the_daemon  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestDaemonOptIn.test_frob_daemon_1_enables_the_daemon  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/modules/serve.md's Daemon liveness section \
# (T-1377/T-1379) is a deliberate architecture doc walking through this exact private \
# opt-in switch's own design, same T-0524/T-0529 per-function architecture-doc \
# precedent every other COV007 waiver in this repo already carries -- not accidental \
# drift onto a private helper"
def _daemon_enabled() -> bool:
    """Whether the daemon path may be used at all.

    T-1379: opt-IN while T-1378's defects stand -- the daemon ignores a
    `frob_shutdown` it acknowledged, leaks its multiprocessing children,
    and its pool competes with the foreground check for CPU badly enough
    to be a net pessimization. Opt-out meant every unsuspecting session
    paid for that by default. `FROB_NO_DAEMON=1` still wins outright so
    existing scripts and the differential test are unaffected.
    """
    # frob:waive SEC110 reason="T-1379: FROB_DAEMON/FROB_NO_DAEMON are boolean feature \
    # flags (same shape as the existing FROB_AGENT/FROB_WORKTREE precedent in \
    # frob.tickets._leases), neither carries a confidential value"
    if os.environ.get("FROB_NO_DAEMON") == "1":
        return False
    return os.environ.get("FROB_DAEMON") == "1"


# frob:doc docs/modules/serve.md#cli-daemon-proxy-t-1093
# frob:tests tests/test_app_daemon_proxy.py::TestQuery.test_no_daemon_env_bypass kind="unit"  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestQuery.test_live_daemon_hit kind="unit"  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestQuery.test_remote_error_falls_back kind="unit"  # noqa: E501
def query(
    root: Path, method: str, params: dict[str, Any] | None = None
) -> Result[Any, ProxyReason]:
    """Attempt one query against the live daemon for `root`, transparently:
    honors `FROB_NO_DAEMON=1` (unconditional bypass, T-1093 acceptance
    [2]), self-heals a version-skewed daemon via `ensure_daemon`, and
    best-effort spawns one if none is up yet (T-1093 acceptance [0]). Every
    `Err` means "the caller must compute this in-process instead" -- never
    surfaced to the user as a daemon error, never a hang (T-1093 acceptance
    [1]): `send_request`'s own socket timeout bounds the worst case, and the
    one retry below is itself bounded by `_SPAWN_GRACE_S`."""
    if not _daemon_enabled():
        _log.info("daemon_proxy: daemon disabled, computing %s in-process", method)
        return Err(ProxyReason.Disabled)

    from frob.serve import DaemonError, send_request

    ensure_daemon(root)

    result = send_request(root, method, params)
    if result.is_err and result.danger_err is DaemonError.Unreachable:
        # A daemon may have just been spawned above and not be bound yet --
        # give it one short, bounded window to come up before falling back
        # for THIS call (a later call will find it warm regardless).
        deadline = time.monotonic() + _SPAWN_GRACE_S
        while time.monotonic() < deadline and result.is_err:
            time.sleep(_SPAWN_POLL_INTERVAL_S)
            result = send_request(root, method, params)

    if result.is_err:
        reason = (
            ProxyReason.RemoteError
            if result.danger_err is DaemonError.RemoteError
            else ProxyReason.Unreachable
        )
        _log.info("daemon_proxy: %s -> fallback (%s)", method, result.danger_err)
        return Err(reason)

    _log.info("daemon_proxy: %s -> daemon hit", method)
    return Ok(result.danger_ok)


class _LeaseConnection:
    """A persistent raw JSON-RPC connection to `root`'s daemon (T-1126),
    used ONLY for holding a `frob_lease_acquire`/`frob_lease_release` pair
    across a long-running operation -- unlike `query()`/`send_request`
    (connect-send-recv-close every call), a lease must be acquired and
    released on the SAME connection so the server's connection-liveness
    release (T-1097: a crashed/killed client's leases are freed
    unconditionally on disconnect) has a concrete connection to tear down
    if this process dies mid-operation. Mirrors `tests/test_serve_leases.
    py`'s own `_RawClient` test scaffold, promoted to production code
    here since a real caller (`frob.testing.run_coverage_wait`) now needs
    the same persistent-connection shape, not just a test."""

    def __init__(self, root: Path, *, timeout_s: float = 10.0) -> None:
        """Connect once; every `call()` reuses the same socket."""
        import socket as _socket

        from frob.serve import socket_path

        self._sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        self._sock.settimeout(timeout_s)
        self._sock.connect(str(socket_path(root.resolve())))
        self._buf = b""

    # frob:doc docs/modules/testing.md#t-1126-daemon-owned-coverage-lease-frob_lease_acquirefrob_lease_release  # noqa: E501
    # frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_round_trip_acquire_call_release_close kind="unit"  # noqa: E501
    def call(self, method: str, params: dict[str, Any] | None = None) -> dict:
        """Send one JSON-RPC request line and read one response line back."""
        import json

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

    # frob:doc docs/modules/testing.md#t-1126-daemon-owned-coverage-lease-frob_lease_acquirefrob_lease_release  # noqa: E501
    # frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_round_trip_acquire_call_release_close kind="unit"  # noqa: E501
    def close(self) -> None:
        """Close the connection -- the server's connection-liveness
        release (T-1097) frees any lease this connection still held,
        whether or not `frob_lease_release` was sent first."""
        self._sock.close()


# frob:doc docs/modules/testing.md#frobtesting_coverage_waitpy-t-0322-cross-worktree-layer-t-1095  # noqa: E501
# frob:tests tests/test_coverage_wait_shared.py::TestWorktreeLock.test_uses_daemon_lease_when_daemon_up kind="unit"  # noqa: E501
# frob:tests tests/test_coverage_wait_shared.py::TestWorktreeLock.test_falls_back_to_file_lock_when_no_daemon kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_round_trip_acquire_call_release_close kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_disabled_env_bypasses_lease kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_no_daemon_falls_back_unreachable kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths.test_call_oserror_closes_connection_and_returns_unreachable  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths.test_remote_error_response_closes_connection  # noqa: E501
def try_daemon_lease(
    root: Path,
    resource: str,
    *,
    capacity: int = 1,
    timeout_s: float | None = None,
) -> Result[_LeaseConnection, ProxyReason]:
    """Try to acquire `resource` via the T-1097 daemon lease RPC (`frob_
    lease_acquire`) over a fresh persistent connection. `Ok(conn)` means
    the lease is held -- the caller does its work, then MUST call
    `release_daemon_lease(conn, resource)` when done (or just let the
    connection close: T-1097's connection-liveness release frees it
    either way, the crash-safety backstop `try_daemon_lease`'s docstring
    promises). `Err(ProxyReason)` means no daemon is reachable, or the
    lease request itself errored -- the caller falls back to its own
    (e.g. file-lock) arbitration, exactly `query()`'s existing fallback
    contract."""
    # frob:waive SEC110 reason="T-1126: FROB_NO_DAEMON is the same boolean opt-out \
    # flag query() already carries this exact waiver for -- no confidential value, \
    # just a bypass switch"
    if not _daemon_enabled():
        _log.info("daemon_proxy: daemon disabled, bypassing daemon lease")
        return Err(ProxyReason.Disabled)

    ensure_daemon(root)
    try:
        conn = _LeaseConnection(root)
    except OSError as exc:
        _log.info("daemon_proxy: lease connect failed for %s: %s", root, exc)
        return Err(ProxyReason.Unreachable)

    try:
        response = conn.call(
            "frob_lease_acquire",
            {"resource": resource, "capacity": capacity, "timeout_s": timeout_s},
        )
    except OSError as exc:
        conn.close()
        _log.info("daemon_proxy: lease acquire failed for %s: %s", root, exc)
        return Err(ProxyReason.Unreachable)

    if "error" in response:
        conn.close()
        _log.info("daemon_proxy: lease acquire remote error: %s", response["error"])
        return Err(ProxyReason.RemoteError)
    if not response.get("result", {}).get("acquired"):
        conn.close()
        _log.info("daemon_proxy: lease acquire timed out for resource=%s", resource)
        return Err(ProxyReason.Unreachable)

    _log.info("daemon_proxy: lease acquired for resource=%s", resource)
    return Ok(conn)


# frob:doc docs/modules/testing.md#t-1126-daemon-owned-coverage-lease-frob_lease_acquirefrob_lease_release  # noqa: E501
# frob:tests tests/test_coverage_wait_shared.py::TestWorktreeLock.test_uses_daemon_lease_when_daemon_up kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease.test_round_trip_acquire_call_release_close kind="unit"  # noqa: E501
# frob:tests tests/unit/test_daemon_proxy_error_paths_t1457.py::TestReleaseDaemonLease.test_call_oserror_is_swallowed_and_connection_still_closed  # noqa: E501
def release_daemon_lease(conn: _LeaseConnection, resource: str) -> None:
    """Explicitly free `resource` on `conn` (best-effort: a failure here
    is harmless -- `conn.close()`, always called right after by the
    caller, triggers the same connection-liveness release T-1097's
    server-side `finally` block guarantees), then close the connection."""
    try:
        conn.call("frob_lease_release", {"resource": resource})
    except OSError as exc:
        _log.info("daemon_proxy: explicit lease release failed (harmless): %s", exc)
    conn.close()


__all__ = [
    "ProxyReason",
    "ensure_daemon",
    "query",
    "release_daemon_lease",
    "try_daemon_lease",
]
