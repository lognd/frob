---
id: T-4292
title: formatter drift in _leases.py/test_fleet_land.py/test_process_tty.py/test_ticket_leases.py
  needs a scope-closure-aware plan
state: dropped
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
- tests/unit/coordinator_suite/test_fleet_land.py
- tests/unit/test_process_tty.py
scope_breadth_ack: true
scope_breadth_ack_reason: scope is exactly the 4 files ruff format wants to rewrite;
  the closure problem is the ticket's actual subject
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob format currently wants to reformat 4 files: src/frob/tickets/_leases.py, tests/test_ticket_leases.py, tests/unit/coordinator_suite/test_fleet_land.py, tests/unit/test_process_tty.py -- these are whitespace-only ruff-format rewrites, no logic change.

Found while working T-4290 (the last unowned self-gate errors), which owns exactly this formatter drift per its own description. Reformatting these 4 files and widening T-4290's scope to cover them (via frob ticket scope --add) is straightforward on its face, but _leases.py in particular is heavily cross-referenced: doing so triggers 20 SCOPE002 errors demanding the ticket's scope also swallow docs/modules/gates.md, docs/modules/tickets-landing.md, docs/modules/tickets-lifecycle.md, scripts/fleet_status.py, src/frob/app/ticket_runner/__init__.py, src/frob/app/worktree_runner.py, src/frob/process/_tty.py, src/frob/tickets/_worktree_sweep.py, tests/gates/test_tdd_order.py, tests/system/test_spawn_budget.py, tests/test_ticket_leases_cross_worktree.py, tests/test_ticket_ownership_guard.py, tests/test_tickets_leases.py, tests/unit/test_land_cross_ticket_leakage.py, tests/unit/test_land_finish_guard.py, and private-helper call sites into src/frob/tickets/__init__.py, _land.py, _store.py, _worktree_sweep.py, tests/unit/conftest.py -- a whole-file-scope pure-formatting change should not need to swallow that much closure. Two of the flagged symbols also carry frob:ticket anchors to now-DONE tickets (T-2714, T-4273), which is why COV002 fires the moment the file enters any ticket's scope at all.

This needs a deliberate call on whether SCOPE002's closure rule should treat a formatter-only (AST-preserving) diff differently from a semantic one, or whether the real fix is retiring the stale T-2714/T-4273 frob:ticket anchors so a future formatting touch does not trip COV002, before anyone commits the reformat. T-4290 declined to force this through and left the 4 files unformatted; the anchor/coverage errors T-4290 actually owned (the two private doc anchors) are fixed separately.

## Drop reason
- 2026-09-08: premise no longer holds on main: T-4290 (5b2594718..44b8e5166) already reformatted these exact 4 files; 'frob format --check' on all 4 now reports 0 changes -- verified 2026-09-08
