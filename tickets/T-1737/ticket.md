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

## Done report

Wired `frob.serve._watch.WatchThread`'s FS-watch `on_change` signal
(instantiated in `run_socket_daemon`, `src/frob/serve/_socketd.py`) to
also call the T-1688 coalescing verify worker's `notify()`
(`frob.serve._daemon._get_verify_worker(root).notify()`) for the same
root, alongside the existing `graph-changed` event publish. This closes
the disclosed scope cut `_poll_verify_worker`'s own module docstring
recorded: the worker previously only woke from a `main`-HEAD-moved poll
(the "queue append" wake proxy) and its own periodic floor; a real
on-disk change observed by the watcher now resets the debounce window
immediately instead of only via the daemon's own ~20s poll cadence.

Both callbacks look the worker up through `_daemon`'s existing
`_VERIFY_WORKERS` cache (keyed by `str(root.resolve())`), so this is the
SAME cached instance `_poll_verify_worker` polls -- an earlier trigger
for the identical debounce/floor decision `tick()` already makes, not a
third independent wake condition with its own state.

Scope was declared as `src/frob/serve/_socketd.py` only; extended (with
recorded reasons in the scope_changes audit trail) to
`src/frob/serve/_daemon.py` (its `_poll_verify_worker` docstring
documented exactly the gap this ticket closes and needed updating),
`docs/modules/serve.md` and `docs/modules/tickets.md` (AFFECT001 --
both carry affects()-closure doc anchors for the two changed symbols),
`tests/test_serve_daemon.py`/`tests/test_serve_socket.py` (test
coverage), and `tickets/T-1737/**` (SCOPE001, the ticket's own
per-ticket ledger file written by ordinary `frob ticket` CLI lifecycle
commands).

New test `TestWatchThreadNotifiesVerifyWorker::
test_fs_change_notifies_the_cached_verify_worker` starts a real
`run_socket_daemon` on a background thread, writes a change to a
tracked file, and asserts the cached `CoalescingWorker`'s
`_pending_since` becomes non-None -- exercising the actual wiring
end-to-end (real `WatchThread` polling, real callback), not a
monkeypatched substitute. All pre-existing tests in
`tests/test_serve_daemon.py` and `tests/test_serve_socket.py` continue
to pass unmodified.

### Changed
```
 docs/modules/serve.md      |  9 ++++++++
 docs/modules/tickets.md    | 18 ++++++++++------
 src/frob/serve/_daemon.py  | 18 ++++++++--------
 src/frob/serve/_socketd.py | 23 ++++++++++++++++++---
 tests/test_serve_daemon.py | 46 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-1737/ticket.md   | 51 +++++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 146 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_serve_daemon.py::TestWatchThreadNotifiesVerifyWorker::test_fs_change_notifies_the_cached_verify_worker` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 991 warning(s), 732 waived
- error-findings: invalid-assignment@tests/test_ticket_land.py
