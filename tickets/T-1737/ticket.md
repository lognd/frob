---
id: T-1737
title: Wire frob.serve._watch.WatchThread on_change to the T-1688 CoalescingWorker.notify()
state: done
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/serve/_socketd.py
- src/frob/serve/_daemon.py
- tests/test_serve_socket.py
- tests/test_serve_daemon.py
- docs/modules/serve.md
- docs/modules/tickets.md
- tickets/T-1737/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/serve/_daemon.py
  reason: the DISCLOSED SCOPE CUT note in _poll_verify_worker's docstring documents
    exactly the gap this ticket closes; must be updated/removed now that the wiring
    exists
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_serve_socket.py
  reason: test coverage for run_socket_daemon's watcher wiring and _poll_verify_worker's
    docstring/behavior
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_serve_daemon.py
  reason: test coverage for run_socket_daemon's watcher wiring and _poll_verify_worker's
    docstring/behavior
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/serve.md
  reason: 'AFFECT001: doc anchors for _poll_verify_worker/run_socket_daemon must reflect
    the new FS-watch->notify() wiring; tickets/T-1737/** for the ticket''s own per-ticket
    ledger file per T-1742''s precedent'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: doc anchors for _poll_verify_worker/run_socket_daemon must reflect
    the new FS-watch->notify() wiring; tickets/T-1737/** for the ticket''s own per-ticket
    ledger file per T-1742''s precedent'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1737/**
  reason: 'AFFECT001: doc anchors for _poll_verify_worker/run_socket_daemon must reflect
    the new FS-watch->notify() wiring; tickets/T-1737/** for the ticket''s own per-ticket
    ledger file per T-1742''s precedent'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_serve_daemon.py::TestWatchThreadNotifiesVerifyWorker::test_fs_change_notifies_the_cached_verify_worker
designated_repro_test: null
threat: null
component: null
---
T-1688's coalescing verify worker (frob.verify._worker.CoalescingWorker)
gets its "queue append" wake proxy from src/frob/serve/_daemon.py's own
HEAD-moved polling, and its periodic floor from its own internal timer,
but the ticket's third wake condition -- the FS-watch push signal
frob.serve._watch.WatchThread already provides -- is not wired to it.
WatchThread is instantiated in frob.serve._socketd.run_socket_daemon,
outside T-1688's own src/frob/serve/_daemon.py scope.

Wire WatchThread(on_change=...) in _socketd.py to also call the
CoalescingWorker.notify() for the same root (frob.serve._daemon.
_get_verify_worker(root).notify()), so a filesystem change observed by
the poller pushes a debounce-window reset immediately instead of only
via the daemon's own ~20s HEAD-moved poll cadence.