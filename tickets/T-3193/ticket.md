---
id: T-3193
title: Split _squash_apply_on_disposable_stage's warm-stage branch into a helper
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
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
T-3176's own scope: T-3135 extended _squash_apply_on_disposable_stage with a ~147-line warm-stage ensure/compose/fallback branch (waived ARCH001 there, follow_up=T-3176). Splitting that branch into its own helper is real function-extraction work -- there is no existing named symbol to relocate, so frob refactor split (a mechanical symbol-to-module move) does not apply; this needs an actual extract-function refactor, done carefully since T-3121/T-3127's own tests and comments reference _squash_apply_on_disposable_stage by exact line/symbol identity. T-3176 did the doc half (docs/modules/tickets-landing.md#the-t-3135-warm-sweep-stage) and left this split for its own ticket rather than half-doing it under one scope.