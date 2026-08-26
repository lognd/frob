---
id: T-2918
title: 'Advisory locks degrade to a logged NO-OP without fcntl: concurrent lands/sweeps
  are unserialized on Windows'
state: done
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
- tickets/archive/T-2595/ticket.md
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
- op: add
  glob: tickets/archive/T-2595/ticket.md
  reason: rebound T-2595 evidence id after renaming its no-fcntl test (test deletion/rename
    must not orphan another ticket evidence)
  actor: logan
  at: '2026-08-25'
evidence:
- tests/unit/test_rapid_sweep.py::TestBaselineLock::test_no_lock_primitive_refuses_loudly
- tests/unit/test_rapid_sweep.py::TestBaselineLock::test_windows_backend_serializes_two_concurrent_holders
- tests/unit/test_rapid_sweep.py::TestBaselineLock::test_serializes_two_concurrent_holders
designated_repro_test: tests/unit/test_rapid_sweep.py::TestBaselineLock::test_no_lock_primitive_refuses_loudly
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
