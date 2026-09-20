## Done report

MEASURED ROOT CAUSE (cProfile, real repo data): one call to
`frob.tickets._archive.load_queue` costs ~10.2s on this repo's ~4200-ticket
active+archive ledger (YAML frontmatter parse dominates). `frob check --only
tickets` did not finish within 540s via the CLI while the same tickets gate
called in-process with an already-loaded queue took ~2.8s -- the gap is
`tickets_gate()` internally re-triggering `load_queue` once PER LEASE FILE,
via TWO independent paths, not one:

1. `_tick010_holder_dead_pass` (T-4319) calls `frob.tickets._leases.
   lease_staleness_reason` once per lease; that judgement's
   `_ticket_ledger_staleness_shape` helper calls `load_queue(root)` fresh
   every time.
2. `frob.tickets._leases.read_all_leases`'s own `_live_leases_pruning_stale`
   calls the SAME `lease_staleness_reason` per lease -- reached from
   `tickets_gate` via `_tick007_undispatched_stale`'s `doable()` call AND
   directly by `_tick012_lease_scope_drift`.

So N leases meant up to 3N full ~4200-ticket ledger re-parses in one `frob
check` run, on top of the one legitimate load `run_gates`'s own
`_load_graph_queue_lock` already did -- confirmed live: this repo's own
`.git/frob-leases/` currently holds real holder-dead leases (T-4392,
T-4393) that exercise exactly this path.

FIX (contained per the coordination note -- another agent holds
`src/frob/tickets/_leases.py`, so nothing there was touched):
`frob.tickets._archive.load_queue_run_scope()` is a new, self-contained,
reentrant, run-scoped cache for `load_queue`, OFF by default (every one of
`load_queue`'s ~45 other call sites -- ticket commands, CLI runners, `frob
serve` -- sees the exact same fresh-read-every-call behavior it always
has). `frob.gates._tickets_gate.tickets_gate` now enters that scope once
around its WHOLE body (split into `tickets_gate`/`_tickets_gate_inner` so
the wrap is one `with`), so every lease-touching pass it runs (TICK007's
`doable()` call, TICK010's own pass, TICK012) shares one cached ledger
read for the run instead of each re-triggering its own O(leases) walk.

Deliberately NOT `frob.check._memo.memoize_per_run`: that would add an
undeclared `tickets_ledger -> checker` component edge (SYS003) -- the
declared flow (design/frob.strata) is `checker -> tickets_ledger`, the
other direction. The self-contained cache avoids that architecture
violation entirely while giving the identical opt-in, reentrant,
clear-on-outermost-exit semantics.

### Measured before/after
- Before (per the coordinator's prior measurement): `frob check --only
  tickets` via the CLI did not finish within 540s; the full `frob check`
  exceeded 1800s.
- After (this fix, same repo, real `.git/frob-leases/` state including two
  genuine holder-dead leases T-4392/T-4393): `frob check --only tickets`
  completed in 50.6s wall (`tickets=17.95s` per the gate-summary timing
  breakdown), twice, reproducibly.
- Isolated proof (cProfile + a debug harness replaying the exact call
  graph): with N=2 synthetic holder-dead leases, `_load_merged` (the real
  parse behind `load_queue`) ran 5 times through `tickets_gate()` before
  the fix (`_tick010_holder_dead_pass` once + `read_all_leases` via TICK007
  + TICK012, each re-triggering `_ticket_ledger_staleness_shape` ->
  `load_queue`); 1 time after.

### Changed
- `src/frob/tickets/_archive.py`: `load_queue_run_scope()` (new
  contextmanager) + `load_queue` cache-check; `frob:waive LARGE001`
  (file already 803 lines on main, now over threshold) and
  `frob:waive AFFECT002` (perf-only change, no dependent doc to update,
  T-3478 precedent).
- `src/frob/gates/_tickets_gate.py`: `tickets_gate` now a thin wrapper
  entering `load_queue_run_scope()` around a new `_tickets_gate_inner`
  (the original body, unchanged rule logic).
- `tests/gates_suite/test_run.py`: `TestLoadQueueMemoization` (3 new
  tests) -- planted 10 holder-dead leases, asserted `_load_merged` runs
  at most twice total across a WHOLE `tickets_gate()` call (not per
  lease, not per pass); asserted caching is OFF outside the scope;
  asserted the scope's own two-callers-share-one-load contract directly.

### Evidence
- `tests/gates_suite/test_run.py::TestLoadQueueMemoization.test_load_queue_is_memoized_across_the_whole_tickets_gate_call`
- `tests/gates_suite/test_run.py::TestLoadQueueMemoization.test_load_queue_reloads_outside_a_run_scope`
- `tests/gates_suite/test_run.py::TestLoadQueueMemoization.test_load_queue_run_scope_caches_within_the_with_block`
- Full local runs green: `tests/gates_suite/test_run.py`,
  `tests/test_gates_tick009_tick010.py`, `tests/test_ticket_leases.py`,
  `tests/test_tickets.py` -- 400/400 passed.
- `--check-repro` on the new evidence returns `TEST_ABSENT_AT_PARENT`
  against `main` -- expected per docs/modules/tickets.md#check-repro-post-land-limitation-t-2025
  (a brand-new test at a fresh worktree has no pre-fix ancestor commit to
  diff against; not a failed verdict).

### Filed
- No new tickets filed. The searched draft id from the brief
  (`T-draft-44b1f40d`) does not exist anywhere in this repo (active,
  archive, or any worktree) -- filed this work as a fresh ticket,
  T-4397, instead of promoting a nonexistent draft.

### Gates
`uv run frob check --ticket T-4397` clean of anything caused by
this diff: AFFECT/COV/LANDPARITY/PRE/SYS all resolved (waived or fixed);
remaining FAILs (ruff-format on `gates/__init__.py`, DRIFT001 on untouched
`_leases.py::read_all_leases`, LARGE001 on two unrelated files, REG005 on
`docs/design/registry/check-coverage.yaml`, TICK gate's repo-wide 13-error
backlog) are pre-existing, repo-wide, and unchanged in count by this diff
(verified: none reference `_archive.py`, `_tickets_gate.py`, or
`test_run.py`; `--ticket` scopes only SCOPE/PREWORK/diff-driven checks to
this ticket, every other gate family's count is repo-wide per the tool's
own note).

### Changed
```
 tickets/T-4397/ticket.md | 65 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 65 insertions(+)
```

### Evidence
- `tests/gates_suite/test_run.py::TestLoadQueueMemoization::test_load_queue_is_memoized_across_the_whole_tickets_gate_call` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestLoadQueueMemoization::test_load_queue_reloads_outside_a_run_scope` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestLoadQueueMemoization::test_load_queue_run_scope_caches_within_the_with_block` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 7 error(s), 4784 warning(s), 963 waived
- error-findings: DRIFT001@src/frob/tickets/_leases.py, LARGE001@src/frob/app/verify_runner.py, LARGE001@src/frob/testing/_collect.py, REG005@docs/design/registry/check-coverage.yaml, TICK004@tickets.md, TICK006@tickets.md, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4393.json
