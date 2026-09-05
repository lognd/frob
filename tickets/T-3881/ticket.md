---
id: T-3881
title: 'INV005 burn-down: 1 unwaived finding'
state: queued
kind: bug
origin: agent
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: priority
  old_value: low
  new_value: medium
  reason: trigger ledger mirror to primary checkout
  actor: logan
  at: '2026-09-05'
- field: priority
  old_value: medium
  new_value: medium
  reason: trigger ledger mirror to primary checkout
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3844 burn-down: INV005 carried 1 unwaived warning-level finding on the 2026-09-05 full unscoped frob check --no-cache baseline measured for T-3844 (see that tickets body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This tickets job: drive the live unwaived finding count for INV005 to zero (real fix and/or a reasoned frob:waive entry), then promote INV005 from warn to error in frob.toml [gates.severity] T-1002 managed zone as a follow-up to this same campaign.