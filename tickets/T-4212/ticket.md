---
id: T-4212
title: 'gates evaluate main only: extend SYS/capability audits to run against a worktree/branch,
  and treat an unrunnable check as unmeasured, not clean'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_sys.py
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
Consolidates F-317/M-1, its own addendum F-039-b/T-0297 (both T-4135), and the general dogfooding-blindness class named across every audit epic this session: SYS100 and sibling gates scan main; code that exists only on a parked/feature branch is structurally invisible to them, so a capability grant added or removed there passes with zero signal either way. Extend frob sys audit (and friends) to run against a given worktree/branch explicitly, and make that an accepted, encouraged mode rather than a workaround. Fixture-testable: YES -- create a branch/worktree in frob's own tree with a new capability and confirm SYS gates see it only when pointed at it.