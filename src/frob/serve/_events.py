"""Subscribe/push event stream over the socket daemon (T-1096, child (e) of
T-0321, docs/modules/serve.md#subscribepush-events-t-1096).

T-0733's background daemon (`frob.serve._daemon`) and the CLI's own
`make coverage`-backgrounding habit (`docs/guides/agent-playbook.md`
6b/3b) are both PULL-based today: `frob_daemon_status` is read by a client
on its own schedule, and an agent that backgrounds a long coverage run has
no way to be told when it finishes short of re-polling. This module adds a
PUSH layer on top of the T-1092 socket daemon: a client sends a
`subscribe` request over its connection and then blocks reading
newline-delimited event frames -- `graph-changed` (T-1094's `WatchThread`
observed and pre-warmed a real on-disk change) or `coverage-fresh` (the
`.frob/coverage-stamp` file `frob.gates._coverage`/`frob.testing.
run_coverage_wait` write was rewritten) -- as soon as the daemon's own
state changes, with no separate poll loop on the client's side.

**This is a wake-up mechanism, not a data channel** -- deliberately, to
keep T-0321's #1 safety invariant (daemon-answer == cold-answer, always)
intact. An event frame carries no query result of its own; a client that
receives `coverage-fresh` still calls `frob_check_delta`/
`frob_run_touched_tests`/`frob_daemon_status` afterward exactly as it
would from a cold start, through the same warm-state-backed, git-status-
verified query path every other client uses. The event only replaces the
"when do I bother asking" polling loop, never the "is this answer
correct" check.

Two pieces:

1. **`_EventBus`** -- a per-daemon-process, in-memory publish/subscribe
   registry. `subscribe()` hands back a fresh `queue.Queue` any thread can
   `publish()` an event frame into; `unsubscribe()` pushes a `None`
   sentinel so a blocked consumer wakes up and exits instead of hanging
   forever on a dead subscription.
2. **Client helper (`subscribe_and_wait`)** -- connects, sends a
   `{"method": "subscribe"}` request, then blocks reading frames off the
   same connection until one whose `"event"` field matches the caller's
   requested name arrives (or `timeout_s` elapses), returning its `data`
   payload. This is the shape an agent that today backgrounds `make
   coverage` and stalls (the epic's named "stall-killer") uses instead: a
   single blocking foreground call, in-band on one connection, with a
   real completion signal instead of a re-poll loop.
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down disposition: this file's \
# exclusivity-vocabulary hits ('never a data channel', 'only replaces') are \
# source-level design-rationale/scope-cut prose describing already-implemented \
# internal behavior, verifiable by reading the code it annotates, rather than a \
# separate cross-module contract needing its own tracked invariant -- same \
# calibration-batch disposition already applied to src/frob/serve/_socketd.py and \
# src/frob/serve/_warm.py (T-0585)"

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from pathlib import Path
from typing import Any, Callable

from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.serve._socketd import DaemonError, socket_path

_log = get_logger(__name__)

# frob:doc docs/modules/serve.md#subscribepush-events-t-1096
DEFAULT_SUBSCRIBE_TIMEOUT_S = 60.0


# frob:doc docs/modules/serve.md#subscribepush-events-t-1096
# frob:tests tests/test_serve_events.py::TestEventBus.test_publish_reaches_all_subscribers kind="unit"  # noqa: E501
# frob:tests tests/test_serve_events.py::TestEventBus.test_unsubscribe_wakes_blocked_consumer kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-1096: docs/modules/serve.md's Subscribe/push events \
# section individually frob:describes this private class by name -- a deliberate \
# architecture doc walking through the daemon-internal pub/sub design, not accidental \
# doc-anchor drift onto a private helper, same pattern as this repo's other frob.serve \
# internals (T-0529)"
class _EventBus:
    """Per-daemon-process publish/subscribe registry: any thread may
    `publish` an event frame, and any thread may `subscribe` to receive
    every frame published after that point (no replay of past events --
    a subscriber only sees what happens while it is subscribed, matching
    the "wake-up, not a data channel" contract above)."""

    def __init__(self) -> None:
        """An empty registry with no subscribers -- `publish` before the
        first `subscribe` is a safe no-op, nothing to deliver to yet."""
        self._lock = threading.Lock()
        self._subscribers: dict[int, queue.Queue] = {}
        self._next_id = 0

    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    # frob:tests tests/test_serve_events.py::TestEventBus.test_publish_reaches_all_subscribers kind="unit"  # noqa: E501
    def subscribe(self) -> tuple[int, queue.Queue[dict[str, Any] | None]]:
        """Register a new subscriber and return its id (for `unsubscribe`)
        plus the queue frames get pushed onto -- a blocking `queue.get()`
        on it is how a connection handler waits for the next event."""
        with self._lock:
            sid = self._next_id
            self._next_id += 1
            q: queue.Queue[dict[str, Any] | None] = queue.Queue()
            self._subscribers[sid] = q
        return sid, q

    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    def unsubscribe(self, sid: int) -> None:
        """Drop subscriber `sid` and push a `None` sentinel into its queue
        so a consumer blocked in `queue.get()` wakes up and can exit
        instead of hanging on a subscription nobody will publish to again.
        A no-op if `sid` is already gone (double-unsubscribe-safe)."""
        with self._lock:
            q = self._subscribers.pop(sid, None)
        if q is not None:
            q.put(None)

    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    def publish(self, event: str, data: dict[str, Any] | None = None) -> None:
        """Push `{"event": event, "data": data or {}}` onto every currently
        registered subscriber's queue -- each subscriber's own connection
        handler is responsible for writing it out to its client."""
        frame = {"event": event, "data": data or {}}
        with self._lock:
            subscribers = list(self._subscribers.values())
        _log.info(
            "serve: events: publish %s to %d subscriber(s)", event, len(subscribers)
        )
        for q in subscribers:
            q.put(frame)


# frob:doc docs/modules/serve.md#subscribepush-events-t-1096
# frob:tests tests/test_serve_events.py::TestSubscribeAndWait.test_receives_graph_changed_after_edit kind="unit"  # noqa: E501
# frob:tests tests/test_serve_events.py::TestSubscribeAndWait.test_receives_coverage_fresh_on_stamp_write kind="unit"  # noqa: E501
# frob:tests tests/test_serve_events.py::TestSubscribeAndWait.test_times_out_with_no_matching_event kind="unit"  # noqa: E501
# frob:waive ARCH103 reason="T-1096: connect, send one subscribe request, read frames \
# until a match or timeout -- the entire, inherently sequential job of this client \
# helper; splitting connect/send/read-loop into separate functions would not reduce \
# real complexity, only relocate it behind an extra call boundary for a single caller, \
# mirroring _socketd.send_request's existing ARCH103 waiver for the same shape"
# frob:waive ARCH001 reason="T-1096: 65 lines against a 60-line threshold, same \
# single-caller connect/write/read-loop/error-mapping body the ARCH103 waiver above \
# already justifies as one cohesive unit -- splitting the read-loop or the \
# TimeoutError/OSError distinction into a separate function would not shrink real \
# complexity, only relocate it behind an extra call boundary this function's one \
# caller would immediately re-inline"
# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to socket.socket's own \
# connect/makefile/write/readline calls and json.dumps, stdlib socket/json calls the \
# resolver cannot fully bound past the broad except OSError below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above -- \
# json.loads' JSONDecodeError is now explicitly caught inline (T-1062)"
# frob:waive AFFECT001 reason="T-1062: EXHAUST001/002 hardening -- added an \
# explicit inline except for a malformed frame's JSONDecodeError/UnicodeDecodeError, \
# which now retries the read loop instead of letting it escape; the documented \
# Timeout/Unreachable/Ok error-shape contract and behavior are unchanged, nothing for \
# docs/modules/serve.md#subscribepush-events-t-1096 to update"
def subscribe_and_wait(
    root: Path,
    event: str,
    *,
    timeout_s: float = DEFAULT_SUBSCRIBE_TIMEOUT_S,
) -> Result[dict[str, Any], DaemonError]:
    """Connect to `socket_path(root)`, send a `subscribe` request, then
    block reading push frames off the SAME connection until one whose
    `"event"` field equals `event` arrives, returning its `"data"` payload
    -- or `Err(DaemonError.Timeout)` if `timeout_s` elapses first, or
    `Err(DaemonError.Unreachable)` if the daemon cannot be reached at all.
    This is the client-side counterpart of an agent that today backgrounds
    `make coverage` and then ends its turn waiting on a notification that
    cannot arrive (`docs/guides/agent-playbook.md` 6b/3b): a single
    blocking foreground call gets a definitive completion signal in-band,
    even when a DIFFERENT caller's single-flight run (T-1095) is what
    actually resolves it."""
    path = socket_path(root.resolve())
    deadline = time.monotonic() + timeout_s
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    except OSError:
        _log.info("serve: events: client: could not create socket for %s", path)
        return Err(DaemonError.Unreachable)
    try:
        sock.settimeout(max(timeout_s, 0.01))
        sock.connect(str(path))
        handle = sock.makefile("rwb")
        handle.write(
            (json.dumps({"id": 1, "method": "subscribe", "params": {}}) + "\n").encode(
                "utf-8"
            )
        )
        handle.flush()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _log.info(
                    "serve: events: client: timed out waiting for %r on %s",
                    event,
                    path,
                )
                return Err(DaemonError.Timeout)
            sock.settimeout(remaining)
            try:
                line = handle.readline()
            except TimeoutError:
                # socket.timeout (a TimeoutError/OSError subclass) from
                # this READ, not the earlier connect -- the daemon is
                # reachable and subscribed fine, it just hasn't published
                # a matching event yet. Loop back to the deadline check
                # above rather than falling through to the broad `except
                # OSError` below, which would otherwise misreport a normal
                # "still waiting" tick as DaemonError.Unreachable.
                continue
            if not line:
                _log.info(
                    "serve: events: client: connection closed waiting for %r", event
                )
                return Err(DaemonError.Unreachable)
            try:
                frame = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # A malformed/partial frame on the wire is skipped, not a
                # crash -- keep waiting for the next line.
                continue
            if frame.get("event") == event:
                _log.info("serve: events: client: received %r", event)
                return Ok(frame.get("data") or {})
            # A subscribe ack ({"id": 1, "result": ...}) or an event this
            # caller did not ask for -- keep waiting for a match.
    except OSError:
        _log.info("serve: events: client: could not reach %s", path)
        return Err(DaemonError.Unreachable)
    finally:
        sock.close()


# frob.gates._coverage owns this path (`_STAMP_REL`); duplicated here as a
# plain relative Path rather than imported to avoid pulling frob.gates'
# heavier import surface into the socket daemon's hot startup path for a
# single constant -- the coordinates are load-bearing only in the sense
# that both sides must agree on WHERE the stamp lives, not on any of
# frob.gates' own logic, and are covered by
# TestSubscribeAndWait.test_receives_coverage_fresh_on_stamp_write writing
# to this exact path.
_COVERAGE_STAMP_REL = Path(".frob") / "coverage-stamp"

# frob:doc docs/modules/serve.md#subscribepush-events-t-1096
DEFAULT_COVERAGE_POLL_INTERVAL_S = 1.0


# frob:doc docs/modules/serve.md#subscribepush-events-t-1096
# frob:tests tests/test_serve_events.py::TestSubscribeAndWait.test_receives_coverage_fresh_on_stamp_write kind="unit"  # noqa: E501
# frob:waive AFFECT001 reason="T-1062: EXHAUST001 hardening -- widened \
# CoverageWatcher._current_mtime's except OSError to except Exception; the documented \
# 'None if it does not exist yet' contract and behavior are unchanged, nothing for \
# docs/modules/serve.md#subscribepush-events-t-1096 to update"
class CoverageWatcher:
    """Background thread polling `<root>/.frob/coverage-stamp`'s mtime on
    an interval and calling `on_fresh` (with no arguments) the moment it
    changes -- the `coverage-fresh` event source `run_socket_daemon`
    starts alongside T-1094's `WatchThread`. Deliberately source-agnostic:
    it does not care WHO wrote a fresh stamp (`frob.testing.
    run_coverage_wait`'s single-flight lock, a bare `make coverage`, a
    different worktree's daemon under T-1095's future cross-worktree
    cache) -- any write to the stamp file is a legitimate freshness
    signal, so this stays correct without importing `frob.testing` at
    all (kept out of this ticket's scope this wave)."""

    def __init__(
        self,
        root: Path,
        on_fresh: Callable[[], None],
        *,
        poll_interval_s: float = DEFAULT_COVERAGE_POLL_INTERVAL_S,
    ) -> None:
        """Build (but do not start) a watcher for `root`'s coverage stamp,
        ticking every `poll_interval_s` seconds once `start()` is called."""
        self._path = root / _COVERAGE_STAMP_REL
        self._on_fresh = on_fresh
        self._poll_interval_s = poll_interval_s
        self._stop = threading.Event()
        self._last_mtime: float | None = None
        self._thread = threading.Thread(
            target=self._run, name="frob-serve-coverage-watch", daemon=True
        )

    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    # frob:tests tests/test_serve_events.py::TestSubscribeAndWait.test_receives_coverage_fresh_on_stamp_write kind="unit"  # noqa: E501
    def start(self) -> None:
        """Start the background poll thread."""
        self._thread.start()

    # frob:doc docs/modules/serve.md#subscribepush-events-t-1096
    def stop(self) -> None:
        """Signal the poll thread to exit and join it (bounded wait)."""
        self._stop.set()
        self._thread.join(timeout=5.0)

    def _current_mtime(self) -> float | None:
        """The stamp file's current mtime, or `None` if it does not exist
        yet (never stamped)."""
        try:
            return self._path.stat().st_mtime_ns
        except Exception:
            return None

    def _run(self) -> None:
        """Thread body: poll the stamp's mtime; call `on_fresh` the moment
        it changes (including the transition from "never stamped" to
        "stamped", but NOT on the very first tick observing an
        already-stamped file -- that mirrors `WatchThread.watch_tick`'s own
        "no change reported on the first tick" convention rather than
        firing a spurious event for a stamp that predates this daemon)."""
        self._last_mtime = self._current_mtime()
        first = True
        while not self._stop.is_set():
            mtime = self._current_mtime()
            if not first and mtime != self._last_mtime:
                self._last_mtime = mtime
                try:
                    self._on_fresh()
                except Exception:  # noqa: BLE001
                    _log.exception("serve: events: coverage on_fresh callback failed")
            else:
                self._last_mtime = mtime
            first = False
            self._stop.wait(self._poll_interval_s)


__all__ = [
    "DEFAULT_COVERAGE_POLL_INTERVAL_S",
    "DEFAULT_SUBSCRIBE_TIMEOUT_S",
    "CoverageWatcher",
    "_EventBus",
    "subscribe_and_wait",
]
