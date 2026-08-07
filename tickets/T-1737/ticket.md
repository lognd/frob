---
id: T-1737
title: Wire frob.serve._watch.WatchThread on_change to the T-1688 CoalescingWorker.notify()
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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