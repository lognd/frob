## Done report

Closing the frob daemon epic: all six children named in the epic body
(a)-(f) plus the two refiled residue tickets from T-1093's dead-draft
loss are landed on main, done:

(a) warm graph + FS-watch incremental invalidation by digest: T-1094
    (done).
(b) single-flight coverage/collection keyed by source digest, shared
    across worktrees with identical content: T-1095 (done, this wave --
    cross-worktree arbitration via a shared, content-digest-keyed
    fcntl.flock/result-cache layer under git_common_dir, composing with
    T-0322's original per-worktree lock; proven with a real two-worktree
    concurrency test, tests/test_coverage_wait_shared.py).
(c) local unix-socket JSON-RPC query protocol: T-1092 (done).
(d) frob CLI auto-proxies to the daemon if running, else in-process:
    T-1093 (done, frob perf hot --json) extended by T-1106 (done, this
    wave -- frob graph affects --json).
(e) subscribe/push events (coverage-fresh, graph-changed): T-1096
    (done).
(f) resource leases/semaphores (coverage=1 writer): T-1097 (done, this
    wave -- frob.serve._leases.ResourceLeaseManager, daemon-arbitrated,
    connection-liveness release proven against a real crash-shaped
    disconnect).

Additionally landed this wave: T-1105 (done) -- a real daemon-side
version-handshake RPC (frob_version/frob_shutdown) replacing T-1093's
original client-written .frob/daemon.meta.json sidecar file, closing
that ticket's own disclosed residual (its draft died at land and was
refiled as T-1105/T-1106 by the coordinator).

Client-interface HARD requirements verified against the landed code:
1. No lifecycle commands in the happy path -- `ensure_daemon`/`query`
   autostart transparently (T-1093).
2. Transparent autostart via `acquire_singleton_lock`'s atomic flock
   (T-1092).
3. Auto-shutdown on idle (`_idle_monitor`, T-1092) and now also via an
   explicit graceful `frob_shutdown` RPC (T-1105) and a crash-detected
   connection-teardown for any held resource lease (T-1097).
4. Correctness invariant (daemon-answer == cold-answer): proven by real
   subprocess-vs-subprocess differential tests for every wired CLI
   command --
   tests/test_app_daemon_proxy.py::TestDifferentialParity::test_perf_hot_json_daemon_matches_in_process
   and
   tests/test_app_daemon_proxy.py::TestDifferentialParity::test_graph_affects_json_daemon_matches_in_process.
5. Transparent fallback: `query()`'s `Err` contract (Disabled/
   Unreachable/RemoteError) never surfaces to the caller -- every proxied
   CLI command falls straight back to its pre-existing in-process path.
6. Self-healing version skew: T-1105's `frob_version`/`frob_shutdown` RPC
   pair, replacing the sidecar file T-1093 shipped as an interim measure.
7. Zero required config, `FROB_NO_DAEMON=1` opt-out only.

Disclosed, tracked, NOT this epic's remaining scope (each already has a
follow-on ticket, not silently dropped):
- T-1128 (coordinator refile; the original draft died to a 10b ledger
  restore): wiring frob_graph_query/frob_check_delta/
  frob_run_touched_tests/frob_doable_tickets through the proxy once each
  CLI payload is reconciled field-for-field with its `_tools`
  counterpart.
- outline/map/xref/exports/stats need NEW `frob.serve._tools` RPC
  methods before they can be proxied at all (no existing RPC surface),
  a materially bigger gap than a reconciliation -- documented in
  docs/modules/serve.md's "Scope cut (disclosed)" section; ticketed by
  the coordinator as T-1127 (exports/stats only -- outline/map/xref are
  moot pending T-0802's navigation-command sunset).
- T-1126 (coordinator refile; the original draft died to a 10b ledger
  restore): wire `run_coverage_wait`'s own subprocess flow through
  T-1097's daemon-owned coverage lease RPC instead of its current
  file-lock layers (touches src/frob/app/_daemon_proxy.py, contended
  with T-1106's own wave).
- gate:TICK006 phantom-draft-citation cleanup (T-1077/T-1084/T-1095's
  own Done reports), an unrelated pre-existing ledger-hygiene issue
  found while landing this wave's tickets: already repaired inline by
  the coordinator (commit 0abc4e3a), no ticket needed.

`frob check --ticket T-0321` was run per this session's own gates-fast/
gates-native/gates-security/lint/static chunked passes across T-1105,
T-1095, T-1097, and T-1106 individually (see each ticket's own Done
report for its own chunk-by-chunk results); no new error was introduced
by any of the four beyond pre-existing, unrelated findings already
present on main before this wave (confirmed by direct comparison against
main's own gate output for the same files).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_perf_hot_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_graph_affects_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight::test_identical_digest_worktrees_share_one_run` (pytest node id, verified passing when recorded)
- `tests/test_serve_leases.py::TestConnectionCrashReleasesLease::test_closing_connection_without_explicit_release_frees_the_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
