---
id: T-3727
title: GATERULE001 fires on downstream repos own lint rule-ids not waivable (apollo)
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
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
apollo FROBLEMS.md 2026-09-03: GATERULE001 demands PREFIX+digits literals be in _KNOWN_GATE_RULES; downstream lint catalogs (COLOR001/SPACE001) trip it, frob:waive GATERULE001 not honored (T-2448). Fix: apply only to frob own repo or honor downstream rule-id namespace.