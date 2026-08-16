# frob.serve -- MCP adapter exposing enforcement queries

One sentence: `frob serve` starts a read-only Model Context Protocol (MCP)
server over stdio so any MCP-aware agent can call frob's enforcement
queries directly, instead of shelling out to the CLI and parsing text.

`frob.serve` never mutates tickets, `frob.lock`, or the graph cache; every
tool is a thin, JSON-serializable wrapper around an existing `frob.graph`,
`frob.tickets`, or `frob.gates` read path. The graph snapshot is loaded
cache-first and rebuilt only on a stale/missing cache, same as `frob graph
query`.

<!-- frob:invariant INV-021 -->

## mcp SDK

<!-- frob:describes src/frob/serve/_tools.py::ServeError -->
<!-- frob:describes src/frob/serve/server.py::McpUnavailable -->
<!-- frob:describes src/frob/serve/server.py::build_server -->
<!-- frob:describes src/frob/serve/server.py::run_stdio -->
<!-- frob:describes src/frob/app/serve_runner.py::run -->

Tools live in `frob.serve._tools` as plain functions returning
`Result[dict, ServeError]` (typani), with **no** dependency on the `mcp`
package -- they are directly unit-testable without a transport. The stdio
transport (`frob.serve.server`, built on `mcp.server.fastmcp.FastMCP`)
imports `mcp` lazily, at server-construction time via `build_server` (and
`run_stdio`, which builds then blocks on the stdio loop); a missing `mcp`
package raises `McpUnavailable`. `frob.app.serve_runner.run` (the `frob
serve` CLI entry) catches `McpUnavailable` and prints a clear "mcp SDK not
installed" message, exiting 1, instead of letting the import error propagate.

T-1823: `run_stdio` also installs the T-1433/T-1466 SIGUSR1 stack-dump
handler (`frob.testing._stackdump.install_stackdump_handler`, opt-in via
`FROB_COVERAGE_STACKDUMP`) before building the server or starting the
background daemon thread -- a long-lived `frob serve` process can wedge
the same way a `make coverage` xdist worker can, and this gives it the
same self-diagnosis path (send `SIGUSR1`, read
`.frob/stackdumps/pid-<pid>.txt`).

## Tools

<!-- frob:describes src/frob/serve/_tools.py::frob_doable_tickets -->
<!-- frob:describes src/frob/serve/_tools.py::frob_stale_docs -->
<!-- frob:describes src/frob/serve/_tools.py::frob_check_scope -->
<!-- frob:describes src/frob/serve/_tools.py::frob_graph_query -->
<!-- frob:describes src/frob/serve/_tools.py::frob_doc_for -->
<!-- frob:describes src/frob/serve/_tools.py::frob_check_delta -->
<!-- frob:describes src/frob/serve/_tools.py::frob_run_touched_tests -->
<!-- frob:describes src/frob/serve/_tools.py::frob_perf_hot -->

- `frob_doable_tickets()` -- the doable ticket list (id/title/kind),
  oldest-first, mirroring `frob ticket doable`.
- `frob_stale_docs()` -- the drift report: DRIFT001 stale acks (a locked
  digest that moved) and DRIFT002 dangling edges (an edge endpoint that no
  longer resolves), mirroring `frob graph why`'s underlying comparison.
- `frob_check_scope(ticket_id)` -- whether the working diff stays within
  `ticket_id`'s declared `scope` globs (SCOPE001), via `frob.gates.run_gates`
  restricted to the `scope` gate.
- `frob_graph_query(symref)` -- resolve `symref` and list its outgoing and
  incoming obligation-graph edges, mirroring `frob graph query`.
- `frob_doc_for(symref)` -- the `frob:doc` edges `symref` declares and the
  `frob:describes` (markdown doc anchor) edges that describe it.
- `frob_check_delta(ticket_id=None, base="main", verify=False)` -- (T-0177)
  runs a full `frob.gates.run_gates` pass and returns only the violations
  NEW since the stamped `.frob/baseline` (mirroring `frob check --delta`),
  using the warm graph/baseline cache described below instead of a cold
  reload per call. `verify=True` additionally forces a fully cold rebuild
  and cross-checks the two violation sets -- see "Staleness/correctness
  contract" below. Also returns `check_result` (T-1147): the SAME
  per-gate-family `ToolResult` list `frob check --only gates --delta
  --json` renders (`frob.check._python._gates_success_result`), wrapped
  as `{"path": ..., "results": [...]}` -- see "CLI-payload daemon proxy"
  below for which one narrow invocation shape this lets the CLI proxy.
- `frob_run_touched_tests(base="main")` -- (T-0177) selects AND runs the
  touched-set tests for `base` (`frob.testing.select_tests` +
  `run_selected`), the MCP counterpart of `frob test --base <base>`,
  against the same warm graph snapshot `frob_check_delta` already paid to
  build.
- `frob_perf_hot(top=None, by="p50xcount")` -- (T-0917, a T-0712 follow-up)
  T-0712's persisted hot-graph sketch store (`frob.perf.list_sketches`),
  ranked by `by` (`p50xcount` default, or `p90`) and truncated to `top`
  rows, mirroring `frob perf hot`'s query surface with no live
  re-collection.
- `frob_daemon_status()` -- (T-0733) the background daemon's latest
  post-land delta/touched-tests verdict and any in-flight-worktree rebase
  conflict warnings; a pure read, never triggers a poll itself. See
  "Daemon jobs" below for what populates it.

## Warm state

<!-- frob:describes src/frob/serve/_warm.py::_WarmState -->
<!-- frob:describes src/frob/serve/_warm.py::_repo_dirty_key -->
<!-- frob:describes src/frob/serve/_warm.py::_warm_state -->
<!-- frob:describes src/frob/serve/_warm.py::_invalidate -->

`frob serve` runs as one long-lived stdio process for the life of the MCP
client session, not one process per tool call. `frob.serve._warm._WarmState`
holds, per repo root, in process memory:

1. the built `GraphSnapshot` (`frob.graph.build_graph`);
2. the stamped violation baseline (`frob.gates.load_baseline`, `None` if
   never stamped);
3. collected python pytest node ids (`frob.testing.collect_python_tests`).

`_warm_state(root)` is the single entry point every tool above uses instead
of loading any of the three cold. It is keyed by `_repo_dirty_key(root)`: a
`git rev-parse HEAD` + `git status --porcelain=v1 --untracked-files=all`
signature (excluding `.frob/` itself via a pathspec -- `build_graph`/
`collect_python_tests` write `.frob/cache.db` and the collection cache as a
side effect of the very build this key gates, so including it would make
every build self-_invalidate on the very next call), PLUS an
`(mtime_ns, size)` tag per path the status output names (closing a real
gap: porcelain status alone only reports THAT a path is untracked or
modified, never its content, so editing an already-untracked file's bytes
without staging it would otherwise be invisible to the key).

- **Cache hit** (key unchanged): the cached `GraphSnapshot` and test ids are
  reused verbatim -- zero re-walk, re-parse, or `pytest --collect-only`
  subprocess. The baseline is still re-read fresh every call regardless of
  the key (a plain json read, and `.frob/baseline` lives under the
  excluded `.frob/` path, so a stamp written between two otherwise-identical
  calls must still be observed).
- **Cache miss** (key changed, or nothing cached yet): `build_graph` (itself
  incremental via the `.frob` sqlite cache -- only files whose content hash
  moved get reparsed) and `collect_python_tests` (itself cached on its own
  content key, T-0333) run again; the result replaces the cached state.
