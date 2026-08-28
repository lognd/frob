---
id: T-3235
title: frob.policy duplicates frob.lang.extract_imports per-language regex
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/**
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
T-2996 measured frob.policy's per-language import-statement regexes (python/typescript/rust/c/cpp) are a second, parallel implementation of the same axis frob.lang.extract_imports (CAPABILITY_IMPORT_GRAPH) already covers -- a NO-DUPLICATION violation. Measured, not fixed, in T-2996's scope.