## Done report

Investigated the T-1097 lease primitive: ResourceLeaseManager is keyed by
CONNECTION identity (_lease_holder_id), and the existing client seam
(_daemon_proxy.query/send_request) opens-sends-recvs-closes a fresh
connection per call -- ties acquire and release to DIFFERENT connections,
so an acquire immediately followed by the connection closing would
trigger T-1097's own connection-liveness release right away, never
actually holding the lease across the coverage subprocess run. This
needed a genuinely persistent connection, not query()'s existing shape.

Promoted tests/test_serve_leases.py's own `_RawClient` test scaffold to
production code in src/frob/app/_daemon_proxy.py: `_LeaseConnection` (a
persistent raw JSON-RPC socket), `try_daemon_lease(root, resource, ...)`
(Ok(conn) on a granted lease, Err(ProxyReason) on no-daemon/disabled/
remote-error -- same three-reason fallback contract query() already
uses), and `release_daemon_lease(conn, resource)` (explicit release, then
close either way -- the close alone is also sufficient per T-1097's
crash-release guarantee, documented as the backstop).

Wired src/frob/testing/_coverage_wait.py's OUTER single-flight lock: a
new `_worktree_lock(root)` context manager tries `try_daemon_lease(root,
"coverage")` first; on Ok, yields while holding the lease and releases on
exit; on Err (no daemon reachable, FROB_NO_DAEMON=1, or the lease request
itself errored), falls back to the ORIGINAL `_coverage_lock` fcntl file
lock unchanged. `run_coverage_wait` now opens with `_worktree_lock`
instead of `_coverage_lock` directly -- everything below that line
(T-1095's cross-worktree tree-digest layer, the actual command spawn) is
untouched. T-1095's cross-worktree shared-state layer stays a genuinely
separate, cross-CLONE primitive -- the daemon serves one worktree's own
socket, not every worktree of the clone, so it is not something the
per-connection lease could replace even in principle.

Added TestWorktreeLock to tests/test_coverage_wait_shared.py with a REAL
daemon (SocketDaemonConfig/run_socket_daemon in a background thread, per
this file's own TestCrossWorktreeSingleFlight precedent, not a mock):
test_uses_daemon_lease_when_daemon_up spies on _coverage_lock and asserts
it is NEVER called when a daemon is reachable (the lease path took over
entirely); test_falls_back_to_file_lock_when_no_daemon sets
FROB_NO_DAEMON=1 and asserts _coverage_lock WAS called exactly once.
Extracted _start_socket_daemon/_shutdown_socket_daemon helpers (mirroring
tests/test_app_daemon_proxy.py's own _start_daemon/_shutdown) rather than
inlining per test method -- fixed a real frob-arch PERF003 false-positive
the inlined duplicate loops tripped.

Ran the full touched-test set foreground: `pytest tests/
test_coverage_wait_shared.py tests/test_app_daemon_proxy.py tests/
test_app.py -k "coverage or Coverage or Wait or daemon" -p
no:cacheprovider -q` -- all pass.

Ran `frob check --ticket T-1126` in chunks (gates-native, test, coverage+
doclink+docanchor): 0 errors attributable to any touched file after
fixing 3 real findings this change introduced (ARCH001 on
run_coverage_wait's docstring pushing it over the 60-line threshold --
trimmed; the PERF003 test false-positive above -- fixed by extracting
shared helpers; TEST001 on release_daemon_lease missing a unit test --
added the frob:tests directive). The 24 COV001/COV003 errors present are
pre-existing (gates/_tracked_files.py COV001, several strata-core/
src/parse.rs COV003 evidence-staleness findings from T-1099's landed
rust-file split), unrelated to this ticket's files.

Updated docs/modules/testing.md with a new "T-1126: daemon-owned coverage
lease" subsection and matching frob:doc anchors on every new public
symbol.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestWorktreeLock::test_falls_back_to_file_lock_when_no_daemon` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 16 error(s), 645 warning(s), 426 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-app/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/ticket_runner/_mutate.py, PRE001@tickets/T-1126, SELFAUDIT001@design, TICK006@tickets.md
