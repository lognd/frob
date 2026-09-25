---
id: T-draft-8980afab
title: STORE2xx repo-fact rules
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-5b96fa72
tier: story
sprint: store-family
runs_last: false
milestone: 0.538.0
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 532
  new_length: 670
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Every research row tagged `Static: config` -- a call shape paired with
one schema/config/repo fact (DDL column type, index list, persistence
config file, connection-object identity) read alongside the call site,
still no runtime data needed (DB-PARADIGM-ASSESSMENT.md's tier 2). Every
leaf is blocked by T-STORE-101-SCAFFOLD for the same detection/findings-
function substrate Story 1 uses; leaves needing a schema/config reader
document which file(s) they read in their own body rather than each
re-implementing a DDL/config scan.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
