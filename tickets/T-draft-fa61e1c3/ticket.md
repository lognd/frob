---
id: T-draft-fa61e1c3
title: 'land: PreLandUnscopedSweepFailed charges the landing ticket with pre-existing
  DOC006 lines in touched files that its diff never changed'
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
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
- tests/unit/tickets/test_pre_land_sweep_baseline.py
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

F-411: the land's unscoped pre-commit sweep refuses with PreLandUnscopedSweepFailed for a DOC006 finding on a line the ticket's diff never touched, in a file it does touch elsewhere -- a pre-existing finding on main attributed to the land because attribution is per file, not per hunk. Sibling of T-draft-8260bee7 (ClaimDivergence baseline). Deliver: attribution of sweep findings to the landing ticket is by changed HUNK (line ranges from the squash diff), findings outside the ticket's hunks are reported as inherited (warning) with the introducing commit, and never refuse the land; positive control: fixture where main has a DOC006 on line 10 of a file and the ticket changes line 50 -> land proceeds; ticket introduces a pointer on line 50 -> refused.
