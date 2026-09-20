---
id: T-4649
title: TICK008 real-repo smoke test exceeds 120s on posix under fleet load
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_tick.py
- src/frob/tickets/_store.py
- src/frob/tickets/_leases.py
- tests/unit/test_store_mode_memoization.py
- src/frob/tickets/_doable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_store.py
  reason: memoize _store_mode / fix per-call re-scan for TICK008 perf fix
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: memoize _store_mode / fix per-call re-scan for TICK008 perf fix
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_store_mode_memoization.py
  reason: new test file for _store_mode memoization fix (test_ticket_store.py is leased
    by T-4632)
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: memoize _store_mode / fix per-call re-scan for TICK008 perf fix
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_memoized
- tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_invalidates_new
- tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_store_mode_cache_invalidates_on_archive
- tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_store_mode_cache_is_per_root
designated_repro_test: tests/unit/test_store_mode_memoization.py::TestStoreModeMemo::test_memoized
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35448990233 (dev tip beedd71c4) failed mac+ubuntu (NOT windows) with a STALL-DETECTED worker crash: tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean exceeded its 120s per-test timeout (thread-method os._exit, 120.1-120.3s elapsed), cascading into 3 collateral land-lock-guard test failures in the same aborted xdist run (test_ticket_reconcile/_parent/_priority LandInProgressGuard tests). This test calls frob.tickets.load_queue(root) against this repo's OWN live tickets/ directory (currently 1000+ ticket dirs and growing under active multi-agent fleet load) and runs the full TICK008 gate over it -- a real-repo smoke test whose cost scales with the live ledger size and is exposed to lock contention from concurrent frob ticket writers, not a fixed-cost unit test. Only mac/ubuntu hit the 120s ceiling in this run; windows completed the full suite without stalling. Investigate whether this is a genuine hang (deadlock/livelock in load_queue under concurrent ticket writes) or purely load/scale-dependent (ledger has grown well past whatever baseline the 120s timeout was calibrated against); reproduce locally with faulthandler and measure wall time outside CI load. If load-dependent, raise the timeout with a measured justification citing current ledger size; if a genuine hang, fix it.

## DIAGNOSIS (reproduced locally, 2026-09-19, worktree t-draft-cdd5b1eb)

Reproduced deterministically: `python -X faulthandler -m pytest
tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean
-p no:xdist` under `timeout 150`, PYTHONFAULTHANDLER=1. real=2m10s against this repo's live ledger
(1013 active ticket dirs at measurement time). NOT a deadlock/lock wait -- faulthandler's stack dump
at the 150s mark shows live CPU-bound Python execution the whole time, deep in:

  _tickets_gate_inner -> _tick007_undispatched_stale -> doable(queue, root)
    -> [per-ticket list comprehension] leased_by(...) -> _leased_by_one_holder
    -> same_worktree_lease -> read_all_leases(root) -> _live_leases_pruning_stale
    -> [per-lease loop] _prune_one_lease_record -> _ticket_ledger_staleness_shape
    -> _store_mode(root) -> _v2_glob(root) + _v2_archive_glob(root)
    -> Path.glob('T-*/ticket.md') -- a FRESH directory scan of the whole tickets/ tree

`_store_mode` (src/frob/tickets/_store.py) does two full `tickets/` directory globs on every call
and has no caching. It is called from `_ticket_ledger_staleness_shape`
(src/frob/tickets/_leases.py), which runs inside `_prune_one_lease_record`, which runs once PER
LEASE inside `read_all_leases`, which `doable()` (src/frob/tickets/_doable.py) calls once PER
CANDIDATE TICKET while filtering for lease collisions. Net cost is O(active_tickets x live_leases)
full-tree glob scans, not O(active_tickets + live_leases) -- genuinely quadratic in this repo's own
live ledger size, and it scales directly with fleet concurrency (more concurrent worktrees = more
live leases = more repeated glob scans per `doable()` call). At today's scale (1013 tickets, ~20+
concurrent leases under active fleet load per `ls .git/frob-leases/ | wc -l` = 45 lease files seen
mid-investigation) this comfortably exceeds a 120s per-test budget; it did not exceed it on windows
in the same CI run purely because windows' filesystem/scheduler timing and/or lower concurrent lease
count at that moment happened to land under the ceiling, not because windows is architecturally
immune -- this is a real, reproducible perf defect, not a flake, and not deadlock.

REMEDIATION NOT LANDED HERE: the actual fix (memoize `_store_mode(root)` per `doable()`/
`read_all_leases()` invocation, e.g. via an explicit cache keyed by root passed down the call chain,
or lru_cache with an invalidation hook) touches src/frob/tickets/_store.py and
src/frob/tickets/_leases.py, BOTH of which are currently held by other in-progress tickets' leases
at investigation time (`.git/frob-leases/T-4625.json` covers _store.py, `.git/frob-leases/T-4632.json`
covers _leases.py) -- landing a change there now would collide with two live worktrees mid-edit on
the exact same hot path. Per the standing brief's scope-collision rule, this ticket does NOT expand
its own scope onto those files; it is left BLOCKED pending either those tickets landing (freeing the
lease) or a coordinator decision to sequence this fix explicitly. A raised CI timeout is a papering
workaround, not a real fix, given the underlying cost is genuinely quadratic and will only get worse
as tickets/ grows -- recommend a dedicated perf ticket (memoize _store_mode) be prioritized instead
of bumping the 120s ceiling.

## Unblock log
- 2026-09-19: unblocked by T-4625 -- prior blocked_by T-4625 was based on a substring false-match (grep for _store.py/_leases.py hit test_ticket_store.py/test_ticket_leases.py); verified via exact lease-scope inspection that no lease file (incl T-4625.json, T-4632.json) actually scopes src/frob/tickets/_store.py or _leases.py; proceeding with the fix in this ticket own worktree