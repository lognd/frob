---
id: T-6541
title: 'frob upgrade turns a green main red: version-bump baseline for new rules,
  COV003 must not re-grade closed tickets, stale sweep misattribution'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
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
- src/frob/gates/_coverage.py
- src/frob/gates/_baseline.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/gates/test_upgrade_baseline.py
- docs/guides/install.md
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

F-397: after installing 0.531.1.dev329 on a tree that was clean at 0.530.0, `frob check` reports 1013 errors: TEST010 (~600, production-side frob:tests now 'redundant' under T-4710), COV003 (~345, closed feature tickets' `cmd:` evidence rejected retroactively), SELFAUDIT001 (36). A stale post-land sweep then attributed the findings to the last landed ticket (T-0414). Deliver: (a) a version-bump baseline -- when the frob version that last wrote the baseline is older, new rule families enter as warnings with a migration ticket auto-filed (`frob check --since-frob <ver>` or the auto-ratchet pool), so an upgrade never flips a green main red by itself; (b) COV003 and other retroactive rules never re-grade tickets in state done; (c) the post-land sweep attributes only findings in the landed diff's hunks to the landed ticket and files the rest against a migration ticket; positive control: fixture baseline at an old version + new rule -> warning + migration ticket, closed ticket with `cmd:` evidence stays green.
