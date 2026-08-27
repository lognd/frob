---
id: T-3050
title: 'Land H3: DirtyMain auto-heal will auto-commit a false state=done to main --
  it never checks the orphan ticket state'
state: in-progress
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
- src/frob/tickets/_land.py
- tests/test_land*.py
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: refuse non-QUEUED orphan ticket dirs in auto-heal
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_land*.py
  reason: refuse non-QUEUED orphan ticket dirs in auto-heal
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/_land.py
  reason: refuse non-QUEUED orphan ticket dirs in auto-heal
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_land*.py
  reason: refuse non-QUEUED orphan ticket dirs in auto-heal
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/tickets/_land.py
  reason: refuse non-QUEUED orphan ticket dirs in auto-heal
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_land*.py
  reason: refuse non-QUEUED orphan ticket dirs in auto-heal
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
  reason: new must-fire/must-stay-quiet fixtures for the state check
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