- `_invalidate(root)` drops the cached state unconditionally, forcing the
  next `_warm_state` call to rebuild cold -- used by `frob_check_delta`'s
  `verify=True` path and by tests.

### Staleness/correctness contract

**What incremental reuse covers**: the graph snapshot, the baseline
document, and the collected test id set -- each is either reused verbatim
on a proven-unchanged tree, or rebuilt via its own already-incremental
on-disk mechanism otherwise. `_repo_dirty_key`'s invalidation logic has a
direct correctness test (`tests/test_serve.py::TestWarmState`) plus a
property test (`test_warm_state_rebuilds_iff_tree_changed`) asserting the
vacuous-pass invariant: a rebuild happens on EVERY call that followed a
real on-disk edit, and on NO call that did not -- an obligation not
re-evaluated must not have had a changed input.

**What it does NOT cover** (scope cut, disclosed honestly rather than
implied): `frob.gates.run_gates` itself still evaluates every selected gate
in full on each `frob_check_delta` call, EXCEPT for the closed
`_CACHEABLE_GATES` allowlist T-0602 added (`drift`, `test`, `policy`,
`parse_failures`, `debt`, `lang_conformance`,
`affect_drift`) -- see "Per-gate dependency-tracked partial re-evaluation
(T-0602)" below. Every OTHER gate (the large majority: anything reading
`st.root`/`st.repo_root` directly, or any combined dispatch name that
bundles a root-scanning sub-check alongside a snapshot-only one, e.g.
`invariant`/`docblocks`) is still fully re-evaluated on every call -- T-0602
excludes these LOUDLY (a hand-audited allowlist, not a best-effort guess)
rather than risk serving a stale answer for a gate this module cannot
soundly observe every file it reads. What `frob_check_delta` DOES
guarantee, unconditionally: its reported delta is always computed against
a freshly-run `run_gates` pass (never a stale cached violation list, for
either the cached or uncached gates) filtered through
`delta_violations`/`is_baseline_stale` -- the same baseline-diff machinery
`frob check --delta` uses on the CLI side, so the two stay consistent by
construction.

### Per-gate dependency-tracked partial re-evaluation (T-0602)

<!-- frob:describes src/frob/gates/_gate_cache.py::TrackedSnapshot -->
<!-- frob:describes src/frob/gates/_gate_cache.py::evaluate_cacheable_gate -->
<!-- frob:describes src/frob/gates/_gate_cache.py::invalidate -->
<!-- frob:describes src/frob/gates/_gate_cache.py::model_side_channel_key -->
<!-- frob:describes src/frob/gates/__init__.py::run_gates -->

