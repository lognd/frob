---
id: T-draft-e956923a
title: Review verdict as ticket evidence + strata verification node
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-draft-da74d98d
parent: T-5747
tier: ticket
sprint: layout-gate
runs_last: false
milestone: v0.537.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/tickets/_evidence.py
- docs/strata/vmodel.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
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
Review verdict as ticket evidence (existing --evidence-cmd wiring only, no new machinery) plus a strata verification node at customer-test level in docs/strata/vmodel.md.

Positive control: a ticket bound to a LAYOUT-gated story with an --evidence-cmd pointing at frob gallery verify shows the verdict in frob ticket show; a stale verdict blocks frob check --ticket.

Doc page: docs/strata/vmodel.md#layout-verification-node

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
