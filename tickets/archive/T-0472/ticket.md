---
id: T-0472
title: 'frob ticket requeue/unstart: no CLI command exists for the state-machine-legal
  in-progress->queued transition (plan/block/close/fail only) -- a parked/mis-started
  ticket cannot be honestly requeued without hand-editing; add the command (releases
  the T-0453 lease)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/__main__.py
- docs/modules/tickets.md
- tests/test_app.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_app.py
  reason: T-0472 app work maps to tests/test_app.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: T-0455 hygiene pass pinned tests/test_app.py, a file that does not exist;
    the real sibling convention for this CLI command (TestTicketStart) already lives
    in tests/unit/test_app_runners_batch7.py, so TestTicketRequeue belongs there
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketRequeue::test_missing_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRequeue::test_unknown_id_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRequeue::test_requeue_success
- tests/unit/test_app_runners_batch7.py::TestTicketRequeue::test_requeue_not_in_progress_exits_1
designated_repro_test: null
threat: null
component: null
---
