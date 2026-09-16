---
id: T-draft-5af5584a
title: 'flatten single-child verb groups: agent env, claude sync, natives build, narrative
  move, worktree sweep'
state: queued
kind: ux
origin: agent
created: '2026-09-16'
priority: low
parent: T-2994
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_core.py
- tests/unit/test_cli_single_child_groups.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob agent, frob claude, frob natives, frob narrative, frob worktree
    WHEN invoked without a subverb THEN each runs what its single child ran, and the
    old two-word spelling keeps working as a documented alias for one release
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-16: five groups wrap exactly one child, so the group name carries no information (agent env 75 doc refs, natives build 121). Polish, not bloat removal; do after the group-deletion decision ticket.