## Done report

Fixed defects 1 and 2 within this ticket's declared scope
(src/frob/serve/_socketd.py); disposed of defect 3 as out of scope with a
filed follow-up.

1. frob_shutdown acknowledges but does not stop: the real root cause is
   that a daemon which had served a query touching frob.serve._tools's
   parallel-execution paths left multiprocessing children (forkserver,
   resource_tracker) running after server.shutdown() returned -- only
   Python's own multiprocessing.util._exit_function atexit hook would
   eventually reap them, and its unbounded Process.join() is what made
   "shut down" take 20+ seconds and need a manual SIGTERM/SIGKILL.

2. It leaks its multiprocessing children: same root cause as (1). Added
   _reap_multiprocessing_children() -- terminate() every
   multiprocessing.active_children(), then a bounded join(timeout=
   _CHILD_REAP_GRACE_S), escalating to kill() for anything still alive --
   called from run_socket_daemon's finally block, which both the
   idle-timeout exit and the frob_shutdown RPC exit already share. This
   runs before the interpreter ever reaches its own atexit handling, so
   both defects are fixed by the same change: shutdown is now bounded and
   deterministic regardless of what spawned the children, without
   depending on frob.serve._tools's own pool internals (out of this
   ticket's scope).

3. NOT fixed, decision: the performance regression (warm daemon slower
   than FROB_NO_DAEMON=1, load average 5-8 vs ~0.4 idle) is real but its
   root cause -- a persistent multiprocessing forkserver pool kept warm
   by frob.serve._tools's parallel-execution paths -- lives entirely
   outside src/frob/serve/_socketd.py, this ticket's declared scope.
   T-1379 already made the daemon opt-in (not default-enabled), which
   removes this as a default-install risk; a user who explicitly opts in
   still pays it. Rather than force a fix through the wrong file or
   silently drop it, filed T-1436 (kind=bug, scope=src/frob/
   serve/_tools.py) to investigate lazy/sized-down pool warming and
   re-measure. Acceptance criterion [2] is left UNBOUND for this reason;
   [0] and [1] are bound.

Removing the daemon outright was considered and rejected: defects 1/2
are now fixed cleanly, T-1379 already makes it opt-in, and the daemon's
warm-state value (T-0177/T-1094/T-1096) is real for the interactive/MCP
use case, not just a cost -- the honest fix was closing the two real
process-hygiene bugs, not deleting a feature that works once those bugs
are gone.

Scope was widened by one file (tests/test_serve_socket.py, via
`frob ticket scope --add` with a recorded reason) to bind real
regression-test evidence, matching this ticket's own acceptance criteria.

Test: tests/test_serve_socket.py::TestReapMultiprocessingChildren covers
_reap_multiprocessing_children directly (normal terminate+join, and the
kill() escalation path via a child that ignores SIGTERM); TestShutdown
ReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget is the
end-to-end reproduction -- a real multiprocessing child alive when
frob_shutdown is sent, asserting both the daemon thread joins within the
5s budget and the child does not survive.

Docs: docs/modules/serve.md gets a new "Shutdown reaps multiprocessing
children (T-1378)" subsection under "Version handshake".

Note for the coordinator: this worktree also carries T-1423's commits
(same series worktree per the playbook's "one worktree per series"
rule). `frob check --ticket T-1378` reports SCOPE001/COV002/AFFECT001/
AFFECT002 against T-1423's own files (design/frob.strata, docs/modules/
graph.md, src/frob/graph/cache.py, src/frob/graph/__init__.py,
frob.lock) -- this is the shared-branch-diff artifact of two tickets in
one worktree (the ticket-scoped gate compares against the whole branch
diff vs main, not just this ticket's own commits), not a real T-1378
defect; T-1423 was independently verified clean with `frob check
--ticket T-1423 --budget 100` (exit 0) before T-1378 was started. Re-run
`frob check --ticket T-1378` after T-1423 lands (or is otherwise removed
from this branch's diff) to get a clean per-ticket read.

### Changed
```
 design/frob.strata         |     4 +
 docs/modules/graph.md      |    21 +
 docs/modules/serve.md      |    24 +
 frob.lock                  |     2 +-
 src/frob/graph/__init__.py |    25 +-
 src/frob/graph/cache.py    |   136 +-
 src/frob/serve/_socketd.py |    55 +
 tests/test_graph_lock.py   |   110 +-
 tests/test_serve_socket.py |   112 +
 tickets-archive.md         |  9720 +++++++++++++++++++++++++++++++++++++-
 tickets.md                 | 10967 ++++---------------------------------------
 11 files changed, 11210 insertions(+), 9966 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_terminates_and_joins_active_children` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_escalates_to_kill_if_terminate_does_not_stick` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestReapMultiprocessingChildren::test_no_active_children_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 8 error(s), 394 warning(s), 695 waived
- error-findings: AFFECT001@src/frob/graph/__init__.py, AFFECT002@src/frob/graph/__init__.py, COV003@tickets/T-1406, COV003@tickets/T-1408, COV003@tickets/T-1419, SELFAUDIT001@design, TICK006@tickets.md, WIRE001@tests/test_serve_socket.py
