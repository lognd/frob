---
id: T-3754
title: slow full-repo self-scan tests crash xdist workers on win32 aborting the suite;
  add to heavy grouping or skipif
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_docptr_gate.py
- tests/system/test_fleet_status_ticket_readiness_arch001.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: skipif(win32) the slow full-repo self-scan tests that timeout-crash xdist
    workers on Windows
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/system/test_fleet_status_ticket_readiness_arch001.py
  reason: skipif(win32) the slow full-repo self-scan tests that timeout-crash xdist
    workers on Windows
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
