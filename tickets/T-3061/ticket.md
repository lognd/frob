---
id: T-3061
title: Put the 2.9s lint gate back on the rapid land path without re-enabling TEST016
  mutation testing
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/check/_python.py
- src/frob/process/parsers/ruff.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: add lint gate to rapid land path (T-3061)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/check/_python.py
  reason: add lint gate to rapid land path (T-3061)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: add lint gate to rapid land path (T-3061)
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
