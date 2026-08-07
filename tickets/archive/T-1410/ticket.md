---
id: T-1410
title: Wire gate_claims_verified into close/land so the T-1399 guard actually fires
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/**
- src/frob/tickets/_land.py
- src/frob/gates/**
- tests/unit/test_ticket_close_gate_claims_t1410.py
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_close_gate_claims_t1410.py
  reason: T-1410's own end-to-end regression test for gate_claims_verified wiring
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: land''s affects()-closure doc must move in the same diff as
    the T-1410 gate-claim wiring'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface auto-writes new cli/testsuite symbol declarations
    for T-1410's new public helpers
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_no_gate_claim_criterion_skips_the_check
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_live_finding_under_the_named_glob_returns_false
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_no_matching_finding_returns_true
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_refused_spawn_fails_closed
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd::test_close_refuses_when_live_findings_remain_under_the_glob
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd::test_close_succeeds_once_the_glob_is_actually_clean
designated_repro_test: null
threat: null
component: null
---
T-1399 added the `gate_claims_verified` injected-boolean guard clause to `frob.tickets._evidence` (mirrors `own_obligations_clean`'s T-1384 shape exactly) that refuses `done` when an acceptance criterion asserts a package-wide gate outcome ("0 <RULE> findings under <glob>") that the bound evidence does not establish -- but, matching `own_obligations_clean`'s own precedent, the guard has NO live caller yet. Nothing in `frob.app.ticket_runner`'s close path or `frob.tickets._land`'s post-merge reverify computes and injects a real `gate_claims_verified` value, so the guard exists but never fires outside its own unit tests.

This ticket wires it up: compute `gate_claims_verified` by (a) detecting any acceptance criterion matching `frob.tickets._evidence._gate_claim_criteria`'s shape, (b) for each, actually running `frob check --only <gate-family-for-rule>` (or the equivalent `frob.gates` entrypoint) scoped to the named glob, and (c) comparing its reported finding count for that rule id under that glob against the "0" the criterion asserts. Wire the result into both `frob.app.ticket_runner._close_cmd.py`'s `_close_guards_for_ticket` (direct `frob ticket close`) and `frob.tickets._land`'s post-merge verification (mirroring how `own_obligations_clean` and `mutation_evidence` are already wired at both sites).

Likely touches: src/frob/app/ticket_runner/**, src/frob/tickets/_land.py, src/frob/gates/**. NOTE: src/frob/tickets/_land.py is held by T-1390 as of this filing -- coordinate/wait for that lease to clear before starting.