---
id: T-4372
title: 'Windows CI Test step time budget: measure per-test/per-file duration and fix
  the measured cause'
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/*.yml
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
T-4269 landed only its acceptance [3] (self-gate step runs on windows even when Test fails, decoupling the two). Acceptance [1] and [2] are carried forward here: the windows Test step still runs 57 minutes against its own ~4500s/80m step budget with little margin (measured: 3,424s of a 64-minute job in one completed run, T-4269's own ticket body has the full step-level decomposition and comparison against ubuntu/macos). Establish where the time goes (per-test/per-file, measured not estimated), then fix the measured cause -- parallelism not applied on this platform, a small number of pathologically slow tests, structurally higher per-test overhead, or genuine extra work. Do not raise the budget as the fix unless measurement shows the work is genuinely that large.