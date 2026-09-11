---
id: T-3234
title: frob.perf hot-graph collector covers 4 of 9 languages
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: T-1597
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: v1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-1597
  reason: 'pass2 backlog org: theme bucket language'
  actor: logan
  at: '2026-09-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2996 measured frob.perf._collectors._LANGUAGE_ADAPTER_EXTENSIONS covers only python/typescript/rust/kotlin, missing bash/c/cpp/csharp/strata. Measured, not fixed, in T-2996's scope.