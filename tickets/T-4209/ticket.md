---
id: T-4209
title: 'TICK006: require a word boundary before T- so V-model ids (UT-/SIT-/SUBT-/CT-nnnn)
  are not misread as phantom ticket filings'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets
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
Consumer F-322 (T-4135). The ticket-id regex matches inside UT-1516, so a done report naming spec rows (COMP-1514, UT-1516) is reported as claiming a phantom T-1516 filing. Require a word boundary before T-, and read 'filed' claims only from the Filed: line, not anywhere in the report. Fixture-testable: YES.