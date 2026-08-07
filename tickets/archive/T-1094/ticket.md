---
id: T-1094
title: 'daemon: FS-watch push invalidation replaces git-status-poll warm-state key'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1092
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/serve/**
- docs/modules/serve.md
- tickets.md
- tests/test_serve_watch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_serve_watch.py::TestWatchTick::test_no_change_leaves_state_cached
- tests/test_serve_watch.py::TestWatchTick::test_change_invalidates_and_prewarms
- tests/test_serve_watch.py::TestWatchTick::test_watch_tick_never_disagrees_with_pull_signal
- tests/test_serve_watch.py::TestWatchThread::test_change_fires_on_change_callback
- tests/test_serve_watch.py::TestWatchThread::test_stop_joins_promptly
designated_repro_test: null
acceptance:
- text: GIVEN the daemon is running and a source file changes on disk WHEN the change
    is saved (no frob command run) THEN the warm GraphSnapshot is invalidated and
    rebuilt via an FS-watch callback, not on the next client's git-status recomputation
  evidence:
  - tests/test_serve_watch.py::TestWatchTick::test_change_invalidates_and_prewarms
  - tests/test_serve_watch.py::TestWatchThread::test_change_fires_on_change_callback
- text: GIVEN a differential harness comparing FS-watch-driven invalidation against
    the existing _repo_dirty_key git-status signature across randomized edit sequences
    THEN the two invalidation decisions always agree (no watch-miss, no stale-serve)
  evidence:
  - tests/test_serve_watch.py::TestWatchTick::test_watch_tick_never_disagrees_with_pull_signal
threat: null
component: null
---
Child (a) of T-0321, the remaining half of T-0177's deliverable (a): src/frob/serve/_warm.py's _repo_dirty_key currently recomputes a git rev-parse+status signature PLUS a per-dirty-path (mtime_ns,size) tag on every _warm_state() call (pull-based, paid at query time) -- there is no OS-level file-watch (inotify/watchdog) anywhere in src/frob/serve/ (confirmed 2026-07-28). For a standalone daemon (T-1092) sitting idle between queries, pull-based invalidation means the FIRST query after an edit still pays the git-status walk; push-based FS-watch lets the daemon pre-invalidate/pre-rebuild during idle time so a query never pays it. Add an inotify-backed (or watchdog-library) watcher scoped to the project's tracked+untracked-but-not-.frob paths, feeding frob.serve._warm._invalidate on change. Treat this as an OPTIMIZATION LAYER over the existing git-status key, not a replacement of its correctness: T-0321 requirement 4 demands daemon-answer == cold-answer always, so the git-status key stays as the authoritative correctness check on every call and FS-watch only pre-warms; a watch-miss (missed event, e.g. under WSL/mount quirks per T-0245) must never serve stale data because the git-status recheck still runs. Add the differential harness proving the two signals never disagree on invalidation decision.