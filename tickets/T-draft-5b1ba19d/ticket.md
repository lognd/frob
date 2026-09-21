---
id: T-draft-5b1ba19d
title: land --dry-run skips the unscoped pre-land sweep, so a clean dry run is still
  refused by the real land on SELFAUDIT001/DOC004/REG findings
state: queued
kind: ux
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_verify.py
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
Measured 2026-09-20: T-4759 dry run clean, real land refused with 9 self-conformance findings (PreLandUnscopedSweepFailed); T-4114 and T-4115 dry run clean, real land refused with SELFAUDIT001 undeclared capability on a new gate file. The agents' brief requires a clean dry run before READY, and the sized 'frob check --files' that would catch these hangs on the sys stage (T-draft-b2e2c562), so every such refusal costs a serial land slot of 5-10 minutes plus a repair round trip. Fix: --dry-run runs the same unscoped pre-land sweep the real land runs (against the staged merge preview, discarding it afterwards) and reports its findings; or, if that is too slow for a dry run, a --dry-run --sweep flag. Found while coordinating lands.