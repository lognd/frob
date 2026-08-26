---
id: T-2918
title: 'Advisory locks degrade to a logged NO-OP without fcntl: concurrent lands/sweeps
  are unserialized on Windows'
state: queued
kind: bug
origin: human
created: '2026-08-25'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: fcntl advisory lock degrade path
  actor: logan
  at: '2026-08-25'
- op: remove
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'starting over: narrow the sweep to exactly the touched fn/tests'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-2918: msvcrt Windows lock backend + loud refusal when neither fcntl nor
    msvcrt exists'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: 'T-2918: msvcrt Windows lock backend + loud refusal when neither fcntl nor
    msvcrt exists'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc anchor for new BaselineLockUnavailable exception
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
