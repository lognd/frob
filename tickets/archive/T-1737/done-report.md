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
