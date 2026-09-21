---
id: T-4641
title: TICK008 real-repo smoke test exceeds 120s on posix under fleet load
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_tick.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean
- tests/gates_suite/test_tick.py::TestTick007UndispatchedStale::test_real_repo_scan_runs_end_to_end_without_crashing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35448990233 (dev tip beedd71c4) failed mac+ubuntu (NOT windows) with a STALL-DETECTED worker crash: tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean exceeded its 120s per-test timeout (thread-method os._exit, 120.1-120.3s elapsed), cascading into 3 collateral land-lock-guard test failures in the same aborted xdist run (test_ticket_reconcile/_parent/_priority LandInProgressGuard tests). This test calls frob.tickets.load_queue(root) against this repo's OWN live tickets/ directory (currently 1000+ ticket dirs and growing under active multi-agent fleet load) and runs the full TICK008 gate over it -- a real-repo smoke test whose cost scales with the live ledger size and is exposed to lock contention from concurrent frob ticket writers, not a fixed-cost unit test. Only mac/ubuntu hit the 120s ceiling in this run; windows completed the full suite without stalling. Investigate whether this is a genuine hang (deadlock/livelock in load_queue under concurrent ticket writes) or purely load/scale-dependent (ledger has grown well past whatever baseline the 120s timeout was calibrated against); reproduce locally with faulthandler and measure wall time outside CI load. If load-dependent, raise the timeout with a measured justification citing current ledger size; if a genuine hang, fix it.