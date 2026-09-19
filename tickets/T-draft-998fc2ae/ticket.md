---
id: T-draft-998fc2ae
title: 'frob ticket land loses the compare-and-swap publish race to sibling ledger
  commits (ticket work/scope/accept mirrors) and refuses instead of re-merging and
  retrying: under 5+ agents every third land bounces with ''dev moved away from''
  and DirtyMain'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
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
body_changes:
- mode: set
  reason: coordinator repro
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 974
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Repro 2026-09-19: T-4553 and T-4555 lands each composed for 10+ minutes then refused with "dev moved away from <sha> while this land was composing (a sibling land published first), so the compare-and-swap publish was rejected" followed by "DirtyMain: root checkout has uncommitted changes". The mover was not a sibling land but agents' ledger mirrors (chore(tickets): mirror accept/scope ... from worktree), which T-3612 deliberately allows during a land.

Land should treat a CAS miss as a retry: re-merge the new tip into the staged squash, re-run only the cheap post-merge checks, and republish, bounded by N attempts; and it must leave the root clean on refusal (the DirtyMain that follows is land's own residue).

Acceptance:
GIVEN the land branch advances by a ledger-only commit while a land composes WHEN the publish CAS misses THEN land re-merges and publishes on the next attempt without operator action.
GIVEN a refused land THEN git status in the root is clean.
