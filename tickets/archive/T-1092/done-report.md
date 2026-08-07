## Done report

Built the standalone unix-socket JSON-RPC daemon process (`frob.serve._socketd`)
as a second frontend over the exact same `frob.serve._tools` core the MCP
stdio transport already calls -- `_TOOL_DISPATCH` maps each exposed method
name directly onto the same `frob.serve._tools` function `server.py`'s
`@server.tool()` registrations use, so no query logic is forked between the
two transports.

Three pieces, matching the ticket's three acceptance criteria:

1. `acquire_singleton_lock` / `_release_singleton_lock`: a kernel-level
   `flock(LOCK_EX | LOCK_NB)` on `.frob/daemon.lock` -- atomic, so of any
   number of racing callers exactly one gets `Ok`, verified directly with
   an 8-thread barrier-synchronized race
   (`TestAcquireSingletonLock::test_n_racing_callers_exactly_one_wins`).
2. `_JsonRpcRequest`/`dispatch_request`/`_TOOL_DISPATCH`/`_RequestHandler`/
   `_DaemonServer`: a newline-delimited JSON-RPC-shaped protocol over a
   `socketserver.ThreadingUnixStreamServer`, dispatching into the warm-
   state-backed `_tools` functions -- verified end-to-end over a real
   socket (`TestRunSocketDaemon::test_serves_one_request_then_idle_exits`)
   and at the dispatch-table level (`TestDispatchRequest`).
3. `_IdleTracker`/`_idle_monitor`/`run_socket_daemon`: an idle-timeout
   background thread that calls `server.shutdown()` once idle, with the
   socket file removed and the lock released on every exit path -- proven
   by the same end-to-end test observing the socket file gone and the
   server thread having exited after the configured idle window.

`send_request` is a minimal synchronous client used by the test suite to
exercise the daemon over a real socket end-to-end; it is also the shape
the next child ticket (CLI wiring) will build on, though wiring the CLI
itself is explicitly out of this ticket's scope.

Scope was expanded by one file, `design/frob.strata` (`frob ticket scope
--add`, reason recorded in the ticket's scope_changes audit trail): the
new module gives the `serve` node its first genuine `fs`/`net` capability
observations (the lock/socket files, the unix-domain-socket transport),
which the SELFAUDIT001 self-audit gate (SYS100) correctly flagged as
undeclared against the node's prior "genuinely zero-may" model -- this is
a required update to the exact code this ticket adds, not unrelated scope
creep, and the change is narrow (the `serve` node's `may` list plus its
explanatory comment).

`docs/modules/serve.md` gained a "Socket daemon (T-1092)" section
documenting the guard, the protocol, and the idle-timeout mechanism, with
`frob:describes` anchors for every new public symbol.

Differential-parity note for T-1093 (CLI wiring, the next child): the
socket daemon and the MCP stdio transport now answer identically for the
same query because both call the identical `frob.serve._tools` functions
against the identical `frob.serve._warm` warm-state cache -- there is no
protocol-specific query logic anywhere in `_socketd.py` to keep in sync.
`send_request(root, method, params)` is the client-side shape T-1093 can
build a CLI-side dispatcher on directly (connect, one JSON-RPC line out,
one line back, unwrap into a `Result`) rather than reinventing the wire
format. T-1093 will additionally need a way to launch the daemon lazily
when no live one is found (this ticket only proves `run_socket_daemon`
answers correctly once started; it does not itself decide who spawns it
first) and cross-worktree single-flight remains explicitly out of scope
per this ticket's Description.

### Changed
```
 design/frob.strata         |  45 +++--
 docs/modules/serve.md      |  86 +++++++++
 docs/strata/roadmap.md     |   7 +
 src/frob/serve/__init__.py |  18 ++
 src/frob/serve/_socketd.py | 469 +++++++++++++++++++++++++++++++++++++++++++++
 tests/test_serve_socket.py | 179 +++++++++++++++++
 tickets.md                 | 330 ++++++++++++++++++++++++++++++-
 7 files changed, 1109 insertions(+), 25 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestAcquireSingletonLock::test_n_racing_callers_exactly_one_wins` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestDispatchRequest::test_known_method_ok` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestRunSocketDaemon::test_serves_one_request_then_idle_exits` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestAcquireSingletonLock::test_first_caller_wins` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestAcquireSingletonLock::test_second_caller_loses_while_first_holds` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestAcquireSingletonLock::test_lock_released_on_close_allows_next_caller` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestDispatchRequest::test_unknown_method_is_error` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestRunSocketDaemon::test_contended_lock_is_err` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestRunSocketDaemon::test_stale_socket_file_is_replaced` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 3 error(s), 577 warning(s), 426 waived
- error-findings: COV003@tickets/T-1090, REG003@docs/design/registry/supply-chain.yaml, TICK006@tickets.md
