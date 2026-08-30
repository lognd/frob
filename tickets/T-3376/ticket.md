---
id: T-3376
title: Recovered from T-3374's phantom TICK006 citation of T-3365
state: queued
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: TICK006 phantom-cited T-3365's claimed fix (VERSION001/TDD001/VMOD001 missing
    from _KNOWN_GATE_RULES) -- verify against the rule set this claim names
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-3374's Done report claimed T-3365 was filed, but T-3365 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> a DIFFERENT root cause
(REG002: VERSION001/TDD001/VMOD001 missing from _KNOWN_GATE_RULES) that
is already being fixed by another agent's in-progress
T-3365 (leases src/frob/gates/_waive.py) plus queued T-3239 --
left untouched, no collision.