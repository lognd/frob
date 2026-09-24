---
id: T-draft-a03f18af
title: Vendor crunk's gallery manifest schema for frob-side validation
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: T-5747
tier: ticket
sprint: layout-gate
runs_last: false
milestone: v0.537.0
points: null
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
- src/frob/webapp/_gallery_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: T-draft-3d1557ad
  new_value: T-5747
  reason: re-parent to the promoted story id; story draft was promoted after this
    leaf was filed and the child parent field was not rewritten
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Vendor and pin crunk's gallery manifest JSON schema into frob for frob-side validation.

Positive control: load crunk's fixture manifest through frob's vendored validator; a manifest missing source_hash is rejected identically to crunk's own check.

Doc page: docs/modules/webapp-layout.md#manifest

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
