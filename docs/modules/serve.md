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
- `frob_daemon_status()` -- (T-0733) the background daemon's latest
  post-land delta/touched-tests verdict and any in-flight-worktree rebase
  conflict warnings; a pure read, never triggers a poll itself. See
  "Daemon jobs" below for what populates it.

## Warm state

<!-- frob:describes src/frob/serve/_warm.py::WarmState -->
<!-- frob:describes src/frob/serve/_warm.py::repo_dirty_key -->
<!-- frob:describes src/frob/serve/_warm.py::warm_state -->
<!-- frob:describes src/frob/serve/_warm.py::invalidate -->

`frob serve` runs as one long-lived stdio process for the life of the MCP
client session, not one process per tool call. `frob.serve._warm.WarmState`
holds, per repo root, in process memory:

1. the built `GraphSnapshot` (`frob.graph.build_graph`);
2. the stamped violation baseline (`frob.gates.load_baseline`, `None` if
   never stamped);
3. collected python pytest node ids (`frob.testing.collect_python_tests`).

`warm_state(root)` is the single entry point every tool above uses instead
of loading any of the three cold. It is keyed by `repo_dirty_key(root)`: a
`git rev-parse HEAD` + `git status --porcelain=v1 --untracked-files=all`
signature (excluding `.frob/` itself via a pathspec -- `build_graph`/
`collect_python_tests` write `.frob/cache.db` and the collection cache as a
side effect of the very build this key gates, so including it would make
every build self-invalidate on the very next call), PLUS an
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
- `invalidate(root)` drops the cached state unconditionally, forcing the
  next `warm_state` call to rebuild cold -- used by `frob_check_delta`'s
  `verify=True` path and by tests.

### Staleness/correctness contract

**What incremental reuse covers**: the graph snapshot, the baseline
document, and the collected test id set -- each is either reused verbatim
on a proven-unchanged tree, or rebuilt via its own already-incremental
on-disk mechanism otherwise. `repo_dirty_key`'s invalidation logic has a
direct correctness test (`tests/test_serve.py::TestWarmState`) plus a
property test (`test_warm_state_rebuilds_iff_tree_changed`) asserting the
vacuous-pass invariant: a rebuild happens on EVERY call that followed a
real on-disk edit, and on NO call that did not -- an obligation not
re-evaluated must not have had a changed input.

**What it does NOT cover** (scope cut, disclosed honestly rather than
implied): `frob.gates.run_gates` itself still evaluates every selected gate
in full on each `frob_check_delta` call -- there is no per-obligation
dependency-tracked partial re-evaluation inside `run_gates` today. The
"only obligations whose inputs changed" framing in T-0177's plan is
achieved at the GRAPH/baseline/test-collection layer (this module), not by
threading a pre-built snapshot into `run_gates`'s own gate dispatch, which
would require changing `_load_inputs`/`_build_jobs`'s signatures -- a
larger, separately-ticketed project (see the Done report / a filed
follow-up ticket). What `frob_check_delta` DOES guarantee: its reported
delta is always computed against a freshly-run `run_gates` pass (never a
stale cached violation list) filtered through `delta_violations`/
`is_baseline_stale` -- the same baseline-diff machinery `frob check
--delta` uses on the CLI side, so the two stay consistent by construction.

`verify=True` is the correctness guarantee for the part that IS cached: it
drops the warm cache (`invalidate`), re-runs `run_gates` fully cold, and
reports `verified` (whether the warm-cache pass and the cold pass produced
identical violation fingerprints) plus `verify_mismatch_count`. A `False`
`verified` would mean the warm graph/baseline/test cache served a stale
answer -- a bug, not an expected outcome; it is not a performance-only
knob to skip in normal use.

## Daemon jobs

