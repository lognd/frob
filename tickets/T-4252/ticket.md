---
id: T-4252
title: 'AFFECT-style check: on ticket close, flag sibling symbols with the same shape
  that still match the PRE-CHANGE form of the symbol just tightened'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consolidates F-327/M-7 (T-4135 sub-epic: one verb's signature was tightened and closed, three sibling verbs in the same file kept the old shape under a docstring describing the new guarantee) with F-386 item 6 (T-4182: a module comment claims both now go through this module but a predates-the-contract sibling symbol was never in scope of the ticket that created it, and no AFFECT/COV edge connects them). Both are the same shape: a ticket's improvement should apply to every sibling with the same pre-change shape, and nothing currently flags the ones left behind. Distinct from T-4075 (binding two independent SPEC-ROW anchors to one invariant for cross-row consistency) -- that is a spec-row pairing mechanism; this is a same-module sibling-signature mechanism, triggered at ticket-close time rather than by an authored invariant. Fixture-testable: YES, frob's own sibling functions are a real fixture.