---
id: T-draft-b2e2c562
title: 'frob check: the sys stage takes 1268s of a 1900s root check and --files scoping
  does not skip it, so every sized agent check hangs past 10 minutes under fleet load'
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_sys.py
- src/frob/check/_python.py
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
Measured 2026-09-20 on the root check: gate-summary timings sys=1267.71s, affect_drift=337.77s, wire=260.50s, tickets=248.26s, archgate=54.46s; total wall time about 32 minutes. Five implementer agents in the same evening reported 'frob check --files <2-4 files>' (also with --only gates) hanging past a 10-minute cap on 2-3 consecutive attempts and gave up, so the pre-land sized check is unmeasurable under fleet load and lands are refused later by the unscoped pre-land sweep instead (T-4759 today: 9 self-conformance findings a clean dry run never showed). Fix: (1) --files must scope or skip the sys stage (the strata design-quality self-audit is not a per-file check; cache its result keyed on the strata files' digest and reuse when they are untouched); (2) profile the sys stage itself, 21 minutes for 614k rule fires is the N+1 shape T-5135 catalogues; (3) frob check prints per-stage elapsed time as it goes so a 20-minute stage is visible instead of read as a hang. Found while coordinating the warning drain.