<!-- frob:describes src/frob/serve/_daemon.py::PostLandVerdict -->
<!-- frob:describes src/frob/serve/_daemon.py::RebaseWarning -->
<!-- frob:describes src/frob/serve/_daemon.py::DaemonStatus -->
<!-- frob:describes src/frob/serve/_daemon.py::poll_post_land -->
<!-- frob:describes src/frob/serve/_daemon.py::poll_rebase_bot -->
<!-- frob:describes src/frob/serve/_daemon.py::daemon_status -->
<!-- frob:describes src/frob/serve/_daemon.py::run_daemon_cycle -->
<!-- frob:describes src/frob/serve/_daemon.py::start_daemon -->
<!-- frob:describes src/frob/serve/_tools.py::frob_daemon_status -->

(T-0733) `run_stdio` starts a background daemon thread (`frob.serve.
_daemon.start_daemon`) alongside the MCP transport, running one cycle
(`run_daemon_cycle`) every `DEFAULT_POLL_INTERVAL_S` (20s) for the life of
the `frob serve` process. Two jobs per cycle:

1. **Post-land re-verify** (`poll_post_land`) -- watches `main`'s resolved
   HEAD (`git rev-parse main`). If it has not moved since the last cycle,
   the cached `PostLandVerdict` is returned untouched (no re-work). If it
   moved (a land happened), the warm cache (`frob.serve._warm`) is
   invalidated and one fresh `frob_check_delta`-equivalent pass runs
   (plus, by default, the touched-set tests against `main`), and the new
   verdict replaces the cached one. At the default interval this means a
   fresh delta verdict is available via `frob_daemon_status` within
   `DEFAULT_POLL_INTERVAL_S` of any land -- comfortably inside a minute --
   without any agent or coordinator invoking `frob check` themselves.
2. **Rebase-bot** (`poll_rebase_bot`) -- for every in-flight worktree
   branch (`frob.tickets._leases.read_all_leases`, the same T-0473
   liveness signal `doable` already trusts), simulates merging current
   `main` into that branch with old-style `git merge-tree <merge-base>
   <branch> <main-head>` -- no checkout, no scratch clone, purely a
   read-only subprocess against the shared git object store. A conflict
   is detected by the presence of `<<<<<<<` markers in that command's
   stdout (this repo's git baseline, 2.34, predates the `--write-tree`
   form whose exit code reports conflicts directly). Every branch whose
   simulated merge would conflict gets a `RebaseWarning`, replacing the
   full warning set for the repo root each cycle (a branch that
   resolved clean, or that landed and dropped its lease, does not linger
   as a stale warning).

Both jobs write into one `DaemonStatus` cache per repo root (mirroring
`frob.serve._warm`'s per-root cache shape); `frob_daemon_status()` -- the
new MCP tool -- reads it back verbatim as JSON (`post_land`,
`rebase_warnings`, `last_poll_at`), never triggering a poll itself. A
`None` `post_land` or empty `rebase_warnings` means the corresponding job
has not completed a cycle yet (or, for `post_land`, that `main` could not
be resolved), not that nothing needs attention.

`run_daemon_cycle(root)` is the same single-cycle unit both the
background loop and tests call -- tests call it (or the two `poll_*`
functions directly) with no real sleep and no thread, for a deterministic
single-cycle assertion; only `start_daemon`'s loop actually sleeps between
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

The `mcp` SDK is `frob`'s own `[serve]` extra in `pyproject.toml` (mirroring
`[smt]`'s `z3-solver`): `uv pip install "frob[serve]"` or
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
- The T-0733 daemon (`_daemon.start_daemon`) is likewise read-only against
  frob-owned state: `poll_post_land`'s delta/touched-tests pass and
  `poll_rebase_bot`'s `git merge-tree` simulation both only ever read (no
  ticket/lock/ledger write, no worktree checkout, no branch switch); the
  only thing they mutate is the in-process `DaemonStatus` cache and,
  transitively through the warm-state rebuild, the same on-disk
  `.frob/cache.db` graph/test-collection cache a normal read tool call
  already writes.