`run_gates(cfg, use_cache=True)` -- the call `frob_check_delta` makes --
opts every selected gate in `frob.gates._CACHEABLE_GATES` (drift, test,
policy, parse_failures, debt, lang_conformance, affect_drift) into
`frob.gates._gate_cache.evaluate_cacheable_gate`: a gate's cached
result from `.frob/gate-cache.db` (a new table alongside `frob.graph.
cache`'s `cache.db` and `frob.gates._baseline`'s `.frob/baseline`, sharing
the SAME `.frob/` derived-state directory -- no parallel cache) is served
instead of re-running the gate, whenever (a) every file the gate touched
last time still hashes identically, (b) the tree's overall tracked-file
membership (its full path SET, not just the touched subset -- T-0602's
"membership guard") is unchanged, closing the "a new file the gate would
now also touch did not exist when its dependency set was last recorded"
soundness hole, and (c) any non-file scalar input the gate also depends on
(`debt`'s `current_date`/`current_version`, and -- as of T-1454 -- every
cacheable gate's OTHER side inputs, folded in via `model_side_channel_key`;
see below) is unchanged. `TrackedSnapshot`
records the touched-file set by OBSERVING real reads through
`.symbols`/`.edges`/`.file_hashes`/`.malformed`/`.parse_failures` during
the gate's own run, rather than a hand-maintained per-gate file-selector
that could silently drift out of sync with the gate's actual logic.
`run_gates`'s default (`use_cache=False`, every pre-T-0602 call site) is
byte-for-byte unaffected. Single-flight safety around concurrent dispatch
(two gate-worker threads, or two `frob` processes, racing to fill the same
cache entry) reuses `frob.process._lock.derived_state_write_lock`
(T-0918's process-wide reentrancy registry) -- the primitive built exactly
for "a worker thread wants EXCLUSIVE while the main `frob check` thread
holds SHARED for the run's whole duration", which is this call's exact
nesting shape. See `frob.gates._gate_cache`'s module docstring for the
full design and `tests/test_gate_cache.py::TestColdDiffOracle` for the
correctness property test: a cold (uncached) evaluation and a
cache-aware evaluation from any prior cache state must agree, across
random file edits, adds, removes, and scalar-extra changes.

**T-1454: side-channel inputs beyond the snapshot now join the key.**
`TrackedSnapshot` only observes reads through the `GraphSnapshot` surface
-- it cannot see a cacheable gate's OTHER positional arguments, e.g.
`drift_gate(snap, st.lock)`'s `st.lock` (the loaded `frob.lock`). A `frob
ack` rewrites `frob.lock` without touching any tracked source file's
digest, so the old key never changed and a stale pre-ack DRIFT001 result
was served indefinitely -- reproduced and confirmed as a real bug, not a
theoretical gap (the reporting session's only workaround was
`FROB_NO_GATE_CACHE=1`). `frob.gates._gate_cache.model_side_channel_key(
*models)` fingerprints one or more pydantic `BaseModel` side inputs via
`model_dump_json`; `_cacheable_gate_call` (`frob.gates`) now folds each
cacheable gate's own side input(s) into its returned `extra` tuple --
`drift` -> `st.lock`, `test` -> `st.systems`/`st.coverage`/`st.tests`/
`st.test_policy`, `policy` -> `st.rules`/`st.diff`, `debt` -> `st.queue`
alongside its existing scalars, `affect_drift` -> `st.diff`
(`parse_failures`/`lang_conformance` have no such input and stay keyed on
`()`). `tests/test_gate_cache.py::TestRunGatesUseCache.
test_ack_invalidates_cached_drift001` is the regression oracle for the
reported case.

`verify=True` is the correctness guarantee for the part that IS cached: it
drops the warm cache (`invalidate`), re-runs `run_gates` fully cold, and
reports `verified` (whether the warm-cache pass and the cold pass produced
identical violation fingerprints) plus `verify_mismatch_count`. A `False`
`verified` would mean the warm graph/baseline/test cache served a stale
answer -- a bug, not an expected outcome; it is not a performance-only
knob to skip in normal use.

## Daemon jobs

<!-- frob:describes src/frob/serve/_daemon.py::_PostLandVerdict -->
<!-- frob:describes src/frob/serve/_daemon.py::_RebaseWarning -->
<!-- frob:describes src/frob/serve/_daemon.py::_DaemonStatus -->
<!-- frob:describes src/frob/serve/_daemon.py::_poll_post_land -->
<!-- frob:describes src/frob/serve/_daemon.py::_poll_rebase_bot -->
<!-- frob:describes src/frob/serve/_daemon.py::daemon_status -->
<!-- frob:describes src/frob/serve/_daemon.py::_run_daemon_cycle -->
<!-- frob:describes src/frob/serve/_daemon.py::_start_daemon -->
<!-- frob:describes src/frob/serve/_tools.py::frob_daemon_status -->
<!-- frob:describes src/frob/serve/_daemon.py::_poll_verify_worker -->
<!-- frob:describes src/frob/serve/_daemon.py::_get_verify_worker -->

(T-0733) `run_stdio` starts a background daemon thread (`frob.serve.
_daemon._start_daemon`) alongside the MCP transport, running one cycle
(`_run_daemon_cycle`) every `DEFAULT_POLL_INTERVAL_S` (20s) for the life of
the `frob serve` process. Three jobs per cycle:

1. **Post-land re-verify** (`_poll_post_land`) -- watches `main`'s resolved
   HEAD (`git rev-parse main`). If it has not moved since the last cycle,
   the cached `_PostLandVerdict` is returned untouched (no re-work). If it
   moved (a land happened), the warm cache (`frob.serve._warm`) is
   invalidated and one fresh `frob_check_delta`-equivalent pass runs
   (plus, by default, the touched-set tests against `main`), and the new
   verdict replaces the cached one. At the default interval this means a
   fresh delta verdict is available via `frob_daemon_status` within
   `DEFAULT_POLL_INTERVAL_S` of any land -- comfortably inside a minute --
   without any agent or coordinator invoking `frob check` themselves.
2. **Rebase-bot** (`_poll_rebase_bot`) -- for every in-flight worktree
   branch (`frob.tickets._leases.read_all_leases`, the same T-0473
   liveness signal `doable` already trusts), simulates merging current
   `main` into that branch with old-style `git merge-tree <merge-base>
   <branch> <main-head>` -- no checkout, no scratch clone, purely a
   read-only subprocess against the shared git object store. A conflict
   is detected by the presence of `<<<<<<<` markers in that command's
   stdout (this repo's git baseline, 2.34, predates the `--write-tree`
   form whose exit code reports conflicts directly). Every branch whose
   simulated merge would conflict gets a `_RebaseWarning`, replacing the
   full warning set for the repo root each cycle (a branch that
   resolved clean, or that landed and dropped its lease, does not linger
   as a stale warning).
3. **Coalescing verify worker** (`_poll_verify_worker`, T-1688) -- the
   T-1686 epic's own trailing-edge-debounce worker
   (`frob.verify._worker.CoalescingWorker`, `_get_verify_worker` caches
   one per repo root the same way `_DaemonStatus` is cached). This job
   does not decide WHAT to verify or WHEN in isolation: it `notify()`s
   the cached worker when `main`'s HEAD has moved since this job last
   looked (a land IS a queue-append event) and calls `tick()`
   unconditionally every cycle -- `tick()` itself is the cheap no-op
   unless the debounce window has gone quiet or the periodic floor has
   elapsed, so the real coalescing decision lives inside
   `frob.verify._worker`, not here. See
   `docs/modules/tickets-verify-sweep.md#coalescing-verify-worker-t-1688` for the full
   design (why it coalesces rather than iterates, why `None` can never
   advance the watermark, and the disclosed FS-watch wiring gap).

All three jobs write into one `_DaemonStatus` cache per repo root (mirroring
`frob.serve._warm`'s per-root cache shape); `frob_daemon_status()` -- the
new MCP tool -- reads it back verbatim as JSON (`post_land`,
`rebase_warnings`, `last_poll_at`), never triggering a poll itself. A
`None` `post_land` or empty `rebase_warnings` means the corresponding job
has not completed a cycle yet (or, for `post_land`, that `main` could not
be resolved), not that nothing needs attention.

`_run_daemon_cycle(root)` is the same single-cycle unit both the
background loop and tests call -- tests call it (or the two `poll_*`
functions directly) with no real sleep and no thread, for a deterministic
single-cycle assertion; only `_start_daemon`'s loop actually sleeps between
cycles, via a `threading.Event.wait` that `run_stdio` sets on shutdown so
the thread does not outlive the stdio transport.

## Socket daemon (T-1092)

<!-- frob:describes src/frob/serve/_socketd.py::DaemonError -->
<!-- frob:describes src/frob/serve/_socketd.py::SocketDaemonConfig -->
<!-- frob:describes src/frob/serve/_socketd.py::lock_path -->
<!-- frob:describes src/frob/serve/_socketd.py::socket_path -->
<!-- frob:describes src/frob/serve/_socketd.py::acquire_singleton_lock -->
<!-- frob:describes src/frob/serve/_socketd.py::dispatch_request -->
<!-- frob:describes src/frob/serve/_socketd.py::run_socket_daemon -->
<!-- frob:describes src/frob/serve/_socketd.py::send_request -->
<!-- frob:describes src/frob/serve/_socketd.py::daemon_version -->

`frob.serve._socketd` (T-1092, splitting off T-0321's daemon epic) stands up
a SECOND frontend over the exact same `frob.serve._tools` core the MCP stdio
transport already uses -- a standalone OS process reachable outside any MCP
client session, over a per-project-root unix domain socket, instead of only
as a background thread inside a live `frob serve` stdio process (the T-0733
daemon documented above). There is no logic fork: `_socketd._TOOL_DISPATCH`
maps each exposed JSON-RPC method name directly onto the SAME `frob.serve.
_tools` function `server.py`'s `@server.tool()` registrations call, so MCP
and the socket daemon answer identically because they call the identical
warm-state-backed (`frob.serve._warm`) query logic -- neither transport
re-implements a query, only how the call arrives and how the result is
serialized back out.

This ticket stands the process + protocol up and proves it answers
correctly; it does NOT wire the CLI to talk to the socket (a follow-on
child) and does NOT add FS-watch invalidation or cross-worktree
single-flight (both separate children of the same epic).

### Single-instance guard

`acquire_singleton_lock(root)` holds an `flock(LOCK_EX | LOCK_NB)` on
`<root>/.frob/daemon.lock` (`lock_path`) for the daemon process's entire
lifetime. `flock` contention is resolved by the kernel, not by any
check-then-act sequence in this process: of any number of processes racing
to acquire it concurrently for the same root, exactly one receives `Ok`
(the file handle to keep open) and every other one receives
`Err(DaemonError.AlreadyRunning)` immediately -- there is no window where
two callers can both believe they hold it, and a losing racer is expected
behavior (someone else is already the daemon for this root), not a
user-facing failure to surface. Releasing the lock (`_release_singleton_
lock`, called on every `run_socket_daemon` exit path -- clean idle
shutdown, bind failure, or an exception) unlocks then closes the handle, so
the next caller finds a clean slate.

### Protocol

One JSON object per newline-delimited line over the unix socket at
`<root>/.frob/daemon.sock` (`socket_path`):

```
--> {"id": 1, "method": "frob_doable_tickets", "params": {}}
<-- {"id": 1, "result": [...]}

--> {"id": 2, "method": "frob_graph_query", "params": {"symref": "..."}}
<-- {"id": 2, "error": {"code": "unknown_method", "message": "..."}}
```

`dispatch_request(root, request)` looks `request.method` up in
`_TOOL_DISPATCH`, calls it as `fn(root, **request.params)`, and never
raises: an unknown method, a bad-`params` `TypeError`, or a tool-level
`Err` all become a JSON-RPC error object (`unknown_method`, `bad_params`,
`tool_error`) instead of an exception escaping the connection handler.
`run_socket_daemon` serves connections on a `socketserver.
ThreadingUnixStreamServer` (one thread per connection, a connection may
carry many sequential request lines). `send_request(root, method, params)`
is a minimal synchronous client used by `tests/test_serve_socket.py` to
exercise the daemon end-to-end over a real socket, and the shape a future
CLI-side client (the next child ticket) will build on.

### Idle timeout

`SocketDaemonConfig(root=..., idle_timeout_s=DEFAULT_IDLE_TIMEOUT_S)`
(default 600s) configures how long the daemon waits with no dispatched
request before exiting. An `_IdleTracker` records the monotonic time of the
last request; a background monitor thread polls it (at an interval scaled
to `idle_timeout_s`, capped at 5s, so a short test-configured timeout is
still observed promptly) and calls `server.shutdown()` once the deadline
passes. `run_socket_daemon`'s `finally` block always removes the socket
file and releases the single-instance lock on the way out -- a clean idle
exit leaves no orphaned process and no stale socket file, and a stale
socket file left over from a prior crash (`_remove_stale_socket`) is
unlinked unconditionally the next time a caller wins the lock (safe: no
other live daemon can be bound to it once this process holds the
exclusive lock).

## Version handshake (T-1105)

<!-- frob:describes src/frob/serve/_socketd.py::daemon_version -->

Two extra JSON-RPC methods, special-cased in `_RequestHandler.handle`
alongside `subscribe` (not routed through `_TOOL_DISPATCH`, since they
answer about the daemon process itself rather than calling into
`frob.serve._tools`):

```
--> {"id": 1, "method": "frob_version", "params": {}}
<-- {"id": 1, "result": {"version": "0.4.2"}}

--> {"id": 2, "method": "frob_shutdown", "params": {}}
<-- {"id": 2, "result": {"shutting_down": true}}
```

`frob_version` answers with `daemon_version()` -- this daemon PROCESS's own
installed `frob` version (`importlib.metadata.version("frob")`, "unknown"
from a raw source checkout with no registered distribution). `frob_shutdown`
starts a short-lived helper thread that calls `server.shutdown()`
(asynchronously -- calling it inline on the connection-handling thread
would deadlock that thread against the very `serve_forever()` loop it is
asking to stop) and immediately acknowledges; the caller sees the socket
and lock file disappear shortly after, the same clean-exit path an idle
timeout takes.

This is the real, protocol-level replacement for T-1093's original
`.frob/daemon.meta.json` sidecar file: a CLI client can now ask a
POTENTIALLY-ALREADY-RUNNING daemon directly what version it is, and tell it
to step aside gracefully, instead of trusting a client-written file that
could go stale relative to whichever process actually happens to be
running the daemon. See "CLI daemon proxy (T-1093)" below, "Version-skew
self-heal", for the client side of this handshake.

### Shutdown reaps multiprocessing children (T-1378)

<!-- frob:describes src/frob/serve/_socketd.py::_reap_multiprocessing_children -->

Before T-1378, `frob_shutdown` acknowledged and stopped `serve_forever()`
but left any `multiprocessing.active_children()` this process had
accumulated (a forkserver, its resource_tracker, or a query-spawned
worker from `frob.serve._tools`'s parallel-execution paths) running --
only Python's own `multiprocessing.util._exit_function` atexit hook
would eventually reap them, and its unbounded `Process.join()` is exactly
what made a "shut down" daemon take 20+ seconds to actually disappear and
sometimes need a manual `SIGTERM`/`SIGKILL`.

`run_socket_daemon`'s shutdown path now calls `_reap_multiprocessing_
children()` itself, right after `server.serve_forever()` returns (both
the idle-timeout exit and the `frob_shutdown` RPC exit go through this
same `finally` block): `terminate()` every active child, then a bounded
`join(timeout=_CHILD_REAP_GRACE_S)`, escalating to `kill()` for anything
still alive after the grace period. This runs before the process ever
reaches Python's own atexit handling, so shutdown is bounded and
deterministic regardless of what spawned the children -- this
deliberately reads only the stdlib's own process registry, with no
dependency on `frob.serve._tools`'s own pool internals.

### Daemon gate runs cap their process pool (T-1436)

<!-- frob:describes src/frob/serve/_tools.py::_DAEMON_GATE_MAX_WORKERS -->

T-1378's third measured defect: with a warm daemon up, a proxied
`frob check --only gates --delta` ran SLOWER than `FROB_NO_DAEMON=1`
because the daemon's gate process pool competed with the foreground
check for the same cores (load average 5-8 on a 4-core WSL box).
`frob_check_delta` and its `verify=True` cold cross-check now run gates
through `frob.gates._run_gates_bounded` with
`_DAEMON_GATE_MAX_WORKERS = 2`, leaving the remaining cores to whatever
foreground work the daemon exists to serve. A direct `run_gates` call
(the non-daemon path) is unchanged -- it still sizes its pool from the
machine.

## FS-watch push invalidation (T-1094)

<!-- frob:describes src/frob/serve/_watch.py::DEFAULT_WATCH_POLL_INTERVAL_S -->
<!-- frob:describes src/frob/serve/_watch.py::watch_tick -->
<!-- frob:describes src/frob/serve/_watch.py::WatchThread -->

`frob.serve._watch` (T-1094, child (a) of T-0321) adds a PUSH layer over
the warm state's existing PULL-based invalidation
(`frob.serve._warm._repo_dirty_key`/`_warm_state`, "Warm state" above): a
background thread inside `run_socket_daemon` (T-1092) re-checks
`_repo_dirty_key` on a short interval (`DEFAULT_WATCH_POLL_INTERVAL_S`,
1s) and, the moment it changes, invalidates and eagerly rebuilds the warm
state during the daemon's own idle time -- so the FIRST client query after
an on-disk edit hits an already-warm cache instead of paying the rebuild
inline.

**This is a fast poller reusing `_repo_dirty_key` itself, not a kernel
inotify/watchdog-library subscription** -- a deliberate, disclosed design
choice (`frob.serve._watch`'s module docstring has the full rationale):
reusing the exact signal the pull path already trusts means a watch tick
structurally cannot disagree with what a client's own next query would
have computed, sidesteps the inotify-under-WSL-bind-mount watch-miss class
this repo has already hit once (T-0245), and adds no new dependency. The
tradeoff is polling overhead/latency instead of true event-driven push;
`WatchThread`'s tick loop is a drop-in swap for a real inotify listener
later if that tradeoff needs revisiting -- the push contract (`on_change`
firing on invalidation) and the correctness contract (below) are
unaffected either way.

### Staleness/correctness contract (T-1094 addendum)

T-0321 requirement 4 (daemon-answer == cold-answer, always) is unaffected
by this module: `_warm_state`'s pull-path recheck against
`_repo_dirty_key` still runs, unconditionally, on every tool call,
regardless of whether the background watcher already pre-warmed the cache
or not. A missed/delayed watch tick (the poll thread hasn't run yet, or
this daemon process isn't running at all -- e.g. the MCP stdio path, which
does not use `_watch` at all) never risks a stale answer -- it only means
the query pays the rebuild cost the pull path always paid before this
ticket, i.e. a forgone optimization, never a correctness gap. This is the
proof shape `tests/test_serve_watch.py::TestWatchTick.
test_watch_tick_never_disagrees_with_pull_signal` exercises over
randomized edit sequences: for every sequence, the watch-tick-observed
`changed` decision agrees with directly comparing two independent
`_repo_dirty_key` calls bracketing the same edit -- true by construction
here (same function, same call), but proven on the actual code path rather
than merely argued in prose.

`run_socket_daemon` starts one `WatchThread` per daemon process (root
`Path`, no config surface beyond `poll_interval_s`/`on_change`) alongside
the existing idle-monitor thread, and stops it in the same `finally` block
that releases the lock and removes the socket file -- a watcher never
outlives its daemon process. `on_change` is wired to publish a
`graph-changed` event (see "Subscribe/push events" below, T-1096) to any
subscribed client; `_watch` itself has no dependency on `_events` at all
(the callback is `None` if unset) and stays a pure optimization layer on
its own.

T-1737: the SAME `on_change` callback also calls `frob.serve._daemon.
_get_verify_worker(root).notify()` -- the T-1688 coalescing verify worker's
own cached instance for this root, the identical object `_poll_verify_worker`
polls from its separate background-daemon loop. A watch tick observing a
real on-disk change now resets that worker's debounce window immediately
instead of only via `_poll_verify_worker`'s own `main`-HEAD-moved check or
its periodic floor; see "Coalescing verify worker" in
`docs/modules/tickets-verify-sweep.md#coalescing-verify-worker-t-1688` for
the debounce/floor mechanics this wakes.

## Subscribe/push events (T-1096)

<!-- frob:describes src/frob/serve/_events.py::DEFAULT_SUBSCRIBE_TIMEOUT_S -->
<!-- frob:describes src/frob/serve/_events.py::DEFAULT_COVERAGE_POLL_INTERVAL_S -->
<!-- frob:describes src/frob/serve/_events.py::_EventBus -->
<!-- frob:describes src/frob/serve/_events.py::CoverageWatcher -->
<!-- frob:describes src/frob/serve/_events.py::subscribe_and_wait -->
<!-- frob:describes src/frob/serve/_socketd.py::DaemonError -->

`frob.serve._events` (T-1096, child (e) of T-0321, this epic's named
"stall-killer") extends the T-1092 socket protocol with a `subscribe`
verb: instead of a client re-polling `frob_daemon_status` on its own
schedule (T-0733's post-land/rebase-bot jobs are still PULL-only), a
client sends `{"method": "subscribe"}` and then blocks reading
newline-delimited PUSH frames off the same connection --
`{"event": "graph-changed", "data": {}}` or
`{"event": "coverage-fresh", "data": {}}` -- the moment the daemon's own
state changes.

### Event sources

Two background threads, both started/stopped by `run_socket_daemon`
alongside the existing idle-monitor and (T-1094) `WatchThread`:

- **`graph-changed`** -- `WatchThread`'s `on_change` callback (T-1094)
  publishes this event every time a watch tick observes and pre-warms a
  real on-disk change.
- **`coverage-fresh`** -- `CoverageWatcher` polls
  `<root>/.frob/coverage-stamp`'s mtime (`DEFAULT_COVERAGE_POLL_INTERVAL_S`,
  1s) and publishes the moment it changes. Deliberately source-agnostic:
  it does not import `frob.testing` or care WHO wrote the stamp (`frob.
  testing.run_coverage_wait`'s single-flight lock, a bare `make coverage`,
  or a future cross-worktree cache hit, T-1095) -- any write to the stamp
  file is treated as a legitimate freshness signal.

`_EventBus.subscribe` and `CoverageWatcher.start` each carry an explicit
`frob:tests` edge (`TestEventBus.test_publish_reaches_all_subscribers` and
`TestSubscribeAndWait.test_receives_coverage_fresh_on_stamp_write`
respectively) rather than relying on the convention-matched-name fallback
`TEST001`/`TEST014` would otherwise credit ambiguously against
`WatchThread.start`/`StackSampler.stop`'s same leaf names elsewhere in
this module and `frob.perf`.

### Protocol and connection handling

`_RequestHandler._handle_subscribe` registers the connection with the
per-process `_DaemonServer.event_bus` (an `_EventBus`, constructed once
per daemon in `_DaemonServer.__init__`) and starts a dedicated per-
connection event-pump thread (`_pump_events`) that blocks on the
subscriber's `queue.Queue` and writes each frame out as it arrives. A
`threading.Lock` (`_write_lock`) serializes writes to the connection's
`wfile` between the main `handle()` loop (still serving ordinary
request/response pairs on the SAME connection -- subscribing does not
stop a client from issuing other requests) and the event-pump thread, so
the two never interleave a partial JSON line onto the wire.
`_EventBus.unsubscribe` pushes a `None` sentinel into the subscriber's
queue so the pump thread wakes up and exits promptly instead of blocking
forever once the connection closes (`handle()`'s `finally` block always
unsubscribes, including on an abrupt disconnect).

### Client helper

`subscribe_and_wait(root, event, timeout_s=DEFAULT_SUBSCRIBE_TIMEOUT_S)`
is the client-side counterpart: connect, send `subscribe`, then block
reading frames until one whose `"event"` matches arrives (returning its
`"data"`), or `Err(DaemonError.Timeout)` if `timeout_s` elapses, or
`Err(DaemonError.Unreachable)` if the daemon cannot be reached at all.
This is the shape an agent that today backgrounds `make coverage` and
stalls waiting on a notification it cannot act on
(`docs/guides/agent-playbook.md` 6b/3b) uses instead: ONE blocking
foreground call, in-band on a single connection, that resolves the moment
ANY caller's coverage run finishes writing the stamp -- including a
DIFFERENT process's single-flight run (T-1095), not just one this client
itself triggered.

### Staleness/correctness contract (T-1096 addendum)

**An event frame is a wake-up signal, never a data channel** -- this is
what keeps T-0321's #1 safety invariant (daemon-answer == cold-answer,
always) intact for this ticket too. `coverage-fresh`/`graph-changed`
frames carry an empty `data` payload today; a client that receives one
still calls `frob_check_delta`/`frob_run_touched_tests`/
`frob_daemon_status` afterward exactly as it would from a cold start,
through the same warm-state-backed, git-status-verified query path every
other client uses (the "Staleness/correctness contract" section above).
Subscribing only replaces the "when do I bother asking" polling loop; it
never substitutes for, or bypasses, the "is this answer correct" check
any query tool still performs on every call.

## Resource leases/semaphores (T-1097)

<!-- frob:describes src/frob/serve/_leases.py::ResourceLeaseManager -->
<!-- frob:describes src/frob/serve/_leases.py::DEFAULT_LEASE_CAPACITY -->

T-0322 shipped coverage single-flight as a plain per-worktree `fcntl.
flock` -- OS-level blocking only, no visibility into who holds it, and no
daemon-mediated release-on-crash semantics. T-1095 moved that arbitration
cross-worktree via a shared, content-digest-keyed lock/cache. This ticket
generalizes the underlying primitive one step further: a NAMED resource
lease/semaphore the daemon itself owns and arbitrates over its own
JSON-RPC connections (`frob.serve._leases.ResourceLeaseManager`),
starting with `coverage` at `DEFAULT_LEASE_CAPACITY` (1, i.e. an
exclusive writer lock) so any future contended resource can register
under its own name instead of each caller inventing its own flock
convention.

Two new JSON-RPC methods, special-cased in `_RequestHandler.handle`
alongside `subscribe`/`frob_version`/`frob_shutdown`:

```
--> {"id": 1, "method": "frob_lease_acquire",
     "params": {"resource": "coverage", "timeout_s": 30.0}}
<-- {"id": 1, "result": {"acquired": true}}

--> {"id": 2, "method": "frob_lease_release", "params": {"resource": "coverage"}}
<-- {"id": 2, "result": {"released": true}}
```

`frob_lease_acquire` blocks THIS connection's own handler thread (never
another connection's -- `_DaemonServer` is a `ThreadingUnixStreamServer`,
one thread per connection) until a slot of `params["resource"]` frees up
or `params["timeout_s"]` elapses; `params["capacity"]` is only consulted
the FIRST time a given resource name is ever mentioned
(`ResourceLeaseManager._state_for`'s create-on-first-mention rule) --
every later acquire of the same name reuses whatever capacity was
established then. `acquired: false` means the timeout elapsed with
nothing held; the caller holds no slot to release.

**Connection-liveness release (T-1097 acceptance [1], T-0321 requirement
3):** every lease is tracked under the ACQUIRING CONNECTION's own
`_lease_holder_id` (assigned once in `_RequestHandler.setup`), not just
an explicit release call the client must remember to make.
`ResourceLeaseManager.release_holder` runs unconditionally in `handle`'s
`finally` block -- the same place `subscribe`'s per-connection
`unsubscribe` already runs (T-1096) -- so a client that crashes or is
killed mid-lease has every resource it held freed the instant the daemon
notices the closed connection, with no explicit `frob_lease_release` and
no daemon restart required. `frob_lease_release` is the well-behaved
client's EXPLICIT counterpart for freeing a resource without closing the
whole connection.

**Scope note**: this ticket ships the daemon-owned arbitration primitive
and proves both acceptance criteria against it directly (real socket
clients, real connection teardown) -- it does NOT rewire `frob.testing.
_coverage_wait.run_coverage_wait`'s own subprocess flow to acquire its
lock THROUGH this daemon RPC instead of its existing file-lock layers
(T-0322's per-worktree `fcntl.flock`, T-1095's shared per-digest
`fcntl.flock`). That wiring would touch `frob.app`'s CLI-proxy layer
(`_daemon_proxy.query`), out of this ticket's `src/frob/serve/**`/
`src/frob/testing/**` scope and contended with T-1106's own `src/frob/
app/` work this wave -- tracked as a disclosed follow-on, not silently
dropped.

## CLI daemon proxy (T-1093)

<!-- frob:describes src/frob/app/_daemon_proxy.py::ProxyReason -->
<!-- frob:describes src/frob/app/_daemon_proxy.py::ensure_daemon -->
<!-- frob:describes src/frob/app/_daemon_proxy.py::query -->

`frob.app._daemon_proxy` (T-1093) is the client-side seam the CLI dispatch
layer uses to talk to the T-1092 socket daemon above, transparently: a
runner calls `query(root, method, params)` instead of computing a proxyable
answer itself, and always gets back a `Result` -- `Ok(result)` on a daemon
hit (render it exactly as the in-process path would have) or `Err(reason)`
meaning "fall back to in-process, nothing user-visible happened". Nine CLI
commands are wired through it today: `frob perf hot --json`
(`frob_perf_hot`), `frob graph query` (`frob_graph_query`), `frob graph
affects` (`frob_affects`), `frob stats` (`frob_stats`), `frob test`'s
touched-set path (`frob_run_touched_tests`), `frob check --only gates
--delta --json` (`frob_check_delta`), `frob ticket doable --json`
(`frob_doable_tickets`), `frob exports <path> --json` (`frob_exports`),
and `frob map --json` (`frob_map`, T-1479) (see "Proxied commands"
below); `outline`/`xref` remain the disclosed residual from T-0321's
integration map, genuinely unwired -- see "Scope cut" below.


### Decision tree

```
query(root, method, params)
  |
  +-- FROB_NO_DAEMON=1 set? --------------------------> Err(Disabled)
  |
  +-- ensure_daemon(root):
  |     send_request(root, "frob_version") to whatever
  |     may already be listening (T-1105)
  |       |
  |       +-- no daemon answered ---------------------> spawn a fresh daemon
  |       +-- daemon version != this client's version -> frob_shutdown RPC
  |       |                                              the stale daemon,
  |       |                                              then spawn a fresh
  |       |                                              one
  |       +-- daemon version matches ------------------> no-op, trust the
  |                                                       existing daemon
  |
  +-- send_request(root, method, params) over the socket
        |
        +-- Unreachable (no socket yet, just spawned) -> retry for up to
        |                                                  _SPAWN_GRACE_S
        |                                                  (1.5s), then
        |                                                  Err(Unreachable)
        +-- RemoteError (daemon returned a JSON-RPC
        |    error, e.g. unknown method) ---------------> Err(RemoteError)
        +-- Ok(result) ---------------------------------> Ok(result)
```

Every `Err` reason means the same thing to the caller: compute the answer
in-process, right now, with no surfaced daemon error and no hang -- T-1093
acceptance [1]. `FROB_NO_DAEMON=1` (acceptance [2]) short-circuits before
ANY daemon I/O, so a differential test can produce a trustworthy in-process
reference answer to diff a daemon-served one against.

### Version-skew self-heal

As of T-1105, `_daemon_proxy._query_daemon_version` asks whatever daemon
may already be running for `root` directly, over the socket, via the
`frob_version` RPC ("Version handshake (T-1105)" above) -- there is no
sidecar meta file to go stale relative to whichever process actually
happens to be running the daemon. A mismatch between the daemon's
self-reported version and the CURRENT client's own version (most likely: a
daemon spawned before a `frob` upgrade, still idling) is asked to step
aside via the `frob_shutdown` RPC (`_shutdown_stale_daemon`, replacing
T-1093's original `SIGTERM`-by-recorded-pid dance) before a fresh daemon
is spawned in its place. `_socketd.acquire_singleton_lock`'s `flock` is
still what actually guarantees exclusivity underneath; the version RPC
only decides WHEN to ask a live daemon to step aside gracefully rather
than relying on `flock` contention alone (which would just make the fresh
spawn silently lose to the stale one it should be replacing). This closes
the follow-on T-1093 disclosed (landed as T-1105).

### Daemon liveness (T-1377) and the opt-in switch (T-1379)

A unix socket file outlives the process that bound it, so its existence is
never evidence a daemon is serving. `probe_daemon` establishes liveness the
only way that is real -- a bounded connect-plus-answer round trip -- and
reports one of five `DaemonLiveness` states, each with a distinct correct
response:

| State | Meaning | Response |
| --- | --- | --- |
| `Live` | version-matched daemon answered | use it |
| `NoSocket` | no socket file | spawn |
| `Orphaned` | socket file present, connect refused | unlink it, then spawn |
| `Wedged` | listening but no answer in budget | do NOT spawn a rival; run in-process |
| `VersionSkew` | answered with a different version | graceful shutdown, then spawn |

The probe budget (`_PROBE_TIMEOUT_S`, 0.5s) is deliberately NOT
`send_request`'s 10s query timeout. Budgeting a health check like a real
query is what previously made an unhealthy daemon cost up to 10 seconds on
every proxying invocation, plus a spawn and a retry.

`Wedged` is the state that most needs its own branch: something is holding
the socket, so a spawned rival loses to `acquire_singleton_lock` and every
later invocation pays another failed spawn. An unclassifiable probe failure
reports `Wedged` deliberately, because that is where doing nothing is
safest.

The daemon is currently **opt-in**: `_daemon_enabled` requires
`FROB_DAEMON=1`, and `FROB_NO_DAEMON=1` still wins outright. This is a
safety default while T-1378 is open (the daemon acknowledges a
`frob_shutdown` it then ignores, leaks its multiprocessing forkserver and
resource_tracker children, and its pool competes with the foreground check
for CPU badly enough to be a net pessimization). Revert to opt-out once
T-1378 lands and the daemon demonstrably beats the in-process path.

### Proxied commands

- `frob perf hot --json` -> `frob_perf_hot` -- the CLI's own in-process
  `--json` payload (`section_key`/`kind`/`label`/`p50`/`p90`/`sample_count`
  per row) is built field-for-field identically to `frob_perf_hot`'s
  `Result[list[dict], ServeError]` shape, so a daemon hit serializes to
  exactly the same JSON `frob perf hot --json` would have printed computing
  it locally -- proven by
  `tests/test_app_daemon_proxy.py::TestDifferentialParity`, a real
  subprocess-vs-subprocess (`FROB_NO_DAEMON=1` in-process vs a live daemon)
  diff of the rendered payload.
- `frob graph affects <ref> --json` -> `frob_affects` (T-1106): the ONE
  reconciliation needed was a key rename -- the RPC's dict uses `ref`,
  the CLI's own `_affects_json_payload` uses `root`, for the identical
  `AffectedSet` fields otherwise (`dependents`/`docs`/`tests`/
  `truncated`). `graph_runner._affects_payload_from_daemon` does that one
  rename; every other field is passed through verbatim. Proven the same
  way as `frob perf hot --json` above --
  `tests/test_app_daemon_proxy.py::TestDifferentialParity::
  test_graph_affects_json_daemon_matches_in_process`, a real
  subprocess-vs-subprocess diff.
- `frob graph query <ref> --json` -> `frob_graph_query` (T-1128): the
  RPC's dict was missing `span`/`digests` and trimmed each edge to two
  fields (`kind`/`target` or `src`/`kind`) instead of the full `Edge`
  model -- extended `frob_graph_query` to return `span`/`digests` plus
  each edge's own `model_dump()`, field-for-field identical to
  `graph_runner._query_json_payload`'s own shape; no CLI-side reshape
  needed at all beyond calling `query()`. Proven by
  `tests/test_app_daemon_proxy.py::TestDifferentialParity::
  test_graph_query_json_daemon_matches_in_process`.
- `frob ticket doable --json` -> `frob_doable_tickets` (T-1128): the RPC
  returned only `id`/`title`/`kind` per ticket; the CLI's own `--json`
  dumps `t.model_dump(mode="json")` per row -- the FULL ticket model.
  Extended `frob_doable_tickets` to return the full `model_dump`, and to
  pass `root` through to `doable()` (the CLI already does, for the
  lease-collision-demotion behavior `root` enables) so an over-broad
  holder lease demotes to warn-only exactly the same way in both paths.
  Only wired for the plain (no `--show-blocked`/`--ignore-lease`/
  `--sprint`) invocation -- the RPC has no parameter for any of those, so
  `_try_doable_via_daemon` falls through to the in-process path whenever
  one is set. Proven by `tests/test_app_daemon_proxy.py::
  TestDifferentialParity::test_doable_tickets_json_daemon_matches_in_process`.
- `frob test --json` (touched-set, no `--all`/`--lang`/`--fallback`) ->
  `frob_run_touched_tests` (T-1128): the RPC returned a flat
  `base`/`touched`/`ok`/`outcomes` dict (each outcome missing `argv`); the
  CLI's own `--json` dumps `test_run.model_dump_json()` -- the full
  `TestRunReport` (`selection`/`outcomes`/`ok`). Extended `frob_run_
  touched_tests` to return `test_run.model_dump(mode="json")` verbatim.
  The CLI's own "nothing touched selects any test" early-return path
  never calls `run_selected` at all and prints just the bare
  `SelectionReport`; `_try_touched_via_daemon` detects the same empty-
  selection case from the RPC's nested `selection` key and reprints just
  that sub-payload, keeping both branches byte-for-byte identical, not
  just the non-empty one. Proven by `tests/test_app_daemon_proxy.py::
  TestDifferentialParity::test_touched_tests_json_daemon_matches_in_process`.
- `frob check --only gates --delta --json` -> `frob_check_delta`'s
  `check_result` key (T-1147): the ONE narrow `frob check --json`
  invocation shape this RPC can fully answer -- `--only gates` alone (no
  other tool stage or individual gate id mixed in), a single detected
  language (python, no polyglot `SKIPPED` siblings), no `deploy/` stage
  to append, and `--delta` itself set. `_try_check_delta_via_daemon`
  (`check_runner.py`) detects exactly this shape before dispatch and
  proxies; anything else (a plain `frob check --json` full multi-tool
  run, a mixed `--only`, no `--delta`, a polyglot/deploy project) falls
  through to the in-process path unchanged, same contract every other
  `_try_*_via_daemon` function here follows. See "Scope cut (disclosed)"
  below for why the FULL multi-tool `--json` shape stays out of scope.
  Proven by `tests/test_app_daemon_proxy.py::TestDifferentialParity::
  test_check_delta_gates_only_json_daemon_matches_in_process` -- one
  caveat disclosed there and not elsewhere in this doc: the rendered
  `gate-summary` `ToolResult`'s own per-gate wall/cpu timing blob is
  GENUINELY non-reproducible between two independent process runs (one
  warm-cache via the daemon, one cold in-process), so that one test
  normalizes just the timing segment out before comparing -- every other
  field (every violation, diagnostic, per-family `ToolResult`, and the
  summary's own error/warning/waived counts) is still asserted
  byte-for-byte.

### Scope cut (disclosed)

T-0321's integration map names `outline`/`map`/`xref`/`parse`/`graph`/
`exports`/`bind`/`docs`/`stats` as eventual proxy targets alongside `check
--delta`-style reads. T-1128 wired `frob_graph_query`/`frob_doable_tickets`/
`frob_run_touched_tests` through `query()` (just above), each needing its
`_tools` counterpart EXTENDED to match the CLI's own `--json` shape rather
than a pure CLI-side reshape (T-1106's `frob_affects` precedent was the one
exception needing only a rename). `frob_check_delta` was investigated by
T-1128 and NOT wired that ticket: `frob check --delta`'s CLI JSON payload
is `_run_all_stages`'s full multi-tool `CheckResult` (ruff/ty/arch/cycle/
dup/bind/exports/deploy-stage `ToolResult`s, gates among them) -- `--delta`
itself only filters the ONE `gates` `ToolResult` inside that larger
payload (`_dispatch_check_python`'s `delta=cfg.check_delta` kwarg threads
into `run_check`, not into ruff/ty/arch/etc). `frob_check_delta`'s
PRE-T-1147 RPC answered only the gates-violations-delta question in
isolation -- a genuinely different, narrower shape than what `frob check
--delta --json` prints, not a key-rename or a missing-fields gap the way
the other three were.

T-1147 chose the second of T-1128's two candidate directions rather than
running the entire non-gate tool pipeline inside the RPC (still judged
too large -- it would duplicate `check_runner.py`'s own multi-tool
dispatch logic server-side for no real gain, since ruff/ty/arch/etc never
touch the daemon's warm graph/baseline cache the way gates does): widen
`frob_check_delta` to render the exact SAME per-gate-family `ToolResult`
list the CLI's own `--only gates --delta --json` path builds (reusing
`frob.check._python._gates_success_result` directly, not a second
hand-built summary), then detect, CLI-side, the ONE invocation shape
where that narrower answer already IS the complete answer -- see
"Proxied commands" above (`_try_check_delta_via_daemon`). The FULL
multi-tool `frob check --json` (no `--only gates`) shape stays
genuinely out of scope for the same reason it was before: reconciling it
would still mean either running ruff/ty/arch/cycle/dup/bind/exports
inside the RPC too, or reshaping a DIFFERENT payload per possible
`--only` combination -- neither is what this ticket's "reconcile the
CLI payload with the RPC" mandate asked for, and no invocation shape
touching a non-gate tool is proxied by this change. `frob ticket doable`
specifically was left unwired again in T-1106: `src/frob/app/
ticket_runner/` (now a package, not a single file) was a CONTENDED path
that wave (a sibling ticket's own scope), and T-1106's own scope was deliberately
narrowed to files with no such collision (`_daemon_proxy.py`,
`graph_runner.py`, their tests) rather than risk a merge collision over
a single additional wired command.
- `outline`/`map`/`xref` were, for a time, scheduled for REMOVAL by
  T-0802's 2026-10-01 navigation-command sunset; T-0802 was DROPPED
  2026-07-29 (superseded -- the user chose regrouping over sunset, T-1238:
  all three move under `frob explore` and are un-deprecated, staying as
  permanent top-level aliases) before this note was ever corrected here,
  so it stayed stale citing a decision no longer in force. `map` got a
  real RPC (T-1479, `frob_map`, below) once the sunset concern was
  confirmed void. `outline`/`xref` remain genuinely unwired -- a disclosed
  subset choice this ticket made (see its own Done report for why `map`
  specifically), not evidence either is still scheduled to disappear.

### `frob exports <path> --json` / `frob stats --json` (T-1127)

`frob_exports`/`frob_stats` are the two commands T-1106's own disclosure
named as having NO `frob.serve._tools` RPC surface at all (`_TOOL_
DISPATCH` had no `frob_exports`/`frob_stats` entry). Both now do:

- `frob_stats(root, *, window_days=30)` -- the DEFAULT (non-`--agentic`)
  `frob stats --json` render only; returns `StatsReport.model_dump(mode=
  "json")` verbatim, field-for-field identical since both sides dump the
  identical pydantic model. `--agentic` (env-var-triggered via
  `FROB_STATS_AGENTIC`) reads a completely different report shape
  (`frob.stats.agentic_report`'s `AgenticReport`) and is out of this RPC's
  scope entirely -- `_try_stats_via_daemon` never calls `frob_stats` for
  that mode.
- `frob_exports(root, pkg_dir, *, include_private=False, exclude_modules=
  ())` -- the DEFAULT (non-`--consumers`, non-`--write`) `frob exports
  <path> --json` render only; returns `ExportsResult.model_dump(mode=
  "json")` verbatim. Unlike every other proxied RPC (which all answer for
  the whole `root` the daemon itself was spawned for), `frob exports`
  answers for one SUBDIRECTORY of that root -- `pkg_dir` is a separate,
  explicit RPC param (the client's own `<path>` argument, sent verbatim)
  rather than assumed to equal `root`, since the daemon connected to via
  `root` (found via `frob.gitio.repo_root(pkg_dir)`, not `pkg_dir` itself)
  lives at the repo root, not the subdirectory. `pkg_dir` is resolved
  relative to the DAEMON PROCESS's own cwd server-side (`exports_package
  (Path(pkg_dir), ...)`'s own `.is_dir()`/`.glob()` calls) -- true for a
  freshly-spawned daemon (`ensure_daemon`'s spawn inherits the calling
  process's cwd) but a KNOWN, disclosed edge for a long-lived daemon
  queried later from a different cwd than it was spawned from; the
  fixed-arity, whole-repo RPCs above do not share this caveat since they
  never resolve a client-relative path server-side at all.

Both proxied the same way as every other command:
`_try_stats_via_daemon`/`_try_exports_via_daemon` in `frob.app.
stats_runner`/`frob.app.exports_runner` try `query()` first, falling
through to the in-process path on any `Err`. Proven by real
subprocess-vs-subprocess diffs: `tests/test_app_daemon_proxy.py::
TestDifferentialParity::test_stats_json_daemon_matches_in_process` /
`::test_exports_json_daemon_matches_in_process`.

### `frob map --json` (T-1479)

`frob_map(root, *, depth=None)` returns `MapResult.model_dump(mode=
"json")` verbatim -- field-for-field identical to `frob map --json`'s own
`result.as_json()`, same "dump the identical pydantic model" shape as
`frob_stats` above, `map_project` itself never returning a `Result` (an
`OSError` from a filesystem race between the walk and a per-file read is
the one documented failure mode, caught server-side and reported as
`ServeError.MapFailed`).

Narrower than `frob_exports`'s subdirectory-echo convention: `frob_map`
only ever answers for `root` itself (the daemon's own served root), not
an arbitrary client-supplied subdirectory -- `_try_map_via_daemon`
(`frob.app.map_runner`) proxies only when `cfg.map_path` is unset or
exactly `.`, falling through to the in-process path for any other target
(`frob map <subdir>`) rather than replicating `frob_exports`'s dedicated
cwd-relative resolution convention for this first pass. Proven by
`tests/test_app_daemon_proxy.py::TestDifferentialParity::
test_map_json_daemon_matches_in_process`.

## CLI

```
frob serve [path]
```

Starts the stdio MCP server rooted at `path` (default `.`), plus the T-0733
background daemon (post-land re-verify + rebase-bot) described above.
Intended to be launched by an MCP client (e.g. an editor or agent
harness), not run interactively.

## Packaging

The `mcp` SDK is `frob`'s own `[project.optional-dependencies].serve` extra in `pyproject.toml` (mirroring
`.smt`'s `z3-solver`): `uv pip install "frob[serve]"` or
`uv sync --extra serve`. `make install-tool` passes `--extra serve` to `uv
tool install` so the globally-installed `frob` binary gets it too, instead
of independently pinning a second `mcp` version via a bare `--with` (T-0177
-- one version constraint, in `pyproject.toml`, not two that can drift).
`_require_mcp`'s remedy message names both install paths.

## Deviations

- No write/mutating tools are exposed by design (T-0010's scope is
  enforcement *queries*); `frob ack`, `frob ticket new/transition`, etc.
  remain CLI-only. `frob_run_touched_tests` is the one exception that
  spawns subprocesses (test runners) -- it still mutates nothing frob-owned
  (no ticket/lock/graph-cache write beyond the normal incremental build a
  read tool already performs).
- The T-0733 daemon (`_daemon._start_daemon`) is likewise read-only against
  frob-owned state: `_poll_post_land`'s delta/touched-tests pass and
  `_poll_rebase_bot`'s `git merge-tree` simulation both only ever read (no
  ticket/lock/ledger write, no worktree checkout, no branch switch); the
  only thing they mutate is the in-process `_DaemonStatus` cache and,
  transitively through the warm-state rebuild, the same on-disk
  `.frob/cache.db` graph/test-collection cache a normal read tool call
  already writes.
