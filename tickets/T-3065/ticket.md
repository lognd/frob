---
id: T-3065
title: Quarantine finding identities are keyed by literal string equality on a path
  whose shape varies by caller; normalize at write time
state: queued
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
- src/frob/verify/_quarantine.py
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- tests/unit/verify/test_quarantine.py
- tests/unit/verify/test_verify_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/_cli_parsers/_verify.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: normalize quarantine finding path identity at write/dispose time (T-3065)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc closure for touched public symbols
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc anchor collapses whole shared module doc; out of scope for this bugfix
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
