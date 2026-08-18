---
id: T-2379
title: Burn frob-arch WARN findings (god-class/god-module/lock-order/etc) to zero,
  then promote to error
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence: []
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral), tool `frob-arch`, 2026-08-18: 21 WARN-tier findings
across categories unguarded-shared-write, lock-order-cycle, type-dispatch-smell,
god-class, self-join-deadlock, god-module.

These are architecture-smell findings, each requiring real design judgment
(not a mechanical fix) -- treat this as a small campaign: read each finding,
decide the real remediation, and keep the diff scoped to just the flagged
module. Re-measure with the command above before starting; do not hand-count.

Closure is two-part per the epic (T-0969): (1) zero frob-arch WARN findings,
verified the same way, AND (2) frob-arch promoted from warning to error
severity once clean -- do not stop at zero and leave it advisory.
