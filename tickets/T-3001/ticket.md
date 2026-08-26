---
id: T-3001
title: 'Verification debt can never drain under fleet load: the budgeted verify run
  truncates, reports Unmeasurable, and retries forever'
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/*.py
- src/frob/app/_check_chunking.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/verify/test_drain.py
- tests/unit/verify/test_worker.py
- tests/unit/verify/test_backpressure.py
- tests/unit/app/test_check_chunking.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/*.py
  reason: 'drain must succeed under load: budget/backoff fix to the verify drain worker'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/_check_chunking.py
  reason: 'drain must succeed under load: budget/backoff fix to the verify drain worker'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'drain must succeed under load: budget/backoff fix to the verify drain worker'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_drain.py
  reason: 'drain must succeed under load: budget/backoff fix to the verify drain worker'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: 'drain must succeed under load: budget/backoff fix to the verify drain worker'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_backpressure.py
  reason: 'drain must succeed under load: budget/backoff fix to the verify drain worker'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/app/test_check_chunking.py
  reason: 'drain must succeed under load: budget/backoff fix to the verify drain worker'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: unscoped-check helper needs a full/unbudgeted mode for the detached drain
    and frob verify now
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: _unscoped_error_findings doc anchor for the new full/unbudgeted mode
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
