---
id: T-3752
title: 'win32 test portability (fcntl class): skipif POSIX fcntl-locking tests'
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
- tests/unit/rapid_sweep_suite/test_baseline.py
- tests/unit/test_process_lock.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/rapid_sweep_suite/test_baseline.py
  reason: 'win32 portability: skipif tests that unconditionally import the POSIX-only
    fcntl module'
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: 'win32 portability: skipif tests that unconditionally import the POSIX-only
    fcntl module'
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'win32 portability: skipif tests that unconditionally import the POSIX-only
    fcntl module'
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
