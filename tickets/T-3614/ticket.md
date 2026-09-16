---
id: T-3614
title: add --wait mode to ticket write verbs
state: queued
kind: ux
origin: human
created: '2026-08-31'
priority: medium
parent: T-3611
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: priority
  old_value: high
  new_value: medium
  reason: 'T-4483 follow-up: TICK004 escalated to error on 2026-09-15 (15d queued
    > 2x the 7d high threshold) and reds every CI leg; these are T-3611 latency-epic
    children, sprint v0.532.0 work behind the v0.531.0 alpha cut, not alpha-path work,
    so medium is the honest priority'
  actor: logan
  at: '2026-09-14'
- field: sprint
  old_value: null
  new_value: v0.532.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Write verbs that hit LandInProgress or a held lock fail instantly
(0.6s), forcing every caller (agents, coordinator, humans) to hand-roll
sleep loops that miss brief open windows. Add `--wait [SECONDS]`
(default off; sensible default budget when given bare) to
new/drop/body/scope/fail/reconcile: block on the contended lock with
backoff + jitter, succeed the moment the window opens, fail loudly with
the holder's identity (pid + ticket) at budget exhaustion. The holder
identity is already computed for the refusal message -- reuse it.
Tests: window opens mid-wait -> success; budget exhausted -> named
holder in the error. Doc: agent briefs stop prescribing sleep loops.
