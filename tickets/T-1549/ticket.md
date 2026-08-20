---
id: T-1549
title: 'Tier-A auto-fix: ClaimDivergence re-run via done-report recap'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_verify.py
- tests/unit/test_land_verify_claim_divergence_sentinel.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'narrowed to the actual fix site: the ClaimDivergence identity comparison
    in _land_verify.py; the auto-fix plan was replaced by a root-cause sentinel filter,
    see Done report'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: 'narrowed to the actual fix site: the ClaimDivergence identity comparison
    in _land_verify.py; the auto-fix plan was replaced by a root-cause sentinel filter,
    see Done report'
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: src/frob/gates/_fix_engine.py
  reason: not building the Tier-A handler; the fix lives entirely in _land_verify.py's
    identity comparison, see Done report for why
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/test_land_verify_claim_divergence_sentinel.py
  reason: not building the Tier-A handler; the fix lives entirely in _land_verify.py's
    identity comparison, see Done report for why
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up from T-1531: a ClaimDivergence land refusal already has a documented manual recipe (re-run the ticket's done-report with its existing why text -- the recap re-measures the claim against current evidence). Wire a Tier-A handler that performs exactly that through the T-1262 verify-or-rollback transaction like every other handler here.