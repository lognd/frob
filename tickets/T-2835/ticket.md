---
id: T-2835
title: Evaluate real decomposition seams for _close_cmd/_land_cmd/_lifecycle (ticket_runner)
state: queued
kind: docs
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
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
Found while working T-2830/T-2829 (LARGE001 burn-down batch). These three ticket_runner command-family modules are large (1756/5528/1438 lines) and each has candidate internal clusters (close/land shared obligation predicates; lifecycle worktree-provisioning helpers that cross-call _start) that LOOK like seams but were not split under T-2830/T-2829 because: (1) the obligation predicates in _close_cmd are reused verbatim by _land_cmd, so moving them changes an import path without changing coupling; (2) the lifecycle worktree helpers cross-call _start, so a naive module split would be circular; (3) _land_cmd.py in particular is the landing critical path every agent depends on, and T-2830's own dispatch brief was explicit that a rushed split there is worse than the warning. This ticket is scoped to actually design a real split (e.g. extracting shared obligation predicates to frob.tickets, or restructuring _start's coupling so worktree provisioning can stand alone) with proper test coverage, not to grind LARGE001 mechanically.