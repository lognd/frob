## Done report

Extended the T-1092 socket daemon protocol with a `subscribe` verb
(`frob.serve._events`, T-1096, child (e) of T-0321, this epic's named
"stall-killer"): a client sends `{"method": "subscribe"}` over its
connection and then blocks reading newline-delimited push frames --
`graph-changed` or `coverage-fresh` -- as soon as the daemon's own state
changes, replacing the poll-your-own-schedule pattern `frob_daemon_status`
(T-0733) still requires.

Two event sources, both background threads `run_socket_daemon` now starts
alongside the existing idle-monitor and T-1094's `WatchThread`:

- `graph-changed`: T-1094's `WatchThread.on_change` callback, now wired to
  `server.event_bus.publish("graph-changed")`.
- `coverage-fresh`: a new `CoverageWatcher` that polls
  `.frob/coverage-stamp`'s mtime (1s default) and publishes the moment it
  changes -- deliberately source-agnostic (imports nothing from
  `frob.testing`, does not care whether `run_coverage_wait`'s single-
  flight, a bare `make coverage`, or a future cross-worktree cache write
  (T-1095, not yet landed) produced the fresh stamp).

Connection handling: `_RequestHandler._handle_subscribe` registers the
connection with a per-daemon-process `_EventBus` and starts a dedicated
per-connection pump thread that blocks on the subscriber's queue and
writes each frame out; a `threading.Lock` serializes writes between that
pump thread and the main `handle()` loop (still serving ordinary request/
response pairs on the same connection) so the two never interleave a
partial JSON line. `unsubscribe` pushes a `None` sentinel so the pump
thread wakes and exits promptly on disconnect (`handle()`'s `finally`
always unsubscribes).

Client helper: `subscribe_and_wait(root, event, timeout_s=...)` connects,
subscribes, and blocks until a matching event or timeout, returning
`Err(DaemonError.Timeout)` or `Err(DaemonError.Unreachable)` on failure --
the shape an agent that today backgrounds `make coverage` and stalls
(agent-playbook.md 6b/3b) uses instead: one blocking foreground call that
resolves the moment ANY caller's coverage run finishes, not just its own.

**Staleness/correctness contract, unchanged**: an event frame is a wake-up
signal, never a data channel -- both event kinds carry an empty `data`
payload today, and a client that receives one still calls
`frob_check_delta`/`frob_run_touched_tests`/`frob_daemon_status`
afterward through the exact same warm-state-backed, git-status-verified
query path every other client uses. T-0321's #1 safety invariant
(daemon-answer == cold-answer, always) is untouched by this ticket:
subscribing only replaces the "when do I bother asking" polling loop.

A real bug was caught and fixed while testing this end-to-end:
`subscribe_and_wait`'s per-read `sock.settimeout(remaining)` raises
`TimeoutError` (a `socket.timeout`/`OSError` subclass) on a normal "no
event yet" tick, and the original code's broad `except OSError` at the
call's outer scope mis-mapped that into `Err(Unreachable)` instead of
looping back to the deadline check and eventually returning
`Err(Timeout)`. Fixed by catching `TimeoutError` specifically around the
per-line `readline()` call and treating it as "keep waiting", leaving the
outer `except OSError` for genuine unreachability only -- covered by
`TestSubscribeAndWait::test_times_out_with_no_matching_event`.

### Scope note
T-1094 (landed first, same wave) already carried `src/frob/serve/_events.py`
and `tests/test_serve_events.py` forward in its own commit (both files
matched T-1094's `src/frob/serve/**` scope glob, and the two tickets were
worked in the same worktree/commit sequence) -- this Done report is the
formal record of that file's actual ownership: `_events.py`'s
`_EventBus`/`CoverageWatcher`/`subscribe_and_wait` and the subscribe-
protocol additions to `_socketd.py` (`DaemonError.Timeout`,
`_RequestHandler._handle_subscribe`/`_pump_events`/`_write_line`,
`_DaemonServer.event_bus`) are T-1096's deliverable. This land's own diff
against main is therefore small (an `ARCH001` line-count waiver fix plus
the ticket ledger transition) since the substantive code already landed
with T-1094; the "Changed" symrefs below name the files this ticket's
Done report is responsible for regardless of which commit physically
introduced them.

Filed T-1107 for a pre-existing, out-of-scope INV006 gate
finding in `src/frob/tickets/_new_renumber.py` (T-1103 residue, confirmed
present on plain `main` independent of this change) discovered while
running `frob check --ticket T-1096`.

### Changed
```
 src/frob/serve/_events.py |   8 ++++
 tickets.md                | 111 ++++++++++++++++++++++++++++++++++++++++++++--
 2 files changed, 116 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_serve_events.py::TestEventBus::test_publish_reaches_all_subscribers` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestEventBus::test_publish_before_any_subscriber_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestEventBus::test_unsubscribe_wakes_blocked_consumer` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_no_daemon_is_unreachable` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_receives_graph_changed_after_edit` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_receives_coverage_fresh_on_stamp_write` (pytest node id, verified passing when recorded)
- `tests/test_serve_events.py::TestSubscribeAndWait::test_times_out_with_no_matching_event` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 755 warning(s), 426 waived
- error-findings: INV006@src/frob/tickets/_new_renumber.py, TICK006@tickets.md
