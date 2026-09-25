---
id: T-6390
title: 'SYSDESIGN202: autoscaled service with no local admission-control/load-shedding
  check'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6495
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/sysdesign/_admission.py (new)
- tests/fixtures/sysdesign/sysdesign202/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN202: autoscaled service with no local admission-control/load-shedding check
kind: feature
tier: leaf
parent: T-SYS-SD
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_admission.py (new), docs/modules/gates.md (SYSDESIGN202 row),
       tests/fixtures/sysdesign/sysdesign202/**
blocked_by: []
tag: Static: code

Research row 6.10: Google SRE Book, "Handling Overload", https://sre.google/sre-book/
handling-overload/ -- "As utilization approaches configured thresholds, we start rejecting
requests based on their criticality (higher thresholds for higher criticalities)." Lint
condition: "A service with autoscaling but no local admission-control/load-shedding check
(accepts every request regardless of local utilization) flags."

Cross-reference row 9.3 (observability pairing, filed here as the same rule's second
requirement, not a separate id, per NO DUPLICATION): "A service with load-shedding logic (6.10)
whose utilization signal is not exported as a metric flags (the control exists but is
unobservable)."

Acceptance criteria: code-level detection of a utilization-based admission check (CPU/queue-
depth threshold consulted before accepting work) on a service declared `capacity replicas
2..N` (autoscaling-shaped); flags its absence, and separately flags presence-with-no-exported-
metric (the 9.3 pairing) as a second finding in the same module. Positive-control fixture:
tests/fixtures/sysdesign/sysdesign202/autoscaled-no-admission-check/**.
