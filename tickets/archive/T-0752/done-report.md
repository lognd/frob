## Done report

Implemented all three display-layer asks against `frob ticket doable`'s default (non-json, non-show-blocked) render:

1. PRIORITY COLUMN: every row (dispatchable and in-flight) now prints `priority=<level>`.
2. IN-FLIGHT/DISPATCHABLE SPLIT: `has_live_lease` (new, reuses `display_state`'s existing `read_all_leases` overlay from T-0716 -- no second lease-read path) partitions `doable()`'s result; rows with a live lease against them render under a separate "In-flight (leased, already being worked)" section below the dispatchable ones.
3. STALENESS ALARM: `undispatched_stale` (new) flags any CRITICAL/HIGH dispatchable ticket whose `dispatch_stale_hours` (measured from `Ticket.created`, the only timestamp the ticket model carries -- see deviation below) exceeds a per-priority `frob.toml [tickets]` threshold (`dispatch_stale_critical_hours`/`dispatch_stale_high_hours`, defaulting to 4h/24h). Alarmed rows sort to the top of the dispatchable section and print a `[UNDISPATCHED Xh > Yh threshold]` suffix.

`--json`/`--ignore-lease` output is unchanged (raw `doable()` result) -- the split/alarm are display-only, matching the ticket's ask that this stay a rendering concern.

DOCS (reviewer ride-along gap, closed): `docs/modules/tickets.md`'s Scope-lease model section documents the two new `frob.toml [tickets]` keys (`dispatch_stale_critical_hours`/`dispatch_stale_high_hours`, matching the existing `large_glob_max_files` entry's style), and the Public API section's `frob:describes` list plus its python code-block gained `has_live_lease`, `dispatch_stale_hours`, and `undispatched_stale` entries.

SPAWN-DISCIPLINE FIX (land blocker, closed): the FIRST landed version of `_doable` computed `breadth = scope_breadth_context(root)` once (one `git ls-files` spawn) for its own warnings, but called `doable(queue, root, ignore_lease=...)` with no way to pass that `breadth` through -- `doable()` had no such kwarg, so its internal `leased_by` filter recomputed `scope_breadth_context` itself, a SECOND `git ls-files` spawn per invocation. This regressed the T-0773 spawn-budget guarantee and failed `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` once current main was merged in for land. Fixed by giving `doable()` the exact same `breadth: tuple[int, tuple[str, ...]] | None = None` kwarg `doable_blocked()` already carries (mirrored precisely: `if root is not None and breadth is None: breadth = scope_breadth_context(root)`), and threading `_doable`'s precomputed `breadth` into the `doable(...)` call. `frob ticket doable`'s default render is now back down to one `git ls-files` per invocation.

DEVIATION (disclosed, not silently dropped): the acceptance criterion also asks for "AND frob check emits a TICK-family warning naming it". `Ticket` has no per-transition timestamp (only `created: date`), so `dispatch_stale_hours` degrades "last state change or filing" to "filing" (`(today - created).days * 24`) -- day-granular, not true wall-clock hours; documented in the function's docstring and the module doc. Wiring an actual TICK-family `frob check` gate warning requires touching `src/frob/gates/__init__.py`, OUTSIDE T-0752's declared scope (`src/frob/tickets/**`, `src/frob/app/ticket_runner.py`, `docs/modules/tickets.md`). Built the alarm judgment as a single reusable library function (`frob.tickets.undispatched_stale`) precisely so a future gate can call it with zero duplicated lease/staleness logic, and filed T-0820 to do that wiring. The ticket's single acceptance criterion is left UNBOUND rather than force-bound.

T-0752's `blocked_by=['T-0716']` was stale at start-of-work: T-0716 is `[done]` -- ticket start proceeded normally.

Verification run in this worktree (final pass, current main merged):
- `uv run --frozen pytest tests/system/test_spawn_budget.py tests/test_tickets_dispatch_stale.py -q` -> 14 passed, 0 failed (spawn-budget duplicate-argv assertion green)
- `uv run ruff check` / `uv run ruff format --check` and bare PATH `ruff check` / `ruff format --check` on the touched files -> clean under both
- Chunked `uv run --frozen frob check --ticket T-0752 --only <lint|static|gates-fast|gates-native|gates-security>` -> all 0 errors (gates-fast FAILed and was fixed across several passes this ticket's history: missing frob:doc/frob:tests/frob:ticket directives + stale pre-work sweeps each time source changed, always resolved by adding the directive/re-running `frob ticket sweep T-0752`)
- `uv run --frozen frob test --base main` -> touched-set selection, prior pass `[PASS] python exit=0 2.45s`; re-verified green via the direct pytest run above after the spawn-discipline fix

Left unmodified: `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes` fails on this worktree both before and after my change (pre-existing strata sys_runner REL200 fixture failure, unrelated to tickets/ticket_runner) -- not touched, not in scope.

### Changed
```
 docs/modules/tickets.md              |  36 +++++++
 src/frob/app/ticket_runner.py        |  67 ++++++++++++-
 src/frob/tickets/__init__.py         | 131 +++++++++++++++++++++++++-
 tests/test_tickets_dispatch_stale.py | 178 +++++++++++++++++++++++++++++++++++
 4 files changed, 405 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_high_past_threshold_alarms` (pytest node id, verified passing when recorded)
- `tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_configured_threshold_from_frob_toml` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
