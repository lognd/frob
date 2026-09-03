---
id: T-3728
title: Every land raises a TEST006 stale-stamp coverage-claim quarantine ceremony
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: every land from a worktree raises a TEST006 claim-divergence quarantine on main because main coverage stamp predates the landed tests. Pure ceremony. Fix: land refreshes the stamp itself OR divergence check exempts land-explained TEST006 staleness. Affects frob own land workflow.