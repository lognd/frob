---
id: T-5815
title: ticket new --points is not persisted
state: in-progress
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob
branch: dev
scope:
- src/frob/tickets/_new_renumber.py
- tests/test_tickets_points.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: fix new_ticket dropping spec.points onto Ticket
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/test_tickets_points.py
  reason: positive-control regression test for the points-persist fix
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/test_tickets_points.py
  reason: positive-control regression test for the points-persist fix
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: document points-persist fix
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket new --points N` accepted the flag but the created ticket
carries `points: null` (measured 2026-09-24 filing the coord tree and the
tiers tree; every filer script had to follow with `frob ticket points`).
Fix: persist points at creation; positive control: new --points 3 then
show must print points 3.
