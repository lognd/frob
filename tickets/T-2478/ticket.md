---
id: T-2478
title: clear the 5-finding lint quarantine raised by T-1135's post-land sweep (E501
  x4, F401 x1)
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/gates/__init__.py
- src/frob/gates/_dup_graph_schema.py
- src/frob/verify/_worker.py
- src/frob/vet/_capability.py
evidence_scope:
- tests/test_capability_registry.py
- tests/unit/test_dup_graph_table_schema.py
- tests/test_serve_daemon.py
- tests/unit/test_app_runners_t2395_contention.py
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py
  reason: T-2462 holds a live lease on this file; will --add back and fix once it
    clears
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/__init__.py
  reason: T-2462's lease on this file has cleared; adding back to fix the remaining
    E501 finding
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): pure lint fix: E501 line-wraps and F401 dead-import
    removal/re-export documentation, no functional/behavioral change to any touched
    function -- confirmed via all 5 bound tests passing unchanged'
  actor: logan
  at: '2026-08-18'
  old_length: 8823
  new_length: 9051
evidence:
- tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_every_pre_registry_needle_still_fires_somewhere
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_now_fire_reports_the_undeclared_key
- tests/test_serve_daemon.py::TestPollVerifyWorker::test_head_moved_notifies_the_worker
- tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_zero_contention_is_explicit_not_silent
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 19ae14f33a5eea97a1101bb2e12dc4bbb9f7b966
---
`frob verify status` raised quarantine on 5 undisposed post-land findings
from T-1135's land -- all lint, all reached main because the land-time
check ran under a budget that silently DROPPED the whole `lint` stage
group from every post-land sweep (T-2456, fixed an hour before this
ticket, budget raised 300 -> 480 after the five stage groups were
measured to sum to ~334.6s). Lint now actually runs and catches
previously-invisible debt -- the repo did not get worse, previously-
invisible debt became visible.

Findings (exact stored strings from `frob verify status`, paths
absolute):

    E501:/home/logan/projects/frob/src/frob/app/ticket_runner/_query.py:
    E501:/home/logan/projects/frob/src/frob/gates/__init__.py:
    E501:/home/logan/projects/frob/src/frob/gates/_dup_graph_schema.py:
    E501:/home/logan/projects/frob/src/frob/verify/_worker.py:
    F401:/home/logan/projects/frob/src/frob/vet/_capability.py:

Deferred landing is OFF repo-wide while quarantine is RAISED (T-1693's
circuit breaker forces fully-synchronous verification on every land),
which is the leading edge of a known death spiral: synchronous
verification slows every land toward the ~540s wrapper cap, a killed
land leaves staged residue, and the retry hits the same wall. Clearing
quarantine restores deferred landing fleet-wide.

FIX: wrap/reflow each E501 line under 88 cols and delete the 3 genuinely
unused imports in `_capability.py` (verified: none of
`_EXT_LANGUAGE`/`_PATTERNS`/`_resolved_candidates_for_language` are in
that module's own `__all__`, and no caller imports
`_resolved_candidates_for_language` via `frob.vet._capability` --
confirmed dead, not a broken re-export). Fix the code; dispose the
quarantine findings only after the tree is clean, never before.