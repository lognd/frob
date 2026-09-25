---
id: T-5386
title: Wire css/scss into capability/dup/docblock FACETS
state: queued
kind: invariant
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: story
sprint: null
runs_last: false
milestone: null
flavour: null
due: null
rank: null
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
- src/frob/lang/_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: tier
  old_value: ticket
  new_value: story
  reason: 'E2 (T-5766, owner decision Q3): reclassify kind:invariant as tier=story;
    evidence-split into a child ticket + kind:invariant retirement deferred to a follow-up
    leaf'
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-5303: css/scss grammars are wired into frob.lang (_EXTENSION_TABLE, _walk_css.py) but not yet into the capability/dup/docblock FACETS registry (_support.py's _PENDING_FACET_WIRING_TICKETS), mirroring zig's T-3513 precedent