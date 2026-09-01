---
id: T-3614
title: add --wait mode to ticket write verbs
state: queued
kind: ux
origin: human
created: '2026-08-31'
priority: high
parent: T-3611
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
