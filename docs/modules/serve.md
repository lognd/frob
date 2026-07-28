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
  contract" below.
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
(`debt`'s `current_date`/`current_version`) is unchanged. `TrackedSnapshot`
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

(T-0733) `run_stdio` starts a background daemon thread (`frob.serve.
_daemon._start_daemon`) alongside the MCP transport, running one cycle
(`_run_daemon_cycle`) every `DEFAULT_POLL_INTERVAL_S` (20s) for the life of
the `frob serve` process. Two jobs per cycle:

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

Both jobs write into one `_DaemonStatus` cache per repo root (mirroring
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
meaning "fall back to in-process, nothing user-visible happened". Today
`frob perf hot --json` is the one CLI command wired through it (see
"Proxied commands" below); every other query-shaped subcommand this ticket's
epic (T-0321) names is a disclosed residual, not yet wired -- see "Scope
cut" below.

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
the follow-on T-1093 disclosed (T-draft-8a56400c).

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

### Scope cut (disclosed)

T-0321's integration map names `outline`/`map`/`xref`/`parse`/`graph`/
`exports`/`bind`/`docs`/`stats` as eventual proxy targets alongside `check
--delta`-style reads. `_socketd._TOOL_DISPATCH` (T-1092) only exposes ten
methods today; most STILL have no field-for-field-identical CLI JSON
payload to diff against (e.g. `frob_graph_query`'s dict omits `span`/
`digests` that `frob graph query --json` prints) -- `frob_affects` (T-1106,
just above) was the one exception needing only a single key rename to
reconcile, not a deeper shape mismatch. This ticket wires that one
additional command (on top of T-1093's `frob perf hot --json`) rather
than force a shape mismatch onto the remaining commands just to claim
broader coverage. Wiring `frob_graph_query`/`frob_check_delta`/
`frob_run_touched_tests`/`frob_doable_tickets` through the same `query()`
seam is straightforward follow-on work once each CLI payload is
reconciled field-for-field with its `_tools` counterpart (or the
counterpart is extended to match) -- tracked as T-draft-296d0d77. `frob
ticket doable` specifically was left unwired again this ticket:
`src/frob/app/ticket_runner.py` was a CONTENDED file this wave (a
sibling ticket's own scope), and T-1106's own scope was deliberately
narrowed to files with no such collision (`_daemon_proxy.py`,
`graph_runner.py`, their tests) rather than risk a merge collision over
a single additional wired command.
- `outline`/`map`/`xref`/`exports`/`stats` are a separate, larger
  disclosed gap from `frob_graph_query`'s: none of the five has ANY
  `frob.serve._tools` RPC method exposing them at all yet (`_TOOL_
  DISPATCH` has no `frob_outline`/`frob_map`/`frob_xref`/`frob_exports`/
  `frob_stats` entry) -- wiring these needs new server-side tool functions
  first (`src/frob/serve/_tools.py`, out of this ticket's `src/frob/app/`
  scope entirely, not just a CLI-side reconciliation), tracked alongside
  T-draft-296d0d77 as the same follow-on epic tail.

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
