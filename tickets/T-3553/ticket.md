---
id: T-3553
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3549):
  6 new (rule, file) identit(ies) (ARCH102, ARCH103, LARGE001, OPAQUE001)'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/arch/_mayraise.py
- src/frob/process/_lock.py
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
findings:
- - ARCH102
  - src/frob/process/_lock.py
- - ARCH103
  - src/frob/tickets/_leases.py
- - LARGE001
  - .claude/hooks/root-write-guard.py
- - LARGE001
  - src/frob/arch/_mayraise.py
- - OPAQUE001
  - src/frob/_cli_parsers/_ticket/_metadata.py
- - PII012
  - tests/test_ticket_leases.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3549) at commit a27a4ba5c838d94bcebdaa500fc3d73fd1a1580b found 6 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- ARCH102  src/frob/process/_lock.py
- ARCH103  src/frob/tickets/_leases.py
- LARGE001  .claude/hooks/root-write-guard.py
- LARGE001  src/frob/arch/_mayraise.py
- OPAQUE001  src/frob/_cli_parsers/_ticket/_metadata.py
- PII012  tests/test_ticket_leases.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.