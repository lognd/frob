---
id: T-3720
title: ROOT001 remedy prescribes frob:external-reader directive that DSL001 rejects
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
scope:
- src/frob/check/**
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
apollo FROBLEMS.md 2026-09-03: ROOT001's remedy text says to add <!-- frob:external-reader dir="..." reason="..." --> but doing so trips DSL001 'unhandled markdown directive (verb=external-reader): nothing reads it'. A gate remedy that another gate errors on is a trap; scaffold's .github/ and invariants/ ROOT001 warnings are therefore left standing with no clean remedy path. Related to T-3719 (scaffold self-conformance) -- same underlying trap, filed separately since the fix is in the check/DSL layer, not the scaffold templates.