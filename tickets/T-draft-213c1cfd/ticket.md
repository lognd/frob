---
id: T-draft-213c1cfd
title: 'SYS111 ratchet ceilings race every land: a ticket that declares a new via
  site bumps accepted_count against a stale dev count, then dev moves and the land
  refuses with ''grew above the committed ceiling''; the land''s composed-tree check
  must auto-accept growth that is exactly the branch''s own declared via additions
  (same posture as the T-4596 testsuite-glob auto-accept)'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_effects.py
- src/frob/tickets/_land_squash.py
- docs/modules/gate-sys111-ratchet-auto-accept.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_effects.py
  reason: SYS111 auto-accept for branch-own via growth
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: auto-accept path for ratchet ceiling growth (T-4596 posture)
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/modules/gate-sys111-ratchet-auto-accept.md
  reason: standalone doc since docs/modules/gates.md is leased by T-4111
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
