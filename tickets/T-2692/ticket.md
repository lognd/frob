---
id: T-2692
title: SELFAUDIT001 capability-ratchet debt in design/frob.strata (split from T-2303)
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design
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
Split from T-2303: the `design` capability-ratchet half of that ticket's
findings (SELFAUDIT001 -- 2 undeclared capability effects in test files
plus fs.write via-list on core at 22 sites, above the committed ratchet
ceiling of 21, docs/design/registry/capability-via-ratchet.lock.json)
could not be worked as part of T-2303 because `design/frob.strata`
carries T-1656's LIVE cross-worktree lease -- `frob ticket start`
refused the collision outright. T-2303 itself proceeded scoped to only
its four Python source files (telemetry.py, _land_cmd.py, _new.py,
_rapid_sweep.py).

Re-measure the SELFAUDIT001 finding against current `main` before
starting this (it may already be affected by T-1656's own land), and
coordinate scope with whatever ticket holds `design/frob.strata` at
that time.
