---
id: T-1092
title: 'daemon: standalone unix-socket JSON-RPC process + single-instance guard'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/serve/**
- docs/modules/serve.md
- tickets.md
- tests/test_serve_socket.py
- design/frob.strata
- docs/strata/roadmap.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'T-1092''s socket daemon introduces the serve node''s first real fs.write

    (lock file, socket file) and net.connect (unix socket client) effects.

    The SELFAUDIT001 self-audit gate (SYS100, design/frob.strata''s `serve`

    node) fails without declaring these -- the node''s model is a required,

    gate-enforced artifact of the exact code this ticket adds, not a

    neighboring concern. Narrow addition only: the `serve` node''s `may`

    capability list and its explanatory comment.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/strata/roadmap.md
  reason: 'The AFFECT001 gate requires docs/strata/roadmap.md#self-hosting-commitments-decision-d7

    to be touched whenever design/frob.strata''s serve node changes (its own

    affects()-closure doc). T-1092 changed that node''s may-capability list,

    so this decision-record doc is a required, gate-enforced companion edit

    to the design/frob.strata change already in scope -- narrow addition

    only (one new bullet).

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_serve_socket.py::TestAcquireSingletonLock::test_n_racing_callers_exactly_one_wins
- tests/test_serve_socket.py::TestDispatchRequest::test_known_method_ok
- tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits
- tests/test_serve_socket.py::TestAcquireSingletonLock::test_first_caller_wins
- tests/test_serve_socket.py::TestAcquireSingletonLock::test_second_caller_loses_while_first_holds
- tests/test_serve_socket.py::TestAcquireSingletonLock::test_lock_released_on_close_allows_next_caller
- tests/test_serve_socket.py::TestDispatchRequest::test_unknown_method_is_error
- tests/test_serve_socket.py::TestRunSocketDaemon::test_contended_lock_is_err
- tests/test_serve_socket.py::TestRunSocketDaemon::test_stale_socket_file_is_replaced
designated_repro_test: null
acceptance:
- text: GIVEN no daemon is running WHEN a client connects to the project's .frob/daemon.sock
    THEN an atomic flock/socket-bind guard spawns exactly one daemon process even
    under N racing concurrent connect attempts, never an 'already running' error and
    never two daemons
  evidence:
  - tests/test_serve_socket.py::TestAcquireSingletonLock::test_n_racing_callers_exactly_one_wins
- text: GIVEN a running daemon WHEN a second client sends a JSON-RPC request over
    the socket THEN it receives a response built from the SAME warm state (frob.serve._warm)
    the MCP stdio path already serves, with no protocol-specific re-implementation
    of the query logic
  evidence:
  - tests/test_serve_socket.py::TestDispatchRequest::test_known_method_ok
  - tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits
- text: GIVEN the daemon has been idle for N minutes (default configurable) WHEN the
    idle timer fires THEN the process exits cleanly, leaving no orphaned process and
    no stale socket file
  evidence:
  - tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits
threat: null
component: null
---
Splits out child (c)+(a-lifecycle) of T-0321: today frob.serve._daemon runs ONLY as a background thread inside a live frob-serve MCP stdio process (T-0733) -- there is no standalone process reachable outside an MCP client session, and no unix-socket transport at all (grep for AF_UNIX/jsonrpc across src/frob/serve/ returns nothing as of 2026-07-28). Build a standalone daemon process (frob.serve._daemon or a new frob.serve._socketd module) that: (1) listens on a per-project-root unix socket (.frob/daemon.sock), (2) speaks a minimal JSON-RPC-shaped protocol wrapping the SAME frob.serve._tools functions the MCP transport already calls (no logic fork -- MCP and socket become two frontends over one core, per T-0321's integration map), (3) uses an atomic single-instance guard (flock on a .frob/daemon.lock file, checked+held before bind) so racing clients converge on exactly one daemon, (4) auto-exits after an idle timeout with no orphaned process. This does NOT yet wire the CLI to use the socket (that is the next child) -- this ticket only stands the process + protocol up and proves it answers correctly. Explicitly NOT in scope: FS-watch invalidation (separate child), cross-worktree single-flight (separate child).