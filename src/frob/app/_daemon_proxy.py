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
6): `_socketd`'s JSON-RPC protocol carries no version field of its own (out
of THIS ticket's scope -- `src/frob/serve/**` belongs to a sibling ticket
this wave), so this module tags the daemon it spawns with a sidecar
`.frob/daemon.meta.json` `{"version", "pid"}` written at spawn time. Before
trusting a socket that already exists, `ensure_daemon` compares that
recorded version against this process's own installed `frob` version
(`importlib.metadata.version("frob")`); a mismatch means the daemon predates
(or postdates) this client's own frob install, most likely a stale daemon
left running across a `frob` upgrade -- it is SIGTERM'd and a fresh one is
spawned in its place before the query proceeds. This is an honest, disclosed
residual: a follow-on ticket giving `_socketd` its own `frob_version` RPC
method (or embedding the version in the JSON-RPC handshake itself) would let
the daemon self-report rather than relying on this sidecar file staying in
sync with whichever process last spawned it; filed as T-draft-8a56400c.

`FROB_NO_DAEMON=1` is an unconditional bypass (T-1093 acceptance [2]): with
it set, `query()` returns `Err(ProxyReason.Disabled)` immediately, before
ever touching the socket, lock, or meta file -- the differential test uses
this to produce the reference in-process answer to diff the daemon-served
one against.
"""
# frob:waive INV006 reason="T-1093: this file's exclusivity-vocabulary hit \
# ('best-effort only' in query()'s docstring) is source-level design-rationale \
# prose describing already-implemented internal behavior (verifiable by reading \
# ensure_daemon/query themselves), not a separate cross-module contract needing \
# its own tracked invariant -- same calibration-batch disposition this repo \
# already applies to src/frob/serve/_socketd.py and src/frob/serve/__init__.py \
# (T-0585/T-1023)"

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

_META_REL = Path(".frob") / "daemon.meta.json"
# How long a fresh spawn is given to bind its socket before this call gives
# up and falls back for THIS query -- kept short (this runs on the CLI's hot
# path) since the payoff is warm state on the NEXT call, not necessarily
# this one.
_SPAWN_GRACE_S = 1.5
_SPAWN_POLL_INTERVAL_S = 0.05
# frob:waive DUP001 reason="T-1093: this SIGTERM grace window mirrors \
# _SPAWN_GRACE_S's shape (a short bounded poll loop) but measures a distinct \
# thing -- an old process releasing its flock, not a new one binding a \
# socket -- and the two callers (ensure_daemon's skew path vs query's fresh- \
# spawn path) would still need two constants even if the values matched"
_KILL_GRACE_S = 1.0


# frob:doc docs/modules/serve.md#cli-daemon-proxy-t-1093
class ProxyReason(ErrorSet):
    """Why a query was NOT served by the daemon. Every value means "fall
    back to in-process, silently" -- none is a user-facing failure."""

    Disabled = "FROB_NO_DAEMON=1 bypasses the daemon unconditionally"
    Unreachable = "no live daemon socket answered for this root"
    RemoteError = "the daemon returned a JSON-RPC error for this query"


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


def _meta_path(root: Path) -> Path:
    """Sidecar file this module writes at spawn time to tag a daemon with
    the client version that spawned it -- `<root>/.frob/daemon.meta.json`."""
    return root / _META_REL


def _read_meta(root: Path) -> dict[str, Any] | None:
    """The last-spawned daemon's recorded `{"version", "pid"}`, or `None` if
    no daemon has ever been spawned for `root` by this module (a missing or
    malformed file is treated as "nothing recorded", not an error)."""
    try:
        return json.loads(_meta_path(root).read_text())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _write_meta(root: Path, pid: int) -> None:
    """Record the spawning client's version + the daemon's pid, for the
    next caller's version-skew check."""
    path = _meta_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": _client_version(), "pid": pid}))


def _spawn_daemon(root: Path) -> None:
    """Best-effort, fire-and-forget spawn of the T-1092 socket daemon
    (`frob.serve.run_socket_daemon`) as a detached subprocess of the
    CURRENTLY RUNNING interpreter (`sys.executable`, so it inherits this
    exact `frob` install rather than whatever a bare `frob` on PATH would
    resolve to), tagged with this process's version via `_write_meta`.
    Never raises: a spawn failure just means the next query stays
    `Unreachable` and falls back in-process, same as any other daemon-down
    case."""
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
    _write_meta(root, proc.pid)
    _log.info(
        "daemon_proxy: spawned daemon pid=%d for %s (version=%s)",
        proc.pid,
        root,
        _client_version(),
    )


def _kill_stale_daemon(root: Path, meta: dict[str, Any]) -> None:
    """SIGTERM the daemon `meta` describes and wait (briefly, bounded by
    `_KILL_GRACE_S`) for its pid to disappear, so a follow-up spawn does not
    race it for the still-held `flock`. A pid that is already gone
    (`ProcessLookupError`) or that outlives the grace window is not an
    error here -- either way the caller proceeds to spawn a replacement;
    `acquire_singleton_lock` is what actually guarantees exclusivity."""
    pid = meta.get("pid")
    if not isinstance(pid, int):
        return
    try:
        os.kill(pid, 15)  # SIGTERM
        _log.info(
            "daemon_proxy: version skew, SIGTERM stale daemon pid=%d "
            "(spawned by version=%s) for %s",
            pid,
            meta.get("version"),
            root,
        )
    except ProcessLookupError:
        _log.info("daemon_proxy: stale daemon pid=%d already gone for %s", pid, root)
        return
    except OSError as exc:
        _log.info("daemon_proxy: could not signal stale daemon pid=%d: %s", pid, exc)
        return
    deadline = time.monotonic() + _KILL_GRACE_S
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(_SPAWN_POLL_INTERVAL_S)


# frob:doc docs/modules/serve.md#cli-daemon-proxy-t-1093
# frob:tests tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_spawns_when_nothing_recorded kind="unit"  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_restarts_on_version_skew kind="unit"  # noqa: E501
# frob:tests tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_noop_when_version_matches kind="unit"  # noqa: E501
def ensure_daemon(root: Path) -> None:
    """Ensure a live, version-matched daemon is running (or freshly
    starting) for `root`, self-healing a version-skewed one first (T-1093
    acceptance [1]). Best-effort only and never raises: a caller that
    cannot get a daemon up simply finds no socket to connect to on the next
    `query()` call and falls back in-process, same as any other
    `Unreachable` case."""
    meta = _read_meta(root)
    if meta is not None and meta.get("version") != _client_version():
        _log.info(
            "daemon_proxy: version skew detected (daemon=%s, client=%s) for %s",
            meta.get("version"),
            _client_version(),
            root,
        )
        _kill_stale_daemon(root, meta)
        meta = None
    if meta is None:
        _spawn_daemon(root)


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
    # frob:waive SEC110 reason="T-1093: FROB_NO_DAEMON is a boolean opt-out flag \
    # (matches the existing FROB_AGENT/FROB_WORKTREE precedent in \
    # frob.tickets._leases), carries no confidential value"
    if os.environ.get("FROB_NO_DAEMON") == "1":
        _log.info("daemon_proxy: FROB_NO_DAEMON=1, bypassing daemon for %s", method)
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


__all__ = ["ProxyReason", "ensure_daemon", "query"]
