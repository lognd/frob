---
id: T-2800
title: 'Burn ruff I001 batch 2: tests/ subset'
state: done
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2373
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/test_ticket_land.py
- tests/test_ticket_land_proof_claims.py
- tests/test_ticket_work_and_land_finish.py
- tests/test_tickets_acceptance.py
- tests/test_tickets_lease.py
- tests/test_tickets_organization.py
- tests/test_tickets_priority.py
- tests/unit/strata/test_selfconform.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_app_runners_json_guard_t2492.py
- tests/unit/test_app_runners_t2395_contention.py
- tickets/T-2373/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-2373/ticket.md
  reason: parent epic start-transition ledger edit landed in the same worktree commit
    range
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tickets/T-2373/ticket.md
  reason: parent epic start-transition ledger edit landed in the same worktree commit
    range
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tickets/T-2373/ticket.md
  reason: parent epic start-transition ledger edit landed in the same worktree commit
    range
  actor: logan
  at: '2026-08-21'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): pure ruff I001 import-reordering fix, zero
    runtime symbol changed'
  actor: logan
  at: '2026-08-21'
  old_length: 2015
  new_length: 2115
evidence:
- tests/test_tickets_acceptance.py::TestUnboundAcceptance::test_empty_acceptance_list_is_never_unbound
- tests/unit/test_app_runners_batch6.py::TestGraphRunner::test_unknown_command_exits_1
- tests/unit/test_app_runners_json_guard_t2492.py::TestBindRunnerJsonGuard::test_planted_leak_does_not_reach_stdout
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9f7377a6650c8413ed4173a289f2791ffc850880
---
Batch 2 of T-2373's ruff I001 (import-sort) burn-down. Re-measured
2026-08-21 in a fresh worktree via
`uv run frob check --json --budget 500` (JSON-filtered for code=="I001"
directly, not hand-grepped -- this repo's filed counts have been wrong
every single time anyone checked this session, in both directions:
T-2373 itself filed 23/measured 42 for batch 1, T-2359 filed 138/
measured 184, T-1945 filed 77/measured 203 and separately 265/measured
1): 31 findings across 24 files remained after batch 1 (T-2788) landed.

This batch covers 12 of those 24 files, all under tests/:

- tests/conftest.py
- tests/test_ticket_land.py
- tests/test_ticket_land_proof_claims.py
- tests/test_ticket_work_and_land_finish.py
- tests/test_tickets_acceptance.py
- tests/test_tickets_lease.py
- tests/test_tickets_organization.py
- tests/test_tickets_priority.py
- tests/unit/strata/test_selfconform.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_app_runners_json_guard_t2492.py
- tests/unit/test_app_runners_t2395_contention.py

Deliberately excludes:
- src/frob/gates/__init__.py, _arch.py, _tickets_gate.py -- T-2359's
  live reformat lease is concentrated in src/frob/gates/, and
  _tickets_gate.py is explicitly on that agent's own stated batch-6
  list.
- src/frob/tickets/_setters.py -- left for batch 3 alongside the
  remaining 8 test files, to keep this batch's diff small.
- Checked for overlap against every OTHER live lease at pick time
  (T-2359, T-2686, T-2780 scope + scope_changes) via
  `grep -c "glob: <path>$"` against each ticket.md -- zero hits for
  every file in this batch's list.

Fix: `ruff check --select I001 --fix` on exactly these 12 files
(import reordering only). Severity promotion (I001 warning -> error)
stays DEFERRED until every sibling batch of T-2373 has landed --
flipping it early would turn every not-yet-fixed file in another
batch into a spurious new ERROR-tier finding for nobody's ticket,
which would red main for work that is already accounted for on the
parent epic.

frob:no-behavior-change reason="pure ruff I001 import-reordering fix, zero runtime symbol changed"