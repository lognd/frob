---
id: T-3837
title: 'F-032: frob ticket evidence --accepts N is 0-indexed and silently accepts
  a wrong index (silent mis-binding)'
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_query.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- tests/test_tickets_evidence_cli.py
- tests/unit/test_ticket_store.py
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: surface for --accepts index validation/display fix
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: surface for --accepts index validation/display fix
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: surface for --accepts index validation/display fix
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: surface for --accepts index validation/display fix
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: surface for --accepts index validation/display fix
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: surface for --accepts index validation/display fix
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: hint text for --accepts also says 0-based, must update with the fix
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
