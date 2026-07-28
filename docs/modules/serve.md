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
