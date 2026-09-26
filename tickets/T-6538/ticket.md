---
id: T-6538
title: 'land: ClaimDivergence charges the landing ticket with findings main already
  had; baseline against pre-land main'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/tickets/_land_verify.py
- src/frob/tickets/_land.py
- tests/unit/tickets/test_claim_divergence_baseline.py
- docs/modules/tickets-landing.md
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
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-403(b): a SELFAUDIT001 finding on docs/design/registry/capability-via-ratchet.lock.json that main ALREADY carried before the land is charged to the landing ticket as ClaimDivergence; refreshing the done-report inside the worktree cannot converge because the worktree does not contain main's change, so the land loops. Deliver: ClaimDivergence compares the post-merge finding set against the PRE-LAND MAIN baseline for the same files and charges the ticket only with the delta; pre-existing findings are reported as inherited (warning), with the commit that introduced them; positive control: fixture where main has a finding in a file the ticket does not touch -> land proceeds; ticket introduces a new one -> refused.
