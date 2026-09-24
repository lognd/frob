---
id: T-5520
title: 'Curated landing: apply classify_ticket_commits in the land squash (keep 2-7
  real commits, squash bookkeeping)'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-3067
parent: T-3004
tier: ticket
sprint: strata-vmodel
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
scope:
- src/frob/tickets/_land_squash.py
- tests/unit/tickets/test_land_squash.py
- docs/guides/landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
- field: parent
  old_value: null
  new_value: T-3004
  reason: 'T-3004 decomposition: this is the wiring follow-up to T-3067''s curated-landing
    primitive, same strata-vmodel sprint family'
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3067 shipped classify_ticket_commits/_is_bookkeeping_commit
(src/frob/tickets/_land_squash.py) as an UNWIRED primitive, same "prove
it in isolation" posture T-3546's classify_test_then_impl_paths used --
but per owner directive this must not become a second "catalogued is not
enforced" gap. This ticket wires it into the live squash-apply path: a
ticket branch's own commit history is classified via
classify_ticket_commits, every real-work commit is kept individually,
and every bookkeeping commit is squashed into one consolidated trailing
commit instead of today's single-commit fold.

Positive control: a ticket worktree branch with 3 real-work commits and
6 bookkeeping commits (frob ticket start/scope/points/evidence/
done-report writes) lands as exactly 3 real-work commits plus 1
consolidated bookkeeping commit on dev -- never all folded into one, and
never all 9 preserved individually.
