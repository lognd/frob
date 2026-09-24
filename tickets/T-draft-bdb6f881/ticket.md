---
id: T-draft-bdb6f881
title: 'frob coord freeze|unfreeze: refuse root ledger writes; the drain is the only
  writer'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob coord freeze | unfreeze: a lock file (.frob/coord-freeze.json with reason and actor) that every root ledger write verb (new, scope, points, promote, drop, milestone, sprint, block, land --queue) refuses against with a named error naming the reason; the drain is the only allowed writer, and splice-scoped writes from the landing worktree remain part of it. Owner decision 2026-09-24: hard refusal, sequenced last because T-5491 and T-5522 already absorb ledger-only drift at publish. Positive control: frozen -> bare land --queue refuses; unfrozen -> succeeds. Replaces the coordinator's freeze broadcasts to agents.
