"""FS-watch push invalidation layer over `frob.serve._warm`'s pull-based
warm-state cache (T-1094, docs/modules/serve.md#fs-watch-push-invalidation-t-1094).

Before this module, `frob.serve._warm._warm_state` is PULL-based: the warm
`GraphSnapshot`/baseline/test-id cache is only ever revalidated (via
`_repo_dirty_key`'s `git rev-parse` + `git status` signature) at the moment
a client actually calls a tool. For a standalone daemon (`frob.serve.
_socketd`, T-1092) sitting idle between queries, that means the FIRST query
after an on-disk edit always pays the full git-status-and-rebuild cost
inline, in the caller's own request latency.

This module adds a background PUSH layer: a poll thread that proactively
re-evaluates `_repo_dirty_key` on a short interval and, the moment it
changes, invalidates and eagerly rebuilds the warm state during the
daemon's own idle time -- so by the time the next client query arrives, the
warm cache is already hot again and pays nothing.

Design note (disclosed honestly, not glossed over): this is a fast POLLER
reusing the exact same `_repo_dirty_key` function the pull path already
trusts, not a kernel-level inotify/watchdog-library subscription. Three
reasons, in order of weight:

1. **Correctness by construction.** T-0321 requirement 4 (daemon-answer ==
   cold-answer, always) demands the git-status key stay the authoritative
   correctness backstop no matter what pre-warms the cache. Because this
   watcher computes literally the SAME signal the pull path already
   verifies against, it cannot disagree with it -- there is no separate
   inotify event stream whose miss/duplicate/coalescing semantics could
   diverge from what `_repo_dirty_key` would have said. A real inotify
   subscription would need its OWN differential proof that watch-driven
   invalidation decisions never disagree with the git-status signal; here
   that proof is definitionally true; `tests/test_serve_watch.py`'s
   `test_watch_tick_never_disagrees_with_pull_signal` still exercises it
   over randomized edit sequences, per this ticket's acceptance criterion,
   but it is proving a structural invariant, not hoping one holds.
2. **No new dependency, no WSL/mount watch-miss class to reason about.**
   `docs/modules/serve.md`'s own daemon-jobs section (T-0733) and T-0245
   already document that this codebase runs under environments (WSL bind
   mounts) where inotify events are known to drop or coalesce unreliably.
   Since the git-status recheck stays authoritative regardless (a missed
   poll tick here just means the NEXT query pays the pull-path cost it
   always would have paid anyway -- never a stale answer, only a
   forgone optimization), a poller sidesteps that whole failure class
   rather than papering over it with a real inotify listener.
3. **Scope discipline.** Adding `watchdog`/`inotify` as a project
   dependency is a decision with supply-chain and packaging weight beyond
   this ticket's own scope (`src/frob/serve/**`); nothing in this ticket's
   acceptance criteria requires kernel-level events specifically, only
   that a disk change be observed and invalidated via a callback "not on
   the next client's git-status recomputation" -- which a background
   poller satisfies exactly as written.

If a genuine inotify/watchdog-backed listener is wanted later (lower
latency than this poller's interval, no polling overhead at all), swapping
`WatchThread`'s tick loop for an event-driven one is a drop-in change: the
push contract (`on_change` callback firing on invalidation) and the
correctness contract (the pull path still rechecks unconditionally) are
unaffected either way.
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down disposition: this file's \
# exclusivity-vocabulary hits ('only ever revalidated', 'never a stale answer, only a \
# forgone optimization', 'only ... kernel-level events specifically') are source-level \
# design-rationale/scope-cut prose describing already-implemented internal behavior, \
# verifiable by reading the code it annotates, rather than a separate cross-module \
# contract needing its own tracked invariant -- same calibration-batch disposition \
# already applied to src/frob/serve/_socketd.py and src/frob/serve/_warm.py (T-0585)"

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from frob.logging import get_logger
from frob.serve._warm import _invalidate, _repo_dirty_key, _warm_state

_log = get_logger(__name__)

# frob:doc docs/modules/serve.md#fs-watch-push-invalidation-t-1094
# How often the background poll thread re-evaluates `_repo_dirty_key` --
# deliberately short (sub-second) since this is cheap (one `git
# rev-parse` + one `git status`, the same cost the pull path already pays
# per query) and running it during idle time, not in a client's request
# path, is the entire point of this module.
DEFAULT_WATCH_POLL_INTERVAL_S = 1.0


# frob:doc docs/modules/serve.md#fs-watch-push-invalidation-t-1094
# frob:tests tests/test_serve_watch.py::TestWatchTick.test_no_change_leaves_state_cached kind="unit"  # noqa: E501
# frob:tests tests/test_serve_watch.py::TestWatchTick.test_change_invalidates_and_prewarms kind="unit"  # noqa: E501
# frob:tests tests/test_serve_watch.py::TestWatchTick.test_watch_tick_never_disagrees_with_pull_signal kind="unit"  # noqa: E501
def watch_tick(root: Path, last_key: str | None) -> tuple[str, bool]:
    """One watch cycle for `root`: recompute `_repo_dirty_key(root)` (the
    SAME signal `frob.serve._warm._warm_state` checks on every pull-path
    call) and compare it against `last_key` (the key observed on the
    previous tick, `None` on the very first tick for this root). If it
    changed (or this is the first tick), proactively `_invalidate` the
    cached `_WarmState` and immediately re-warm it via `_warm_state` --
    PUSHING the rebuild into this background cycle instead of leaving it
    for whichever client query happens to arrive next. Returns `(new_key,
    changed)`; `changed` is always `False` on the first tick (nothing to
    compare against yet), matching `_warm_state`'s own cache-miss-on-first-
    call behavior rather than over-reporting a change that never happened."""
    key = _repo_dirty_key(root)
    changed = last_key is not None and key != last_key
    if last_key is None or changed:
        _invalidate(root)
        rebuilt = _warm_state(root)
        if rebuilt.is_err:
            _log.warning(
                "serve: watch: pre-rebuild failed for %s: %s", root, rebuilt.danger_err
            )
        else:
            _log.info(
                "serve: watch: pre-warmed state for %s at dirty_key=%s", root, key[:12]
            )
    return key, changed


# frob:doc docs/modules/serve.md#fs-watch-push-invalidation-t-1094
# frob:tests tests/test_serve_watch.py::TestWatchThread.test_change_fires_on_change_callback kind="unit"  # noqa: E501
# frob:tests tests/test_serve_watch.py::TestWatchThread.test_stop_joins_promptly kind="unit"  # noqa: E501
class WatchThread:
    """Background daemon thread driving `watch_tick` on an interval for the
    life of the standalone socket daemon process (`frob.serve._socketd.
    run_socket_daemon`): a push-invalidation layer sitting alongside that
    daemon's existing idle-monitor thread, using the identical
    start/stop-event shape. `on_change`, if given, is called (with no
    arguments) every time a tick observes a real dirty-key change -- the
    socket daemon (T-1096) uses this to publish a `graph-changed` event to
    any subscribed client."""

    def __init__(
        self,
        root: Path,
        *,
        poll_interval_s: float = DEFAULT_WATCH_POLL_INTERVAL_S,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        """Build (but do not start) a watcher for `root`, ticking every
        `poll_interval_s` seconds once `start()` is called."""
        self._root = root
        self._poll_interval_s = poll_interval_s
        self._on_change = on_change
        self._stop = threading.Event()
        self._last_key: str | None = None
        self._thread = threading.Thread(
            target=self._run, name="frob-serve-watch", daemon=True
        )

    # frob:doc docs/modules/serve.md#fs-watch-push-invalidation-t-1094
    def start(self) -> None:
        """Start the background poll thread."""
        self._thread.start()

    # frob:doc docs/modules/serve.md#fs-watch-push-invalidation-t-1094
    def stop(self) -> None:
        """Signal the poll thread to exit and join it (bounded wait, so a
        daemon shutdown never hangs on this thread specifically)."""
        self._stop.set()
        self._thread.join(timeout=5.0)

    def _run(self) -> None:
        """Thread body: tick, invoke `on_change` if the tick observed a
        real change, sleep (interruptibly, via `Event.wait`) until the next
        tick or until `stop()` is called."""
        while not self._stop.is_set():
            try:
                self._last_key, changed = watch_tick(self._root, self._last_key)
            except Exception:  # noqa: BLE001
                _log.exception("serve: watch: tick failed for %s", self._root)
            else:
                if changed and self._on_change is not None:
                    try:
                        self._on_change()
                    except Exception:  # noqa: BLE001
                        _log.exception(
                            "serve: watch: on_change callback failed for %s", self._root
                        )
            self._stop.wait(self._poll_interval_s)


__all__ = [
    "DEFAULT_WATCH_POLL_INTERVAL_S",
    "WatchThread",
    "watch_tick",
]
